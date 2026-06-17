import os
import logging
import asyncio
import asyncpg
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATABASE_URL = os.environ.get("DATABASE_URL")

# Bosqichlar - Sartaroshxona egasi
SARTOR_ISM, SARTOR_MANZIL, SARTOR_TELEFON, SARTOR_NARX = range(4)

# Bosqichlar - Mijoz
MIJOZ_TANLASH, MIJOZ_XIZMAT, MIJOZ_VAQT, MIJOZ_ISM, MIJOZ_TELEFON = range(4, 9)

db_pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sartaroshxonalar (
                id SERIAL PRIMARY KEY,
                ega_id BIGINT UNIQUE,
                ism TEXT,
                manzil TEXT,
                telefon TEXT,
                narx TEXT,
                faol BOOLEAN DEFAULT TRUE,
                yaratilgan TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS navbatlar (
                id SERIAL PRIMARY KEY,
                sartarosh_id INTEGER REFERENCES sartaroshxonalar(id),
                mijoz_id BIGINT,
                mijoz_ism TEXT,
                mijoz_telefon TEXT,
                xizmat TEXT,
                vaqt TEXT,
                holat TEXT DEFAULT 'kutilmoqda',
                yaratilgan TIMESTAMP DEFAULT NOW()
            )
        """)
    print("✅ Database tayyor!")

# === ASOSIY MENU ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💈 Sartaroshxona topish"],
        ["🏪 Sartaroshxona ro'yxatdan o'tkazish"],
        ["📋 Mening navbatlarim"],
    ]
    # Agar sartarosh bo'lsa
    async with db_pool.acquire() as conn:
        sartor = await conn.fetchrow("SELECT * FROM sartaroshxonalar WHERE ega_id=$1", update.effective_user.id)
    if sartor:
        keyboard.insert(1, ["⚙️ Mening sartaroshxonam"])

    await update.message.reply_text(
        "💈 Sartarosh Platform ga xush kelibsiz!\n\nNimani xohlaysiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

# === SARTAROSHXONA RO'YXATDAN O'TISH ===
async def sartor_royxat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with db_pool.acquire() as conn:
        mavjud = await conn.fetchrow("SELECT * FROM sartaroshxonalar WHERE ega_id=$1", update.effective_user.id)
    if mavjud:
        await update.message.reply_text("❌ Siz allaqachon ro'yxatdan o'tgansiz!\n\n⚙️ Mening sartaroshxonam tugmasini bosing.")
        return ConversationHandler.END
    await update.message.reply_text(
        "🏪 Sartaroshxona ro'yxatdan o'tkazish\n\nSartaroshxona nomini kiriting:",
        reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True)
    )
    return SARTOR_ISM

async def sartor_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_ism"] = update.message.text
    await update.message.reply_text("📍 Manzilini kiriting (to'liq):\nMasalan: Toshkent, Chilonzor, 5-mavze 12-uy")
    return SARTOR_MANZIL

async def sartor_manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_manzil"] = update.message.text
    await update.message.reply_text("📞 Telefon raqamini kiriting:\nMasalan: +998901234567")
    return SARTOR_TELEFON

async def sartor_telefon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_telefon"] = update.message.text
    await update.message.reply_text(
        "💰 Narxlarni kiriting:\nMasalan: Soch - 15000, Soqol - 10000, Ikkalasi - 20000"
    )
    return SARTOR_NARX

async def sartor_narx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_narx"] = update.message.text
    data = context.user_data

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO sartaroshxonalar (ega_id, ism, manzil, telefon, narx)
            VALUES ($1, $2, $3, $4, $5)
        """, update.effective_user.id, data["sartor_ism"], data["sartor_manzil"],
            data["sartor_telefon"], data["sartor_narx"])

    await update.message.reply_text(
        f"✅ Sartaroshxona muvaffaqiyatli ro'yxatdan o'tdi!\n\n"
        f"🏪 Nom: {data['sartor_ism']}\n"
        f"📍 Manzil: {data['sartor_manzil']}\n"
        f"📞 Telefon: {data['sartor_telefon']}\n"
        f"💰 Narxlar: {data['sartor_narx']}\n\n"
        f"Endi mijozlar sizni topa oladi! 🎉"
    )
    return await start(update, context)

# === MENING SARTAROSHXONAM ===
async def mening_sartorim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with db_pool.acquire() as conn:
        sartor = await conn.fetchrow("SELECT * FROM sartaroshxonalar WHERE ega_id=$1", update.effective_user.id)
        navbatlar = await conn.fetch("""
            SELECT * FROM navbatlar WHERE sartarosh_id=$1 AND holat='kutilmoqda'
            ORDER BY yaratilgan DESC LIMIT 10
        """, sartor["id"])

    matn = (
        f"⚙️ Sizning sartaroshxonangiz:\n\n"
        f"🏪 Nom: {sartor['ism']}\n"
        f"📍 Manzil: {sartor['manzil']}\n"
        f"📞 Telefon: {sartor['telefon']}\n"
        f"💰 Narxlar: {sartor['narx']}\n\n"
    )

    if navbatlar:
        matn += f"📋 Kutilayotgan navbatlar ({len(navbatlar)} ta):\n\n"
        for n in navbatlar:
            matn += f"👤 {n['mijoz_ism']} | {n['xizmat']} | ⏰ {n['vaqt']} | 📞 {n['mijoz_telefon']}\n"
    else:
        matn += "📋 Hozircha navbat yo'q."

    await update.message.reply_text(matn)
    return ConversationHandler.END

# === SARTAROSHXONA TOPISH ===
async def sartor_topish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with db_pool.acquire() as conn:
        sartorllar = await conn.fetch("SELECT * FROM sartaroshxonalar WHERE faol=TRUE ORDER BY id DESC")

    if not sartorllar:
        await update.message.reply_text("😔 Hozircha ro'yxatdan o'tgan sartaroshxona yo'q.")
        return ConversationHandler.END

    keyboard = []
    context.user_data["sartorllar"] = {str(s["id"]): s for s in sartorllar}

    matn = "💈 Mavjud sartaroshxonalar:\n\n"
    for i, s in enumerate(sartorllar, 1):
        matn += f"{i}. 🏪 {s['ism']}\n📍 {s['manzil']}\n💰 {s['narx']}\n📞 {s['telefon']}\n\n"
        keyboard.append([f"{i}. {s['ism']}"])

    keyboard.append(["❌ Bekor qilish"])
    context.user_data["sartor_list"] = list(sartorllar)

    await update.message.reply_text(
        matn + "Qaysi sartaroshxonani tanlaysiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MIJOZ_TANLASH

async def mijoz_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)

    sartor_list = context.user_data.get("sartor_list", [])
    tanlangan = None

    for i, s in enumerate(sartor_list, 1):
        if update.message.text.startswith(f"{i}."):
            tanlangan = s
            break

    if not tanlangan:
        await update.message.reply_text("Iltimos, ro'yxatdan tanlang!")
        return MIJOZ_TANLASH

    context.user_data["tanlangan_sartor"] = tanlangan

    keyboard = [
        ["✂️ Soch olish"],
        ["🪒 Soqol olish"],
        ["✂️🪒 Ikkalasi"],
        ["❌ Bekor qilish"]
    ]
    await update.message.reply_text(
        f"✅ {tanlangan['ism']} tanlandi!\n\nQaysi xizmatni xohlaysiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MIJOZ_XIZMAT

async def mijoz_xizmat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)

    xizmatlar = ["✂️ Soch olish", "🪒 Soqol olish", "✂️🪒 Ikkalasi"]
    if update.message.text not in xizmatlar:
        await update.message.reply_text("Iltimos, ro'yxatdan tanlang!")
        return MIJOZ_XIZMAT

    context.user_data["xizmat"] = update.message.text

    vaqtlar = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"]
    keyboard = [vaqtlar[i:i+2] for i in range(0, len(vaqtlar), 2)]
    keyboard.append(["❌ Bekor qilish"])

    await update.message.reply_text(
        "⏰ Qaysi vaqtda kelasiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MIJOZ_VAQT

async def mijoz_vaqt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)

    vaqtlar = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"]
    if update.message.text not in vaqtlar:
        await update.message.reply_text("Iltimos, vaqtni tanlang!")
        return MIJOZ_VAQT

    context.user_data["vaqt"] = update.message.text
    await update.message.reply_text(
        "👤 Ismingizni kiriting:",
        reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True)
    )
    return MIJOZ_ISM

async def mijoz_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["mijoz_ism"] = update.message.text
    await update.message.reply_text(
        "📞 Telefon raqamingizni kiriting:\nMasalan: +998901234567"
    )
    return MIJOZ_TELEFON

async def mijoz_telefon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)

    context.user_data["mijoz_telefon"] = update.message.text
    data = context.user_data
    sartor = data["tanlangan_sartor"]

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO navbatlar (sartarosh_id, mijoz_id, mijoz_ism, mijoz_telefon, xizmat, vaqt)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, sartor["id"], update.effective_user.id,
            data["mijoz_ism"], data["mijoz_telefon"],
            data["xizmat"], data["vaqt"])

    await update.message.reply_text(
        f"✅ Navbat muvaffaqiyatli qabul qilindi!\n\n"
        f"🏪 Sartaroshxona: {sartor['ism']}\n"
        f"📍 Manzil: {sartor['manzil']}\n"
        f"📞 Tel: {sartor['telefon']}\n"
        f"✂️ Xizmat: {data['xizmat']}\n"
        f"⏰ Vaqt: {data['vaqt']}\n\n"
        f"Belgilangan vaqtda keling! 🎉",
        reply_markup=ReplyKeyboardRemove()
    )

    # Sartarosh ga xabar
    try:
        await context.bot.send_message(
            chat_id=sartor["ega_id"],
            text=f"🔔 YANGI NAVBAT!\n\n"
                 f"👤 Mijoz: {data['mijoz_ism']}\n"
                 f"📞 Tel: {data['mijoz_telefon']}\n"
                 f"✂️ Xizmat: {data['xizmat']}\n"
                 f"⏰ Vaqt: {data['vaqt']}"
        )
    except Exception as e:
        logging.error(f"Xato: {e}")

    return await start(update, context)

# === MENING NAVBATLARIM ===
async def mening_navbatlarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with db_pool.acquire() as conn:
        navbatlar = await conn.fetch("""
            SELECT n.*, s.ism as sartor_ism, s.manzil, s.telefon
            FROM navbatlar n
            JOIN sartaroshxonalar s ON n.sartarosh_id = s.id
            WHERE n.mijoz_id=$1
            ORDER BY n.yaratilgan DESC LIMIT 5
        """, update.effective_user.id)

    if not navbatlar:
        await update.message.reply_text("😔 Hozircha navbatingiz yo'q.")
        return ConversationHandler.END

    matn = "📋 Sizning navbatlaringiz:\n\n"
    for n in navbatlar:
        matn += (
            f"🏪 {n['sartor_ism']}\n"
            f"📍 {n['manzil']}\n"
            f"✂️ {n['xizmat']} | ⏰ {n['vaqt']}\n"
            f"📊 Holat: {n['holat']}\n\n"
        )
    await update.message.reply_text(matn)
    return ConversationHandler.END

def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💈 Sartaroshxona topish$"), sartor_topish),
            MessageHandler(filters.Regex("^🏪 Sartaroshxona ro'yxatdan o'tkazish$"), sartor_royxat),
            MessageHandler(filters.Regex("^⚙️ Mening sartaroshxonam$"), mening_sartorim),
            MessageHandler(filters.Regex("^📋 Mening navbatlarim$"), mening_navbatlarim),
        ],
        states={
            SARTOR_ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, sartor_ism)],
            SARTOR_MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sartor_manzil)],
            SARTOR_TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, sartor_telefon)],
            SARTOR_NARX: [MessageHandler(filters.TEXT & ~filters.COMMAND, sartor_narx)],
            MIJOZ_TANLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, mijoz_tanlash)],
            MIJOZ_XIZMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mijoz_xizmat)],
            MIJOZ_VAQT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mijoz_vaqt)],
            MIJOZ_ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, mijoz_ism)],
            MIJOZ_TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, mijoz_telefon)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
