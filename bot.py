import logging
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ChatMemberHandler
import os

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID"))
CREDENTIALS_FILE = "creds.json"

# === ДОСТУП К GOOGLE SHEETS ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(GOOGLE_SHEET_NAME).sheet1

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)

def save_chat(chat):
    chat_id = chat.id
    title = chat.title or f"Chat {chat_id}"
    rows = sheet.get_all_records()
    if any(str(chat_id) == str(row['Chat ID']) for row in rows):
        return
    sheet.append_row([title, str(chat_id), datetime.datetime.now().strftime("%Y-%m-%d")])

async def chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member.new_chat_member
    if member.user.id == context.bot.id:
        chat = update.effective_chat
        logging.info(f"Добавлен в чат: {chat.title} ({chat.id})")
        save_chat(chat)

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Нет доступа.")
        return

    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Используй: /send текст")
        return

    rows = sheet.get_all_records()
    sent = 0
    for row in rows:
        try:
            await context.bot.send_message(chat_id=int(row['Chat ID']), text=message)
            sent += 1
        except Exception as e:
            logging.warning(f"Ошибка в {row['Chat ID']}: {e}")

    await update.message.reply_text(f"Отправлено в {sent} чатов.")

# === ЗАПУСК ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(ChatMemberHandler(chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
app.add_handler(CommandHandler("send", send))

print("Бот запущен")
app.run_polling()

