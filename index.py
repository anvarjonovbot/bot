#!/usr/bin/env python3
"""
Vakansiya Telegram Boti (24/7 UptimeRobot moslashuvi bilan)
=========================================================
Kutubxonalar:
  pip install pyTelegramBotAPI flask
"""

import telebot
from telebot import types
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8787381343:AAHIdMEjAreb8pmD3v9SfWNSIrn2JHMaE80"  # @BotFather dan oling
ADMIN_IDS = [123456789]             # Admin Telegram ID lari (o'zgartiring!)

# Ma'lumotlar fayli
DATA_FILE = "vacancies.json"

# ======================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# 24/7 ishlash uchun UptimeRobot kelib uriladigan manzil
@app.route('/')
def home():
    return "Bot 24/7 rejimda faol ishlamoqda!"

def run_web_server():
    # Render, Replit yoki shunga o'xshash platformalar portni o'zi beradi
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ===================== MA'LUMOTLAR =====================

def load_data():
    """JSON fayldan ma'lumot yuklash"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"vacancies": [], "next_id": 1, "employers": {}}

def save_data(data):
    """Ma'lumotni JSON faylga saqlash"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Foydalanuvchi holatlari (state machine)
user_states = {}
user_temp = {}

# Asosiy menyu tugmalari ro'yxati
MAIN_MENU_BUTTONS = [
    "📋 Vakansiyalar", "🔍 Qidirish",
    "➕ Vakansiya qo'shish", "➕ Vakansiya yuborish (ish beruvchi)",
    "🗑 Vakansiya o'chirish", "📊 Statistika", "ℹ️ Yordam"
]

# ===================== YORDAMCHI FUNKSIYALAR =====================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_main_keyboard(user_id):
    """Asosiy menyu tugmalari"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📋 Vakansiyalar", "🔍 Qidirish")
    if is_admin(user_id):
        kb.row("➕ Vakansiya qo'shish", "🗑 Vakansiya o'chirish")
        kb.row("📊 Statistika")
    else:
        kb.row("➕ Vakansiya yuborish (ish beruvchi)")
    kb.row("ℹ️ Yordam")
    return kb

def format_vacancy(v):
    """Vakansiyani chiroyli ko'rsatish"""
    salary = v.get("salary", "Kelishiladi")
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 *{v['title']}*  #{v['id']}\n"
        f"🏢 Kompaniya: {v['company']}\n"
        f"📍 Manzil: {v['location']}\n"
        f"💰 Maosh: {salary}\n"
        f"📝 Tavsif:\n{v['description']}\n"
        f"📞 Bog'lanish: {v['contact']}\n"
        f"📅 Sana: {v['date']}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    return text

# ===================== /START =====================

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    user_states[uid] = None
    user_temp.pop(uid, None)

    welcome = (
        f"👋 Salom, *{name}*!\n\n"
        "🤖 *Vakansiya Botiga xush kelibsiz!*\n\n"
        "Bu bot orqali:\n"
        "• 📋 Mavjud vakansiyalarni ko'ring\n"
        "• 🔍 Kalit so'z bilan qidiring\n"
        "• ➕ Vakansiya joylashtiring\n\n"
        "Quyidagi menyudan tanlang 👇"
    )
    bot.send_message(message.chat.id, welcome,
                     parse_mode="Markdown",
                     reply_markup=get_main_keyboard(uid))

# ===================== VAKANSIYALARNI KO'RISH =====================

@bot.message_handler(func=lambda m: m.text == "📋 Vakansiyalar")
def show_vacancies(message):
    uid = message.from_user.id
    user_states[uid] = None

    data = load_data()
    vacancies = data["vacancies"]

    if not vacancies:
        bot.send_message(message.chat.id,
                         "😔 Hozircha hech qanday vakansiya yo'q.\n"
                         "Birinchi bo'lib vakansiya joylashtiring!",
                         reply_markup=get_main_keyboard(uid))
        return

    bot.send_message(message.chat.id,
                     f"📋 *Jami {len(vacancies)} ta vakansiya (Oxirgi 10 tasi):*",
                     parse_mode="Markdown")

    for v in vacancies[-10:]:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "📩 Ariza yuborish", callback_data=f"apply_{v['id']}"))
        bot.send_message(message.chat.id,
                         format_vacancy(v),
                         parse_mode="Markdown",
                         reply_markup=kb)

# ===================== QIDIRISH =====================

@bot.message_handler(func=lambda m: m.text == "🔍 Qidirish")
def search_start(message):
    user_states[message.from_user.id] = "searching"
    bot.send_message(message.chat.id,
                     "🔍 Qidirish uchun kalit so'z kiriting:\n"
                     "_(masalan: dasturchi, hisobchi, sotuvchi)_",
                     parse_mode="Markdown",
                     reply_markup=types.ReplyKeyboardRemove())

# ===================== VAKANSIYA QO'SHISH =====================

@bot.message_handler(func=lambda m: m.text in [
    "➕ Vakansiya qo'shish",
    "➕ Vakansiya yuborish (ish beruvchi)"
])
def add_vacancy_start(message):
    uid = message.from_user.id
    user_states[uid] = "add_title"
    user_temp[uid] = {}

    bot.send_message(message.chat.id,
                     "✍️ *Yangi vakansiya qo'shish*\n\n"
                     "1️⃣ Lavozim nomini kiriting:\n"
                     "_(masalan: Python Dasturchi)_",
                     parse_mode="Markdown",
                     reply_markup=types.ReplyKeyboardRemove())

# ===================== VAKANSIYA O'CHIRISH (ADMIN) =====================

@bot.message_handler(func=lambda m: m.text == "🗑 Vakansiya o'chirish")
def delete_vacancy_start(message):
    uid = message.from_user.id
    user_states[uid] = None

    if not is_admin(uid):
        bot.send_message(message.chat.id, "❌ Ruxsat yo'q!")
        return

    data = load_data()
    if not data["vacancies"]:
        bot.send_message(message.chat.id, "Vakansiyalar yo'q.")
        return

    kb = types.InlineKeyboardMarkup()
    for v in data["vacancies"]:
        kb.add(types.InlineKeyboardButton(
            f"❌ #{v['id']} — {v['title']}",
            callback_data=f"delete_{v['id']}"
        ))
    bot.send_message(message.chat.id,
                     "🗑 O'chirish uchun vakansiyani tanlang:",
                     reply_markup=kb)

# ===================== STATISTIKA (ADMIN) =====================

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def statistics(message):
    uid = message.from_user.id
    user_states[uid] = None

    if not is_admin(uid):
        bot.send_message(message.chat.id, "❌ Ruxsat yo'q!")
        return

    data = load_data()
    total = len(data["vacancies"])
    bot.send_message(
        message.chat.id,
        f"📊 *Statistika*\n\n"
        f"💼 Jami vakansiyalar: *{total}* ta\n"
        f"🗓 So'nggi yangilanish: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="Markdown"
    )

# ===================== YORDAM =====================

@bot.message_handler(func=lambda m: m.text == "ℹ️ Yordam")
def help_msg(message):
    uid = message.from_user.id
    user_states[uid] = None
    bot.send_message(
        message.chat.id,
        "ℹ️ *Yordam*\n\n"
        "📋 *Vakansiyalar* — barcha vakansiyalarni ko'rish\n"
        "🔍 *Qidirish* — kalit so'z bilan qidirish\n"
        "➕ *Vakansiya qo'shish* — yangi ish o'rni e'lon qilish\n"
        "📩 *Ariza yuborish* — vakansiyaga murojaat qilish\n\n"
        "❓ Savollar bo'lsa admin bilan bog'laning.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(uid)
    )

# ===================== MATN XABARLARI (STATE MACHINE) =====================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    state = user_states.get(uid)
    text = message.text.strip()

    # Menyu tugmasi bosilsa — holatni bekor qilish
    if text in MAIN_MENU_BUTTONS:
        user_states[uid] = None
        user_temp.pop(uid, None)
        bot.send_message(message.chat.id,
                         "Amal bekor qilindi. Bosh menyu:",
                         reply_markup=get_main_keyboard(uid))
        return

    # Holat yo'q bo'lsa
    if not state:
        bot.send_message(message.chat.id,
                         "Iltimos, menyudan foydalaning 👇",
                         reply_markup=get_main_keyboard(uid))
        return

    # ----- QIDIRISH -----
    if state == "searching":
        user_states[uid] = None
        data = load_data()
        results = [
            v for v in data["vacancies"]
            if text.lower() in v["title"].lower()
            or text.lower() in v["description"].lower()
            or text.lower() in v["company"].lower()
        ]
        if not results:
            bot.send_message(message.chat.id,
                             f"😔 *'{text}'* bo'yicha vakansiya topilmadi.",
                             parse_mode="Markdown",
                             reply_markup=get_main_keyboard(uid))
            return

        bot.send_message(message.chat.id,
                         f"🔍 *'{text}'* bo'yicha {len(results)} ta natija:",
                         parse_mode="Markdown")
        for v in results:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton(
                "📩 Ariza yuborish", callback_data=f"apply_{v['id']}"))
            bot.send_message(message.chat.id, format_vacancy(v),
                             parse_mode="Markdown", reply_markup=kb)
        bot.send_message(message.chat.id, "Asosiy menyu:",
                         reply_markup=get_main_keyboard(uid))
        return

    # ----- VAKANSIYA QO'SHISH BOSQICHLARI -----
    if state == "add_title":
        user_temp[uid]["title"] = text
        user_states[uid] = "add_company"
        bot.send_message(message.chat.id, "2️⃣ Kompaniya nomini kiriting:")
        return

    if state == "add_company":
        user_temp[uid]["company"] = text
        user_states[uid] = "add_location"
        bot.send_message(message.chat.id,
                         "3️⃣ Manzilni kiriting:\n_(shahar yoki tuman)_",
                         parse_mode="Markdown")
        return

    if state == "add_location":
        user_temp[uid]["location"] = text
        user_states[uid] = "add_salary"
        bot.send_message(message.chat.id,
                         "4️⃣ Maosh kiriting:\n_(masalan: 3 000 000 so'm yoki Kelishiladi)_",
                         parse_mode="Markdown")
        return

    if state == "add_salary":
        user_temp[uid]["salary"] = text
        user_states[uid] = "add_description"
        bot.send_message(message.chat.id,
                         "5️⃣ Vakansiya tavsifini kiriting:\n"
                         "_(talablar, vazifalar, ish vaqti va h.k.)_",
                         parse_mode="Markdown")
        return

    if state == "add_description":
        user_temp[uid]["description"] = text
        user_states[uid] = "add_contact"
        bot.send_message(message.chat.id,
                         "6️⃣ Bog'lanish uchun ma'lumot kiriting:\n"
                         "_(telefon, Telegram username yoki email)_",
                         parse_mode="Markdown")
        return

    if state == "add_contact":
        user_temp[uid]["contact"] = text
        user_states[uid] = None

        data = load_data()
        new_vacancy = {
            "id": data["next_id"],
            "title": user_temp[uid]["title"],
            "company": user_temp[uid]["company"],
            "location": user_temp[uid]["location"],
            "salary": user_temp[uid]["salary"],
            "description": user_temp[uid]["description"],
            "contact": user_temp[uid]["contact"],
            "date": datetime.now().strftime("%d.%m.%Y"),
            "added_by": uid
        }
        data["vacancies"].append(new_vacancy)
        data["next_id"] += 1
        save_data(data)
        user_temp.pop(uid, None)

        bot.send_message(
            message.chat.id,
            "✅ *Vakansiya muvaffaqiyatli qo'shildi!*\n\n" + format_vacancy(new_vacancy),
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(uid)
        )

        # Adminlarga xabar berish (admin bo'lmagan foydalanuvchi qo'shsa)
        if not is_admin(uid):
            username = message.from_user.username or "username yo'q"
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        "🔔 *Yangi vakansiya yuborildi!*\n\n"
                        + format_vacancy(new_vacancy)
                        + f"\n\n👤 Yuboruvchi: @{username}",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        return

# ===================== CALLBACK (INLINE TUGMALAR) =====================

@bot.callback_query_handler(func=lambda c: c.data.startswith("apply_"))
def apply_vacancy(call):
    vacancy_id = int(call.data.split("_")[1])
    data = load_data()
    vacancy = next((v for v in data["vacancies"] if v["id"] == vacancy_id), None)

    if not vacancy:
        bot.answer_callback_query(call.id, "Vakansiya topilmadi!")
        return

    user = call.from_user
    contact_info = vacancy["contact"]

    bot.answer_callback_query(call.id, "✅ Ariza yuborildi!")
    bot.send_message(
        call.message.chat.id,
        f"📩 *Arizangiz qabul qilindi!*\n\n"
        f"💼 Vakansiya: *{vacancy['title']}*\n"
        f"🏢 Kompaniya: {vacancy['company']}\n\n"
        f"📞 Quyidagi kontakt orqali bog'laning:\n"
        f"*{contact_info}*\n\n"
        "🍀 Omad tilaymiz!",
        parse_mode="Markdown"
    )

    # Adminlarga ariza haqida xabar
    username = user.username or "username yo'q"
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(
                admin_id,
                f"📩 *Yangi ariza!*\n\n"
                f"💼 Vakansiya: *{vacancy['title']}* (ID: #{vacancy['id']})\n"
                f"🏢 Kompaniya: *{vacancy['company']}*\n"
                f"👤 Ariza beruvchi: {user.first_name} (@{username})\n"
                f"🆔 ID: {user.id}",
                parse_mode="Markdown"
            )
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("delete_"))
def delete_vacancy(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!")
        return

    vacancy_id = int(call.data.split("_")[1])
    data = load_data()
    before = len(data["vacancies"])
    data["vacancies"] = [v for v in data["vacancies"] if v["id"] != vacancy_id]

    if len(data["vacancies"]) < before:
        save_data(data)
        bot.answer_callback_query(call.id, "✅ Vakansiya o'chirildi!")
        bot.edit_message_text(
            f"✅ Vakansiya #{vacancy_id} muvaffaqiyatli o'chirildi.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Vakansiya topilmadi!")

# ===================== BOTNI ISHGA TUSHIRISH =====================

if __name__ == "__main__":
    print("🤖 Vakansiya boti fonda server bilan ishga tushmoqda...")
    
    # Flask serverni alohida oqimda (Thread) ishga tushiramiz
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Botni asosiy oqimda ishga tushiramiz
    bot.infinity_polling()