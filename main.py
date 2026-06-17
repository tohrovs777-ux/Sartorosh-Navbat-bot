import os
import logging
import psycopg2
import psycopg2.extras
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATABASE_URL = os.environ.get("DATABASE_URL")

SARTOR_ISM, SARTOR_MANZIL, SARTOR_TELEFON, SARTOR_NARX = range(4)
MIJOZ_TANLASH, MIJOZ_XIZMAT, MIJOZ_VAQT, MIJOZ_ISM, MIJOZ_TELEFON = range(4, 9)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
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
    cur.execute("""
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
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tayyor!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sartaroshxonalar WHERE ega_id=%s", (update.effective_user.id,))
    sartor = cur.fetchone()
    cur.close()
    conn.close()

    keyboard = [
        ["💈 Sartaroshxona topish"],
        ["🏪 Sartaroshxona ro'yxatdan o'tkazish"],
        ["📋 Mening navbatlarim"],
    ]
    if sartor:
        keyboard.insert(1, ["⚙️ Mening sartaroshxonam"])

    await update.message.reply_text(
        "💈 Sartarosh Platformaga xush kelibsiz!\n\nNimani xohlaysiz?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

# === SARTAROSHXONA RO'YXATDAN O'TISH ===
async def sartor_royxat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sartaroshxonalar WHERE ega_id=%s", (update.effective_user.id,))
    mavjud = cur.fetchone()
    cur.close()
    conn.close()

    if mavjud:
        await update.message.reply_text("❌ Siz allaqachon ro'yxatdan o'tgansiz!\n\n⚙️ Mening sartaroshxonam tugmasini bosing.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🏪 Sartaroshxona nomi kiriting:",
        reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True)
    )
    return SARTOR_ISM

async def sartor_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_ism"] = update.message.text
    await update.message.reply_text("📍 To'liq manzilini kiriting:\nMasalan: Toshkent, Chilonzor, 5-mavze 12-uy")
    return SARTOR_MANZIL

async def sartor_manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_manzil"] = update.message.text
    await update.message.reply_text("📞 Telefon raqami:\nMasalan: +998901234567")
    return SARTOR_TELEFON

async def sartor_telefon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["sartor_telefon"] = update.message.text
    await update.message.reply_text("💰 Narxlarni kiriting:\nMasalan: Soch-15000, Soqol-10000, Ikkalasi-20000")
    return SARTOR_NARX

async def sartor_narx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    data = context.user_data

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sartaroshxonalar (ega_id, ism, manzil, telefon, narx)
        VALUES (%s, %s, %s, %s, %s)
    """, (update.effective_user.id, data["sartor_ism"], data["sartor_manzil"],
          data["sartor_telefon"], update.message.text))
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(
        f"✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"🏪 Nom: {data['sartor_ism']}\n"
        f"📍 Manzil: {data['sartor_manzil']}\n"
        f"📞 Telefon: {data['sartor_telefon']}\n"
        f"💰 Narxlar: {update.message.text}\n\n"
        f"Endi mijozlar sizni topa oladi! 🎉"
    )
    return await start(update, context)

# === MENING SARTAROSHXONAM ===
async def mening_sartorim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM sartaroshxonalar WHERE ega_id=%s", (update.effective_user.id,))
    sartor = cur.fetchone()
    cur.execute("""
        SELECT * FROM navbatlar WHERE sartarosh_id=%s AND holat='kutilmoqda'
        ORDER BY yaratilgan DESC LIMIT 10
    """, (sartor["id"],))
    navbatlar = cur.fetchall()
    cur.close()
    conn.close()

    matn = (
        f"⚙️ Sizning sartaroshxonangiz:\n\n"
        f"🏪 {sartor['ism']}\n"
        f"📍 {sartor['manzil']}\n"
        f"📞 {sartor['telefon']}\n"
        f"💰 {sartor['narx']}\n\n"
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
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM sartaroshxonalar WHERE faol=TRUE ORDER BY id DESC")
    sartorllar = cur.fetchall()
    cur.close()
    conn.close()

    if not sartorllar:
        await update.message.reply_text("😔 Hozircha ro'yxatdan o'tgan sartaroshxona yo'q.")
        return ConversationHandler.END

    context.user_data["sartor_list"] = list(sartorllar)
    keyboard = []
    matn = "💈 Mavjud sartaroshxonalar:\n\n"

    for i, s in enumerate(sartorllar, 1):
        matn += f"{i}. 🏪 {s['ism']}\n📍 {s['manzil']}\n💰 {s['narx']}\n📞 {s['telefon']}\n\n"
        keyboard.append([f"{i}. {s['ism']}"])

    keyboard.append(["❌ Bekor qilish"])
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

    context.user_data["tanlangan_sartor"] = dict(tanlangan)
    keyboard = [["✂️ Soch olish"], ["🪒 Soqol olish"], ["✂️🪒 Ikkalasi"], ["❌ Bekor qilish"]]
    await update.message.reply_text(
        f"✅ {tanlangan['ism']} tanlandi!\n\nQaysi xizmat?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MIJOZ_XIZMAT

async def mijoz_xizmat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    xizmatlar = ["✂️ Soch olish", "🪒 Soqol olish", "✂️🪒 Ikkalasi"]
    if update.message.text not in xizmatlar:
        await update.message.reply_text("Ro'yxatdan tanlang!")
        return MIJOZ_XIZMAT
    context.user_data["xizmat"] = update.message.text
    vaqtlar = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"]
    keyboard = [vaqtlar[i:i+2] for i in range(0, len(vaqtlar), 2)]
    keyboard.append(["❌ Bekor qilish"])
    await update.message.reply_text("⏰ Vaqtni tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return MIJOZ_VAQT

async def mijoz_vaqt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    vaqtlar = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"]
    if update.message.text not in vaqtlar:
        await update.message.reply_text("Vaqtni tanlang!")
        return MIJOZ_VAQT
    context.user_data["vaqt"] = update.message.text
    await update.message.reply_text("👤 Ismingiz:", reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True))
    return MIJOZ_ISM

async def mijoz_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)
    context.user_data["mijoz_ism"] = update.message.text
    await update.message.reply_text("📞 Telefon raqamingiz:")
    return MIJOZ_TELEFON

async def mijoz_telefon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await start(update, context)

    data = context.user_data
    sartor = data["tanlangan_sartor"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO navbatlar (sartarosh_id, mijoz_id, mijoz_ism, mijoz_telefon, xizmat, vaqt)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sartor["id"], update.effective_user.id,
          data["mijoz_ism"], update.message.text,
          data["xizmat"], data["vaqt"]))
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(
        f"✅ Navbat qabul qilindi!\n\n"
        f"🏪 {sartor['ism']}\n"
        f"📍 {sartor['manzil']}\n"
        f"📞 {sartor['telefon']}\n"
        f"✂️ {data['xizmat']} | ⏰ {data['vaqt']}\n\n"
        f"Belgilangan vaqtda keling! 🎉",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        await context.bot.send_message(
            chat_id=sartor["ega_id"],
            text=f"🔔 YANGI NAVBAT!\n\n"
                 f"👤 {data['mijoz_ism']}\n"
                 f"📞 {update.message.text}\n"
                 f"✂️ {data['xizmat']} | ⏰ {data['vaqt']}"
        )
    except Exception as e:
        logging.error(f"Xato: {e}")

    return await start(update, context)

# === MENING NAVBATLARIM ===
async def mening_navbatlarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT n.*, s.ism as sartor_ism, s.manzil, s.telefon
        FROM navbatlar n
        JOIN sartaroshxonalar s ON n.sartarosh_id = s.id
        WHERE n.mijoz_id=%s ORDER BY n.yaratilgan DESC LIMIT 5
    """, (update.effective_user.id,))
    navbatlar = cur.fetchall()
    cur.close()
    conn.close()

    if not navbatlar:
        await update.message.reply_text("😔 Hozircha navbatingiz yo'q.")
        return ConversationHandler.END

    matn = "📋 Sizning navbatlaringiz:\n\n"
    for n in navbatlar:
        matn += f"🏪 {n['sartor_ism']}\n📍 {n['manzil']}\n✂️ {n['xizmat']} | ⏰ {n['vaqt']}\n📊 {n['holat']}\n\n"
    await update.message.reply_text(matn)
    return ConversationHandler.END

def main():
    init_db()
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
