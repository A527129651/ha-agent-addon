# HA Agent Add-on — התקנה

## דרישות
- Home Assistant OS או Supervised
- Anthropic API Key (מ-console.anthropic.com)

## שלב 1 — הוסף את ה-Add-on ל-HA

העתק את תיקיית `ha-agent-addon/` לתוך:
```
/config/addons/ha_agent/
```
(דרך File Editor, Samba, או SSH)

## שלב 2 — בנה את ה-Frontend (פעם אחת)

```bash
cd /config/addons/ha_agent/frontend
npm install && npm run build
```

## שלב 3 — התקן ב-HA

1. **Settings → Add-ons → Add-on Store**
2. לחץ **⋮ (שלוש נקודות) → Check for updates**
3. גלול למטה → **Local add-ons**
4. מצא **HA Agent** → לחץ **Install**

## שלב 4 — הגדר API Key

בלשונית **Configuration** של ה-Add-on:
```yaml
anthropic_api_key: "sk-ant-api03-YOUR-KEY-HERE"
log_level: "info"
```

## שלב 5 — הפעל

לחץ **Start** → פתח דרך **Open Web UI** או מהסרגל הצדדי.

## הערות
- ה-Add-on מקבל גישה ל-HA API אוטומטית דרך ה-Supervisor Token
- אין צורך להזין שום token של HA — הכל אוטומטי
- ה-Anthropic Key הוא הדבר היחיד שצריך להגדיר
