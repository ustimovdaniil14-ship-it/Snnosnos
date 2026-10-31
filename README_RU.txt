ГОТОВЫЙ КОМПЛЕКТ ДЛЯ RENDER FREE

1. Загрузи ВСЕ файлы из этой папки в корень одного GitHub-репозитория:
   - telegram_complaint_helper_fixed.py
   - requirements.txt
   - render.yaml

2. На Render создай New + Blueprint и выбери этот GitHub-репозиторий.
   Либо создай Web Service вручную:
   Build Command: pip install -r requirements.txt
   Start Command: python telegram_complaint_helper_fixed.py
   Instance Type / Plan: Free

3. В Environment добавь:
   BOT_TOKEN = токен от @BotFather
   ADMIN_CODE = придумай свой секретный код администратора
   WEBHOOK_SECRET = случайная строка минимум 32 символа, только латинские
                   буквы, цифры, подчёркивание или дефис.
   Пример формата (замени на собственную строку):
   q7Vn_4pL9xR2mK8sT5wB1cD6fH3jN0aZ

   RENDER_EXTERNAL_URL Render задаёт автоматически. Вручную её не добавляй.

4. После Deploy открой адрес сервиса Render:
   https://ИМЯ-СЕРВИСА.onrender.com/health
   Должен появиться ответ: {"status":"ok"}

ВАЖНЫЕ ОГРАНИЧЕНИЯ FREE:
- Бесплатный Render Web Service засыпает после периода без запросов.
  Первое сообщение после сна может обрабатываться с задержкой.
- Локальная SQLite-база на бесплатном Render НЕ является постоянным хранилищем:
  данные могут пропасть при перезапуске или новом деплое.
- FSM-состояния aiogram хранятся в памяти и сбрасываются после перезапуска.
- Не публикуй BOT_TOKEN, ADMIN_CODE или WEBHOOK_SECRET в GitHub и никому их не отправляй.
- Этот бот только составляет черновики добросовестных обращений; он не отправляет
  массовые жалобы и не блокирует аккаунты.
