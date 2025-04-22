import logging
import datetime
import gspread
import os
import json
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ChatMemberHandler
)

# === НАСТРОЙКИ ===
BOT_TOKEN = "7948716492:AAH0mCXwT_39BY0KnEt8OIZKMwAkq2BC7bc"
GOOGLE_SHEET_NAME = "Tos information BOT"
AUTHORIZED_USER_ID = 702836229
CREDENTIALS_FILE = "creds.json"
MESSAGES_FILE = "messages.json"

# === ДОСТУП К GOOGLE SHEETS ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(GOOGLE_SHEET_NAME).sheet1

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)

# === СОХРАНЕНИЕ ЧАТА ===
def save_chat(chat):
    chat_id = chat.id
    title = chat.title or f"Chat {chat_id}"
    rows = sheet.get_all_records()
    if any(str(chat_id) == str(row['Chat ID']) for row in rows):
        return
    sheet.append_row([title, str(chat_id), datetime.datetime.now().strftime("%Y-%m-%d")])

# === ПРИ ДОБАВЛЕНИИ В ЧАТ ===
async def chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.my_chat_member:
        member = update.my_chat_member.new_chat_member
        if member.user.id == context.bot.id:
            chat = update.effective_chat
            logging.info(f"Бот добавлен в чат: {chat.title} ({chat.id})")
            save_chat(chat)
    else:
        logging.warning("update.my_chat_member is None")

# === /START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Твой Telegram ID: {user_id}")

# === /SAVE ===
async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    logging.info(f"Команда /save от: {chat.title} ({chat.id})")
    save_chat(chat)
    await update.message.reply_text("Чат сохранён в таблицу.")

# === /SEND ===
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
    message_data = {}
    for row in rows:
        try:
            msg = await context.bot.send_message(chat_id=int(row['Chat ID']), text=message)
            message_data[str(row['Chat ID'])] = msg.message_id
            sent += 1
        except Exception as e:
            logging.warning(f"Ошибка в {row['Chat ID']}: {e}")

    with open(MESSAGES_FILE, "w") as f:
        json.dump(message_data, f)

    await update.message.reply_text(f"Отправлено в {sent} чатов.")

# === /DELETELAST ===
async def delete_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Нет доступа.")
        return

    try:
        with open(MESSAGES_FILE, "r") as f:
            message_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Нет сохранённых сообщений.")
        return

    deleted = 0
    for chat_id, message_id in message_data.items():
        try:
            await context.bot.delete_message(chat_id=int(chat_id), message_id=int(message_id))
            deleted += 1
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение в {chat_id}: {e}")

    await update.message.reply_text(f"Удалено {deleted} сообщений.")

# === ЗАПУСК ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(ChatMemberHandler(chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("save", save_command))
app.add_handler(CommandHandler("send", send))
app.add_handler(CommandHandler("deletelast", delete_last))

print("Бот запущен")
app.run_polling()
