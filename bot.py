import telebot
import datetime
import json
import os
from collections import defaultdict

# اطلاعات ربات و ادمین
TOKEN = "8392998317:AAEQI1n-SZgDVfoNr_8GLkj7tjEVKmkXeC8"
ADMIN_ID = 5489748445
ADMIN_USERNAME = "GolMohammadiM"
VIOLATION_GROUP_ID = -4878202393

# نام فایل‌ها برای ذخیره اطلاعات
SUBSCRIPTIONS_FILE = 'subscriptions.json'
TEACHERS_FILE = 'teachers.json'
SCORES_FILE = 'teacher_scores.json'
MESSAGE_DATABASE_FILE = 'message_database.json'
PHONE_NUMBERS_FILE = 'phone_numbers.json'

# نگاشت درس‌های فارسی به انگلیسی و بالعکس
SUBJECT_MAP_FA_TO_EN = {
    "ریاضی": "math",
    "فیزیک": "physics",
}
SUBJECT_MAP_EN_TO_FA = {v: k for k, v in SUBJECT_MAP_FA_TO_EN.items()}

# لیست دبیران
teachers_by_subject = {}

# تمام دبیران
all_teachers_ids = set()

# اطلاعات اشتراک‌ها
subscriptions = {}

# اطلاعات امتیاز دبیران
teacher_scores = {}

# دیتابیس پیام‌ها
message_database = {}

# وضعیت پرسیدن سوال کاربر و درس انتخابی
user_question_state = {}

# گزارشات در حال انتظار
pending_reports = {}

# شماره تلفن‌های کاربران
phone_numbers = {}

bot = telebot.TeleBot(TOKEN)

# ---------- توابع برای خواندن و نوشتن اطلاعات در فایل ----------

def load_data():
    global teachers_by_subject, all_teachers_ids, subscriptions, teacher_scores, message_database, phone_numbers
    
    # بارگذاری دبیران
    if os.path.exists(TEACHERS_FILE):
        with open(TEACHERS_FILE, 'r', encoding='utf-8') as f:
            teachers_by_subject = json.load(f)
            for subject_teachers in teachers_by_subject.values():
                for teacher_id in subject_teachers:
                    all_teachers_ids.add(teacher_id)
    
    # بارگذاری اشتراک‌ها
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            loaded_subscriptions = json.load(f)
            for user_id_str, data in loaded_subscriptions.items():
                user_id = int(user_id_str)
                subscriptions[user_id] = {
                    'end_date': datetime.datetime.strptime(data['end_date'], '%Y-%m-%d %H:%M:%S'),
                    'banned': data['banned'],
                    'telegram_username': data.get('telegram_username'),
                    'suspended_until': datetime.datetime.strptime(data['suspended_until'], '%Y-%m-%d %H:%M:%S') if data.get('suspended_until') else None,
                    'math_questions': data.get('math_questions', 0),
                    'physics_questions': data.get('physics_questions', 0)
                }
    
    # بارگذاری امتیاز دبیران
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            teacher_scores = json.load(f)
            teacher_scores = {int(k): v for k, v in teacher_scores.items()}
                
    # بارگذاری دیتابیس پیام‌ها
    if os.path.exists(MESSAGE_DATABASE_FILE):
        with open(MESSAGE_DATABASE_FILE, 'r', encoding='utf-8') as f:
            message_database = json.load(f)
            message_database = {int(k): v for k, v in message_database.items()}
            
    # بارگذاری شماره تلفن‌ها
    if os.path.exists(PHONE_NUMBERS_FILE):
        with open(PHONE_NUMBERS_FILE, 'r', encoding='utf-8') as f:
            phone_numbers = json.load(f)
            phone_numbers = {int(k): v for k, v in phone_numbers.items()}

def save_data():
    # ذخیره دبیران
    with open(TEACHERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(teachers_by_subject, f, ensure_ascii=False, indent=4)

    # ذخیره اشتراک‌ها
    serializable_subscriptions = {}
    for user_id, data in subscriptions.items():
        serializable_subscriptions[user_id] = {
            'end_date': data['end_date'].strftime('%Y-%m-%d %H:%M:%S'),
            'banned': data['banned'],
            'telegram_username': data.get('telegram_username'),
            'suspended_until': data.get('suspended_until').strftime('%Y-%m-%d %H:%M:%S') if data.get('suspended_until') else None,
            'math_questions': data.get('math_questions', 0),
            'physics_questions': data.get('physics_questions', 0)
        }
    with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_subscriptions, f, ensure_ascii=False, indent=4)

    # ذخیره امتیاز دبیران
    with open(SCORES_FILE, 'w', encoding='utf-8') as f:
        json.dump(teacher_scores, f, ensure_ascii=False, indent=4)
        
    # ذخیره دیتابیس پیام‌ها
    with open(MESSAGE_DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(message_database, f, ensure_ascii=False, indent=4)
        
    # ذخیره شماره تلفن‌ها
    with open(PHONE_NUMBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(phone_numbers, f, ensure_ascii=False, indent=4)

# ---------- بارگذاری اطلاعات هنگام شروع ربات ----------
load_data()

# ---------- توابع کمکی ----------
def check_subscription(chat_id):
    # چک می‌کند که کاربر اشتراک فعال و غیر بن شده دارد
    if chat_id not in subscriptions:
        return False
    
    user_data = subscriptions[chat_id]
    
    # چک کردن وضعیت بن
    if user_data['banned']:
        return False
        
    # چک کردن تعلیق موقت
    if user_data.get('suspended_until') and user_data['suspended_until'] > datetime.datetime.now():
        return False
        
    # چک کردن تاریخ انقضای اشتراک
    return user_data['end_date'] > datetime.datetime.now()

def get_teacher_keyboard(user_id, message_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    answer_button = telebot.types.InlineKeyboardButton(text="ارسال پاسخ", callback_data=f"answer_{user_id}_{message_id}")
    report_button = telebot.types.InlineKeyboardButton(text="گزارش تخلف", callback_data=f"report_{user_id}_{message_id}")
    keyboard.add(answer_button, report_button)
    return keyboard

def delete_question_messages(original_message_id):
    """حذف تمام پیام‌های مربوط به یک سوال از پیوی تمام دبیران"""
    messages_to_delete = []
    
    # پیدا کردن تمام پیام‌های مربوط به این سوال
    for msg_id, msg_data in list(message_database.items()):
        if msg_data['original_message_id'] == original_message_id:
            messages_to_delete.append((msg_id, msg_data))
    
    # حذف پیام‌ها از تلگرام و دیتابیس
    for msg_id, msg_data in messages_to_delete:
        try:
            bot.delete_message(msg_data['teacher_id'], msg_id)
        except Exception as e:
            print(f"Error deleting message {msg_id} from teacher {msg_data['teacher_id']}: {e}")
        
        # حذف از دیتابیس
        del message_database[msg_id]
    
    save_data()

# ---------- هندلرهای عمومی ----------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_username = message.from_user.username
    
    # ذخیره یوزرنیم اگر وجود دارد
    if user_username:
        if user_id in subscriptions:
            subscriptions[user_id]['telegram_username'] = user_username
            save_data()
    
    # بررسی نوع کاربر
    if user_id == ADMIN_ID:
        bot.reply_to(message, "سلام ادمین عزیز! به ربات مدیریت سوالات درسی خوش آمدید.\nبرای مشاهده دستورات /help را بزنید.")
    elif user_id in all_teachers_ids:
        score = teacher_scores.get(user_id, 0)
        bot.reply_to(message, f"سلام دبیر گرامی! به ربات مدیریت سوالات درسی خوش آمدید.\nبرای مشاهده امتیازت /score را بزن. امتیاز فعلی شما: {score}")
    else:
        # اگر کاربر شماره تلفن ندارد، درخواست شماره تلفن
        if user_id not in phone_numbers:
            keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            keyboard.add(telebot.types.KeyboardButton("اشتراک گذاری شماره تلفن", request_contact=True))
            bot.send_message(user_id, "لطفاً برای ادامه، شماره تلفن خود را به اشتراک بگذارید:", reply_markup=keyboard)
            return
            
        if check_subscription(user_id):
            subscription_end_date = subscriptions[user_id]['end_date'].strftime("%Y-%m-%d %H:%M")
            math_questions = subscriptions[user_id].get('math_questions', 0)
            physics_questions = subscriptions[user_id].get('physics_questions', 0)
            
            # چک کردن تعلیق موقت
            if subscriptions[user_id].get('suspended_until') and subscriptions[user_id]['suspended_until'] > datetime.datetime.now():
                suspended_until = subscriptions[user_id]['suspended_until'].strftime("%Y-%m-%d %H:%M")
                bot.reply_to(message, f"اشتراک شما تا تاریخ {subscription_end_date} فعال است، اما تا تاریخ {suspended_until} از ارسال سوال محروم هستید.")
                return
                
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("ریاضی", callback_data="ask_subject_math"))
            keyboard.add(telebot.types.InlineKeyboardButton("فیزیک", callback_data="ask_subject_physics"))
            bot.send_message(user_id, f"دانش‌آموز گرامی، اشتراک شما تا تاریخ {subscription_end_date} فعال است.\nتعداد سوالات باقیمانده:\nریاضی: {math_questions}\nفیزیک: {physics_questions}\n\nلطفاً درس مورد نظر برای ارسال سوال را انتخاب کنید:", reply_markup=keyboard)
        else:
            bot.reply_to(message, "دانش‌آموز گرامی، شما اشتراک فعالی ندارید. برای راهنمایی جهت تهیه اشتراک /help را بزنید.")

# هندلر برای دریافت شماره تلفن
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    contact = message.contact
    
    if contact.user_id == user_id:  # مطمئن شویم که شماره متعلق به خود کاربر است
        phone_numbers[user_id] = contact.phone_number
        save_data()
        
        # حذف کیبورد
        bot.send_message(user_id, "شماره تلفن شما با موفقیت ثبت شد.", reply_markup=telebot.types.ReplyKeyboardRemove())
        
        # ادامه فرآیند استارت
        if check_subscription(user_id):
            subscription_end_date = subscriptions[user_id]['end_date'].strftime("%Y-%m-%d %H:%M")
            math_questions = subscriptions[user_id].get('math_questions', 0)
            physics_questions = subscriptions[user_id].get('physics_questions', 0)
            
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("ریاضی", callback_data="ask_subject_math"))
            keyboard.add(telebot.types.InlineKeyboardButton("فیزیک", callback_data="ask_subject_physics"))
            bot.send_message(user_id, f"دانش‌آموز گرامی، اشتراک شما تا تاریخ {subscription_end_date} فعال است.\nتعداد سوالات باقیمانده:\nریاضی: {math_questions}\nفیزیک: {physics_questions}\n\nلطفاً درس مورد نظر برای ارسال سوال را انتخاب کنید:", reply_markup=keyboard)
        else:
            bot.reply_to(message, "دانش‌آموز گرامی، شما اشتراک فعالی ندارید. برای راهنمایی جهت تهیه اشتراک /help را بزنید.")
    else:
        bot.send_message(user_id, "لطفاً فقط شماره تلفن خودتان را به اشتراک بگذارید.")

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.chat.id
    if user_id == ADMIN_ID:
        subjects_list = ", ".join([f"'{en}' ({fa})" for fa, en in SUBJECT_MAP_FA_TO_EN.items()])
        bot.reply_to(message, f"""
            سلام ادمین عزیز!
            دستورات مدیریت ربات:
            /add_subscription [chat_id] [days] [math_questions] [physics_questions] - فعال کردن اشتراک برای کاربر
            /remove_subscription [chat_id] - غیرفعال کردن اشتراک کاربر
            /add_teacher [chat_id] [subject_en] - افزودن دبیر به درس مشخص
                (مثال: /add_teacher 123456789 math)
                لیست دروس معتبر (انگلیسی): {subjects_list}
            /remove_teacher [chat_id] [subject_en] - حذف دبیر از درس مشخص
                (مثال: /remove_teacher 123456789 math)
            /ban_user [chat_id] - بن کردن کاربر (اشتراک غیرفعال می‌شود)
            /unban_user [chat_id] - رفع بن کاربر
            /suspend_user [chat_id] [hours] - تعلیق موقت کاربر برای مدت مشخص (ساعت)
            /score [chat_id] - مشاهده امتیاز یک دبیر (اختیاری)
            /all_teacher_scores - مشاهده لیست امتیازات تمامی دبیران
            /decrease_score [chat_id] [amount] - کاهش امتیاز مشخص یک دبیر
            /get_phone [chat_id] - مشاهده شماره تلفن کاربر
            /add_questions [chat_id] [math/physics/all] [amount] - اضافه کردن سوال به کاربر
                (مثال: /add_questions 123456789 math 10 - اضافه کردن 10 سوال ریاضی)
                (مثال: /add_questions 123456789 all 20 - اضافه کردن 20 سوال به همه دروس)
        """)
    elif user_id in all_teachers_ids:
        score = teacher_scores.get(user_id, 0)
        bot.reply_to(message, f"""
            سلام دبیر گرامی!
            شما به عنوان دبیر در ربات فعالیت می‌کنید.
            منتظر سوالات دانش‌آموزان باشید و با دکمه "ارسال پاسخ" جواب دهید.
            
            برای مشاهده امتیازات خود /score را بزنید.
        """)
    else:
        if check_subscription(user_id):
            subscription_end_date = subscriptions[user_id]['end_date'].strftime("%Y-%m-%d %H:%M")
            math_questions = subscriptions[user_id].get('math_questions', 0)
            physics_questions = subscriptions[user_id].get('physics_questions', 0)
            
            # چک کردن تعلیق موقت
            if subscriptions[user_id].get('suspended_until') and subscriptions[user_id]['suspended_until'] > datetime.datetime.now():
                suspended_until = subscriptions[user_id]['suspended_until'].strftime("%Y-%m-%d %H:%M")
                bot.reply_to(message, f"""
                    دانش‌آموز گرامی، اشتراک شما تا تاریخ {subscription_end_date} فعال است اما تا تاریخ {suspended_until} از ارسال سوال محروم هستید.
                    پس از این تاریخ می‌توانید از سرویس استفاده کنید.
                """)
            else:
                bot.reply_to(message, f"""
                    دانش‌آموز گرامی، اشتراک شما تا تاریخ {subscription_end_date} فعال است.
                    تعداد سوالات باقیمانده:
                    ریاضی: {math_questions}
                    فیزیک: {physics_questions}
                    
                    برای ارسال سوال /start را بزنید و درس مورد نظر را انتخاب کنید.
                    
                    نکات مهم:
                    - پاسخ تمامی سوالات تا ساعت 12 شب ارسال می‌شوند.
                    - در صورت اتمام سوالات هر درس، برای شارژ بیشتر به ادمین پیام دهید.
                """)
        else:
            bot.reply_to(message, """دانش اموز گرامی جهت تهیه اشتراک ۳ ماهه حل سوالات درسی شامل ۴۵ سوال ریاضی و ۴۵ سوال فیزیک از طریق زیر اقدام کنید

شماره کارت:
۶۰۳۷۹۹۷۲۷۵۹۵۷۳۷۲
به نام : منصور گل محمدی

فیش واریزی را همراه یوزرآیدی تلگرام خود  برای ادمین ارسال کنید تا اشتراک شما فعال شود.

آیدی ادمین: @GolMohammadiM

- برای گرفتن یوزرآیدی از طریق ربات @userinfobot اقدام کنید""")

# ---------- هندلرهای ادمین ----------
@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 5:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /add_subscription 123456789 30 50 40")
                return
            _, chat_id_str, days_str, math_questions_str, physics_questions_str = parts
            chat_id = int(chat_id_str)
            days = int(days_str)
            math_questions = int(math_questions_str)
            physics_questions = int(physics_questions_str)
            
            end_date = datetime.datetime.now() + datetime.timedelta(days=days)
            subscriptions[chat_id] = {
                'end_date': end_date, 
                'banned': False, 
                'telegram_username': None,
                'suspended_until': None,
                'math_questions': math_questions,
                'physics_questions': physics_questions
            }
            bot.reply_to(message, f"اشتراک برای کاربر {chat_id} تا {end_date.strftime('%Y-%m-%d %H:%M')} فعال شد.\nتعداد سوالات: ریاضی: {math_questions}, فیزیک: {physics_questions}")
            try:
                bot.send_message(chat_id, f"اشتراک شما فعال شد! شما می‌توانید {math_questions} سوال ریاضی و {physics_questions} سوال فیزیک بپرسید.\nبرای شروع /start را بزنید.")
            except Exception as e:
                bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
            save_data()
        except ValueError:
            bot.reply_to(message, "مقادیر باید عددی باشند. مثال: /add_subscription 123456789 30 50 40")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['add_questions'])
def add_questions(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 4:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /add_questions 123456789 math 10")
                return
            _, chat_id_str, subject_type, amount_str = parts
            chat_id = int(chat_id_str)
            amount = int(amount_str)
            
            if chat_id not in subscriptions:
                bot.reply_to(message, f"کاربر {chat_id} اشتراکی ندارد.")
                return
                
            if subject_type == 'math':
                subscriptions[chat_id]['math_questions'] += amount
                bot.reply_to(message, f"{amount} سوال ریاضی به کاربر {chat_id} اضافه شد. تعداد جدید: {subscriptions[chat_id]['math_questions']}")
            elif subject_type == 'physics':
                subscriptions[chat_id]['physics_questions'] += amount
                bot.reply_to(message, f"{amount} سوال فیزیک به کاربر {chat_id} اضافه شد. تعداد جدید: {subscriptions[chat_id]['physics_questions']}")
            elif subject_type == 'all':
                subscriptions[chat_id]['math_questions'] += amount
                subscriptions[chat_id]['physics_questions'] += amount
                bot.reply_to(message, f"{amount} سوال به همه دروس کاربر {chat_id} اضافه شد. تعداد جدید: ریاضی: {subscriptions[chat_id]['math_questions']}, فیزیک: {subscriptions[chat_id]['physics_questions']}")
            else:
                bot.reply_to(message, "نوع درس نامعتبر است. از math، physics یا all استفاده کنید.")
                
            try:
                bot.send_message(chat_id, f"تعداد سوالات شما افزایش یافت!\nریاضی: {subscriptions[chat_id]['math_questions']}\nفیزیک: {subscriptions[chat_id]['physics_questions']}")
            except Exception as e:
                bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                
            save_data()
        except ValueError:
            bot.reply_to(message, "آیدی کاربر یا تعداد سوال باید عددی باشد. مثال: /add_questions 123456789 math 10")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['remove_subscription'])
def remove_subscription(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 2:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /remove_subscription 123456789")
                return
            _, chat_id_str = parts
            chat_id = int(chat_id_str)
            if chat_id in subscriptions:
                del subscriptions[chat_id]
                bot.reply_to(message, f"اشتراک کاربر {chat_id} غیرفعال شد.")
                try:
                    bot.send_message(chat_id, "اشتراک شما غیرفعال شد.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                save_data()
            else:
                bot.reply_to(message, f"کاربر {chat_id} اشتراکی ندارد.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /remove_subscription 123456789")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['add_teacher'])
def add_teacher(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /add_teacher 123456789 math")
                return
            _, chat_id_str, subject_en = parts
            chat_id = int(chat_id_str)
            
            subject_en = subject_en.strip().lower()
            
            if subject_en not in SUBJECT_MAP_EN_TO_FA:
                bot.reply_to(message, f"درس '{subject_en}' نامعتبر است. لیست دروس معتبر (انگلیسی): {', '.join(SUBJECT_MAP_EN_TO_FA.keys())}")
                return

            if subject_en not in teachers_by_subject:
                teachers_by_subject[subject_en] = []

            if chat_id not in teachers_by_subject[subject_en]:
                teachers_by_subject[subject_en].append(chat_id)
                all_teachers_ids.add(chat_id)
                if chat_id not in teacher_scores:
                    teacher_scores[chat_id] = 0
                
                bot.reply_to(message, f"کاربر {chat_id} به لیست دبیران درس '{SUBJECT_MAP_EN_TO_FA[subject_en]}' اضافه شد.")
                try:
                    bot.send_message(chat_id, f"شما به عنوان دبیر درس '{SUBJECT_MAP_EN_TO_FA[subject_en]}' اضافه شدید!")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                save_data()
            else:
                bot.reply_to(message, f"کاربر {chat_id} از قبل دبیر درس '{SUBJECT_MAP_EN_TO_FA[subject_en]}' بوده است.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /add_teacher 123456789 math")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['remove_teacher'])
def remove_teacher(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /remove_teacher 123456789 math")
                return
            _, chat_id_str, subject_en = parts
            chat_id = int(chat_id_str)
            
            subject_en = subject_en.strip().lower()
            
            if subject_en not in SUBJECT_MAP_EN_TO_FA:
                bot.reply_to(message, f"درس '{subject_en}' نامعتبر است. لیست دروس معتبر (انگلیسی): {', '.join(SUBJECT_MAP_EN_TO_FA.keys())}")
                return

            if subject_en in teachers_by_subject and chat_id in teachers_by_subject[subject_en]:
                teachers_by_subject[subject_en].remove(chat_id)
                is_teacher_in_other_subjects = False
                for teacher_list in teachers_by_subject.values():
                    if chat_id in teacher_list:
                        is_teacher_in_other_subjects = True
                        break
                
                if not is_teacher_in_other_subjects:
                    all_teachers_ids.discard(chat_id)
                
                bot.reply_to(message, f"کاربر {chat_id} از لیست دبیران درس '{SUBJECT_MAP_EN_TO_FA[subject_en]}' حذف شد.")
                try:
                    bot.send_message(chat_id, f"شما دیگر دبیر درس '{SUBJECT_MAP_EN_TO_FA[subject_en]}' نیستید.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                save_data()
            else:
                bot.reply_to(message, f"کاربر {chat_id} دبیر درس '{SUBJECT_MAP_EN_TO_FA[subject_en]}' نبوده است.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /remove_teacher 123456789 math")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['ban_user'])
def ban_user(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 2:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /ban_user 123456789")
                return
            _, chat_id_str = parts
            chat_id = int(chat_id_str)
            if chat_id in subscriptions:
                subscriptions[chat_id]['banned'] = True
                bot.reply_to(message, f"کاربر {chat_id} بن شد.")
                try:
                    bot.send_message(chat_id, "شما بن شدید و دیگر قادر به استفاده از ربات نیستید.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                save_data()
            else:
                bot.reply_to(message, f"کاربر {chat_id} اشتراکی ندارد.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /ban_user 123456789")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['unban_user'])
def unban_user(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 2:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /unban_user 123456789")
                return
            _, chat_id_str = parts
            chat_id = int(chat_id_str)
            if chat_id in subscriptions:
                subscriptions[chat_id]['banned'] = False
                bot.reply_to(message, f"کاربر {chat_id} از بن خارج شد.")
                try:
                    bot.send_message(chat_id, "شما از بن خارج شدید و می‌توانید دوباره از ربات استفاده کنید.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                save_data()
            else:
                bot.reply_to(message, f"کاربر {chat_id} اشتراکی ندارد.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /unban_user 123456789")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['suspend_user'])
def suspend_user(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /suspend_user 123456789 24")
                return
            _, chat_id_str, hours_str = parts
            chat_id = int(chat_id_str)
            hours = int(hours_str)
            
            if chat_id in subscriptions:
                suspend_until = datetime.datetime.now() + datetime.timedelta(hours=hours)
                subscriptions[chat_id]['suspended_until'] = suspend_until
                bot.reply_to(message, f"کاربر {chat_id} به مدت {hours} ساعت از ارسال سوال محروم شد. این محرومیت تا {suspend_until.strftime('%Y-%m-%d %H:%M')} فعال خواهد بود.")
                try:
                    bot.send_message(chat_id, f"شما به مدت {hours} ساعت از ارسال سوال محروم شده‌اید. این محرومیت تا {suspend_until.strftime('%Y-%m-%d %H:%M')} فعال خواهد بود.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
                save_data()
            else:
                bot.reply_to(message, f"کاربر {chat_id} اشتراکی ندارد.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر یا مدت زمان باید عددی باشد. مثال: /suspend_user 123456789 24")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

@bot.message_handler(commands=['score'])
def show_score(message):
    user_id = message.chat.id
    if user_id == ADMIN_ID:
        parts = message.text.split()
        if len(parts) == 2:
            try:
                target_user_id = int(parts[1])
                score = teacher_scores.get(target_user_id, 0)
                
                teacher_subjects_fa = []
                for subject_en, ids in teachers_by_subject.items():
                    if target_user_id in ids:
                        teacher_subjects_fa.append(SUBJECT_MAP_EN_TO_FA.get(subject_en, subject_en))
                
                subjects_str = ", ".join(teacher_subjects_fa) if teacher_subjects_fa else "در هیچ درسی"
                
                bot.reply_to(message, f"امتیاز دبیر {target_user_id}: {score}\nدروس تدریس: {subjects_str}")
            except ValueError:
                bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /score 123456789")
        else:
            bot.reply_to(message, "برای مشاهده امتیاز یک دبیر خاص، آیدی او را وارد کنید. مثال: /score 123456789")
    elif user_id in all_teachers_ids:
        score = teacher_scores.get(user_id, 0)
        teacher_subjects_fa = []
        for subject_en, ids in teachers_by_subject.items():
            if user_id in ids:
                teacher_subjects_fa.append(SUBJECT_MAP_EN_TO_FA.get(subject_en, subject_en))

        subjects_str = ", ".join(teacher_subjects_fa) if teacher_subjects_fa else "در هیچ درسی ثبت نشده‌اید."
        bot.reply_to(message, f"شما در لیست دبیران درس‌های: {subjects_str} ثبت شده‌اید.\n امتیاز شما: {score}")
    else:
        bot.reply_to(message, "شما دبیر یا ادمین نیستید و نمی‌توانید از این دستور استفاده کنید.")

@bot.message_handler(commands=['all_teacher_scores'])
def all_teacher_scores(message):
    if message.chat.id == ADMIN_ID:
        if not teacher_scores:
            bot.reply_to(message, "هنوز هیچ دبیری امتیازی ندارد.")
            return

        response_text = "لیست امتیازات دبیران:\n"
        for teacher_id, score in sorted(teacher_scores.items(), key=lambda item: item[1], reverse=True):
            teacher_username = None
            if teacher_id in subscriptions and subscriptions[teacher_id]['telegram_username']:
                teacher_username = subscriptions[teacher_id]['telegram_username']
            
            username_display = f" (@{teacher_username})" if teacher_username else ""
            
            teacher_subjects_fa = []
            for subject_en, ids in teachers_by_subject.items():
                if teacher_id in ids:
                    teacher_subjects_fa.append(SUBJECT_MAP_EN_TO_FA.get(subject_en, subject_en))
            subjects_str = f" ({', '.join(teacher_subjects_fa)})" if teacher_subjects_fa else ""

            response_text += f"- ID: {teacher_id}{username_display}{subjects_str}, امتیاز: {score}\n"
        
        bot.reply_to(message, response_text)
    else:
        bot.reply_to(message, "شما ادمین نیستید و نمی‌توانید از این دستور استفاده کنید.")

@bot.message_handler(commands=['decrease_score'])
def decrease_score(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /decrease_score 123456789 5")
                return
            _, chat_id_str, amount_str = parts
            chat_id = int(chat_id_str)
            amount = int(amount_str)

            if chat_id in teacher_scores:
                teacher_scores[chat_id] = max(0, teacher_scores[chat_id] - amount)
                bot.reply_to(message, f"امتیاز دبیر {chat_id} به {teacher_scores[chat_id]} کاهش یافت.")
                save_data()
            else:
                bot.reply_to(message, f"دبیر {chat_id} یافت نشد یا امتیازی ندارد.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر یا مقدار کاهش باید عددی باشد. مثال: /decrease_score 123456789 5")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")
    else:
        bot.reply_to(message, "شما ادمین نیستید و نمی‌توانید از این دستور استفاده کنید.")

# دستور جدید برای مشاهده شماره تلفن کاربر
@bot.message_handler(commands=['get_phone'])
def get_phone_number(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 2:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /get_phone 123456789")
                return
                
            _, chat_id_str = parts
            chat_id = int(chat_id_str)
            
            if chat_id in phone_numbers:
                phone_number = phone_numbers[chat_id]
                username = subscriptions.get(chat_id, {}).get('telegram_username', 'نامشخص')
                bot.reply_to(message, f"شماره تلفن کاربر {chat_id} (یوزرنیم: @{username}): {phone_number}")
            else:
                bot.reply_to(message, f"شماره تلفن کاربر {chat_id} یافت نشد.")
        except ValueError:
            bot.reply_to(message, "آیدی کاربر باید عددی باشد. مثال: /get_phone 123456789")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")
    else:
        bot.reply_to(message, "شما ادمین نیستید و نمی‌توانید از این دستور استفاده کنید.")

# ---------- مدیریت سوالات (دانش‌آموز) ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_subject_'))
def ask_subject_callback(call):
    user_id = call.from_user.id
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "شما اشتراک فعالی ندارید.")
        bot.send_message(user_id, "شما اشتراک فعالی ندارید. برای راهنمایی /help را بزنید.")
        return

    subject_en = call.data.replace('ask_subject_', '')
    if subject_en not in SUBJECT_MAP_EN_TO_FA:
        bot.answer_callback_query(call.id, "درس انتخاب شده نامعتبر است.")
        bot.send_message(user_id, "درس انتخاب شده نامعتبر است. لطفاً از دکمه‌های موجود استفاده کنید.")
        return

    subject_fa = SUBJECT_MAP_EN_TO_FA[subject_en]
    
    # چک کردن تعداد سوالات باقیمانده
    remaining_questions = subscriptions[user_id].get(f'{subject_en}_questions', 0)
    if remaining_questions <= 0:
        bot.answer_callback_query(call.id, f"سوالات درس {subject_fa} شما تمام شده است.")
        bot.send_message(user_id, f"سوالات درس {subject_fa} شما تمام شده است. برای شارژ بیشتر به ادمین پیام دهید.")
        return

    bot.answer_callback_query(call.id, f"شما درس {subject_fa} را انتخاب کردید.")
    bot.send_message(user_id, f"سوال خود را در مورد درس {subject_fa} ارسال کنید:")
    user_question_state[user_id] = {'state': True, 'subject_en': subject_en}

@bot.message_handler(func=lambda message: message.chat.id in user_question_state and user_question_state[message.chat.id]['state'], content_types=['text', 'photo', 'video', 'document', 'voice'])
def handle_question(message):
    user_id = message.chat.id
    
    if not check_subscription(user_id):
        bot.send_message(user_id, "شما اشتراک فعالی ندارید. برای راهنمایی /help را بزنید.")
        if user_id in user_question_state:
            del user_question_state[user_id]
        return

    subject_en = user_question_state[user_id]['subject_en']
    subject_fa = SUBJECT_MAP_EN_TO_FA.get(subject_en, subject_en)
    del user_question_state[user_id]

    # چک کردن تعداد سوالات باقیمانده
    remaining_questions = subscriptions[user_id].get(f'{subject_en}_questions', 0)
    if remaining_questions <= 0:
        bot.reply_to(message, f"سوالات درس {subject_fa} شما تمام شده است. برای شارژ بیشتر به ادمین پیام دهید.")
        return

    # کاهش تعداد سوالات
    subscriptions[user_id][f'{subject_en}_questions'] -= 1
    save_data()

    target_teachers = teachers_by_subject.get(subject_en, [])
    if not target_teachers:
        bot.reply_to(message, f"متاسفانه در حال حاضر دبیری برای درس {subject_fa} در دسترس نیست. لطفاً به ادمین اطلاع دهید.")
        return

    successful_sends = 0
    
    user_info = f"سوال از طرف کاربر "
    if message.from_user.username:
        user_info += f" (@{message.from_user.username})"

    for teacher_id in target_teachers:
        try:
            sent_message = None
            if message.content_type == 'text':
                sent_message = bot.send_message(teacher_id, f" در درس {subject_fa}:\n{message.text}", reply_markup=get_teacher_keyboard(user_id, message.message_id))
            elif message.content_type == 'photo':
                sent_message = bot.send_photo(teacher_id, message.photo[-1].file_id, caption=f" در درس {subject_fa}:\n{message.caption if message.caption else ''}", reply_markup=get_teacher_keyboard(user_id, message.message_id))
            elif message.content_type == 'video':
                sent_message = bot.send_video(teacher_id, message.video.file_id, caption=f" در درس {subject_fa}:\n{message.caption if message.caption else ''}", reply_markup=get_teacher_keyboard(user_id, message.message_id))
            elif message.content_type == 'document':
                sent_message = bot.send_document(teacher_id, message.document.file_id, caption=f" در درس {subject_fa}:\n{message.caption if message.caption else ''}", reply_markup=get_teacher_keyboard(user_id, message.message_id))
            elif message.content_type == 'voice':  # اضافه کردن ویس
                sent_message = bot.send_voice(teacher_id, message.voice.file_id, caption=f" در درس {subject_fa}:\n{message.caption if message.caption else ''}", reply_markup=get_teacher_keyboard(user_id, message.message_id))

            if sent_message:
                # ذخیره اطلاعات پیام در دیتابیس
                message_database[sent_message.message_id] = {
                    'user_id': user_id,
                    'teacher_id': teacher_id,
                    'original_message_id': message.message_id,
                    'subject': subject_en
                }
                successful_sends += 1
        except Exception as e:
            print(f"Error sending question to teacher {teacher_id}: {e}")
            bot.send_message(ADMIN_ID, f"Error sending question to teacher {teacher_id} for user {user_id} in subject {subject_fa}: {e}")

    if successful_sends > 0:
        new_remaining = subscriptions[user_id].get(f'{subject_en}_questions', 0)
        bot.reply_to(message, f"سوال شما در مورد درس {subject_fa} برای دبیران ارسال شد. منتظر پاسخ باشید.\nتعداد سوالات باقیمانده {subject_fa}: {new_remaining}")
    else:
        # اگر ارسال ناموفق بود، سوال برگردانده شود
        subscriptions[user_id][f'{subject_en}_questions'] += 1
        save_data()
        bot.reply_to(message, "خطایی در ارسال سوال به دبیران رخ داد. لطفاً دوباره امتحان کنید.")


# ---------- مدیریت پاسخ دبیر ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_'))
def answer_query(call):
    teacher_id = call.from_user.id
    if teacher_id not in all_teachers_ids:
        bot.answer_callback_query(call.id, "شما دبیر نیستید.")
        return

    _, user_id_str, original_message_id_str = call.data.split('_')
    user_id = int(user_id_str)
    original_message_id = int(original_message_id_str)
    
    bot.answer_callback_query(call.id, "لطفا پاسخ خود را ارسال کنید.")
    bot.register_next_step_handler(call.message, lambda message: send_answer(teacher_id, user_id, message, original_message_id))

def send_answer(teacher_id, user_id, message, original_message_id):
    # افزایش امتیاز دبیر
    teacher_scores[teacher_id] = teacher_scores.get(teacher_id, 0) + 1
    save_data()

    # ارسال پاسخ به دانش‌آموز
    try:
        if message.content_type == 'text':
            bot.send_message(user_id, f"پاسخ دبیر:\n{message.text}")
        elif message.content_type == 'photo':
            bot.send_photo(user_id, message.photo[-1].file_id, caption=f"پاسخ دبیر:\n{message.caption if message.caption else ''}")
        elif message.content_type == 'video':
            bot.send_video(user_id, message.video.file_id, caption=f"پاسخ دبیر:\n{message.caption if message.caption else ''}")
        elif message.content_type == 'document':
            bot.send_document(user_id, message.document.file_id, caption=f"پاسخ دبیر:\n{message.caption if message.caption else ''}")
        elif message.content_type == 'voice':  # اضافه کردن ویس
            bot.send_voice(user_id, message.voice.file_id, caption=f"پاسخ دبیر:\n{message.caption if message.caption else ''}")
        bot.reply_to(message, "پاسخ شما با موفقیت ارسال شد.")
    except Exception as e:
        print(f"Error sending answer to user {user_id}: {e}")
        bot.send_message(ADMIN_ID, f"خطا در ارسال پاسخ به کاربر {user_id} از دبیر {teacher_id}: {e}")
        bot.reply_to(message, "خطایی در ارسال پاسخ رخ داد.")

    # حذف پیام سوال از تمام دبیران
    delete_question_messages(original_message_id)

# ---------- مدیریت گزارش تخلف ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def report_query(call):
    teacher_id = call.from_user.id
    if teacher_id not in all_teachers_ids:
        bot.answer_callback_query(call.id, "شما دبیر نیستید.")
        return

    _, user_id_str, original_message_id_str = call.data.split('_')
    user_id = int(user_id_str)
    original_message_id = int(original_message_id_str)

    # ذخیره اطلاعات در pending_reports
    pending_reports[teacher_id] = {
        'user_id': user_id,
        'original_message_id': original_message_id,
        'message': call.message
    }

    bot.answer_callback_query(call.id, "لطفا دلیل تخلف را ارسال کنید.")
    bot.send_message(teacher_id, "لطفاً دلیل تخلف را توضیح دهید:")

@bot.message_handler(func=lambda message: message.chat.id in pending_reports)
def handle_report_reason(message):
    teacher_id = message.chat.id
    report_data = pending_reports.get(teacher_id)
    if not report_data:
        return

    user_id = report_data['user_id']
    original_message_id = report_data['original_message_id']
    question_message = report_data['message']

    reason = message.text

    # حذف گزارش از pending_reports
    del pending_reports[teacher_id]

    # ارسال گزارش به گروه
    user_username = subscriptions.get(user_id, {}).get('telegram_username')
    user_username_display = f" (@{user_username})" if user_username else ""

    teacher_username = message.from_user.username
    teacher_username_display = f" (@{teacher_username})" if teacher_username else ""

    # ایجاد کپشن برای گزارش
    report_caption = (
        f"🚨 گزارش تخلف 🚨\n"
        f"دبیر: {teacher_id}{teacher_username_display}\n"
        f"دانش‌آموز: {user_id}{user_username_display}\n"
        f"دلیل تخلف: {reason}\n"
        f"متن سوال "
    )

    # ارسال سوال به گروه (با توجه به نوع محتوا)
    try:
        if question_message.content_type == 'text':
            full_report = report_caption + question_message.text
            bot.send_message(VIOLATION_GROUP_ID, full_report)
        elif question_message.content_type == 'photo':
            bot.send_photo(VIOLATION_GROUP_ID, question_message.photo[-1].file_id, caption=report_caption + (question_message.caption if question_message.caption else ""))
        elif question_message.content_type == 'video':
            bot.send_video(VIOLATION_GROUP_ID, question_message.video.file_id, caption=report_caption + (question_message.caption if question_message.caption else ""))
        elif question_message.content_type == 'document':
            bot.send_document(VIOLATION_GROUP_ID, question_message.document.file_id, caption=report_caption + (question_message.caption if question_message.caption else ""))
        elif question_message.content_type == 'voice':  # اضافه کردن ویس
            bot.send_voice(VIOLATION_GROUP_ID, question_message.voice.file_id, caption=report_caption + (question_message.caption if question_message.caption else ""))
    except Exception as e:
        print(f"Error sending violation report: {e}")
        bot.send_message(ADMIN_ID, f"خطا در ارسال گزارش تخلف به گروه: {e}")

    # حذف پیام سوال از تمام دبیران
    delete_question_messages(original_message_id)

    bot.send_message(teacher_id, "گزارش تخلف با موفقیت ثبت و به گروه ارسال شد.")

# —--------------------------
# اجرای ربات
# —--------------------------
print("ربات در حال اجرا می باشد ...")
bot.infinity_polling()
