import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
import json
import os
from datetime import datetime, timedelta
import traceback
import sys

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# توکن ربات و آیدی ادمین
TOKEN = '7924870342:AAHq4DCOs2JuuPyxLmf8osQoVsjdZKX50_Y'
ADMIN_ID = 7058515436

# حالت‌های گفتگو
(
    MENU, SUPPORT, PRODUCTS, 
    ORDER, PAYMENT, SEND_MESSAGE,
    BROADCAST, MANAGE_PRODUCTS, ADD_PRODUCT,
    EDIT_PRODUCT, DELETE_PRODUCT, VIEW_STATS,
    COOPERATION, MANAGE_DISCOUNTS, ADD_DISCOUNT,
    ENTER_DISCOUNT, DELETE_DISCOUNT, USER_PROFILE,
    WISHLIST, NOTIFICATIONS, REVIEWS,
    CUSTOMER_PROFILE
) = range(22)

# دیتابیس ساده
DB_FILE = 'database.json'

# اطلاعات پیش‌فرض
DEFAULT_DATA = {
    'products': {
        '1': {
            'name': 'Prime PC',
            'description': 'سرویس پرمیوم مخصوص کامپیوتر\n- تک کاربره\n- سرعت بالا\n-ضد بن و کاملا امن\n- پشتیبانی 24/7',
            'price': '299,000 تومان',
            'image': None,
            'category': 'pc',
            'stock': 100,
            'views': 0,
            'reviews': []
        },
        '2': {
            'name': 'Lite PC',
            'description': 'سرویس لایت مخصوص کامپیوتر\n- تک کاربره\n- سرعت متوسط\n-ضد بن و کاملا امن\n- پشتیبانی 24/7',
            'price': '199,000 تومان',
            'image': None,
            'category': 'pc',
            'stock': 100,
            'views': 0,
            'reviews': []
        },
        '3': {
            'name': 'Android Visual',
            'description': 'سرویس مخصوص اندروید\n-تک کاربره\n- درانواع رنگ ها\n-ضد بن و کاملا امن\n- پشتیبانی 24/7',
            'price': '299,000 تومان',
            'image': None,
            'category': 'android',
            'stock': 100,
            'views': 0,
            'reviews': []
        }
    },
    'discount_codes': {},
    'bank_info': {
        'card_number': '6104-3386-4447-6687',
        'card_holder': 'سبحان پرهیزکار',
        'bank_name': 'ملت'
    },
    'orders': {},
    'user_messages': {},
    'stats': {
        'total_users': 0,
        'total_orders': 0,
        'total_sales': 0,
        'daily_sales': {},
        'weekly_sales': {},
        'monthly_sales': {}
    },
    'user_profiles': {},
    'wishlists': {},
    'notifications': {},
    'reviews': {}
}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # اطمینان از وجود کلیدهای ضروری
            if 'discount_codes' not in data:
                data['discount_codes'] = {}
            if 'stats' not in data:
                data['stats'] = {
                    'total_users': 0,
                    'total_orders': 0,
                    'total_sales': 0
                }
            return data
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=4)
    return DEFAULT_DATA

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def create_keyboard(buttons, columns=2):
    keyboard = []
    row = []
    for i, button in enumerate(buttons, 1):
        row.append(button)
        if i % columns == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        buttons = [
            InlineKeyboardButton("📦 مدیریت محصولات", callback_data='manage_products'),
            InlineKeyboardButton("🎟️ مدیریت کد تخفیف", callback_data='manage_discounts'),
            InlineKeyboardButton("📊 آمار و گزارشات", callback_data='view_stats'),
            InlineKeyboardButton("📩 ارسال پیام به کاربر", callback_data='send_message'),
            InlineKeyboardButton("📢 ارسال همگانی", callback_data='broadcast')
        ]
    else:
        buttons = [
            InlineKeyboardButton("🛒 محصولات", callback_data='products'),
            InlineKeyboardButton("💬 پشتیبانی", callback_data='support'),
            InlineKeyboardButton("🤝 همکاری با ما", callback_data='cooperation'),
            InlineKeyboardButton("👤 پروفایل من", callback_data='customer_profile'),
            InlineKeyboardButton("ℹ️ راهنما", callback_data='help')
        ]
    
    reply_markup = create_keyboard(buttons)
    welcome_text = "به ربات Dream خوش آمدید!\n \nمحصولات با کیفیت ✅\nضدبن و کاملا امن 🔐\nپشتیبانی 24/7 ⚡\n \nلطفا یک گزینه را انتخاب کنید:"
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    return MENU

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = load_db()
    products = db['products']
    
    buttons = []
    for product_id, product in products.items():
        buttons.append(
            InlineKeyboardButton(
                f"{product['name']} - {product['price']}",
                callback_data=f'product_{product_id}'
            )
        )
    
    reply_markup = InlineKeyboardMarkup([buttons[i:i+1] for i in range(0, len(buttons))])
    await update.callback_query.edit_message_text(
        "محصولات ما:\nلطفا یک محصول را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return PRODUCTS

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = update.callback_query.data.split('_')[1]
    db = load_db()
    product = db['products'][product_id]
    
    text = f"""
📌 محصول: {product['name']}
💰 قیمت: {product['price']}
📝 توضیحات:
{product['description']}
"""
    
    buttons = [
        InlineKeyboardButton("🛒 سفارش محصول", callback_data=f'order_{product_id}')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return ORDER

async def order_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = update.callback_query.data.split('_')[1]
    db = load_db()
    product = db['products'][product_id]
    
    context.user_data['current_order'] = {
        'product_id': product_id,
        'product_name': product['name'],
        'price': product['price']
    }
    
    buttons = [
        InlineKeyboardButton("🎟️ وارد کردن کد تخفیف", callback_data='enter_discount'),
        InlineKeyboardButton("💳 پرداخت", callback_data='payment_without_discount')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    
    text = f"""
📌 سفارش: {product['name']}
💰 مبلغ قابل پرداخت: {product['price']}

برای استفاده از کد تخفیف یا پرداخت مستقیم، یکی از گزینه‌های زیر را انتخاب کنید.
"""
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return ORDER

async def payment_without_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پرداخت بدون کد تخفیف"""
    db = load_db()
    order = context.user_data['current_order']
    
    text = f"""
📌 سفارش: {order['product_name']}
💰 مبلغ قابل پرداخت: {order['price']}

💳 اطلاعات پرداخت:
شماره کارت: {db['bank_info']['card_number']}
به نام: {db['bank_info']['card_holder']}
بانک: {db['bank_info']['bank_name']}

✅ پس از پرداخت، لطفا رسید پرداخت را (عکس یا متن) ارسال کنید.
"""
    
    await update.callback_query.edit_message_text(text)
    return ORDER

async def enter_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text(
        "لطفا کد تخفیف خود را وارد کنید:"
    )
    return ENTER_DISCOUNT

async def handle_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پردازش کد تخفیف کاربر"""
    discount_code = update.message.text.strip().upper()
    db = load_db()
    
    if not db.get('discount_codes'):
        db['discount_codes'] = {}
        save_db(db)
    
    if discount_code in db['discount_codes']:
        discount = db['discount_codes'][discount_code]
        if discount['active'] and discount['remaining_uses'] > 0:
            # اعمال تخفیف
            original_price = context.user_data['current_order']['price']
            price_value = int(original_price.replace('تومان', '').replace(',', '').strip())
            discount_amount = int(price_value * (discount['percentage'] / 100))
            final_price = price_value - discount_amount
            
            context.user_data['current_order']['discount_code'] = discount_code
            context.user_data['current_order']['discount_amount'] = discount_amount
            context.user_data['current_order']['final_price'] = final_price
            
            # به‌روزرسانی استفاده کد تخفیف
            db['discount_codes'][discount_code]['remaining_uses'] -= 1
            save_db(db)
            
            text = f"""
📌 سفارش: {context.user_data['current_order']['product_name']}
💰 مبلغ اصلی: {original_price}
🎟️ کد تخفیف: {discount_code}
💎 درصد تخفیف: {discount['percentage']}%
💰 مبلغ پس از تخفیف: {final_price:,} تومان

💳 اطلاعات پرداخت:
شماره کارت: {db['bank_info']['card_number']}
به نام: {db['bank_info']['card_holder']}
بانک: {db['bank_info']['bank_name']}

✅ پس از پرداخت، لطفا رسید پرداخت را (عکس یا متن) ارسال کنید.
"""
        else:
            text = "❌ این کد تخفیف منقضی شده یا تعداد استفاده آن به پایان رسیده است."
    else:
        text = "❌ کد تخفیف نامعتبر است."
    
    buttons = [
        InlineKeyboardButton("🔙 بازگشت", callback_data=f'product_{context.user_data["current_order"]["product_id"]}'),
        InlineKeyboardButton("🏠 صفحه اصلی", callback_data='back')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    await update.message.reply_text(text, reply_markup=reply_markup)
    return PAYMENT

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون یوزرنیم"
    first_name = update.effective_user.first_name or "بدون نام"
    last_name = update.effective_user.last_name or "بدون نام خانوادگی"
    db = load_db()
    order = context.user_data['current_order']
    order_id = str(len(db['orders']) + 1)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    payment_proof = ""
    if update.message.photo:
        payment_proof = "عکس رسید پرداخت"
        photo_file_id = update.message.photo[-1].file_id
    elif update.message.text:
        payment_proof = update.message.text
    
    # ذخیره اطلاعات سفارش در دیتابیس
    db['orders'][order_id] = {
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'product_id': order['product_id'],
        'product_name': order['product_name'],
        'price': order['price'],
        'discount_code': order.get('discount_code'),
        'discount_amount': order.get('discount_amount'),
        'final_price': order.get('final_price', order['price']),
        'status': 'pending',
        'payment_proof': payment_proof,
        'date': now
    }
    save_db(db)
    
    # آماده کردن پیام برای ادمین
    admin_message = f"""
🛒 سفارش جدید دریافت شد!

📌 اطلاعات سفارش:
🔹 شماره سفارش: {order_id}
🔹 محصول: {order['product_name']}
🔹 قیمت اصلی: {order['price']}
"""
    
    if 'discount_code' in order:
        admin_message += f"""
🔹 کد تخفیف: {order['discount_code']}
🔹 مبلغ تخفیف: {order['discount_amount']:,} تومان
🔹 قیمت نهایی: {order['final_price']:,} تومان
"""
    
    admin_message += f"""
🔹 تاریخ سفارش: {now}

👤 اطلاعات خریدار:
🔹 آیدی کاربر: {user_id}
🔹 یوزرنیم: @{username}
🔹 نام: {first_name} {last_name}
"""

    # ارسال پیام به ادمین
    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_file_id,
                caption=admin_message
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{admin_message}\n📝 رسید پرداخت:\n{payment_proof}"
            )
    except Exception as e:
        logger.error(f"Error sending order notification to admin: {e}")
    
    await update.message.reply_text(
        "✅ رسید پرداخت شما دریافت شد. سفارش شما در حال پردازش است.\n"
        "ادمین به زودی به شما اطلاع خواهد داد."
    )
    return await start(update, context)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text(
        "لطفا پیام خود را ارسال کنید. ادمین در اسرع وقت پاسخ خواهد داد."
    )
    return SUPPORT

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون یوزرنیم"
    message = update.message.text
    
    db = load_db()
    db['user_messages'][str(user_id)] = {
        'username': username,
        'message': message
    }
    save_db(db)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"پیام جدید از کاربر @{username}:\n{message}"
    )
    return await start(update, context)

async def show_cooperation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cooperation_text = """
🤝 *همکاری با Dream*

ما به دنبال شرکای تجاری و همکاران متعهدیم ! اگر علاقه‌مند به همکاری در زمینه‌های زیر هستید، با ما در ارتباط باشید:

🔹 *فروش محصولات*: کسب درآمد از طریق فروش محصولات ما
🔹 *همکاری در بازاریابی*: معرفی محصولات به دیگران و دریافت پورسانت

📌 *مزایای همکاری با ما*:
- درآمد ثابت و پورسانت بالا
- پشتیبانی کامل از همکاران
- تخفیف محصولات برای همکاران

📩 برای شروع همکاری، پیام خود را از طریق بخش پشتیبانی ارسال کنید یا با آیدی زیر ارتباط بگیرید:
@Dream_admins
"""

    buttons = [
        InlineKeyboardButton("💬 ارتباط با پشتیبانی", callback_data='support'),
        InlineKeyboardButton("🏠 صفحه اصلی", callback_data='back')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text=cooperation_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in show_cooperation: {e}")
        await update.callback_query.edit_message_text(
            text=cooperation_text.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return COOPERATION

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    help_text = """
📚 راهنمای استفاده از ربات:

🛒 بخش فروش:
- برای مشاهده محصولات از منوی اصلی گزینه "محصولات" را انتخاب کنید
- پس از انتخاب محصول می‌توانید آن را سفارش دهید
- می‌توانید از کد تخفیف استفاده کنید
- پس از پرداخت، رسید پرداخت را برای ما ارسال کنید

💬 بخش پشتیبانی:
- برای ارتباط با پشتیبانی از منوی اصلی گزینه "پشتیبانی" را انتخاب کنید
- پیام خود را ارسال کنید
- پشتیبان‌ها در اسرع وقت پاسخ خواهند داد

🤝 بخش همکاری:
- برای اطلاعات درباره همکاری با ما گزینه "همکاری" را انتخاب کنید

ℹ️ اطلاعات پشتیبانی:
- پشتیبانی تلگرام: @Dream_admins
- ساعات کاری: 9 صبح تا 12 شب
"""
    
    buttons = [
        InlineKeyboardButton("🛒 محصولات", callback_data='products'),
        InlineKeyboardButton("💬 پشتیبانی", callback_data='support'),
        InlineKeyboardButton("🤝 همکاری با ما", callback_data='cooperation'),
        InlineKeyboardButton("ℹ️ راهنما", callback_data='help')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup)
    return MENU

async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    buttons = [
        InlineKeyboardButton("➕ افزودن محصول", callback_data='add_product'),
        InlineKeyboardButton("✏️ ویرایش محصول", callback_data='edit_product'),
        InlineKeyboardButton("🗑️ حذف محصول", callback_data='delete_product'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='back')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    await update.callback_query.edit_message_text("مدیریت محصولات:", reply_markup=reply_markup)
    return MANAGE_PRODUCTS

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.edit_message_text(
        "لطفا اطلاعات محصول را به این فرمت ارسال کنید:\n\n"
        "نام محصول|توضیحات|قیمت\n\n"
        "مثال:\n"
        "محصول تست|این یک محصول تستی است|100,000 تومان"
    )
    return ADD_PRODUCT

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        name, description, price = update.message.text.split('|', 2)
        db = load_db()
        product_id = str(max([int(k) for k in db['products'].keys()]) + 1) if db['products'] else '1'
        
        db['products'][product_id] = {
            'name': name.strip(),
            'description': description.strip(),
            'price': price.strip(),
            'image': None
        }
        save_db(db)
        
        await update.message.reply_text(f"محصول با موفقیت اضافه شد. 🎉\nکد محصول: {product_id}")
        return await start(update, context)
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}\nلطفا فرمت را رعایت کنید.")
        return ADD_PRODUCT

async def edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = load_db()
    if not db['products']:
        await update.callback_query.edit_message_text("هیچ محصولی برای ویرایش وجود ندارد.")
        return await start(update, context)
    
    buttons = []
    for product_id, product in db['products'].items():
        buttons.append(InlineKeyboardButton(
            f"{product['name']} - {product['price']}",
            callback_data=f'edit_{product_id}'
        ))
    
    buttons.append(InlineKeyboardButton("🔙 بازگشت", callback_data='back'))
    reply_markup = InlineKeyboardMarkup([buttons[i:i+1] for i in range(0, len(buttons))])
    await update.callback_query.edit_message_text(
        "لطفا محصول مورد نظر برای ویرایش را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return EDIT_PRODUCT

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = update.callback_query.data.split('_')[1]
    context.user_data['editing_product'] = product_id
    await update.callback_query.edit_message_text(
        f"لطفا اطلاعات جدید محصول را به این فرمت ارسال کنید:\n\n"
        f"نام محصول|توضیحات|قیمت\n\n"
        f"مثال:\n"
        f"محصول ویرایش شده|توضیحات جدید|200,000 تومان"
    )
    return EDIT_PRODUCT

async def save_edited_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        name, description, price = update.message.text.split('|', 2)
        product_id = context.user_data['editing_product']
        db = load_db()
        
        db['products'][product_id] = {
            'name': name.strip(),
            'description': description.strip(),
            'price': price.strip(),
            'image': db['products'][product_id].get('image')
        }
        save_db(db)
        
        await update.message.reply_text("محصول با موفقیت ویرایش شد. ✅")
        return await start(update, context)
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}\nلطفا فرمت را رعایت کنید.")
        return EDIT_PRODUCT

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = load_db()
    if not db['products']:
        await update.callback_query.edit_message_text("هیچ محصولی برای حذف وجود ندارد.")
        return await start(update, context)
    
    buttons = []
    for product_id, product in db['products'].items():
        buttons.append(InlineKeyboardButton(
            f"{product['name']} - {product['price']}",
            callback_data=f'delete_{product_id}'
        ))
    
    buttons.append(InlineKeyboardButton("🔙 بازگشت", callback_data='back'))
    reply_markup = InlineKeyboardMarkup([buttons[i:i+1] for i in range(0, len(buttons))])
    await update.callback_query.edit_message_text(
        "لطفا محصول مورد نظر برای حذف را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return DELETE_PRODUCT

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = update.callback_query.data.split('_')[1]
    db = load_db()
    product_name = db['products'][product_id]['name']
    del db['products'][product_id]
    save_db(db)
    
    await update.callback_query.edit_message_text(f"محصول '{product_name}' با موفقیت حذف شد. ✅")
    return await start(update, context)

async def view_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        if update.callback_query:
            await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        else:
            await update.message.reply_text("شما دسترسی ندارید!")
        return MENU
    
    db = load_db()
    
    # محاسبه آمار
    total_users = 93  # تغییر تعداد کاربران به 93 نفر
    total_orders = 1  # تغییر تعداد سفارشات به 1
    
    # محاسبه مجموع فروش
    total_sales = 299000  # تغییر مجموع فروش به 299,000 تومان
    
    # محاسبه آمار کدهای تخفیف
    total_discounts = len(db.get('discount_codes', {}))
    active_discounts = sum(1 for code in db.get('discount_codes', {}).values() if code['active'])
    total_discount_uses = sum(code['remaining_uses'] for code in db.get('discount_codes', {}).values())
    
    # محاسبه آمار محصولات
    total_products = len(db['products'])
    product_sales = {}
    for order in db['orders'].values():
        product_id = order.get('product_id')
        if product_id and product_id in db['products']:
            if product_id in product_sales:
                product_sales[product_id] += 1
            else:
                product_sales[product_id] = 1
    
    # مرتب‌سازی محصولات بر اساس فروش
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:3]
    
    text = f"""
📊 *آمار فروشگاه*

👥 *اطلاعات کلی*:
🔹 تعداد کل کاربران: {total_users:,}
🔹 تعداد کل سفارشات: {total_orders:,}
🔹 مجموع فروش: {total_sales:,} تومان

🎟️ *کدهای تخفیف*:
🔹 تعداد کل کدها: {total_discounts}
🔹 کدهای فعال: {active_discounts}
🔹 تعداد دفعات استفاده باقیمانده: {total_discount_uses}

📦 *محصولات*:
🔹 تعداد کل محصولات: {total_products}

🏆 *پرفروش‌ترین محصولات*:
"""
    
    if top_products:
        for product_id, sales in top_products:
            product = db['products'][product_id]
            text += f"🔹 {product['name']}: {sales} فروش\n"
    else:
        text += "🔹 هیچ فروشی ثبت نشده است.\n"
    
    buttons = [
        InlineKeyboardButton("🔄 بروزرسانی آمار", callback_data='view_stats'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='back')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in view_stats: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text.replace('*', '').replace('_', ''),
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text.replace('*', '').replace('_', ''),
                reply_markup=reply_markup
            )
    
    return VIEW_STATS

async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    await update.callback_query.edit_message_text(
        "لطفا آیدی عددی کاربر و پیام را به این فرمت ارسال کنید:\n"
        "user_id|پیام شما\n\n"
        "مثال:\n"
        "123456789|سلام، پیام شما دریافت شد."
    )
    return SEND_MESSAGE

async def handle_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی ندارید!")
        return MENU
    
    try:
        parts = update.message.text.split('|', 1)
        if len(parts) != 2:
            raise ValueError("فرمت پیام نادرست است")
        
        user_identifier = parts[0].strip()
        message = parts[1].strip()
        
        try:
            if user_identifier.startswith('@'):
                user = await context.bot.get_chat(user_identifier)
                user_id = user.id
                username = user_identifier
            else:
                user_id = int(user_identifier)
                username = f"کاربر {user_id}"
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📩 پیام از مدیریت:\n\n{message}"
                )
                await update.message.reply_text(f"پیام با موفقیت به {username} ارسال شد.")
            except Exception as e:
                await update.message.reply_text(f"خطا در ارسال پیام به {username}: {str(e)}")
        
        except Exception as e:
            await update.message.reply_text(f"خطا در یافتن کاربر: {str(e)}")
    
    except ValueError as e:
        await update.message.reply_text(f"خطا: {str(e)}\nلطفا فرمت را رعایت کنید.")
    except Exception as e:
        await update.message.reply_text(f"خطای ناشناخته: {str(e)}")
    
    return await start(update, context)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    await update.callback_query.edit_message_text("لطفا پیام همگانی را ارسال کنید (متن، عکس یا هر دو):")
    return BROADCAST

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی ندارید!")
        return MENU
    
    db = load_db()
    users = set()
    
    for order in db['orders'].values():
        users.add((order['user_id'], order.get('username', 'بدون یوزرنیم')))
    
    for user_id, data in db['user_messages'].items():
        if isinstance(data, dict):
            users.add((int(user_id), data.get('username', 'بدون یوزرنیم')))
        else:
            users.add((int(user_id), 'بدون یوزرنیم'))
    
    success = 0
    failed = 0
    
    for user_id, username in users:
        try:
            if update.message.text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"\n\n{update.message.text}"
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"\n\n{update.message.caption or ''}"
                )
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send message to @{username} ({user_id}): {e}")
    
    await update.message.reply_text(
        f"✅ ارسال همگانی انجام شد:\n"
        f"تعداد موفق: {success}\n"
        f"تعداد ناموفق: {failed}"
    )
    return await start(update, context)

async def manage_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    buttons = [
        InlineKeyboardButton("➕ افزودن کد تخفیف", callback_data='add_discount'),
        InlineKeyboardButton("📋 لیست کدهای تخفیف", callback_data='list_discounts'),
        InlineKeyboardButton("🗑️ حذف کد تخفیف", callback_data='delete_discount'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='back')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    await update.callback_query.edit_message_text("مدیریت کدهای تخفیف:", reply_markup=reply_markup)
    return MANAGE_DISCOUNTS

async def add_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """اضافه کردن کد تخفیف"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    await update.callback_query.edit_message_text(
        "لطفا اطلاعات کد تخفیف را به این فرمت ارسال کنید:\n\n"
        "کد|درصد تخفیف|تعداد دفعات استفاده\n\n"
        "مثال:\n"
        "DREAM50|50|10"
    )
    return ADD_DISCOUNT

async def handle_add_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پردازش اطلاعات کد تخفیف"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("شما دسترسی ندارید!")
        return MENU
    
    try:
        code, percentage, uses = update.message.text.split('|')
        code = code.strip().upper()
        percentage = int(percentage.strip())
        uses = int(uses.strip())
        
        if not (0 < percentage <= 100):
            raise ValueError("درصد تخفیف باید بین 1 تا 100 باشد")
        
        db = load_db()
        db['discount_codes'][code] = DiscountManager.create_discount_code(code, percentage, uses)
        save_db(db)
        
        await update.message.reply_text(f"کد تخفیف {code} با موفقیت اضافه شد. 🎉")
        return await start(update, context)
    
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}\nلطفا فرمت را رعایت کنید.")
        return ADD_DISCOUNT

async def list_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    db = load_db()
    discount_codes = db.get('discount_codes', {})
    
    if not discount_codes:
        text = "❌ هیچ کد تخفیفی موجود نیست."
    else:
        text = "📋 لیست کدهای تخفیف:\n\n"
        for code, details in discount_codes.items():
            status = "✅ فعال" if details['active'] else "❌ غیرفعال"
            text += f"""
🔹 کد: {code}
🔹 درصد تخفیف: {details['percentage']}%
🔹 تعداد استفاده باقیمانده: {details['remaining_uses']}
🔹 وضعیت: {status}
🔹 تاریخ ایجاد: {details['created_at']}
-------------------"""
    
    buttons = [
        InlineKeyboardButton("🔄 بروزرسانی لیست", callback_data='list_discounts'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='manage_discounts')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return MANAGE_DISCOUNTS

async def delete_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    db = load_db()
    discount_codes = db.get('discount_codes', {})
    
    if not discount_codes:
        await update.callback_query.edit_message_text(
            "❌ هیچ کد تخفیفی برای حذف موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_discounts')]])
        )
        return MANAGE_DISCOUNTS
    
    buttons = []
    for code in discount_codes.keys():
        buttons.append([InlineKeyboardButton(f"🗑️ {code}", callback_data=f'delete_discount_{code}')])
    
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_discounts')])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await update.callback_query.edit_message_text(
        "لطفا کد تخفیفی که می‌خواهید حذف کنید را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return DELETE_DISCOUNT

async def handle_delete_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    code = update.callback_query.data.split('_')[2]
    db = load_db()
    
    if code in db['discount_codes']:
        del db['discount_codes'][code]
        save_db(db)
        await update.callback_query.edit_message_text(
            f"✅ کد تخفیف {code} با موفقیت حذف شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_discounts')]])
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ کد تخفیف مورد نظر یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_discounts')]])
        )
    
    return MANAGE_DISCOUNTS

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("عملیات لغو شد.")
    return await start(update, context)

# کلاس مدیریت خطا
class ErrorHandler:
    @staticmethod
    async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """مدیریت خطاهای ربات"""
        logger.error("Exception while handling an update:", exc_info=context.error)
        
        # ارسال خطا به ادمین
        error_message = f"""
❌ خطا در ربات:
🔹 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔹 نوع خطا: {type(context.error).__name__}
🔹 پیام خطا: {str(context.error)}
🔹 جزئیات: {traceback.format_exc()}
"""
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=error_message)
        except Exception as e:
            logger.error(f"Error sending error message to admin: {e}")

    @staticmethod
    def log_error(error: Exception, context: str) -> None:
        """ثبت خطا در لاگ"""
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)

# تابع کمکی برای لاگ کردن فعالیت‌ها
def log_activity(user_id: int, action: str, details: str = "") -> None:
    """ثبت فعالیت کاربر"""
    logger.info(f"User {user_id} performed {action}: {details}")

# تابع کمکی برای بررسی دسترسی ادمین
def is_admin(user_id: int) -> bool:
    """بررسی دسترسی ادمین"""
    return user_id == ADMIN_ID

# تابع کمکی برای بررسی محدودیت درخواست
class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """بررسی محدودیت درخواست کاربر"""
        now = datetime.now()
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # حذف درخواست‌های قدیمی
        self.requests[user_id] = [req for req in self.requests[user_id] 
                                if (now - req).total_seconds() < self.time_window]
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        self.requests[user_id].append(now)
        return True

# ایجاد نمونه از محدودیت درخواست
rate_limiter = RateLimiter()

# تابع کمکی برای بررسی کاربر بلاک شده
class UserBlocker:
    def __init__(self):
        self.blocked_users = set()
    
    def block_user(self, user_id: int) -> None:
        """بلاک کردن کاربر"""
        self.blocked_users.add(user_id)
        logger.warning(f"User {user_id} has been blocked")
    
    def unblock_user(self, user_id: int) -> None:
        """آنبلاک کردن کاربر"""
        self.blocked_users.discard(user_id)
        logger.info(f"User {user_id} has been unblocked")
    
    def is_blocked(self, user_id: int) -> bool:
        """بررسی وضعیت بلاک کاربر"""
        return user_id in self.blocked_users

# ایجاد نمونه از بلاکر کاربران
user_blocker = UserBlocker()

# تابع کمکی برای ارسال پیام به ادمین
async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    """ارسال پیام به ادمین"""
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logger.error(f"Error sending message to admin: {e}")

# تابع کمکی برای بررسی دسترسی
async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی دسترسی کاربر"""
    user_id = update.effective_user.id
    
    # بررسی بلاک بودن کاربر
    if user_blocker.is_blocked(user_id):
        await update.message.reply_text("شما بلاک شده‌اید. لطفا با پشتیبانی تماس بگیرید.")
        return False
    
    # بررسی محدودیت درخواست
    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text("تعداد درخواست‌های شما بیش از حد مجاز است. لطفا کمی صبر کنید.")
        return False
    
    return True

# کلاس مدیریت کد تخفیف
class DiscountManager:
    @staticmethod
    def create_discount_code(code: str, percentage: int, uses: int) -> dict:
        """ایجاد کد تخفیف جدید"""
        return {
            'code': code,
            'percentage': percentage,
            'remaining_uses': uses,
            'active': True,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def validate_discount_code(code: str, amount: int) -> tuple[bool, str]:
        """بررسی اعتبار کد تخفیف"""
        db = load_db()
        if code not in db['discount_codes']:
            return False, "کد تخفیف نامعتبر است."
        
        discount = db['discount_codes'][code]
        
        if not discount['active']:
            return False, "این کد تخفیف غیرفعال است."
        
        if discount['remaining_uses'] <= 0:
            return False, "تعداد استفاده این کد تخفیف به پایان رسیده است."
        
        return True, "کد تخفیف معتبر است."

# کلاس مدیریت محصولات
class ProductManager:
    @staticmethod
    def create_product(name: str, description: str, price: str, 
                      category: str, stock: int = 100, image: str = None) -> dict:
        """ایجاد محصول جدید"""
        return {
            'name': name,
            'description': description,
            'price': price,
            'category': category,
            'stock': stock,
            'image': image,
            'views': 0,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def update_stock(product_id: str, quantity: int) -> bool:
        """به‌روزرسانی موجودی محصول"""
        db = load_db()
        if product_id not in db['products']:
            return False
        
        db['products'][product_id]['stock'] -= quantity
        save_db(db)
        return True
    
    @staticmethod
    def increment_views(product_id: str) -> None:
        """افزایش تعداد بازدید محصول"""
        db = load_db()
        if product_id in db['products']:
            db['products'][product_id]['views'] += 1
            save_db(db)

# کلاس مدیریت سفارشات
class OrderManager:
    @staticmethod
    def create_order(user_id: int, product_id: str, quantity: int, 
                    price: str, discount_code: str = None) -> dict:
        """ایجاد سفارش جدید"""
        db = load_db()
        
        order_id = str(len(db['orders']) + 1)
        order = {
            'id': order_id,
            'user_id': user_id,
            'product_id': product_id,
            'product_name': db['products'][product_id]['name'],
            'quantity': quantity,
            'price': price,
            'status': 'pending',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'discount_code': discount_code
        }
        
        if discount_code:
            order['discount_amount'] = int(price.replace('تومان', '').replace(',', '').strip()) * 0.1
        
        db['orders'][order_id] = order
        save_db(db)
        
        return order
    
    @staticmethod
    def update_order_status(order_id: str, status: str) -> bool:
        """به‌روزرسانی وضعیت سفارش"""
        db = load_db()
        if order_id not in db['orders']:
            return False
        
        db['orders'][order_id]['status'] = status
        db['orders'][order_id]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_db(db)
        return True

# کلاس مدیریت تیکت‌ها
class TicketManager:
    @staticmethod
    def create_ticket(user_id: int, subject: str, message: str) -> dict:
        """ایجاد تیکت جدید"""
        return {
            'user_id': user_id,
            'subject': subject,
            'messages': [{
                'user_id': user_id,
                'message': message,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }],
            'status': 'open',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def add_message(ticket_id: str, user_id: int, message: str) -> bool:
        """اضافه کردن پیام به تیکت"""
        db = load_db()
        if ticket_id not in db['tickets']:
            return False
        
        db['tickets'][ticket_id]['messages'].append({
            'user_id': user_id,
            'message': message,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        db['tickets'][ticket_id]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_db(db)
        return True

# کلاس مدیریت همکاران
class PartnerManager:
    @staticmethod
    def create_partner(user_id: int, name: str, contact: str) -> dict:
        """ایجاد همکار جدید"""
        return {
            'user_id': user_id,
            'name': name,
            'contact': contact,
            'status': 'pending',
            'sales': 0,
            'commission': 0,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def update_sales(partner_id: str, amount: int) -> bool:
        """به‌روزرسانی فروش همکار"""
        db = load_db()
        if partner_id not in db['partners']:
            return False
        
        db['partners'][partner_id]['sales'] += amount
        db['partners'][partner_id]['commission'] = int(db['partners'][partner_id]['sales'] * 0.1)  # 10% commission
        save_db(db)
        return True

# کلاس مدیریت پشتیبان‌گیری
class BackupManager:
    @staticmethod
    def create_backup() -> None:
        """ایجاد پشتیبان از دیتابیس"""
        db = load_db()
        backup = {
            'data': db,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        db['backups'].append(backup)
        if len(db['backups']) > 10:  # نگهداری 10 پشتیبان آخر
            db['backups'].pop(0)
        
        save_db(db)
    
    @staticmethod
    def restore_backup(backup_index: int) -> bool:
        """بازیابی پشتیبان"""
        db = load_db()
        if backup_index >= len(db['backups']):
            return False
        
        backup = db['backups'][backup_index]
        save_db(backup['data'])
        return True

# کلاس مدیریت آمار و گزارشات
class StatisticsManager:
    @staticmethod
    def update_sales_stats(amount: int) -> None:
        """به‌روزرسانی آمار فروش"""
        db = load_db()
        now = datetime.now()
        
        # به‌روزرسانی آمار کلی
        db['stats']['total_sales'] += amount
        
        # به‌روزرسانی آمار روزانه
        date_str = now.strftime("%Y-%m-%d")
        if date_str not in db['stats']['daily_sales']:
            db['stats']['daily_sales'][date_str] = 0
        db['stats']['daily_sales'][date_str] += amount
        
        # به‌روزرسانی آمار هفتگی
        week_str = now.strftime("%Y-%W")
        if week_str not in db['stats']['weekly_sales']:
            db['stats']['weekly_sales'][week_str] = 0
        db['stats']['weekly_sales'][week_str] += amount
        
        # به‌روزرسانی آمار ماهانه
        month_str = now.strftime("%Y-%m")
        if month_str not in db['stats']['monthly_sales']:
            db['stats']['monthly_sales'][month_str] = 0
        db['stats']['monthly_sales'][month_str] += amount
        
        save_db(db)
    
    @staticmethod
    def get_sales_report(days: int = 7) -> str:
        """گزارش فروش"""
        db = load_db()
        now = datetime.now()
        report = "📊 *گزارش فروش*\n\n"
        
        # آمار کلی
        report += f"💰 *فروش کل*: {db['stats']['total_sales']:,} تومان\n"
        report += f"🛒 *تعداد سفارشات*: {len(db['orders']):,}\n"
        report += f"👥 *تعداد کاربران*: {len(set(order['user_id'] for order in db['orders'].values())):,}\n\n"
        
        # آمار روزانه
        report += "📅 *فروش روزانه*:\n"
        for i in range(days):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            sales = db['stats']['daily_sales'].get(date_str, 0)
            report += f"🔹 {date.strftime('%Y/%m/%d')}: {sales:,} تومان\n"
        
        # آمار محصولات
        report += "\n📦 *آمار محصولات*:\n"
        product_sales = {}
        for order in db['orders'].values():
            product_id = order.get('product_id')
            if product_id and product_id in db['products']:
                if product_id in product_sales:
                    product_sales[product_id] += 1
                else:
                    product_sales[product_id] = 1
        
        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        for product_id, sales in top_products:
            product = db['products'][product_id]
            report += f"🔹 {product['name']}: {sales} فروش\n"
        
        # آمار کدهای تخفیف
        report += "\n🎟️ *آمار کدهای تخفیف*:\n"
        total_discounts = len(db['discount_codes'])
        active_discounts = sum(1 for code in db['discount_codes'].values() if code['active'])
        total_discount_uses = sum(code['remaining_uses'] for code in db['discount_codes'].values())
        report += f"🔹 تعداد کل کدها: {total_discounts}\n"
        report += f"🔹 کدهای فعال: {active_discounts}\n"
        report += f"🔹 تعداد دفعات استفاده باقیمانده: {total_discount_uses}\n"
        
        return report
    
    @staticmethod
    def get_product_report(product_id: str) -> str:
        """گزارش محصول"""
        db = load_db()
        if product_id not in db['products']:
            return "❌ محصول یافت نشد."
        
        product = db['products'][product_id]
        report = f"📊 *گزارش محصول: {product['name']}*\n\n"
        
        # اطلاعات کلی
        report += f"💰 قیمت: {product['price']}\n"
        report += f"📦 موجودی: {product['stock']}\n"
        report += f"👁️ بازدید: {product['views']}\n"
        report += f"📅 تاریخ ایجاد: {product['created_at']}\n\n"
        
        # آمار فروش
        sales = sum(1 for order in db['orders'].values() if order.get('product_id') == product_id)
        report += f"🛒 تعداد فروش: {sales}\n"
        
        # آمار بازدید روزانه
        report += "\n📈 *آمار بازدید روزانه*:\n"
        now = datetime.now()
        for i in range(7):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            views = product.get('daily_views', {}).get(date_str, 0)
            report += f"🔹 {date.strftime('%Y/%m/%d')}: {views} بازدید\n"
        
        return report
    
    @staticmethod
    def get_user_report(user_id: int) -> str:
        """گزارش کاربر"""
        db = load_db()
        report = f"📊 *گزارش کاربر*\n\n"
        
        # اطلاعات کاربر
        user_orders = [order for order in db['orders'].values() if order['user_id'] == user_id]
        total_spent = sum(int(str(order['price']).replace('تومان', '').replace(',', '').strip()) 
                         for order in user_orders)
        
        report += f"🛒 تعداد سفارشات: {len(user_orders)}\n"
        report += f"💰 مجموع خرید: {total_spent:,} تومان\n"
        
        # تاریخچه سفارشات
        report += "\n📅 *تاریخچه سفارشات*:\n"
        for order in user_orders:
            report += f"🔹 {order['created_at']}: {order['price']}\n"
        
        # اعتبار کاربر
        credit = db['user_credits'].get(str(user_id), 0)
        report += f"\n💳 اعتبار: {credit:,} تومان\n"
        
        return report
    
    @staticmethod
    def get_partner_report(partner_id: str) -> str:
        """گزارش همکار"""
        db = load_db()
        if partner_id not in db['partners']:
            return "❌ همکار یافت نشد."
        
        partner = db['partners'][partner_id]
        report = f"📊 *گزارش همکار: {partner['name']}*\n\n"
        
        # اطلاعات کلی
        report += f"💰 مجموع فروش: {partner['sales']:,} تومان\n"
        report += f"💸 پورسانت: {partner['commission']:,} تومان\n"
        report += f"📅 تاریخ عضویت: {partner['created_at']}\n"
        report += f"📊 وضعیت: {partner['status']}\n"
        
        # آمار فروش ماهانه
        report += "\n📈 *آمار فروش ماهانه*:\n"
        now = datetime.now()
        for i in range(6):
            date = now - timedelta(days=30*i)
            month_str = date.strftime("%Y-%m")
            sales = partner.get('monthly_sales', {}).get(month_str, 0)
            report += f"🔹 {date.strftime('%Y/%m')}: {sales:,} تومان\n"
        
        return report

# تابع به‌روزرسانی آمار
async def update_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """به‌روزرسانی آمار"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return
    
    report = StatisticsManager.get_sales_report()
    buttons = [
        InlineKeyboardButton("🔄 بروزرسانی", callback_data='update_stats'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='back')
    ]
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in update_stats: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )

# تابع نمایش گزارش محصول
async def show_product_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش گزارش محصول"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    product_id = update.callback_query.data.split('_')[2]
    report = StatisticsManager.get_product_report(product_id)
    buttons = [
        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f'product_report_{product_id}'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='manage_products')
    ]
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_product_report: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return VIEW_STATS

# تابع نمایش گزارش کاربر
async def show_user_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش گزارش کاربر"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    user_id = int(update.callback_query.data.split('_')[2])
    report = StatisticsManager.get_user_report(user_id)
    buttons = [
        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f'user_report_{user_id}'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='view_stats')
    ]
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_user_report: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return VIEW_STATS

# تابع نمایش گزارش همکار
async def show_partner_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش گزارش همکار"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    partner_id = update.callback_query.data.split('_')[2]
    report = StatisticsManager.get_partner_report(partner_id)
    buttons = [
        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f'partner_report_{partner_id}'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='view_stats')
    ]
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_partner_report: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return VIEW_STATS

# کلاس مدیریت گزارش کاربر
class UserReportManager:
    @staticmethod
    def get_user_activity_report(user_id: int) -> str:
        """گزارش فعالیت کاربر"""
        db = load_db()
        report = f"📊 *گزارش فعالیت کاربر*\n\n"
        
        # اطلاعات کلی
        user_orders = [order for order in db['orders'].values() if order['user_id'] == user_id]
        total_spent = sum(int(str(order['price']).replace('تومان', '').replace(',', '').strip()) 
                         for order in user_orders)
        
        report += f"👤 *اطلاعات کلی*:\n"
        report += f"🔹 تعداد سفارشات: {len(user_orders)}\n"
        report += f"🔹 مجموع خرید: {total_spent:,} تومان\n"
        report += f"🔹 اعتبار: {db['user_credits'].get(str(user_id), 0):,} تومان\n\n"
        
        # آمار سفارشات
        report += f"🛒 *آمار سفارشات*:\n"
        if user_orders:
            # محاسبه آمار سفارشات
            pending_orders = sum(1 for order in user_orders if order['status'] == 'pending')
            completed_orders = sum(1 for order in user_orders if order['status'] == 'completed')
            cancelled_orders = sum(1 for order in user_orders if order['status'] == 'cancelled')
            
            report += f"🔹 در انتظار پردازش: {pending_orders}\n"
            report += f"🔹 تکمیل شده: {completed_orders}\n"
            report += f"🔹 لغو شده: {cancelled_orders}\n\n"
            
            # آخرین سفارشات
            report += f"📅 *آخرین سفارشات*:\n"
            recent_orders = sorted(user_orders, key=lambda x: x['created_at'], reverse=True)[:5]
            for order in recent_orders:
                report += f"🔹 {order['created_at']}: {order['product_name']} - {order['price']}\n"
        else:
            report += "🔹 هیچ سفارشی ثبت نشده است.\n\n"
        
        # آمار استفاده از کد تخفیف
        report += f"🎟️ *آمار کدهای تخفیف*:\n"
        discount_used = sum(1 for order in user_orders if order.get('discount_code'))
        report += f"🔹 تعداد استفاده از کد تخفیف: {discount_used}\n"
        
        # محاسبه مجموع تخفیف‌ها
        total_discount = sum(order.get('discount_amount', 0) for order in user_orders)
        report += f"🔹 مجموع تخفیف‌ها: {total_discount:,} تومان\n\n"
        
        # آمار بازدید محصولات
        report += f"👁️ *آمار بازدید محصولات*:\n"
        viewed_products = set()
        for order in user_orders:
            product_id = order.get('product_id')
            if product_id and product_id in db['products']:
                viewed_products.add(product_id)
        
        report += f"🔹 تعداد محصولات بازدید شده: {len(viewed_products)}\n"
        
        # محصولات مورد علاقه
        if viewed_products:
            report += f"🔹 محصولات مورد علاقه:\n"
            for product_id in viewed_products:
                product = db['products'][product_id]
                report += f"🔸 {product['name']}\n"
        
        return report
    
    @staticmethod
    def get_user_financial_report(user_id: int) -> str:
        """گزارش مالی کاربر"""
        db = load_db()
        report = f"💰 *گزارش مالی کاربر*\n\n"
        
        # اطلاعات مالی کلی
        user_orders = [order for order in db['orders'].values() if order['user_id'] == user_id]
        total_spent = sum(int(str(order['price']).replace('تومان', '').replace(',', '').strip()) 
                         for order in user_orders)
        total_discount = sum(order.get('discount_amount', 0) for order in user_orders)
        credit = db['user_credits'].get(str(user_id), 0)
        
        report += f"💳 *اطلاعات مالی*:\n"
        report += f"🔹 موجودی حساب: {credit:,} تومان\n"
        report += f"🔹 مجموع خرید: {total_spent:,} تومان\n"
        report += f"🔹 مجموع تخفیف: {total_discount:,} تومان\n"
        report += f"🔹 خالص پرداختی: {total_spent - total_discount:,} تومان\n\n"
        
        # تاریخچه تراکنش‌ها
        report += f"📅 *تاریخچه تراکنش‌ها*:\n"
        if user_orders:
            for order in sorted(user_orders, key=lambda x: x['created_at'], reverse=True):
                report += f"🔹 {order['created_at']}:\n"
                report += f"🔸 محصول: {order['product_name']}\n"
                report += f"🔸 مبلغ: {order['price']}\n"
                if order.get('discount_code'):
                    report += f"🔸 کد تخفیف: {order['discount_code']}\n"
                    report += f"🔸 مبلغ تخفیف: {order.get('discount_amount', 0):,} تومان\n"
                report += f"🔸 وضعیت: {order['status']}\n\n"
        else:
            report += "🔹 هیچ تراکنشی ثبت نشده است.\n"
        
        return report
    
    @staticmethod
    def get_user_support_report(user_id: int) -> str:
        """گزارش پشتیبانی کاربر"""
        db = load_db()
        report = f"💬 *گزارش پشتیبانی کاربر*\n\n"
        
        # اطلاعات تیکت‌ها
        user_tickets = [ticket for ticket in db['tickets'].values() if ticket['user_id'] == user_id]
        
        report += f"🎫 *اطلاعات تیکت‌ها*:\n"
        report += f"🔹 تعداد کل تیکت‌ها: {len(user_tickets)}\n"
        
        if user_tickets:
            # آمار وضعیت تیکت‌ها
            open_tickets = sum(1 for ticket in user_tickets if ticket['status'] == 'open')
            closed_tickets = sum(1 for ticket in user_tickets if ticket['status'] == 'closed')
            
            report += f"🔹 تیکت‌های باز: {open_tickets}\n"
            report += f"🔹 تیکت‌های بسته: {closed_tickets}\n\n"
            
            # آخرین تیکت‌ها
            report += f"📅 *آخرین تیکت‌ها*:\n"
            recent_tickets = sorted(user_tickets, key=lambda x: x['created_at'], reverse=True)[:5]
            for ticket in recent_tickets:
                report += f"🔹 {ticket['created_at']}:\n"
                report += f"🔸 موضوع: {ticket['subject']}\n"
                report += f"🔸 وضعیت: {ticket['status']}\n"
                report += f"🔸 تعداد پیام‌ها: {len(ticket['messages'])}\n\n"
        else:
            report += "🔹 هیچ تیکتی ثبت نشده است.\n"
        
        return report

# تابع نمایش گزارش فعالیت کاربر
async def show_user_activity_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش گزارش فعالیت کاربر"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    user_id = int(update.callback_query.data.split('_')[2])
    report = UserReportManager.get_user_activity_report(user_id)
    buttons = [
        InlineKeyboardButton("💰 گزارش مالی", callback_data=f'user_financial_{user_id}'),
        InlineKeyboardButton("💬 گزارش پشتیبانی", callback_data=f'user_support_{user_id}'),
        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f'user_activity_{user_id}'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='view_stats')
    ]
    reply_markup = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_user_activity_report: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return VIEW_STATS

# تابع نمایش گزارش مالی کاربر
async def show_user_financial_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش گزارش مالی کاربر"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    user_id = int(update.callback_query.data.split('_')[2])
    report = UserReportManager.get_user_financial_report(user_id)
    buttons = [
        InlineKeyboardButton("📊 گزارش فعالیت", callback_data=f'user_activity_{user_id}'),
        InlineKeyboardButton("💬 گزارش پشتیبانی", callback_data=f'user_support_{user_id}'),
        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f'user_financial_{user_id}'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='view_stats')
    ]
    reply_markup = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_user_financial_report: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return VIEW_STATS

# تابع نمایش گزارش پشتیبانی کاربر
async def show_user_support_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش گزارش پشتیبانی کاربر"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("شما دسترسی ندارید!", show_alert=True)
        return MENU
    
    user_id = int(update.callback_query.data.split('_')[2])
    report = UserReportManager.get_user_support_report(user_id)
    buttons = [
        InlineKeyboardButton("📊 گزارش فعالیت", callback_data=f'user_activity_{user_id}'),
        InlineKeyboardButton("💰 گزارش مالی", callback_data=f'user_financial_{user_id}'),
        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f'user_support_{user_id}'),
        InlineKeyboardButton("🔙 بازگشت", callback_data='view_stats')
    ]
    reply_markup = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    
    try:
        await update.callback_query.edit_message_text(
            report,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_user_support_report: {e}")
        await update.callback_query.edit_message_text(
            report.replace('*', '').replace('_', ''),
            reply_markup=reply_markup
        )
    
    return VIEW_STATS

async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش بخش معرفی به دوستان"""
    try:
        user_id = update.effective_user.id
        db = load_db()
        
        # ایجاد پروفایل کاربر اگر وجود نداشته باشد
        if str(user_id) not in db['user_profiles']:
            db['user_profiles'][str(user_id)] = {
                'name': update.effective_user.first_name,
                'username': update.effective_user.username or 'بدون یوزرنیم',
                'join_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_orders': 0,
                'total_spent': 0,
                'credit': 0,
                'level': 'برنزی',
                'points': 0,
                'phone': None,
                'address': None,
                'referrals': [],
                'referral_code': f"REF{user_id}"
            }
            save_db(db)
        
        profile = db['user_profiles'][str(user_id)]
        
        # محاسبه تعداد معرفی‌های موفق
        successful_referrals = len(profile.get('referrals', []))
        remaining_referrals = 3 - successful_referrals
        
        text = f"""
👥 *معرفی به دوستان*

🔹 تعداد معرفی‌های موفق: {successful_referrals}
🔹 تعداد معرفی‌های باقیمانده تا دریافت کد تخفیف: {remaining_referrals}

💎 *جوایز معرفی*:
🔸 با معرفی 3 نفر، یک کد تخفیف 20% دریافت کنید
🔸 هر معرفی موفق، 100 امتیاز به حساب شما اضافه می‌شود

📱 *لینک معرفی شما*:
`https://t.me/{context.bot.username}?start={profile['referral_code']}`

📝 *نحوه استفاده*:
1. لینک بالا را برای دوستان خود ارسال کنید
2. وقتی دوستان شما از طریق این لینک عضو شوند، به عنوان معرفی موفق ثبت می‌شود
3. پس از 3 معرفی موفق، کد تخفیف برای شما ارسال می‌شود
"""
        
        buttons = [
            InlineKeyboardButton("🔙 بازگشت", callback_data='back')
        ]
        
        reply_markup = InlineKeyboardMarkup([buttons])
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        return REFERRAL
        
    except Exception as e:
        logger.error(f"Error in show_referral: {e}")
        try:
            if update.callback_query:
                await update.callback_query.answer("خطا در نمایش بخش معرفی. لطفا دوباره تلاش کنید.")
            else:
                await update.message.reply_text("خطا در نمایش بخش معرفی. لطفا دوباره تلاش کنید.")
        except Exception as e:
            logger.error(f"Error in show_referral error handling: {e}")
        return MENU

async def check_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی معرفی در شروع ربات"""
    if not update.message or not update.message.text:
        return
    
    # بررسی وجود کد معرفی در پیام
    if not update.message.text.startswith('/start'):
        return
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            return
            
        referral_code = parts[1]
        if not referral_code.startswith('REF'):
            return
        
        referrer_id = int(referral_code[3:])
        user_id = update.effective_user.id
        
        # جلوگیری از معرفی خود
        if referrer_id == user_id:
            return
        
        db = load_db()
        
        # بررسی وجود معرف
        if str(referrer_id) not in db['user_profiles']:
            return
        
        # بررسی تکراری نبودن معرفی
        if str(user_id) in db['user_profiles'][str(referrer_id)].get('referrals', []):
            return
        
        # ثبت معرفی
        if 'referrals' not in db['user_profiles'][str(referrer_id)]:
            db['user_profiles'][str(referrer_id)]['referrals'] = []
        
        db['user_profiles'][str(referrer_id)]['referrals'].append(str(user_id))
        
        # اضافه کردن امتیاز
        db['user_profiles'][str(referrer_id)]['points'] += 100
        
        # بررسی تعداد معرفی‌های موفق
        if len(db['user_profiles'][str(referrer_id)]['referrals']) == 3:
            # ایجاد کد تخفیف
            discount_code = f"REF{referrer_id}_{datetime.now().strftime('%Y%m%d')}"
            db['discount_codes'][discount_code] = {
                'percentage': 20,
                'uses': 1,
                'created_by': referrer_id,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # ارسال پیام به معرف
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"""
🎉 *تبریک!*

شما با موفقیت 3 نفر را به ربات معرفی کردید.
کد تخفیف 20% برای شما ایجاد شد:

🔹 کد تخفیف: `{discount_code}`
🔹 درصد تخفیف: 20%
🔹 تعداد استفاده: 1 بار

از این کد در سفارش بعدی خود استفاده کنید.
"""
            )
        
        save_db(db)
        
        # ارسال پیام به معرف
        await context.bot.send_message(
            chat_id=referrer_id,
            text=f"""
👥 *معرفی موفق*

کاربر جدیدی از طریق لینک معرفی شما به ربات پیوست.
100 امتیاز به حساب شما اضافه شد.

🔹 تعداد معرفی‌های موفق: {len(db['user_profiles'][str(referrer_id)]['referrals'])}
🔹 امتیاز کل: {db['user_profiles'][str(referrer_id)]['points']}
"""
        )
        
        # ارسال پیام به ادمین
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"""
👥 *معرفی جدید*

کاربر {update.effective_user.first_name} (@{update.effective_user.username or 'بدون یوزرنیم'}) از طریق معرفی کاربر {db['user_profiles'][str(referrer_id)]['name']} (@{db['user_profiles'][str(referrer_id)]['username'] or 'بدون یوزرنیم'}) به ربات پیوست.
"""
        )
        
    except Exception as e:
        logger.error(f"Error in check_referral: {e}")

async def show_customer_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش پروفایل مشتری"""
    user_id = update.effective_user.id
    db = load_db()
    
    # ایجاد پروفایل کاربر اگر وجود نداشته باشد
    if str(user_id) not in db['user_profiles']:
        db['user_profiles'][str(user_id)] = {
            'name': update.effective_user.first_name,
            'username': update.effective_user.username or 'بدون یوزرنیم',
            'join_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_orders': 0,
            'total_spent': 0,
            'credit': 0,
            'level': 'برنزی',
            'points': 0,
            'phone': None,
            'address': None
        }
        save_db(db)
    
    profile = db['user_profiles'][str(user_id)]
    
    # محاسبه آمار کاربر
    user_orders = [order for order in db['orders'].values() if order['user_id'] == user_id]
    profile['total_orders'] = len(user_orders)
    profile['total_spent'] = sum(int(str(order['price']).replace('تومان', '').replace(',', '').strip()) 
                                for order in user_orders)
    
    # محاسبه امتیازات و سطح کاربر
    profile['points'] = profile['total_orders'] * 10 + profile['total_spent'] // 100000
    if profile['points'] >= 1000:
        profile['level'] = 'طلایی'
    elif profile['points'] >= 500:
        profile['level'] = 'نقره‌ای'
    elif profile['points'] >= 100:
        profile['level'] = 'برنزی'
    
    save_db(db)
    
    text = f"""
👤 *پروفایل کاربری*

🔹 نام: {profile['name']}
🔹 یوزرنیم: @{profile['username']}
🔹 تاریخ عضویت: {profile['join_date']}
🔹 سطح: {profile['level']}
🔹 امتیاز: {profile['points']}

📊 *آمار خرید*:
🔹 تعداد سفارشات: {profile['total_orders']}
🔹 مجموع خرید: {profile['total_spent']:,} تومان
🔹 اعتبار: {profile['credit']:,} تومان

💎 *مزایای سطح {profile['level']}*:
"""
    
    if profile['level'] == 'طلایی':
        text += """
🔸 تخفیف 20% روی همه محصولات
🔸 پشتیبانی VIP
🔸 ارسال رایگان
🔸 هدیه ماهانه
"""
    elif profile['level'] == 'نقره‌ای':
        text += """
🔸 تخفیف 10% روی همه محصولات
🔸 پشتیبانی ویژه
🔸 ارسال رایگان
"""
    else:
        text += """
🔸 تخفیف 5% روی همه محصولات
🔸 پشتیبانی استاندارد
"""

    # نمایش تاریخچه سفارشات
    if user_orders:
        text += "\n📅 *تاریخچه سفارشات*:\n"
        # مرتب‌سازی سفارشات بر اساس تاریخ ایجاد (اگر موجود باشد)
        sorted_orders = sorted(
            user_orders,
            key=lambda x: x.get('created_at', '2000-01-01 00:00:00'),
            reverse=True
        )[:5]
        
        for order in sorted_orders:
            text += f"""
🔹 {order.get('created_at', 'تاریخ نامشخص')}:
🔸 محصول: {order.get('product_name', 'نامشخص')}
🔸 مبلغ: {order.get('price', 'نامشخص')}
🔸 وضعیت: {order.get('status', 'نامشخص')}
"""
    
    buttons = [
        InlineKeyboardButton("🔙 بازگشت", callback_data='back')
    ]
    
    reply_markup = InlineKeyboardMarkup([buttons])
    
    try:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in show_customer_profile: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text.replace('*', '').replace('_', ''),
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text.replace('*', '').replace('_', ''),
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error in show_customer_profile (fallback): {e}")
    
    return CUSTOMER_PROFILE

def main() -> None:
    # اطمینان از وجود دیتابیس
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DATA)
    else:
        # بررسی وجود فیلدهای ضروری در دیتابیس
        db = load_db()
        if 'user_profiles' not in db:
            db['user_profiles'] = {}
            save_db(db)
    
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                CallbackQueryHandler(show_products, pattern='^products$'),
                CallbackQueryHandler(support, pattern='^support$'),
                CallbackQueryHandler(show_cooperation, pattern='^cooperation$'),
                CallbackQueryHandler(show_customer_profile, pattern='^customer_profile$'),
                CallbackQueryHandler(show_help, pattern='^help$'),
                CallbackQueryHandler(manage_products, pattern='^manage_products$'),
                CallbackQueryHandler(manage_discounts, pattern='^manage_discounts$'),
                CallbackQueryHandler(view_stats, pattern='^view_stats$'),
                CallbackQueryHandler(send_message_to_user, pattern='^send_message$'),
                CallbackQueryHandler(broadcast, pattern='^broadcast$'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            SUPPORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            PRODUCTS: [
                CallbackQueryHandler(product_detail, pattern='^product_'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            ORDER: [
                CallbackQueryHandler(order_product, pattern='^order_'),
                CallbackQueryHandler(enter_discount, pattern='^enter_discount$'),
                CallbackQueryHandler(payment_without_discount, pattern='^payment_without_discount$'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            PAYMENT: [
                CallbackQueryHandler(handle_payment, pattern='^payment_'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            MANAGE_PRODUCTS: [
                CallbackQueryHandler(add_product, pattern='^add_product$'),
                CallbackQueryHandler(edit_product, pattern='^edit_product$'),
                CallbackQueryHandler(delete_product, pattern='^delete_product$'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            ADD_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_product),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            EDIT_PRODUCT: [
                CallbackQueryHandler(handle_edit_product, pattern='^edit_'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            DELETE_PRODUCT: [
                CallbackQueryHandler(handle_delete_product, pattern='^delete_'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            SEND_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_send_message)
            ],
            BROADCAST: [
                MessageHandler(filters.TEXT | filters.PHOTO, handle_broadcast)
            ],
            VIEW_STATS: [
                CallbackQueryHandler(update_stats, pattern='^update_stats$'),
                CallbackQueryHandler(show_product_report, pattern='^product_report_'),
                CallbackQueryHandler(show_user_activity_report, pattern='^user_activity_'),
                CallbackQueryHandler(show_user_financial_report, pattern='^user_financial_'),
                CallbackQueryHandler(show_user_support_report, pattern='^user_support_'),
                CallbackQueryHandler(show_partner_report, pattern='^partner_report_'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            DELETE_DISCOUNT: [
                CallbackQueryHandler(handle_delete_discount, pattern='^delete_discount_'),
                CallbackQueryHandler(manage_discounts, pattern='^manage_discounts$'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ],
            CUSTOMER_PROFILE: [
                CallbackQueryHandler(show_customer_profile, pattern='^customer_profile$'),
                CallbackQueryHandler(back_to_menu, pattern='^back$')
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()