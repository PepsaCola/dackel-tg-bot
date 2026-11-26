# Feedback Bot

[English](README.md) | [Українська](README.uk.md) | **Deutsch**

Ein Service, der Feedback und Beschwerden aus der Sprachlern-App entgegennimmt und in einer Telegram-Gruppe des Teams veröffentlicht.

```
App ──POST /api/v1/feedback (X-API-Key)──► FastAPI ──► aiogram Bot ──► Telegram-Gruppe
```

- **FastAPI** nimmt die HTTP-Anfrage entgegen, prüft API-Schlüssel und Daten und begrenzt die Anfragerate.
- **aiogram** sendet eine formatierte Nachricht an Telegram.
- Die App erhält `201` erst, wenn die Nachricht zugestellt ist. Ist Telegram nicht erreichbar, kommt `503`, und die Anfrage kann wiederholt werden.

> Die Hauptdokumentation ist auf Englisch: [README.md](README.md). Bei Abweichungen gilt die englische Version.

---

## Inhalt

- [Projektstruktur](#projektstruktur)
- [Schnellstart](#schnellstart)
- [Umgebungsvariablen](#umgebungsvariablen)
- [API](#api)
- [Demo-Seite](#demo-seite)
- [Tests](#tests)
- [Deployment](#deployment)
- [Häufige Probleme](#häufige-probleme)
- [Sicherheit](#sicherheit)

---

## Projektstruktur

```
feedback-bot/
├── app/
│   ├── main.py              # FastAPI-App, Start/Stopp des Bots, Demo-Seite
│   ├── config.py            # Einstellungen aus Umgebungsvariablen (.env)
│   ├── api/
│   │   ├── routes.py        # Endpunkte /health und /api/v1/feedback
│   │   └── deps.py          # API-Schlüssel-Prüfung, Rate Limit, Zugriff auf den Bot
│   ├── core/
│   │   ├── logging.py       # Log-Format
│   │   └── rate_limit.py    # Anfragelimit pro IP
│   ├── schemas/
│   │   └── feedback.py      # Request- und Response-Modelle (Validierung)
│   ├── services/
│   │   ├── formatter.py     # erstellt die HTML-Nachricht für Telegram
│   │   └── notifier.py      # Versand an Telegram mit Wiederholungen
│   └── web/
│       └── index.html       # Demo-Seite /demo/ (EN / UK / DE)
├── tests/                   # pytest
├── .env.example             # Vorlage für die Einstellungen
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

---

## Schnellstart

Benötigt Python 3.12+.

1. Erstelle einen Bot über [@BotFather](https://t.me/BotFather) und füge ihn der Gruppe als Administrator hinzu.
2. Ermittle die Gruppen-ID: Schreibe eine Nachricht in die Gruppe und öffne
   `https://api.telegram.org/bot<TOKEN>/getUpdates` (ohne spitze Klammern).
   Benötigt wird der Wert `message.chat.id`.
3. Kopiere `.env.example` nach `.env` und trage die Werte ein.
4. Installiere die Abhängigkeiten und starte den Service:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Nach dem Start:

- http://localhost:8000/health liefert `{"status":"ok"}`
- http://localhost:8000/demo/ zeigt das Demo-Formular
- http://localhost:8000/docs öffnet Swagger (nur bei `APP_ENV=development`)

API-Schlüssel erzeugen:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Umgebungsvariablen

| Variable                | Pflicht | Standard      | Beschreibung                                                               |
| ----------------------- | ------- | ------------- | -------------------------------------------------------------------------- |
| `BOT_TOKEN`             | ja      | —             | Bot-Token von @BotFather                                                   |
| `CHANNEL_ID`            | ja      | —             | ID der Gruppe oder des Kanals, der das Feedback erhält                     |
| `API_KEYS`              | ja      | —             | API-Schlüssel für die App, durch Komma getrennt                            |
| `APP_ENV`               | nein    | `production`  | `production` oder `development`. `/docs` nur in development                |
| `LOG_LEVEL`             | nein    | `INFO`        | `DEBUG`, `INFO`, `WARNING`, `ERROR`                                        |
| `TIMEZONE`              | nein    | `Europe/Kyiv` | Zeitzone für den Zeitstempel in der Nachricht                              |
| `RATE_LIMIT_PER_MINUTE` | nein    | `5`           | Max. Feedback-Anfragen pro Minute und IP                                   |
| `CORS_ORIGINS`          | nein    | leer          | Domains der Web-App, durch Komma getrennt, z. B. `https://app.example.com` |
| `DEMO_ENABLED`          | nein    | `false`       | `true` aktiviert die Demo-Seite `/demo/`                                   |
| `PORT`                  | nein    | `8000`        | HTTP-Port (wird von den meisten Hostern automatisch gesetzt)               |

---

## API

### `GET /health`

Prüft, ob der Service läuft. Kein Schlüssel erforderlich.

```json
{ "status": "ok" }
```

### `POST /api/v1/feedback`

Feedback senden.

**Header**

| Header         | Wert                           |
| -------------- | ------------------------------ |
| `Content-Type` | `application/json`             |
| `X-API-Key`    | einer der Werte aus `API_KEYS` |

**Body**

| Feld          | Typ     | Pflicht | Einschränkungen                              |
| ------------- | ------- | ------- | -------------------------------------------- |
| `type`        | string  | ja      | `feedback`, `complaint`, `bug`, `suggestion` |
| `message`     | string  | ja      | 3–3000 Zeichen                               |
| `rating`      | integer | nein    | 1–5                                          |
| `user_id`     | string  | nein    | bis 64 Zeichen                               |
| `contact`     | string  | nein    | bis 128 Zeichen (E-Mail, @telegram)          |
| `platform`    | string  | nein    | `ios`, `android`, `web`, `other`             |
| `app_version` | string  | nein    | bis 32 Zeichen                               |
| `locale`      | string  | nein    | bis 16 Zeichen, z. B. `de`                   |

Unbekannte Felder werden mit `422` abgelehnt.

**Beispiel**

```json
{
  "type": "complaint",
  "message": "Lektion 5 lässt sich nicht öffnen",
  "rating": 2,
  "user_id": "u_42",
  "platform": "android",
  "app_version": "1.3.0",
  "locale": "de"
}
```

**Antworten**

| Code  | Bedeutung                                                        | Was die App tun sollte                                             |
| ----- | ---------------------------------------------------------------- | ------------------------------------------------------------------ |
| `201` | Zugestellt. Body: `{"id": "a1b2c3d4e5f6", "status": "accepted"}` | „Danke!“ anzeigen                                                  |
| `401` | `X-API-Key` fehlt oder ist ungültig                              | Schlüssel in der App-Konfiguration prüfen                          |
| `422` | Fehlerhafte Daten (Typ, Länge, unbekannte Felder)                | Anfrage korrigieren; Details in `detail`                           |
| `429` | Zu viele Anfragen von dieser IP                                  | Nutzer bitten, es später erneut zu versuchen                       |
| `503` | Telegram nicht erreichbar                                        | Nach einigen Sekunden wiederholen oder speichern und später senden |

**So sieht es in Telegram aus**

Die Nachrichten sind für das Team auf Ukrainisch; die Texte stehen in `app/services/formatter.py`.

```
⚠️ Скарга  #complaint
Оцінка: ⭐⭐☆☆☆
│ Lektion 5 lässt sich nicht öffnen
Користувач: u_42
Платформа: android
Версія: 1.3.0
Час: 26.11.2026 14:05
ID: a1b2c3d4e5f6
```

Hashtags (`#bug`, `#complaint`, …) erleichtern das Filtern in der Gruppe.

### Integrationsbeispiele

**JavaScript / TypeScript**

```ts
const response = await fetch("https://<domain>/api/v1/feedback", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": FEEDBACK_API_KEY,
  },
  body: JSON.stringify({
    type: "bug",
    message: "In Lektion 3 wird kein Audio abgespielt",
    platform: "web",
  }),
});

if (!response.ok) {
  throw new Error(`Feedback failed: ${response.status}`);
}
const { id } = await response.json();
```

**cURL**

```bash
curl -X POST "https://<domain>/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FEEDBACK_API_KEY" \
  -d '{"type":"suggestion","message":"Bitte einen Dark Mode hinzufügen"}'
```

**Python**

```python
import os

import httpx

response = httpx.post(
    "https://<domain>/api/v1/feedback",
    headers={"X-API-Key": os.environ["FEEDBACK_API_KEY"]},
    json={"type": "feedback", "message": "Die Karteikarten sind super!", "rating": 5},
    timeout=10,
)
response.raise_for_status()
print(response.json()["id"])
```

---

## Demo-Seite

Mit `DEMO_ENABLED=true` stellt `/demo/` ein Formular zum Senden von Test-Feedback bereit:

- die Sprache der Oberfläche wählst du im Dropdown oben rechts (English, Українська, Deutsch); die Auswahl merkt sich der Browser;
- gib die Service-URL (standardmäßig die aktuelle Domain) und einen API-Schlüssel ein;
- fülle das Formular aus und sende es ab; die Nachricht erscheint in der Gruppe;
- der Block „Request-Beispiel“ zeigt fertigen Code (JavaScript, cURL, Python) für die eingegebenen Daten.

Der API-Schlüssel ist nicht in die Seite eingebaut. Er wird manuell eingegeben und bis zum Schließen des Tabs in `sessionStorage` gehalten.
Die Demo-Seite wird vom selben Server ausgeliefert und braucht daher kein CORS.

---

## Tests

```powershell
pytest -v
```

Die Tests rufen Telegram nicht auf: Der Nachrichtenversand wird durch ein Fake-Objekt ersetzt.

---

## Deployment

### Render (kostenloser Tarif)

1. Lade den Code auf GitHub hoch.
2. Auf [render.com](https://render.com): **New → Web Service** → Repository verbinden.
3. **Language:** Docker, **Instance Type:** Free.
4. **Environment Variables:** `BOT_TOKEN`, `CHANNEL_ID`, `API_KEYS`, `APP_ENV=production`,
   `TIMEZONE=Europe/Kyiv`, `DEMO_ENABLED=true`. `PORT` setzt Render selbst.
5. **Advanced → Health Check Path:** `/health`.
6. Prüfe `https://<service>.onrender.com/health` und `https://<service>.onrender.com/demo/`.

Jeder Push auf `main` löst ein neues Deployment aus.

**Damit der Service nicht einschläft.** Kostenlose Render-Services schlafen nach 15 Minuten ohne Anfragen ein und brauchen 30 Sekunden bis 2 Minuten zum Aufwachen.
Lege einen kostenlosen [UptimeRobot](https://uptimerobot.com)-Monitor vom Typ HTTP(s) für `https://<service>.onrender.com/health`
mit einem Intervall von 5 Minuten an. Er hält den Service wach (ein Service rund um die Uhr passt in die 750 kostenlosen Stunden pro Monat)
und schickt eine E-Mail, falls der Bot ausfällt. Setze in der App zur Sicherheit ein Request-Timeout von etwa 60 Sekunden.

### Kostenpflichtige Alternative

[Railway](https://railway.app) (Hobby, etwa 5 $ pro Monat) funktioniert genauso: Deployment aus GitHub, dieselben Variablen
plus `PORT=8000`, danach **Settings → Networking → Generate Domain**.

---

## Häufige Probleme

| Symptom                                                   | Ursache                                                  | Lösung                                                  |
| --------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------- |
| `getUpdates` liefert `404 Not Found`                      | `< >` um den Token stehen gelassen oder Token falsch     | Format: `.../bot123:ABC/getUpdates`                     |
| Service startet nicht: `Unauthorized`                     | Falscher `BOT_TOKEN`                                     | Token bei @BotFather prüfen                             |
| `503`, im Log `chat not found`                            | Falsche `CHANNEL_ID` oder Bot nicht in der Gruppe        | ID über `getUpdates` prüfen, Bot hinzufügen             |
| `503`, im Log `not enough rights`                         | Bot ist kein Administrator                               | Dem Bot das Recht zum Posten geben                      |
| `503`, im Log `upgraded to a supergroup`                  | Die Gruppe wurde zur Supergruppe und hat eine neue ID    | Neue ID (`-100…`) aus `getUpdates` übernehmen           |
| `401`                                                     | Schlüssel der App stimmt nicht mit `API_KEYS` überein    | Beide Werte vergleichen                                 |
| Demo: „Keine Verbindung“                                  | Falsche URL oder Seite von einer anderen Domain geöffnet | URL prüfen oder Domain zu `CORS_ORIGINS` hinzufügen     |
| Erste Anfrage dauert bis zu einer Minute                  | Kostenlose Render-Instanz hat geschlafen                 | UptimeRobot-Monitor einrichten                          |
| `ModuleNotFoundError: No module named 'app'` in den Tests | `__init__.py`-Dateien fehlen                             | Prüfen, dass sie in `app/*` und `tests/` vorhanden sind |

---

## Sicherheit

- `.env` wird nie committet (steht in `.gitignore`). Token und Schlüssel nicht auf Screenshots zeigen.
- Falls der Token geleakt ist: `/revoke` bei @BotFather ausführen und `BOT_TOKEN` ersetzen.
- Ein in einen Mobil- oder Web-Client eingebauter Schlüssel kann ausgelesen werden. Das Rate Limit schützt vor Spam, am besten wird Feedback aber über das eigene Backend gesendet.
- Feedback-Texte werden nicht geloggt; jeder Text vom Nutzer wird vor dem Versand an Telegram escaped.
- Schlüssel rotieren: neuen hinzufügen (`API_KEYS=old,new`), App aktualisieren, dann den alten entfernen.
