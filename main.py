import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

XIZMAT, VAQT, ISM, TELEFON = range(4)

XIZMATLAR = {
    "✂️ Soch olish - 15,000 so'm": "Soch olish",
    "🪒 Soqol olish - 10,000 so'm": "Soqol olish",
    "✂️🪒 Ikkalasi - 20,000 so'm": "Soch + Soqol",
}

VAQTLAR = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[k] for k in XIZMATLAR.keys()]
    await update.message.reply_text(
        "💈 Sartaroshxonaga Xush Kelibsiz!\n\nQaysi xizmatni tanlaysiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return XIZMAT

async def xizmat_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tanlangan = update.message.text
    if tanlangan not in XIZMATLAR:
        await update.message.reply_text("Iltimos, ro'yxatdan tanlang!")
        return XIZMAT
    context.user_data["xizmat"] = XIZMATLAR[tanlangan]
    keyboard = [VAQTLAR[i:i+2] for i in range(0, len(VAQTLAR), 2)]
    keyboard.append(["🔙 Orqaga"])
    await update.message.reply_text(
        f"Qaysi vaqtda kelasiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return VAQT

async def vaqt_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Orqaga":
        return await start(update, context)
    if update.message.text not in VAQTLAR:
        await update.message.reply_text("Iltimos, vaqtni tanlang!")
        return VAQT
    context.user_data["vaqt"] = update.message.text
    await update.message.reply_text(
        "Ismingizni kiriting:",
        reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True)
    )
    return ISM

async def ism_kiritish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Orqaga":
        keyboard = [VAQTLAR[i:i+2] for i in range(0, len(VAQTLAR), 2)]
        keyboard.append(["🔙 Orqaga"])
        await update.message.reply_text("Vaqtni tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return VAQT
    context.user_data["ism"] = update.message.text
    await update.message.reply_text(
        "Telefon raqamingizni kiriting:\nMasalan: +998901234567",
        reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True)
    )
    return TELEFON

async def telefon_kiritish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Orqaga":
        await update.message.reply_text("Ismingizni kiriting:", reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True))
        return ISM
    context.user_data["telefon"] = update.message.text
    data = context.user_data
    await update.message.reply_text(
        f"Navbatingiz qabul qilindi!\n\n"
        f"Ism: {data['ism']}\n"
        f"Xizmat: {data['xizmat']}\n"
        f"Vaqt: {data['vaqt']}\n"
        f"Telefon: {data['telefon']}\n\n"
        f"Belgilangan vaqtda keling!",
        reply_markup=ReplyKeyboardRemove()
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"YANGI NAVBAT!\n\nIsm: {data['ism']}\nXizmat: {data['xizmat']}\nVaqt: {data['vaqt']}\nTelefon: {data['telefon']}"
        )
    except Exception as e:
        logging.error(f"Xato: {e}")
    return ConversationHandler.END

async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. /start bosing.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            XIZMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, xizmat_tanlash)],
            VAQT: [MessageHandler(filters.TEXT & ~filters.COMMAND, vaqt_tanlash)],
            ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ism_kiritish)],
            TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, telefon_kiritish)],
        },
        fallbacks=[CommandHandler("bekor", bekor)],
    )
    app.add_handler(conv)
    print("Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
