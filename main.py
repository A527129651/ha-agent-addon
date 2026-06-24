"""
HA Agent Add-on Backend
Runs inside Home Assistant as an Add-on.
Communicates with HA via Supervisor API (no token needed from user).
"""

import os, json, re, asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx

app = FastAPI(title="HA Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Inside addon: HA credentials come from environment ──────────────────────
# SUPERVISOR_TOKEN is injected automatically by HA Supervisor
HA_URL         = os.getenv("HA_URL", "http://supervisor/core")
HA_TOKEN       = os.getenv("SUPERVISOR_TOKEN", os.getenv("HA_TOKEN", ""))
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")

# ─── HA API helpers ───────────────────────────────────────────────────────────
async def ha_get(path: str):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{HA_URL.rstrip('/')}{path}",
            headers={"Authorization": f"Bearer {HA_TOKEN}"}
        )
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        return r.json() if "application/json" in ct else r.text

async def ha_post(path: str, body: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{HA_URL.rstrip('/')}{path}",
            json=body,
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
        )
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        return r.json() if "application/json" in ct else r.text

# ─── Deep snapshot ────────────────────────────────────────────────────────────
async def build_snapshot() -> dict:
    results = await asyncio.gather(
        ha_get("/api/states"),
        ha_get("/api/config"),
        ha_get("/api/error_log"),
        ha_get("/api/services"),
        return_exceptions=True
    )
    states    = results[0] if isinstance(results[0], list) else []
    cfg       = results[1] if isinstance(results[1], dict) else {}
    error_log = results[2] if isinstance(results[2], str)  else ""
    services  = results[3] if isinstance(results[3], list) else []

    now = datetime.utcnow()

    by_domain: dict = {}
    for s in states:
        d = s["entity_id"].split(".")[0]
        by_domain.setdefault(d, []).append(s)

    automations = by_domain.get("automation", [])
    scripts     = by_domain.get("script", [])
    sensors     = by_domain.get("sensor", [])

    unavailable = [
        {"entity_id": s["entity_id"], "state": s["state"], "last_changed": s.get("last_changed")}
        for s in states if s["state"] in ("unavailable", "unknown")
    ]

    stuck = []
    for s in sensors:
        lc = s.get("last_changed", "")
        try:
            age = now - datetime.fromisoformat(lc.replace("Z", "+00:00")).replace(tzinfo=None)
            if age > timedelta(hours=24):
                stuck.append({
                    "entity_id":     s["entity_id"],
                    "state":         s["state"],
                    "hours_stuck":   round(age.total_seconds() / 3600),
                    "friendly_name": s.get("attributes", {}).get("friendly_name", ""),
                })
        except Exception:
            pass

    idle_scripts = []
    for s in scripts:
        lt   = s.get("attributes", {}).get("last_triggered")
        name = s.get("attributes", {}).get("friendly_name", s["entity_id"])
        if not lt:
            idle_scripts.append({"entity_id": s["entity_id"], "friendly_name": name, "last_triggered": "מעולם"})
        else:
            try:
                age = now - datetime.fromisoformat(lt.replace("Z", "+00:00")).replace(tzinfo=None)
                if age > timedelta(days=30):
                    idle_scripts.append({"entity_id": s["entity_id"], "friendly_name": name,
                                          "last_triggered": lt, "days_ago": age.days})
            except Exception:
                pass

    auto_data = [
        {"entity_id": a["entity_id"],
         "name": a.get("attributes", {}).get("friendly_name", a["entity_id"]),
         "state": a["state"],
         "last_triggered": a.get("attributes", {}).get("last_triggered")}
        for a in automations
    ]
    name_groups: dict = {}
    for a in auto_data:
        key = re.sub(r'[\s_\-]+\d+$', '', a["name"].lower().strip())
        name_groups.setdefault(key, []).append(a)
    duplicates = [g for g in name_groups.values() if len(g) > 1]

    log_lines     = error_log.split("\n") if error_log else []
    error_lines   = [l for l in log_lines if "ERROR"   in l][-40:]
    warning_lines = [l for l in log_lines if "WARNING" in l][-30:]

    return {
        "summary": {
            "location_name":         cfg.get("location_name", "?"),
            "version":               cfg.get("version", "?"),
            "total_entities":        len(states),
            "automations":           len(automations),
            "scripts":               len(scripts),
            "sensors":               len(sensors),
            "unavailable":           len(unavailable),
            "stuck_sensors":         len(stuck),
            "idle_scripts":          len(idle_scripts),
            "duplicate_automations": len(duplicates),
            "errors_in_log":         len(error_lines),
            "warnings_in_log":       len(warning_lines),
        },
        "automations":             auto_data,
        "scripts":                 [{"entity_id": s["entity_id"],
                                     "friendly_name": s.get("attributes",{}).get("friendly_name"),
                                     "last_triggered": s.get("attributes",{}).get("last_triggered")} for s in scripts],
        "unavailable_entities":    unavailable,
        "stuck_sensors":           stuck,
        "idle_scripts":            idle_scripts,
        "duplicate_automations":   duplicates,
        "domains":                 {k: len(v) for k, v in by_domain.items()},
        "service_domains":         list({s.get("domain") for s in services if isinstance(s, dict)}),
        "error_log_errors":        error_lines,
        "error_log_warnings":      warning_lines,
        "all_entity_ids":          [s["entity_id"] for s in states],
    }

# ─── Claude ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an elite Home Assistant AI agent. Always speak Hebrew.

You have LIVE data from the user's Home Assistant system in the snapshot below.
Use specific entity IDs and numbers from it. Be precise and technical.

## CRITICAL RULE — CONFIRM BEFORE EVERY ACTION
1. Analyze and explain findings clearly
2. Say EXACTLY: "מצאתי פתרון. לבצע?"
3. Wait for "כן" / "בצע" / "אישור"
4. Only then output the action JSON block

## ACTION FORMAT (only after confirmation)
```action
{
  "type": "call_service",
  "domain": "automation",
  "service": "turn_off",
  "entity_id": "automation.example",
  "data": {}
}
```
For YAML creation:
```action
{
  "type": "yaml_output",
  "filename": "automations.yaml",
  "yaml": "- alias: My Automation\\n  trigger: ..."
}
```

## SEVERITY: 🔴 קריטי | 🟡 בינוני | 🟢 נמוך

## ANALYSIS
- "למה HA איטי" → errors, unavailable entities, heavy domains, warnings
- "מצא אוטומציות כפולות" → duplicate_automations
- "מצא חיישנים תקועים" → stuck_sensors (hours_stuck)
- "מצא סקריפטים שלא הופעלו" → idle_scripts
- "נתח לוגים" → error_log_errors + error_log_warnings
- "מצא ישויות לא זמינות" → unavailable_entities"""

async def call_claude(messages: list, snapshot: dict) -> str:
    key = ANTHROPIC_KEY
    if not key:
        raise ValueError("Anthropic API Key לא מוגדר — הגדר ב-Add-on Configuration")

    snap_str = json.dumps(snapshot, ensure_ascii=False, indent=2)
    if len(snap_str) > 8000:
        trimmed = {
            "summary":               snapshot["summary"],
            "unavailable_entities":  snapshot["unavailable_entities"],
            "stuck_sensors":         snapshot["stuck_sensors"],
            "idle_scripts":          snapshot["idle_scripts"],
            "duplicate_automations": snapshot["duplicate_automations"],
            "error_log_errors":      snapshot["error_log_errors"][-20:],
            "error_log_warnings":    snapshot["error_log_warnings"][-10:],
            "domains":               snapshot["domains"],
            "automation_names":      [a["name"] for a in snapshot["automations"]][:60],
        }
        snap_str = json.dumps(trimmed, ensure_ascii=False, indent=2)

    system = SYSTEM_PROMPT + f"\n\n## LIVE SYSTEM SNAPSHOT\n```json\n{snap_str}\n```"

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         key,
                "anthropic-version": "2023-06-01",
                "Content-Type":      "application/json",
            },
            json={
                "model":      "claude-sonnet-4-6",
                "max_tokens": 2048,
                "system":     system,
                "messages":   messages,
            }
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []))

# ─── Action executor ──────────────────────────────────────────────────────────
async def execute_action(action: dict) -> dict:
    atype = action.get("type")
    if atype == "call_service":
        domain = action["domain"]
        service = action["service"]
        data = action.get("data", {})
        if action.get("entity_id"):
            data["entity_id"] = action["entity_id"]
        result = await ha_post(f"/api/services/{domain}/{service}", data)
        return {"ok": True, "result": result}
    elif atype == "yaml_output":
        return {"ok": True, "yaml": action.get("yaml"),
                "filename": action.get("filename"),
                "message": "YAML מוכן — העתק לקובץ הנכון ב-HA"}
    return {"ok": False, "error": f"Unknown action: {atype}"}

# ─── Models ───────────────────────────────────────────────────────────────────
class AskReq(BaseModel):
    messages: list
    snapshot: Optional[dict] = None

class ActionReq(BaseModel):
    action: dict

class ServiceReq(BaseModel):
    domain:  str
    service: str
    data:    dict = {}

# ─── API Routes ───────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "ha_url": HA_URL, "has_key": bool(ANTHROPIC_KEY)}

@app.get("/api/snapshot")
async def snapshot():
    try:
        snap = await build_snapshot()
        return {"ok": True, "snapshot": snap}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/ask")
async def ask(req: AskReq):
    try:
        snapshot = req.snapshot or await build_snapshot()
        reply    = await call_claude(req.messages, snapshot)
        return {"ok": True, "reply": reply}
    except httpx.HTTPStatusError as e:
        raise HTTPException(400, f"Claude API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/execute")
async def execute(req: ActionReq):
    try:
        result = await execute_action(req.action)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/service")
async def call_service(req: ServiceReq):
    try:
        result = await ha_post(f"/api/services/{req.domain}/{req.service}", req.data)
        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/logs")
async def logs():
    try:
        log   = await ha_get("/api/error_log")
        lines = log.split("\n") if isinstance(log, str) else []
        return {
            "ok":       True,
            "errors":   [l for l in lines if "ERROR"   in l][-50:],
            "warnings": [l for l in lines if "WARNING" in l][-50:],
        }
    except Exception as e:
        raise HTTPException(400, str(e))

# ─── Serve React frontend (built) ─────────────────────────────────────────────
import os as _os
_frontend = "/app/frontend/dist"
if _os.path.exists(_frontend):
    app.mount("/assets", StaticFiles(directory=f"{_frontend}/assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(f"{_frontend}/index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        f = f"{_frontend}/{full_path}"
        if _os.path.exists(f):
            return FileResponse(f)
        return FileResponse(f"{_frontend}/index.html")
