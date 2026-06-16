import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# --- SOZLAMALAR ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Bosqichlar
XIZMAT, VAQT, ISM, TELEFON = range(4)

# Xizmatlar va narxlar
XIZMATLAR = {
    "✂️ Soch olish - 15,000 so'm": "Soch olish",
    "🪒 Soqol olish - 10,000 so'm": "Soqol olish",
    "✂️🪒 Ikkalasi - 20,000 so'm": "Soch + Soqol",
}

# Ish vaqtlari
VAQTLAR = [
    "09:00", "10:00", "11:00", "12:00",
    "13:00", "14:00", "15:00", "16:00",
    "17:00", "18:00"
]

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[k] for k in XIZMATLAR.keys()]
    await update.message.reply_text(
        "💈 *Sartaroshxonaga Xush Kelibsiz!*\n\n"
        "Qaysi xizmatni tanlaysiz?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return XIZMAT


async def xizmat_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tanlangan = update.message.text
    if tanlangan not in XIZMATLAR:
        await update.message.reply_text("❌ Iltimos, ro'yxatdan tanlang!")
        return XIZMAT

    context.user_data["xizmat"] = XIZMATLAR[tanlangan]
    context.user_data["xizmat_narx"] = tanlangan

    keyboard = [VAQTLAR[i:i+2] for i in range(0, len(VAQTLAR), 2)]
    keyboard.append(["🔙 Orqaga"])

    await update.message.reply_text(
        f"✅ *{XIZMATLAR[tanlangan]}* tanlandi!\n\n"
        "⏰ Qaysi vaqtda kelasiz?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return VAQT


async def vaqt_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Orqaga":
        return await start(update, context)

    if update.message.text not in VAQTLAR:
        await update.message.reply_text("❌ Iltimos, vaqtni ro'yxatdan tanlang!")
        return VAQT

    context.user_data["vaqt"] = update.message.text

    await update.message.reply_text(
        "👤 Ismingizni kiriting:",
        reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True)
    )
    return ISM


async def ism_kiritish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Orqaga":
        keyboard = [VAQTLAR[i:i+2] for i in range(0, len(VAQTLAR), 2)]
        keyboard.append(["🔙 Orqaga"])
        await update.message.reply_text(
            "⏰ Vaqtni tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return VAQT

    context.user_data["ism"] = update.message.text

    await update.message.reply_text(
        "📞 Telefon raqamingizni kiriting:\n"
        "Masalan: +998901234567",
        reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True)
    )
    return TELEFON


async def telefon_kiritish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Orqaga":
        await update.message.reply_text(
            "👤 Ismingizni kiriting:",
            reply_markup=ReplyKeyboardMarkup([["🔙 Orqaga"]], resize_keyboard=True)
        )
        return ISM

    context.user_data["telefon"] = update.message.text
    data = context.user_data

    await update.message.reply_text(
        f"✅ *Navbatingiz qabul qilindi!*\n\n"
        f"📋 *Ma'lumotlar:*\n"
        f"👤 Ism: {data['ism']}\n"
        f"✂️ Xizmat: {data['xizmat']}\n"
        f"⏰ Vaqt: {data['vaqt']}\n"
        f"📞 Telefon: {data['telefon']}\n\n"
        f"⚠️ Iltimos, belgilangan vaqtda keling!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 *YANGI NAVBAT!*\n\n"
                 f"👤 Ism: {data['ism']}\n"
                 f"✂️ Xizmat: {data['xizmat']}\n"
                 f"⏰ Vaqt: {data['vaqt']}\n"
                 f"📞 Telefon: {data['telefon']}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Admin xabar yuborishda xato: {e}")

    return ConversationHandler.END


async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()

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
    print("✅ Bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
