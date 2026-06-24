import os, json, re, asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HA_URL        = os.getenv("HA_URL", "http://supervisor/core")
HA_TOKEN      = os.getenv("SUPERVISOR_TOKEN", os.getenv("HA_TOKEN", ""))
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

async def ha_get(path):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{HA_URL.rstrip('/')}{path}", headers={"Authorization": f"Bearer {HA_TOKEN}"})
        r.raise_for_status()
        return r.json() if "application/json" in r.headers.get("content-type","") else r.text

async def ha_post(path, body):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{HA_URL.rstrip('/')}{path}", json=body,
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"})
        r.raise_for_status()
        return r.json() if "application/json" in r.headers.get("content-type","") else r.text

async def build_snapshot():
    results = await asyncio.gather(
        ha_get("/api/states"), ha_get("/api/config"),
        ha_get("/api/error_log"), ha_get("/api/services"),
        return_exceptions=True)
    states    = results[0] if isinstance(results[0], list) else []
    cfg       = results[1] if isinstance(results[1], dict) else {}
    error_log = results[2] if isinstance(results[2], str)  else ""
    services  = results[3] if isinstance(results[3], list) else []
    now = datetime.utcnow()
    by_domain = {}
    for s in states:
        d = s["entity_id"].split(".")[0]
        by_domain.setdefault(d, []).append(s)
    automations = by_domain.get("automation", [])
    scripts     = by_domain.get("script", [])
    sensors     = by_domain.get("sensor", [])
    unavailable = [{"entity_id":s["entity_id"],"state":s["state"],"last_changed":s.get("last_changed")}
                   for s in states if s["state"] in ("unavailable","unknown")]
    stuck = []
    for s in sensors:
        try:
            age = now - datetime.fromisoformat(s.get("last_changed","").replace("Z","+00:00")).replace(tzinfo=None)
            if age > timedelta(hours=24):
                stuck.append({"entity_id":s["entity_id"],"state":s["state"],
                              "hours_stuck":round(age.total_seconds()/3600),
                              "friendly_name":s.get("attributes",{}).get("friendly_name","")})
        except: pass
    idle_scripts = []
    for s in scripts:
        lt = s.get("attributes",{}).get("last_triggered")
        name = s.get("attributes",{}).get("friendly_name", s["entity_id"])
        if not lt:
            idle_scripts.append({"entity_id":s["entity_id"],"friendly_name":name,"last_triggered":"מעולם"})
        else:
            try:
                age = now - datetime.fromisoformat(lt.replace("Z","+00:00")).replace(tzinfo=None)
                if age > timedelta(days=30):
                    idle_scripts.append({"entity_id":s["entity_id"],"friendly_name":name,"days_ago":age.days})
            except: pass
    auto_data = [{"entity_id":a["entity_id"],
                  "name":a.get("attributes",{}).get("friendly_name",a["entity_id"]),
                  "state":a["state"],"last_triggered":a.get("attributes",{}).get("last_triggered")}
                 for a in automations]
    ng = {}
    for a in auto_data:
        k = re.sub(r'[\s_\-]+\d+$','',a["name"].lower().strip())
        ng.setdefault(k,[]).append(a)
    duplicates = [g for g in ng.values() if len(g)>1]
    log_lines     = error_log.split("\n") if error_log else []
    error_lines   = [l for l in log_lines if "ERROR"   in l][-40:]
    warning_lines = [l for l in log_lines if "WARNING" in l][-30:]
    return {
        "summary": {
            "location_name":cfg.get("location_name","?"),"version":cfg.get("version","?"),
            "total_entities":len(states),"automations":len(automations),
            "scripts":len(scripts),"sensors":len(sensors),
            "unavailable":len(unavailable),"stuck_sensors":len(stuck),
            "idle_scripts":len(idle_scripts),"duplicate_automations":len(duplicates),
            "errors_in_log":len(error_lines),"warnings_in_log":len(warning_lines),
        },
        "automations":auto_data,
        "scripts":[{"entity_id":s["entity_id"],"friendly_name":s.get("attributes",{}).get("friendly_name"),
                    "last_triggered":s.get("attributes",{}).get("last_triggered")} for s in scripts],
        "unavailable_entities":unavailable,"stuck_sensors":stuck,
        "idle_scripts":idle_scripts,"duplicate_automations":duplicates,
        "domains":{k:len(v) for k,v in by_domain.items()},
        "service_domains":list({s.get("domain") for s in services if isinstance(s,dict)}),
        "error_log_errors":error_lines,"error_log_warnings":warning_lines,
        "all_entity_ids":[s["entity_id"] for s in states],
    }

SYSTEM_PROMPT = """You are an elite Home Assistant AI agent. Always speak Hebrew.
Use LIVE data from the snapshot. Be precise with real entity IDs and numbers.

CRITICAL: Before any change:
1. Explain findings clearly
2. Say EXACTLY: "מצאתי פתרון. לבצע?"
3. Only after "כן"/"בצע"/"אישור" → output action JSON

ACTION FORMAT (after confirmation only):
```action
{"type":"call_service","domain":"automation","service":"turn_off","entity_id":"automation.xxx","data":{}}
```
For YAML creation:
```action
{"type":"yaml_output","filename":"automations.yaml","yaml":"..."}
```
SEVERITY: 🔴 קריטי | 🟡 בינוני | 🟢 נמוך"""

async def call_claude(messages, snapshot):
    if not ANTHROPIC_KEY:
        raise ValueError("Anthropic API Key לא מוגדר — הגדר ב-Add-on Configuration")
    snap = json.dumps(snapshot, ensure_ascii=False, indent=2)
    if len(snap) > 8000:
        snap = json.dumps({"summary":snapshot["summary"],
            "unavailable_entities":snapshot["unavailable_entities"],
            "stuck_sensors":snapshot["stuck_sensors"],"idle_scripts":snapshot["idle_scripts"],
            "duplicate_automations":snapshot["duplicate_automations"],
            "error_log_errors":snapshot["error_log_errors"][-20:],
            "domains":snapshot["domains"],
            "automation_names":[a["name"] for a in snapshot["automations"]][:60]},
            ensure_ascii=False, indent=2)
    system = SYSTEM_PROMPT + f"\n\n## LIVE SNAPSHOT\n```json\n{snap}\n```"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-6","max_tokens":2048,"system":system,"messages":messages})
        r.raise_for_status()
        return "".join(b.get("text","") for b in r.json().get("content",[]))

async def execute_action(action):
    if action.get("type") == "call_service":
        data = action.get("data", {})
        if action.get("entity_id"): data["entity_id"] = action["entity_id"]
        result = await ha_post(f"/api/services/{action['domain']}/{action['service']}", data)
        return {"ok":True,"result":result,"message":"הפעולה בוצעה בהצלחה!"}
    elif action.get("type") == "yaml_output":
        return {"ok":True,"yaml":action.get("yaml"),"filename":action.get("filename"),
                "message":"YAML מוכן — העתק לקובץ הנכון ב-HA"}
    return {"ok":False,"error":"Unknown action"}

class AskReq(BaseModel):
    messages: list
    snapshot: Optional[dict] = None

class ActionReq(BaseModel):
    action: dict

class ServiceReq(BaseModel):
    domain: str; service: str; data: dict = {}

@app.get("/api/health")
def health():
    return {"status":"ok","has_key":bool(ANTHROPIC_KEY)}

@app.get("/api/snapshot")
async def get_snapshot():
    try:
        return {"ok":True,"snapshot": await build_snapshot()}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/ask")
async def ask(req: AskReq):
    try:
        snap = req.snapshot or await build_snapshot()
        reply = await call_claude(req.messages, snap)
        return {"ok":True,"reply":reply}
    except httpx.HTTPStatusError as e:
        raise HTTPException(400, f"Claude API: {e.response.text}")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/execute")
async def execute(req: ActionReq):
    try:
        return await execute_action(req.action)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/service")
async def svc(req: ServiceReq):
    try:
        return {"ok":True,"result": await ha_post(f"/api/services/{req.domain}/{req.service}", req.data)}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Serve static HTML (no build needed!) ──────────────────────────────────────
_fe = "/app/frontend"
if os.path.exists(_fe):
    @app.get("/")
    async def idx(): return FileResponse(f"{_fe}/index.html")
    app.mount("/", StaticFiles(directory=_fe, html=True), name="frontend")
