БЕСПЛАТНЫЙ ЗАПУСК TELEGRAM-БОТА ЧЕРЕЗ ТЕЛЕФОН

Файлы:
- main.py — код бота с Telegram webhook для Render Web Service
- requirements.txt — библиотеки
- render.yaml — настройки Render
- .gitignore — не даст случайно добавить базу/секреты

1) На телефоне скачай ZIP и распакуй его.
2) На github.com войди в аккаунт, создай New repository.
3) Загрузи в корень репозитория main.py, requirements.txt, render.yaml и .gitignore.
   README_RU.txt можно загрузить по желанию.
4) На render.com войди через GitHub.
5) Нажми New + -> Blueprint, выбери репозиторий и подтверди.
   Если Blueprint не появляется, создай New + -> Web Service и выбери репозиторий:
   Runtime Python; Build Command: pip install -r requirements.txt;
   Start Command: python main.py; Instance Type: Free.
6) В Environment добавь:
   BOT_TOKEN = токен от @BotFather
   ADMIN_CODE = придумай свой длинный секретный код
   WEBHOOK_SECRET = случайная строка из 30+ латинских букв/цифр
   DB_PATH = /tmp/complaints_bot.db
   Если Render сам создал WEBHOOK_SECRET через Blueprint, оставь его.
7) Нажми Deploy и смотри Logs. При успехе будет строка «Webhook установлен».

ВАЖНО:
- Это бесплатный Render Web Service + Telegram webhook, не Background Worker.
- Бесплатный Render может «усыплять» сервис после периода без запросов. Первое сообщение
  после сна может прийти с задержкой.
- На бесплатном плане нет постоянного диска. База в /tmp может очиститься после
  перезапуска/деплоя. Для надёжного хранения нужна внешняя БД.
- Бот использует официальный Telegram Bot API для своего интерфейса и подготовки
  обоснованных обращений. Он не рассылает массовые жалобы и не автоматизирует
  блокировку аккаунтов.
- Никогда не добавляй BOT_TOKEN в GitHub. Если он случайно опубликован, перевыпусти
  его через @BotFather.
