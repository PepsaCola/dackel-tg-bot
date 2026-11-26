# Feedback Bot

[English](README.md) | **Українська** | [Deutsch](README.de.md)

Сервіс приймає відгуки та скарги із застосунку для вивчення мов і публікує їх у робочу групу Telegram.

```
Застосунок ──POST /api/v1/feedback (X-API-Key)──► FastAPI ──► aiogram Bot ──► Telegram-група
```

- **FastAPI** приймає HTTP-запит, перевіряє API-ключ і дані, обмежує частоту запитів.
- **aiogram** надсилає оформлене повідомлення в Telegram.
- Застосунок отримує `201`, тільки коли повідомлення вже доставлено. Якщо Telegram недоступний, повертається `503`, і запит можна повторити.

> Основна документація англійською: [README.md](README.md). Якщо версії розходяться, правильною вважається англійська.

---

## Зміст

- [Структура проєкту](#структура-проєкту)
- [Швидкий старт](#швидкий-старт)
- [Змінні середовища](#змінні-середовища)
- [API](#api)
- [Демо-сторінка](#демо-сторінка)
- [Тести](#тести)
- [Деплой](#деплой)
- [Типові проблеми](#типові-проблеми)
- [Безпека](#безпека)

---

## Структура проєкту

```
feedback-bot/
├── app/
│   ├── main.py              # створення FastAPI, запуск і зупинка бота, демо-сторінка
│   ├── config.py            # налаштування зі змінних середовища (.env)
│   ├── api/
│   │   ├── routes.py        # ендпоінти /health і /api/v1/feedback
│   │   └── deps.py          # перевірка API-ключа, rate limit, доступ до бота
│   ├── core/
│   │   ├── logging.py       # формат логів
│   │   └── rate_limit.py    # обмеження запитів з однієї IP
│   ├── schemas/
│   │   └── feedback.py      # модель запиту і відповіді (валідація)
│   ├── services/
│   │   ├── formatter.py     # формує HTML-повідомлення для Telegram
│   │   └── notifier.py      # відправка в Telegram з повторами
│   └── web/
│       └── index.html       # демо-сторінка /demo/ (EN / UK / DE)
├── tests/                   # pytest
├── .env.example             # шаблон налаштувань
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

---

## Швидкий старт

Потрібен Python 3.12+.

1. Створи бота в [@BotFather](https://t.me/BotFather) і додай його в групу як адміністратора.
2. Дізнайся ID групи: напиши в групу повідомлення й відкрий
   `https://api.telegram.org/bot<ТОКЕН>/getUpdates` (кутові дужки не пишуться).
   Потрібне значення: `message.chat.id`.
3. Скопіюй `.env.example` у `.env` і заповни значення.
4. Встанови залежності й запусти:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Після старту:

- http://localhost:8000/health відповідає `{"status":"ok"}`
- http://localhost:8000/demo/ показує демо-форму
- http://localhost:8000/docs відкриває Swagger (тільки коли `APP_ENV=development`)

Згенерувати API-ключ:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Змінні середовища

| Змінна                  | Обов'язкова | За замовчуванням | Опис                                                              |
| ----------------------- | ----------- | ---------------- | ----------------------------------------------------------------- |
| `BOT_TOKEN`             | так         | —                | Токен бота від @BotFather                                         |
| `CHANNEL_ID`            | так         | —                | ID групи або каналу, куди надсилати відгуки                       |
| `API_KEYS`              | так         | —                | Ключі доступу для застосунку, через кому                          |
| `APP_ENV`               | ні          | `production`     | `production` або `development`. У development доступний `/docs`   |
| `LOG_LEVEL`             | ні          | `INFO`           | `DEBUG`, `INFO`, `WARNING`, `ERROR`                               |
| `TIMEZONE`              | ні          | `Europe/Kyiv`    | Часовий пояс для часу в повідомленні                              |
| `RATE_LIMIT_PER_MINUTE` | ні          | `5`              | Максимум відгуків на хвилину з однієї IP                          |
| `CORS_ORIGINS`          | ні          | порожньо         | Домени веб-застосунку через кому, напр. `https://app.example.com` |
| `DEMO_ENABLED`          | ні          | `false`          | `true` вмикає демо-сторінку `/demo/`                              |
| `PORT`                  | ні          | `8000`           | HTTP-порт (більшість хостингів задає його автоматично)            |

---

## API

### `GET /health`

Перевірка, що сервіс живий. Не потребує ключа.

```json
{ "status": "ok" }
```

### `POST /api/v1/feedback`

Надіслати відгук.

**Заголовки**

| Заголовок      | Значення                   |
| -------------- | -------------------------- |
| `Content-Type` | `application/json`         |
| `X-API-Key`    | одне зі значень `API_KEYS` |

**Тіло запиту**

| Поле          | Тип     | Обов'язкове | Обмеження                                    |
| ------------- | ------- | ----------- | -------------------------------------------- |
| `type`        | string  | так         | `feedback`, `complaint`, `bug`, `suggestion` |
| `message`     | string  | так         | 3–3000 символів                              |
| `rating`      | integer | ні          | 1–5                                          |
| `user_id`     | string  | ні          | до 64 символів                               |
| `contact`     | string  | ні          | до 128 символів (email, @telegram)           |
| `platform`    | string  | ні          | `ios`, `android`, `web`, `other`             |
| `app_version` | string  | ні          | до 32 символів                               |
| `locale`      | string  | ні          | до 16 символів, напр. `uk`                   |

Невідомі поля відхиляються з кодом `422`.

**Приклад**

```json
{
  "type": "complaint",
  "message": "Урок 5 не відкривається",
  "rating": 2,
  "user_id": "u_42",
  "platform": "android",
  "app_version": "1.3.0",
  "locale": "uk"
}
```

**Відповіді**

| Код   | Значення                                                                | Що робити застосунку                                           |
| ----- | ----------------------------------------------------------------------- | -------------------------------------------------------------- |
| `201` | Відгук доставлено. Тіло: `{"id": "a1b2c3d4e5f6", "status": "accepted"}` | Показати «Дякуємо!»                                            |
| `401` | Неправильний або відсутній `X-API-Key`                                  | Перевірити ключ у конфігурації                                 |
| `422` | Помилка в даних (тип, довжина, зайві поля)                              | Виправити запит; деталі в `detail`                             |
| `429` | Забагато запитів з цієї IP                                              | Попросити спробувати пізніше                                   |
| `503` | Telegram недоступний                                                    | Повторити через кілька секунд або зберегти й надіслати пізніше |

**Як виглядає в Telegram**

```
⚠️ Скарга  #complaint
Оцінка: ⭐⭐☆☆☆
│ Урок 5 не відкривається
Користувач: u_42
Платформа: android
Версія: 1.3.0
Час: 26.11.2026 14:05
ID: a1b2c3d4e5f6
```

Хештеги (`#bug`, `#complaint`, …) дозволяють фільтрувати повідомлення в групі. Тексти повідомлень лежать в `app/services/formatter.py`.

### Приклади підключення

**JavaScript / TypeScript**

```ts
const response = await fetch("https://<домен>/api/v1/feedback", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": FEEDBACK_API_KEY,
  },
  body: JSON.stringify({
    type: "bug",
    message: "Не відтворюється аудіо в уроці 3",
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
curl -X POST "https://<домен>/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FEEDBACK_API_KEY" \
  -d '{"type":"suggestion","message":"Додайте темну тему"}'
```

**Python**

```python
import os

import httpx

response = httpx.post(
    "https://<домен>/api/v1/feedback",
    headers={"X-API-Key": os.environ["FEEDBACK_API_KEY"]},
    json={"type": "feedback", "message": "Дуже зручні картки!", "rating": 5},
    timeout=10,
)
response.raise_for_status()
print(response.json()["id"])
```

---

## Демо-сторінка

Коли `DEMO_ENABLED=true`, за адресою `/demo/` відкривається форма для тестових відгуків:

- мова інтерфейсу вибирається у випадаючому списку вгорі праворуч (English, Українська, Deutsch), і браузер запам'ятовує вибір;
- вкажи URL сервісу (за замовчуванням поточний домен) і API-ключ;
- заповни форму й надішли, повідомлення прийде в групу;
- блок «Приклад запиту» показує готовий код (JavaScript, cURL, Python) для введених даних.

API-ключ не вшитий у сторінку. Його вводять вручну, і він зберігається в `sessionStorage` до закриття вкладки.
Демо-сторінку роздає той самий сервер, тому CORS для неї не потрібен.

---

## Тести

```powershell
pytest -v
```

Тести не звертаються до Telegram: відправку повідомлень у них підмінено фейковим об'єктом.

---

## Деплой

### Render (безкоштовний тариф)

1. Завантаж код на GitHub.
2. На [render.com](https://render.com): **New → Web Service** → підключи репозиторій.
3. **Language:** Docker, **Instance Type:** Free.
4. **Environment Variables:** `BOT_TOKEN`, `CHANNEL_ID`, `API_KEYS`, `APP_ENV=production`,
   `TIMEZONE=Europe/Kyiv`, `DEMO_ENABLED=true`. `PORT` Render задає сам.
5. **Advanced → Health Check Path:** `/health`.
6. Перевір `https://<сервіс>.onrender.com/health` і `https://<сервіс>.onrender.com/demo/`.

Кожен push у `main` запускає новий деплой.

**Щоб сервіс не засинав.** Безкоштовний сервіс на Render засинає після 15 хвилин без запитів і прокидається від 30 секунд до 2 хвилин.
Створи безкоштовний монітор [UptimeRobot](https://uptimerobot.com) типу HTTP(s) на `https://<сервіс>.onrender.com/health`
з інтервалом 5 хвилин. Він не дає сервісу заснути (один сервіс 24/7 вміщується в 750 безкоштовних годин на місяць)
і надішле лист, якщо бот упаде. Про всяк випадок постав у застосунку тайм-аут запиту близько 60 секунд.

### Платна альтернатива

[Railway](https://railway.app) (Hobby, близько $5 на місяць) працює так само: деплой із GitHub, ті самі змінні
плюс `PORT=8000`, далі **Settings → Networking → Generate Domain**.

---

## Типові проблеми

| Симптом                                               | Причина                                                    | Рішення                                      |
| ----------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------- |
| `getUpdates` повертає `404 Not Found`                 | У URL лишилися `< >` навколо токена або токен неправильний | Формат: `.../bot123:ABC/getUpdates`          |
| Сервіс не стартує: `Unauthorized`                     | Неправильний `BOT_TOKEN`                                   | Перевір токен у @BotFather                   |
| `503`, у логах `chat not found`                       | Неправильний `CHANNEL_ID` або бота немає в групі           | Перевір ID через `getUpdates`, додай бота    |
| `503`, у логах `not enough rights`                    | Бот не адміністратор                                       | Дай боту право публікувати                   |
| `503`, у логах `upgraded to a supergroup`             | Група стала супергрупою й отримала новий ID                | Візьми новий ID (`-100…`) з `getUpdates`     |
| `401`                                                 | Ключ у застосунку не збігається з `API_KEYS`               | Перевір обидва значення                      |
| Демо: «Не вдалося з'єднатися»                         | Неправильний URL або сторінка відкрита з іншого домену     | Перевір URL або додай домен у `CORS_ORIGINS` |
| Перший запит іде до хвилини                           | Безкоштовний інстанс Render спав                           | Налаштуй монітор UptimeRobot                 |
| `ModuleNotFoundError: No module named 'app'` у тестах | Немає файлів `__init__.py`                                 | Перевір, що вони є в `app/*` і `tests/`      |

---

## Безпека

- `.env` не комітиться (є в `.gitignore`). Токен і ключі не показувати на скріншотах.
- Якщо токен потрапив у сторонні руки, виконай `/revoke` у @BotFather і заміни `BOT_TOKEN`.
- Ключ, вшитий у мобільний чи веб-клієнт, можна витягнути. Rate limit захищає від спаму, але найкраще надсилати відгуки через власний бекенд.
- Текст відгуків не пишеться в логи; весь текст від користувача екранується перед відправкою в Telegram.
- Для ротації ключа додай новий через кому (`API_KEYS=old,new`), онови застосунок, потім прибери старий.
