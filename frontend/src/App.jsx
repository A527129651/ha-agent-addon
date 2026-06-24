import { useState, useRef, useEffect } from "react";
const QUICK=["למה Home Assistant איטי?","מצא אוטומציות כפולות","מצא חיישנים תקועים","מצא סקריפטים שלא הופעלו חודש","נתח את הלוגים","מצא ישויות לא זמינות","הצע אופטימיזציות","בדוק קונפליקטים"];
function parseAction(t){const m=t.match(/```action\n([\s\S]*?)```/);if(!m)return null;try{return JSON.parse(m[1]);}catch{return null;}}
function stripAction(t){return t.replace(/```action\n[\s\S]*?```/g,"").trim();}
function Dots(){return(<div style={{display:"flex",gap:5,padding:"10px 4px"}}>{[0,1,2].map(i=>(<div key={i} style={{width:7,height:7,borderRadius:"50%",background:"#38bdf8",animation:`blink 1.2s ease-in-out ${i*.2}s infinite`}}/>))}<style>{`@keyframes blink{0%,100%{opacity:.3;transform:scale(.8)}50%{opacity:1;transform:scale(1)}}`}</style></div>);}
function Code({lang,code}){const[c,setC]=useState(false);return(<div style={{margin:"10px 0",borderRadius:10,overflow:"hidden",border:"1px solid #1e293b"}}><div style={{background:"#0f172a",padding:"5px 14px",display:"flex",justifyContent:"space-between",alignItems:"center"}}><span style={{fontSize:11,color:"#475569",fontFamily:"monospace"}}>{lang||"code"}</span><button onClick={()=>{navigator.clipboard.writeText(code);setC(true);setTimeout(()=>setC(false),1800);}} style={{background:"none",border:"none",color:c?"#34d399":"#475569",fontSize:11,cursor:"pointer"}}>{c?"✓ הועתק":"העתק"}</button></div><pre style={{background:"#090e1a",margin:0,padding:"12px 14px",overflowX:"auto",fontSize:12.5,color:"#7dd3fc",fontFamily:"'Fira Code','Courier New',monospace",lineHeight:1.65,direction:"ltr",textAlign:"left"}}>{code}</pre></div>);}
function Fmt({content}){const parts=content.split(/(```[\s\S]*?```)/g);return<>{parts.map((p,i)=>{if(p.startsWith("```")){const lines=p.slice(3).split("\n");const lang=lines[0].trim();const code=lines.slice(1).join("\n").replace(/```$/,"").trim();if(lang==="action")return null;return<Code key={i} lang={lang} code={code}/>;}return<span key={i} style={{whiteSpace:"pre-wrap"}}>{p}</span>;})}</>;}
function ActionPanel({action,onExec,exec}){const desc=action.type==="call_service"?`${action.domain}.${action.service}${action.entity_id?" → "+action.entity_id:""}`:`יצירת ${action.filename}`;return(<div style={{margin:"12px 0",padding:"14px 16px",background:"linear-gradient(135deg,#0f2a4a,#0f1a4a)",border:"1px solid #38bdf8",borderRadius:12}}><div style={{fontSize:10,color:"#38bdf8",fontWeight:700,letterSpacing:1.2,marginBottom:8}}>⚡ פעולה ממתינה לאישור</div><div style={{fontSize:13,color:"#cbd5e1",marginBottom:12,direction:"rtl"}}><strong>סוג:</strong> {action.type}<br/><strong>פרטים:</strong> {desc}</div><div style={{display:"flex",gap:8}}><button onClick={onExec} disabled={exec} style={{padding:"8px 20px",borderRadius:8,border:"none",background:exec?"#1e293b":"linear-gradient(135deg,#0ea5e9,#6366f1)",color:exec?"#475569":"#fff",fontSize:13,fontWeight:700,cursor:exec?"wait":"pointer"}}>{exec?"מבצע...":"✓ בצע"}</button></div></div>);}
function Msg({msg,onExec,executing}){const isUser=msg.role==="user";const action=!isUser?parseAction(msg.content):null;const text=action?stripAction(msg.content):msg.content;const isC=!isUser&&msg.content.includes("מצאתי פתרון. לבצע?");return(<div style={{display:"flex",justifyContent:isUser?"flex-end":"flex-start",marginBottom:18}}>{!isUser&&<div style={{width:36,height:36,borderRadius:10,flexShrink:0,marginRight:10,marginTop:3,background:"linear-gradient(135deg,#0ea5e9,#6366f1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>🏠</div>}<div style={{maxWidth:"80%"}}><div style={{padding:"12px 16px",borderRadius:isUser?"18px 18px 4px 18px":"18px 18px 18px 4px",background:isUser?"linear-gradient(135deg,#0ea5e9,#6366f1)":isC?"linear-gradient(135deg,#0f2a4a,#0f1a4a)":"#1a2540",color:"#f1f5f9",fontSize:14.5,lineHeight:1.75,border:isC?"1px solid #38bdf8":"1px solid #243046",direction:"rtl",textAlign:"right",fontFamily:"'Segoe UI',system-ui,sans-serif"}}>{isC&&<div style={{fontSize:10,color:"#38bdf8",marginBottom:6,fontWeight:700,letterSpacing:1.2}}>⚡ ממתין לאישורך</div>}<Fmt content={text}/></div>{action&&<ActionPanel action={action} onExec={()=>onExec(action)} exec={executing}/>}{msg.execResult&&<div style={{marginTop:8,padding:"10px 14px",borderRadius:10,background:msg.execResult.ok?"rgba(52,211,153,.08)":"rgba(239,68,68,.08)",border:`1px solid ${msg.execResult.ok?"rgba(52,211,153,.3)":"rgba(239,68,68,.3)"}`,fontSize:13,color:msg.execResult.ok?"#6ee7b7":"#fca5a5",direction:"rtl"}}>{msg.execResult.ok?"✅ ":"❌ "}{msg.execResult.message||(msg.execResult.ok?"בוצע!":"שגיאה")}{msg.execResult.yaml&&<Code lang={msg.execResult.filename} code={msg.execResult.yaml}/>}</div>}</div></div>);}
function Badge({icon,label,value,warn}){return(<div style={{background:"#111827",border:`1px solid ${warn&&value>0?"#854d0e":"#1e2d45"}`,borderRadius:10,padding:"8px 14px",display:"flex",alignItems:"center",gap:8,flexShrink:0}}><span style={{fontSize:18}}>{icon}</span><div><div style={{fontSize:17,fontWeight:700,color:warn&&value>0?"#fbbf24":"#f1f5f9",lineHeight:1}}>{value}</div><div style={{fontSize:10,color:"#64748b",marginTop:2}}>{label}</div></div></div>);}
export default function App(){
  const[snap,setSnap]=useState(null);const[loading,setLoading]=useState(true);const[err,setErr]=useState("");
  const[msgs,setMsgs]=useState([]);const[input,setInput]=useState("");const[sending,setSending]=useState(false);const[executing,setExecuting]=useState(false);
  const bottomRef=useRef(null);const taRef=useRef(null);
  useEffect(()=>{
    fetch("/api/snapshot").then(r=>r.json()).then(d=>{
      if(d.ok){setSnap(d.snapshot);const s=d.snapshot.summary;
        setMsgs([{role:"assistant",content:`✅ HA Agent מחובר!\n\n**${s.location_name}** · גרסה ${s.version}\n\n📊 **סקירה:**\n• ${s.total_entities} entities\n• ${s.automations} אוטומציות · ${s.scripts} סקריפטים · ${s.sensors} חיישנים\n${s.unavailable>0?`• 🔴 ${s.unavailable} לא זמינים`:"• ✅ הכל זמין"}${s.stuck_sensors>0?`\n• 🟡 ${s.stuck_sensors} חיישנים תקועים`:""}${s.idle_scripts>0?`\n• 🟡 ${s.idle_scripts} סקריפטים לא פעילים`:""}${s.duplicate_automations>0?`\n• 🟡 ${s.duplicate_automations} כפולות`:""}${s.errors_in_log>0?`\n• 🔴 ${s.errors_in_log} שגיאות בלוג`:""}\n\nמה תרצה לנתח?`}]);}
      else setErr(d.detail||"שגיאה");
    }).catch(e=>setErr(e.message)).finally(()=>setLoading(false));
  },[]);
  useEffect(()=>{bottomRef.current?.scrollIntoView({behavior:"smooth"});},[msgs,sending]);
  const refresh=()=>{fetch("/api/snapshot").then(r=>r.json()).then(d=>{if(d.ok)setSnap(d.snapshot);});};
  const send=async(text)=>{
    const t=(text||input).trim();if(!t||sending)return;
    setInput("");if(taRef.current)taRef.current.style.height="48px";
    const userMsg={role:"user",content:t};const newMsgs=[...msgs,userMsg];setMsgs(newMsgs);setSending(true);
    try{const r=await fetch("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({messages:newMsgs.map(m=>({role:m.role,content:m.content})),snapshot:snap})});
      const d=await r.json();if(!r.ok)throw new Error(d.detail||r.statusText);
      setMsgs(p=>[...p,{role:"assistant",content:d.reply}]);}
    catch(e){setMsgs(p=>[...p,{role:"assistant",content:`❌ שגיאה: ${e.message}`}]);}
    setSending(false);};
  const execAction=async(action)=>{
    setExecuting(true);
    try{const r=await fetch("/api/execute",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action})});
      const result=await r.json();
      setMsgs(prev=>{const copy=[...prev];for(let i=copy.length-1;i>=0;i--){if(copy[i].role==="assistant"){copy[i]={...copy[i],execResult:result};break;}}return copy;});
      refresh();}catch(e){console.error(e);}
    setExecuting(false);};
  const s=snap?.summary||{};
  if(loading)return(<div style={{minHeight:"100vh",background:"#070d1a",display:"flex",alignItems:"center",justifyContent:"center",color:"#38bdf8",fontSize:18,gap:12,fontFamily:"'Segoe UI',system-ui,sans-serif"}}><div style={{animation:"spin 1s linear infinite",fontSize:28}}>⚙️</div>טוען נתוני מערכת...<style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style></div>);
  if(err)return(<div style={{minHeight:"100vh",background:"#070d1a",display:"flex",alignItems:"center",justifyContent:"center",flexDirection:"column",gap:16,color:"#f1f5f9",padding:24,fontFamily:"'Segoe UI',system-ui,sans-serif"}}><div style={{fontSize:48}}>❌</div><div style={{fontSize:18,fontWeight:700}}>שגיאת חיבור</div><div style={{color:"#fca5a5",fontSize:14,textAlign:"center",direction:"rtl"}}>{err}</div><div style={{color:"#64748b",fontSize:13,direction:"rtl",textAlign:"center",maxWidth:400}}>בדוק שה-Anthropic API Key מוגדר ב-Add-on Configuration</div><button onClick={()=>window.location.reload()} style={{padding:"10px 24px",borderRadius:10,border:"none",background:"linear-gradient(135deg,#0ea5e9,#6366f1)",color:"#fff",fontSize:14,cursor:"pointer",fontWeight:700}}>נסה שוב</button></div>);
  return(<div style={{minHeight:"100vh",background:"#070d1a",display:"flex",flexDirection:"column",color:"#f1f5f9",fontFamily:"'Segoe UI',system-ui,sans-serif"}}>
    <div style={{padding:"13px 20px",borderBottom:"1px solid #1a2540",background:"#0a1020",display:"flex",alignItems:"center",gap:12,position:"sticky",top:0,zIndex:10}}>
      <div style={{width:38,height:38,borderRadius:10,background:"linear-gradient(135deg,#0ea5e9,#6366f1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,boxShadow:"0 0 14px rgba(14,165,233,.3)"}}>🏠</div>
      <div><div style={{fontWeight:700,fontSize:15}}>HA Agent</div><div style={{fontSize:11,color:"#34d399"}}>● מחובר · {s.location_name} · v{s.version}</div></div>
      <button onClick={refresh} style={{marginLeft:"auto",padding:"6px 12px",borderRadius:8,border:"1px solid #1e293b",background:"transparent",color:"#64748b",fontSize:12,cursor:"pointer"}}>↻ רענן</button>
    </div>
    <div style={{padding:"10px 20px",borderBottom:"1px solid #1a2540",background:"#090e1a",overflowX:"auto"}}>
      <div style={{display:"flex",gap:8,minWidth:"max-content"}}>
        <Badge icon="📦" label="Entities" value={s.total_entities}/>
        <Badge icon="⚙️" label="אוטומציות" value={s.automations}/>
        <Badge icon="📜" label="סקריפטים" value={s.scripts}/>
        <Badge icon="🌡️" label="חיישנים" value={s.sensors}/>
        {s.unavailable>0&&<Badge icon="🔴" label="לא זמין" value={s.unavailable} warn/>}
        {s.stuck_sensors>0&&<Badge icon="🟡" label="תקועים" value={s.stuck_sensors} warn/>}
        {s.idle_scripts>0&&<Badge icon="💤" label="לא פעיל" value={s.idle_scripts} warn/>}
        {s.duplicate_automations>0&&<Badge icon="♊" label="כפולות" value={s.duplicate_automations} warn/>}
        {s.errors_in_log>0&&<Badge icon="🚨" label="שגיאות" value={s.errors_in_log} warn/>}
      </div>
    </div>
    <div style={{flex:1,overflowY:"auto",padding:"20px 20px 0"}}>
      <div style={{maxWidth:780,margin:"0 auto"}}>
        {msgs.length===1&&<div style={{marginBottom:20,direction:"rtl"}}><div style={{fontSize:13,color:"#64748b",marginBottom:12}}>פקודות מהירות:</div><div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>{QUICK.map(q=><button key={q} onClick={()=>send(q)} style={{padding:"10px 14px",borderRadius:10,border:"1px solid #1a2540",background:"#0d1424",color:"#94a3b8",fontSize:13,cursor:"pointer",textAlign:"right",direction:"rtl",lineHeight:1.4}} onMouseEnter={e=>{e.target.style.borderColor="#38bdf8";e.target.style.color="#f1f5f9";}} onMouseLeave={e=>{e.target.style.borderColor="#1a2540";e.target.style.color="#94a3b8";}}>{q}</button>)}</div></div>}
        {msgs.map((m,i)=><Msg key={i} msg={m} onExec={execAction} executing={executing}/>)}
        {sending&&<div style={{display:"flex",alignItems:"center",gap:10,marginBottom:16}}><div style={{width:36,height:36,borderRadius:10,flexShrink:0,background:"linear-gradient(135deg,#0ea5e9,#6366f1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>🏠</div><div style={{padding:"10px 16px",background:"#1a2540",borderRadius:"18px 18px 18px 4px",border:"1px solid #243046"}}><Dots/></div></div>}
        <div ref={bottomRef} style={{height:20}}/>
      </div>
    </div>
    <div style={{padding:"14px 20px 18px",borderTop:"1px solid #1a2540",background:"#0a1020"}}>
      <div style={{maxWidth:780,margin:"0 auto",display:"flex",gap:10,alignItems:"flex-end"}}>
        <textarea ref={taRef} value={input} onChange={e=>{setInput(e.target.value);e.target.style.height="auto";e.target.style.height=Math.min(e.target.scrollHeight,130)+"px";}} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}}} placeholder="שאל את הסוכן... (Enter לשליחה)" disabled={sending} style={{flex:1,background:"#111827",border:"1px solid #1e293b",borderRadius:12,padding:"12px 16px",color:"#f1f5f9",fontSize:14.5,outline:"none",resize:"none",minHeight:48,maxHeight:130,direction:"rtl",fontFamily:"'Segoe UI',system-ui,sans-serif",lineHeight:1.6,boxSizing:"border-box",transition:"border-color .15s"}} onFocus={e=>e.target.style.borderColor="#38bdf8"} onBlur={e=>e.target.style.borderColor="#1e293b"}/>
        <button onClick={()=>send()} disabled={sending||!input.trim()} style={{width:48,height:48,borderRadius:12,border:"none",flexShrink:0,background:!sending&&input.trim()?"linear-gradient(135deg,#0ea5e9,#6366f1)":"#111827",color:!sending&&input.trim()?"#fff":"#334155",fontSize:20,cursor:!sending&&input.trim()?"pointer":"not-allowed",display:"flex",alignItems:"center",justifyContent:"center"}}>{sending?"⏳":"↑"}</button>
      </div>
    </div>
  </div>);
}
