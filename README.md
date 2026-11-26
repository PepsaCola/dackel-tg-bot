# Feedback Bot

**English** | [Українська](README.uk.md) | [Deutsch](README.de.md)

A service that receives feedback and complaints from the language-learning app and posts them to a Telegram team group.

```
App ──POST /api/v1/feedback (X-API-Key)──► FastAPI ──► aiogram Bot ──► Telegram group
```

- **FastAPI** receives the HTTP request, checks the API key and the payload, and applies rate limiting.
- **aiogram** posts a formatted message to Telegram.
- The app gets `201` only once the message has been delivered. If Telegram is unreachable it gets `503` and can retry.

---

## Contents

- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Environment variables](#environment-variables)
- [API](#api)
- [Demo page](#demo-page)
- [Tests](#tests)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

---

## Project structure

```
feedback-bot/
├── app/
│   ├── main.py              # FastAPI app, bot startup/shutdown, demo page
│   ├── config.py            # settings from environment variables (.env)
│   ├── api/
│   │   ├── routes.py        # /health and /api/v1/feedback endpoints
│   │   └── deps.py          # API key check, rate limit, notifier access
│   ├── core/
│   │   ├── logging.py       # log format
│   │   └── rate_limit.py    # per-IP request limit
│   ├── schemas/
│   │   └── feedback.py      # request and response models (validation)
│   ├── services/
│   │   ├── formatter.py     # builds the HTML message for Telegram
│   │   └── notifier.py      # sends to Telegram with retries
│   └── web/
│       └── index.html       # demo page /demo/ (EN / UK / DE)
├── tests/                   # pytest
├── .env.example             # settings template
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

---

## Quick start

Requires Python 3.12+.

1. Create a bot with [@BotFather](https://t.me/BotFather) and add it to the group as an administrator.
2. Find the group ID: post a message in the group and open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` (without the angle brackets).
   You need the `message.chat.id` value.
3. Copy `.env.example` to `.env` and fill in the values.
4. Install dependencies and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

After startup:

- http://localhost:8000/health returns `{"status":"ok"}`
- http://localhost:8000/demo/ shows the demo form
- http://localhost:8000/docs opens Swagger (only when `APP_ENV=development`)

Generate an API key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Environment variables

| Variable                | Required | Default       | Description                                                             |
| ----------------------- | -------- | ------------- | ----------------------------------------------------------------------- |
| `BOT_TOKEN`             | yes      | —             | Bot token from @BotFather                                               |
| `CHANNEL_ID`            | yes      | —             | ID of the group or channel that receives feedback                       |
| `API_KEYS`              | yes      | —             | Comma-separated API keys for the app                                    |
| `APP_ENV`               | no       | `production`  | `production` or `development`. `/docs` is available in development only |
| `LOG_LEVEL`             | no       | `INFO`        | `DEBUG`, `INFO`, `WARNING`, `ERROR`                                     |
| `TIMEZONE`              | no       | `Europe/Kyiv` | Time zone used for the timestamp in the message                         |
| `RATE_LIMIT_PER_MINUTE` | no       | `5`           | Max feedback requests per minute from one IP                            |
| `CORS_ORIGINS`          | no       | empty         | Comma-separated web app domains, e.g. `https://app.example.com`         |
| `DEMO_ENABLED`          | no       | `false`       | `true` enables the `/demo/` page                                        |
| `PORT`                  | no       | `8000`        | HTTP port (set automatically by most hosting providers)                 |

---

## API

### `GET /health`

Liveness check. No key required.

```json
{ "status": "ok" }
```

### `POST /api/v1/feedback`

Submit feedback.

**Headers**

| Header         | Value                        |
| -------------- | ---------------------------- |
| `Content-Type` | `application/json`           |
| `X-API-Key`    | one of the `API_KEYS` values |

**Body**

| Field         | Type    | Required | Constraints                                  |
| ------------- | ------- | -------- | -------------------------------------------- |
| `type`        | string  | yes      | `feedback`, `complaint`, `bug`, `suggestion` |
| `message`     | string  | yes      | 3–3000 characters                            |
| `rating`      | integer | no       | 1–5                                          |
| `user_id`     | string  | no       | up to 64 characters                          |
| `contact`     | string  | no       | up to 128 characters (email, @telegram)      |
| `platform`    | string  | no       | `ios`, `android`, `web`, `other`             |
| `app_version` | string  | no       | up to 32 characters                          |
| `locale`      | string  | no       | up to 16 characters, e.g. `en`               |

Unknown fields are rejected with `422`.

**Example**

```json
{
  "type": "complaint",
  "message": "Lesson 5 doesn't open",
  "rating": 2,
  "user_id": "u_42",
  "platform": "android",
  "app_version": "1.3.0",
  "locale": "en"
}
```

**Responses**

| Code  | Meaning                                                         | What the app should do                             |
| ----- | --------------------------------------------------------------- | -------------------------------------------------- |
| `201` | Delivered. Body: `{"id": "a1b2c3d4e5f6", "status": "accepted"}` | Show "Thank you!"                                  |
| `401` | Missing or invalid `X-API-Key`                                  | Check the key in the app config                    |
| `422` | Invalid data (type, length, unknown fields)                     | Fix the request; details in `detail`               |
| `429` | Too many requests from this IP                                  | Ask the user to try again later                    |
| `503` | Telegram is unavailable                                         | Retry after a few seconds, or store and send later |

**What it looks like in Telegram**

Messages are in Ukrainian for the team; the texts live in `app/services/formatter.py`.

```
⚠️ Скарга  #complaint
Оцінка: ⭐⭐☆☆☆
│ Lesson 5 doesn't open
Користувач: u_42
Платформа: android
Версія: 1.3.0
Час: 26.11.2026 14:05
ID: a1b2c3d4e5f6
```

Hashtags (`#bug`, `#complaint`, …) make it easy to filter messages in the group.

### Integration examples

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
    message: "Audio doesn't play in lesson 3",
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
  -d '{"type":"suggestion","message":"Please add a dark theme"}'
```

**Python**

```python
import os

import httpx

response = httpx.post(
    "https://<domain>/api/v1/feedback",
    headers={"X-API-Key": os.environ["FEEDBACK_API_KEY"]},
    json={"type": "feedback", "message": "Love the flashcards!", "rating": 5},
    timeout=10,
)
response.raise_for_status()
print(response.json()["id"])
```

---

## Demo page

With `DEMO_ENABLED=true`, `/demo/` serves a form for sending test feedback:

- pick the interface language in the top-right dropdown (English, Українська, Deutsch); the choice is remembered in the browser;
- enter the service URL (defaults to the current domain) and an API key;
- fill in the form and send it; the message arrives in the group;
- the "Request example" block shows ready-to-use code (JavaScript, cURL, Python) for the entered data.

The API key is not embedded in the page. It is typed in manually and kept in `sessionStorage` until the tab is closed.
The demo page is served by the same server, so it doesn't need CORS.

---

## Tests

```powershell
pytest -v
```

Tests don't call Telegram: message delivery is replaced with a fake object.

---

## Deployment

### Render (free tier)

1. Push the code to GitHub.
2. On [render.com](https://render.com): **New → Web Service** → connect the repository.
3. **Language:** Docker, **Instance Type:** Free.
4. **Environment Variables:** `BOT_TOKEN`, `CHANNEL_ID`, `API_KEYS`, `APP_ENV=production`,
   `TIMEZONE=Europe/Kyiv`, `DEMO_ENABLED=true`. `PORT` is set by Render.
5. **Advanced → Health Check Path:** `/health`.
6. Check `https://<service>.onrender.com/health` and `https://<service>.onrender.com/demo/`.

Every push to `main` triggers a redeploy.

**Keeping it awake.** Free Render services sleep after 15 minutes without traffic and take 30 s–2 min to wake up.
Create a free [UptimeRobot](https://uptimerobot.com) HTTP(s) monitor for `https://<service>.onrender.com/health`
with a 5-minute interval. It keeps the service awake (one always-on service fits into the 750 free hours a month)
and emails you if the bot goes down. As a fallback, give the app's request a timeout of about 60 seconds.

### Paid alternative

[Railway](https://railway.app) (Hobby, about $5/month) works the same way: deploy from GitHub, set the same variables,
add `PORT=8000`, and use **Settings → Networking → Generate Domain**.

---

## Troubleshooting

| Symptom                                               | Cause                                              | Fix                                             |
| ----------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------- |
| `getUpdates` returns `404 Not Found`                  | `< >` left around the token, or the token is wrong | Format: `.../bot123:ABC/getUpdates`             |
| Service fails to start: `Unauthorized`                | Wrong `BOT_TOKEN`                                  | Check the token in @BotFather                   |
| `503`, logs show `chat not found`                     | Wrong `CHANNEL_ID`, or the bot isn't in the group  | Check the ID via `getUpdates`, add the bot      |
| `503`, logs show `not enough rights`                  | The bot isn't an admin                             | Give the bot permission to post                 |
| `503`, logs show `upgraded to a supergroup`           | The group became a supergroup and got a new ID     | Take the new ID (`-100…`) from `getUpdates`     |
| `401`                                                 | The app's key doesn't match `API_KEYS`             | Compare both values                             |
| Demo: "Couldn't connect"                              | Wrong URL, or page opened from another domain      | Fix the URL or add the domain to `CORS_ORIGINS` |
| First request takes up to a minute                    | Free Render instance was asleep                    | Set up the UptimeRobot monitor                  |
| `ModuleNotFoundError: No module named 'app'` in tests | Missing `__init__.py` files                        | Make sure they exist in `app/*` and `tests/`    |

---

## Security

- `.env` is never committed (it's in `.gitignore`). Don't show the token or keys in screenshots.
- If the token leaks, run `/revoke` in @BotFather and update `BOT_TOKEN`.
- A key embedded in a mobile or web client can be extracted. Rate limiting protects against spam, but sending feedback through your own backend is best.
- Feedback text is never written to logs, and all user text is escaped before it is sent to Telegram.
- To rotate a key: add the new one (`API_KEYS=old,new`), update the app, then remove the old one.
