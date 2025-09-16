import telebot
import datetime
import json
import os
from collections import defaultdict

# اطلاعات ربات و ادمین
TOKEN = "8392998317:AAEQI1n-SZgDVfoNr_8GLkj7tjEVKmkXeC8"
ADMIN_ID = 5489748445
ADMIN_USERNAME = "GolMohammadiM"
VIOLATION_GROUP_ID = -4840581050

# نام فایل‌ها برای ذخیره اطلاعات
SUBSCRIPTIONS_FILE = 'subscriptions.json'
TEACHERS_FILE = 'teachers.json'
SCORES_FILE = 'teacher_scores.json'
MESSAGE_DATABASE_FILE = 'message_database.json'
PHONE_NUMBERS_FILE = 'phone_numbers.json'

# نگاشت درس‌های فارسی به انگلیسی و بالعکس (فقط ریاضی و فیزیک)
SUBJECT_MAP_FA_TO_EN = {
    "ریاضی": "math",
    "فیزیک": "physics"
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
                    'question_limits': data.get('question_limits', {'math': 0, 'physics': 0})
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
            'question_limits': data.get('question_limits', {'math': 0, 'physics': 0})
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
    if chat_id not in subscriptions:
        return False
    
    user_data = subscriptions[chat_id]
    
    if user_data['banned']:
        return False
        
    if user_data.get('suspended_until') and user_data['suspended_until'] > datetime.datetime.now():
        return False
        
    return user_data['end_date'] > datetime.datetime.now()

def get_teacher_keyboard(user_id, message_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    answer_button = telebot.types.InlineKeyboardButton(text="ارسال پاسخ", callback_data=f"answer_{user_id}_{message_id}")
    report_button = telebot.types.InlineKeyboardButton(text="گزارش تخلف", callback_data=f"report_{user_id}_{message_id}")
    keyboard.add(answer_button, report_button)
    return keyboard

def delete_question_messages(original_message_id):
    messages_to_delete = []
    
    for msg_id, msg_data in list(message_database.items()):
        if msg_data['original_message_id'] == original_message_id:
            messages_to_delete.append((msg_id, msg_data))
    
    for msg_id, msg_data in messages_to_delete:
        try:
            bot.delete_message(msg_data['teacher_id'], msg_id)
        except Exception as e:
            print(f"Error deleting message {msg_id} from teacher {msg_data['teacher_id']}: {e}")
        
        del message_database[msg_id]
    
    save_data()

# ---------- هندلرهای عمومی ----------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_username = message.from_user.username
    
    if user_username:
        if user_id in subscriptions:
            subscriptions[user_id]['telegram_username'] = user_username
            save_data()
    
    if user_id == ADMIN_ID:
        bot.reply_to(message, "سلام ادمین عزیز! به ربات مدیریت سوالات درسی خوش آمدید.\nبرای مشاهده دستورات /help را بزنید.")
    elif user_id in all_teachers_ids:
        score = teacher_scores.get(user_id, 0)
        bot.reply_to(message, f"سلام دبیر گرامی! به ربات مدیریت سوالات درسی خوش آمدید.\nبرای مشاهده امتیازت /score را بزن. امتیاز فعلی شما: {score}")
    else:
        if user_id not in phone_numbers:
            keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            keyboard.add(telebot.types.KeyboardButton("اشتراک گذاری شماره تلفن", request_contact=True))
            bot.send_message(user_id, "لطفاً برای ادامه، شماره تلفن خود را به اشتراک بگذارید:", reply_markup=keyboard)
            return
            
        if check_subscription(user_id):
            subscription_end_date = subscriptions[user_id]['end_date'].strftime("%Y-%m-%d %H:%M")
            
            if subscriptions[user_id].get('suspended_until') and subscriptions[user_id]['suspended_until'] > datetime.datetime.now():
                suspended_until = subscriptions[user_id]['suspended_until'].strftime("%Y-%m-%d %H:%M")
                bot.reply_to(message, f"اشتراک شما تا تاریخ {subscription_end_date} فعال است، اما تا تاریخ {suspended_until} از ارسال سوال محروم هستید.")
                return
                
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("ریاضی", callback_data="ask_subject_math"))
            keyboard.add(telebot.types.InlineKeyboardButton("فیزیک", callback_data="ask_subject_physics"))
            bot.send_message(user_id, f"دانش‌آموز گرامی،لطفاً درس مورد نظر برای ارسال سوال را انتخاب کنید: \n \n- برای اطلاع از وضعیت اشتراک خود و تعداد سوالات باقی مانده خود /help را وارد کنید.", reply_markup=keyboard)
        else:
            bot.reply_to(message, "دانش‌آموز گرامی، شما اشتراک فعالی ندارید. برای راهنمایی جهت تهیه اشتراک /help را بزنید.")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id
    contact = message.contact
    
    if contact.user_id == user_id:
        phone_numbers[user_id] = contact.phone_number
        save_data()
        
        bot.send_message(user_id, "شماره تلفن شما با موفقیت ثبت شد.", reply_markup=telebot.types.ReplyKeyboardRemove())
        
        if check_subscription(user_id):
            subscription_end_date = subscriptions[user_id]['end_date'].strftime("%Y-%m-%d %H:%M")
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("ریاضی", callback_data="ask_subject_math"))
            keyboard.add(telebot.types.InlineKeyboardButton("فیزیک", callback_data="ask_subject_physics"))
            bot.send_message(user_id, f"دانش‌آموز گرامی، برای اطلاع از وضعیت اشتراک خود و تعداد سوالات باقی مانده خود /help را وارد کنید .\nلطفاً درس مورد نظر برای ارسال سوال را انتخاب کنید:", reply_markup=keyboard)
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
            /add_questions [chat_id] [subject/all] [amount] - اضافه کردن سوال به کاربر
                (مثال: /add_questions 123456789 math 10 - اضافه کردن 10 سوال ریاضی)
                (مثال: /add_questions 123456789 all 20 - اضافه کردن 20 سوال به همه دروس)
            /remove_subscription [chat_id] - غیرفعال کردن اشتراک کاربر
            /add_teacher [chat_id] [subject_en] - افزودن دبیر به درس مشخص
                (مثال: /add_teacher 123456789 math)
                لیست دروس معتبر (انگلیسی): {subjects_list}
            /remove_teacher [chat_id] [subject_en] - حذف دبیر از درس مشخص
            /ban_user [chat_id] - بن کردن کاربر (اشتراک غیرفعال می‌شود)
            /unban_user [chat_id] - رفع بن کاربر
            /suspend_user [chat_id] [hours] - تعلیق موقت کاربر برای مدت مشخص (ساعت)
            /score [chat_id] - مشاهده امتیاز یک دبیر (اختیاری)
            /all_teacher_scores - مشاهده لیست امتیازات تمامی دبیران
            /decrease_score [chat_id] [amount] - کاهش امتیاز مشخص یک دبیر
            /get_phone [chat_id] - مشاهده شماره تلفن کاربر
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
            if subscriptions[user_id].get('suspended_until') and subscriptions[user_id]['suspended_until'] > datetime.datetime.now():
                suspended_until = subscriptions[user_id]['suspended_until'].strftime("%Y-%m-%d %H:%M")
                bot.reply_to(message, f"""
                    دانش‌آموز گرامی، اشتراک شما فعال است اما تا تاریخ {suspended_until} از ارسال سوال محروم هستید.
                    پس از این تاریخ می‌توانید از سرویس استفاده کنید.
                """)
            else:
                limits = subscriptions[user_id].get('question_limits', {'math': 0, 'physics': 0})
                end_date = subscriptions[user_id]['end_date'].strftime("%Y-%m-%d")
                bot.reply_to(message, f"""
                    دانش‌آموز گرامی، اشتراک شما تا تاریخ {end_date} فعال است.
                    شما می‌توانید:
                    - {limits['math']} سوال ریاضی
                    - {limits['physics']} سوال فیزیک
                    ارسال کنید.
                    
                    برای ارسال سوال /start را بزنید و درس مورد نظر را انتخاب کنید.
                    
                    نکات مهم:
           #         - پاسخ تمامی سوالات تا ساعت 12 شب ارسال می‌شوند.
                    - در صورت اتمام سوالات مجاز، برای شارژ بیشتر به ادمین پیام دهید.
                """)
        else:
            bot.reply_to(message, """دانش اموز گرامی جهت تهیه اشتراک ۳ ماهه حل سوالات درسی شامل ۴۵ سوال ریاضی و ۴۵ سوال فیزیک از طریق زیر اقدام کنید

شماره کارت:
۶۰۳۷۹۹۷۲۷۵۹۵۷۳۷۲
به نام : منصور گل محمدی

فیش واریزی را همراه یوزرآیدی تلگرام خود  برای ادمین ارسال کنید تا اشتراک شما فعال شود.

برای گرفتن یوزرآیدی از طریق ربات .... اقدام کنید""")

# ---------- هندلرهای ادمین ----------
@bot.message_handler(commands=['add_questions'])
def add_questions(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) < 4:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال:\n"
                                     "/add_questions 123456789 math 10 - اضافه کردن 10 سوال ریاضی\n"
                                     "/add_questions 123456789 all 20 - اضافه کردن 20 سوال به همه دروس")
                return
            
            _, chat_id_str, subject_str, amount_str = parts
            chat_id = int(chat_id_str)
            amount = int(amount_str)
            subject = subject_str.lower()
            
            if chat_id not in subscriptions:
                bot.reply_to(message, f"کاربر {chat_id} اشتراک فعالی ندارد.")
                return
            
            if not check_subscription(chat_id):
                bot.reply_to(message, f"اشتراک کاربر {chat_id} منقضی شده یا بن شده است.")
                return
            
            if subject == 'all':
                # اضافه کردن به همه دروس
                for subject_en in SUBJECT_MAP_EN_TO_FA.keys():
                    subscriptions[chat_id]['question_limits'][subject_en] += amount
                
                bot.reply_to(message, f"{amount} سوال به همه دروس کاربر {chat_id} اضافه شد.")
                try:
                    bot.send_message(chat_id, f"{amount} سوال به همه دروس شما اضافه شد.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
            
            elif subject in SUBJECT_MAP_EN_TO_FA:
                # اضافه کردن به درس خاص
                subscriptions[chat_id]['question_limits'][subject] += amount
                subject_fa = SUBJECT_MAP_EN_TO_FA[subject]
                
                bot.reply_to(message, f"{amount} سوال به درس {subject_fa} کاربر {chat_id} اضافه شد.")
                try:
                    bot.send_message(chat_id, f"{amount} سوال به درس {subject_fa} شما اضافه شد.")
                except Exception as e:
                    bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
            
            else:
                valid_subjects = ", ".join(['all'] + list(SUBJECT_MAP_EN_TO_FA.keys()))
                bot.reply_to(message, f"درس '{subject}' نامعتبر است. درس‌های معتبر: {valid_subjects}")
            
            save_data()
            
        except ValueError:
            bot.reply_to(message, "آیدی کاربر یا تعداد سوالات باید عددی باشد. مثال: /add_questions 123456789 math 10")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")
    else:
        bot.reply_to(message, "شما ادمین نیستید و نمی‌توانید از این دستور استفاده کنید.")
@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if message.chat.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) != 5:
                bot.reply_to(message, "فرمت دستور اشتباه است. مثال: /add_subscription 123456789 30 50 30")
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
                'question_limits': {
                    'math': math_questions,
                    'physics': physics_questions
                }
            }
            bot.reply_to(message, f"اشتراک برای کاربر {chat_id} تا {end_date.strftime('%Y-%m-%d %H:%M')} فعال شد.\nتعداد سوالات: ریاضی={math_questions}, فیزیک={physics_questions}")
            try:
                bot.send_message(chat_id, f"اشتراک شما فعال شد! شما می‌توانید {math_questions} سوال ریاضی و {physics_questions} سوال فیزیک بپرسید.")
            except Exception as e:
                bot.reply_to(message, f"خطا در ارسال پیام به کاربر {chat_id}: {e}")
            save_data()
        except ValueError:
            bot.reply_to(message, "مقادیر باید عددی باشند. مثال: /add_subscription 123456789 30 50 30")
        except Exception as e:
            bot.reply_to(message, f"خطای غیرمنتظره: {e}")

# سایر دستورات ادمین بدون تغییر باقی می‌مانند (با حذف ارجاع به دروس زیست و شیمی)

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
    
    # بررسی تعداد سوالات باقیمانده
    remaining = subscriptions[user_id]['question_limits'][subject_en]
    if remaining <= 0:
        bot.answer_callback_query(call.id, f"سوالات {subject_fa} شما تمام شده است.")
        bot.send_message(user_id, f"سوالات {subject_fa} شما تمام شده است. برای شارژ بیشتر به ادمین پیام دهید.")
        return

    bot.answer_callback_query(call.id, f"شما درس {subject_fa} را انتخاب کردید.")
    bot.send_message(user_id, f"سوال خود را در مورد درس {subject_fa} ارسال کنید:")
    user_question_state[user_id] = {'state': True, 'subject_en': subject_en}

@bot.message_handler(func=lambda message: message.chat.id in user_question_state and user_question_state[message.chat.id]['state'], content_types=['text', 'photo', 'video', 'document'])
def handle_question(message):
    user_id = message.chat.id
    
    if not check_subscription(user_id):
        bot.send_message(user_id, "شما اشتراک فعالی ندارید. برای راهنمایی /help را بزنید.")
        if user_id in user_question_state:
            del user_question_state[user_id]
        return

    subject_en = user_question_state[user_id]['subject_en']
    subject_fa = SUBJECT_MAP_EN_TO_FA.get(subject_en, subject_en)
    
    # بررسی تعداد سوالات باقیمانده
    remaining = subscriptions[user_id]['question_limits'][subject_en]
    if remaining <= 0:
        bot.send_message(user_id, f"سوالات {subject_fa} شما تمام شده است. برای شارژ بیشتر به ادمین پیام دهید.")
        if user_id in user_question_state:
            del user_question_state[user_id]
        return

    # کاهش تعداد سوالات باقیمانده
    subscriptions[user_id]['question_limits'][subject_en] = remaining - 1
    save_data()
    
    del user_question_state[user_id]

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

            if sent_message:
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
        remaining_after = subscriptions[user_id]['question_limits'][subject_en]
        bot.reply_to(message, f"سوال شما در مورد درس {subject_fa} برای دبیران ارسال شد. منتظر پاسخ باشید.\nسوالات باقیمانده {subject_fa}: {remaining_after}")
    else:
        # اگر ارسال نشد، سوال برگردانده می‌شود
        subscriptions[user_id]['question_limits'][subject_en] = remaining
        save_data()
        bot.reply_to(message, "خطایی در ارسال سوال به دبیران رخ داد. لطفاً دوباره امتحان کنید.")

# سایر بخش‌های کد بدون تغییر باقی می‌مانند (با حذف بخش‌های مربوط به زیست و شیمی)

print("ربات در حال اجراست...")
bot.infinity_polling()
