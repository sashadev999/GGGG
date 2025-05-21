import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import json
from datetime import datetime
import bcrypt
from admin_handlers import (
    handle_admin_products, handle_admin_discounts, handle_admin_stats,
    handle_admin_broadcast, handle_broadcast_message, handle_add_product,
    handle_product_info, handle_add_discount, handle_discount_info,
    handle_delete_discount, handle_delete_discount_confirm, handle_list_discounts,
    handle_edit_product, handle_edit_product_selected, handle_edit_product_info,
    handle_delete_product, handle_delete_product_confirm,
    handle_admin_advanced, handle_manage_orders, handle_manage_users,
    handle_manage_support, handle_backup_database,
    handle_block_user, handle_block_user_confirm, handle_unblock_user,
    handle_unblock_user_confirm, handle_confirm_order, handle_confirm_order_action,
    handle_cancel_order, handle_cancel_order_action,
    handle_quick_edit_price, handle_quick_price_selected, handle_toggle_product,
    handle_toggle_product_action, handle_product_stats, handle_sort_products,
    handle_admin_panel, handle_bulk_add_products, handle_bulk_products_info,
    handle_export_products, handle_import_products, handle_import_file
)
from order_handlers import (
    handle_product_selection, handle_add_to_cart, handle_view_cart,
    handle_checkout, handle_enter_discount, handle_discount_code,
    handle_receipt, handle_discount_input
)

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = '7924870342:AAHq4DCOs2JuuPyxLmf8osQoVsjdZKX50_Y'
ADMIN_IDS = ["7058515436"]

# ساختار دیتابیس
class Database:
    def __init__(self):
        self.db_file = 'database.json'
        self.load_db()

    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'users': {},
                'products': {},
                'orders': {},
                'discount_codes': {},
                'support_messages': {},
                'referrals': {}  # اضافه کردن بخش دعوت‌ها
            }
            self.save_db()

    def save_db(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

db = Database()

# توابع کمکی
def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_IDS

# هندلرهای اصلی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # بررسی دعوت کننده
    if context.args and context.args[0].startswith('ref_'):
        referrer_id = context.args[0].split('_')[1]
        if referrer_id != user_id and referrer_id in db.data['users']:
            if 'referrals' not in db.data:
                db.data['referrals'] = {}
            if user_id not in db.data['referrals']:
                db.data['referrals'][user_id] = referrer_id
                # اضافه کردن امتیاز به دعوت کننده
                if 'points' not in db.data['users'][referrer_id]:
                    db.data['users'][referrer_id]['points'] = 0
                db.data['users'][referrer_id]['points'] += 100
                db.save_db()
    
    if user_id not in db.data['users']:
        db.data['users'][user_id] = {
            'username': update.effective_user.username,
            'first_name': update.effective_user.first_name,
            'join_date': datetime.now().isoformat(),
            'orders': [],
            'support_messages': [],
            'points': 0,  # امتیازات کاربر
            'referral_count': 0,  # تعداد دعوت‌های موفق
            'rank': 'برنزی'  # رنک اولیه
        }
        db.save_db()

    # بررسی وضعیت مسدودیت کاربر
    if db.data['users'][user_id].get('is_blocked', False):
        keyboard = [
            [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')]
        ]
        await update.message.reply_text(
            "❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if is_admin(update.effective_user.id):
        keyboard = [
            [InlineKeyboardButton("📊 آمار و گزارشات", callback_data='admin_stats')],
            [InlineKeyboardButton("📦 مدیریت محصولات", callback_data='admin_products')],
            [InlineKeyboardButton("🎟 مدیریت کد تخفیف", callback_data='admin_discounts')],
            [InlineKeyboardButton("📨 ارسال پیام همگانی", callback_data='admin_broadcast')],
            [InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data='admin_advanced')]
        ]
        await update.message.reply_text(
            "👨‍💼 پنل مدیریت\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🛍 محصولات", callback_data='products')],
            [InlineKeyboardButton("👤 پروفایل من", callback_data='profile')],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')],
            [InlineKeyboardButton("❓ راهنما", callback_data='help')]
        ]
        await update.message.reply_text(
            "به فروشگاه ما خوش آمدید! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    # بارگذاری مجدد دیتابیس
    db.load_db()
    
    # بررسی وضعیت مسدودیت کاربر
    if db.data['users'][user_id].get('is_blocked', False):
        if query.data == 'support':
            await show_support(update, context)
        else:
            keyboard = [[InlineKeyboardButton("📞 پشتیبانی", callback_data='support')]]
            await query.message.edit_text(
                "❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    if query.data == 'products':
        await show_products(update, context)
    elif query.data == 'profile':
        await show_profile(update, context)
    elif query.data == 'support':
        await show_support(update, context)
    elif query.data == 'help':
        await show_help(update, context)
    elif query.data == 'back_to_main':
        await start(update, context)
    elif query.data == 'admin_panel':
        await handle_admin_panel(update, context)
    elif query.data.startswith('product_'):
        await handle_product_selection(update, context)
    elif query.data.startswith('buy_'):
        await handle_buy_product(update, context)
    elif query.data.startswith('discount_'):
        await handle_discount_input(update, context)
    elif query.data == 'view_cart':
        await handle_view_cart(update, context)
    elif query.data == 'checkout':
        await handle_checkout(update, context)
    elif query.data == 'enter_discount':
        await handle_enter_discount(update, context)
    elif query.data == 'confirm_order':
        await handle_confirm_order(update, context)
    elif query.data == 'admin_products':
        await handle_admin_products(update, context)
    elif query.data == 'admin_discounts':
        await handle_admin_discounts(update, context)
    elif query.data == 'admin_stats':
        await handle_admin_stats(update, context)
    elif query.data == 'admin_broadcast':
        await handle_admin_broadcast(update, context)
    elif query.data == 'admin_advanced':
        await handle_admin_advanced(update, context)
    elif query.data == 'manage_orders':
        await handle_manage_orders(update, context)
    elif query.data == 'manage_users':
        await handle_manage_users(update, context)
    elif query.data == 'manage_support':
        await handle_manage_support(update, context)
    elif query.data == 'backup_database':
        await handle_backup_database(update, context)
    elif query.data == 'add_product':
        await handle_add_product(update, context)
    elif query.data == 'edit_product':
        await handle_edit_product(update, context)
    elif query.data.startswith('edit_product_'):
        await handle_edit_product_selected(update, context)
    elif query.data == 'delete_product':
        await handle_delete_product(update, context)
    elif query.data.startswith('delete_product_'):
        await handle_delete_product_confirm(update, context)
    elif query.data == 'add_discount':
        await handle_add_discount(update, context)
    elif query.data == 'delete_discount':
        await handle_delete_discount(update, context)
    elif query.data == 'list_discounts':
        await handle_list_discounts(update, context)
    elif query.data.startswith('delete_discount_'):
        await handle_delete_discount_confirm(update, context)
    elif query.data == 'block_user':
        await handle_block_user(update, context)
    elif query.data.startswith('block_user_'):
        await handle_block_user_confirm(update, context)
    elif query.data == 'unblock_user':
        await handle_unblock_user(update, context)
    elif query.data.startswith('unblock_user_'):
        await handle_unblock_user_confirm(update, context)
    elif query.data.startswith('confirm_order_'):
        await handle_confirm_order_action(update, context)
    elif query.data == 'cancel_order':
        await handle_cancel_order(update, context)
    elif query.data.startswith('cancel_order_'):
        await handle_cancel_order_action(update, context)
    elif query.data == 'quick_edit_price':
        await handle_quick_edit_price(update, context)
    elif query.data.startswith('quick_price_'):
        await handle_quick_price_selected(update, context)
    elif query.data == 'toggle_product':
        await handle_toggle_product(update, context)
    elif query.data.startswith('toggle_'):
        await handle_toggle_product_action(update, context)
    elif query.data == 'product_stats':
        await handle_product_stats(update, context)
    elif query.data.startswith('sort_'):
        await handle_sort_products(update, context)

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    
    # بارگذاری مجدد دیتابیس
    db.load_db()
    
    # بررسی مسدود بودن کاربر
    if user_id in db.data['users'] and db.data['users'][user_id].get('is_blocked', False):
        keyboard = [[InlineKeyboardButton("📞 پشتیبانی", callback_data='support')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=reply_markup
        )
        return

    if not db.data['products']:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "❌ در حال حاضر هیچ محصولی موجود نیست.",
            reply_markup=reply_markup
        )
        return

    keyboard = []
    for product_id, product in db.data['products'].items():
        # فقط محصولات فعال را نمایش بده
        if product.get('is_active', True):
            keyboard.append([InlineKeyboardButton(
                f"{product['name']} - {product['price']:,} تومان",
                callback_data=f'product_{product_id}'
            )])
    
    if not keyboard:  # اگر هیچ محصول فعالی نباشد
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "❌ در حال حاضر هیچ محصول فعالی موجود نیست.",
            reply_markup=reply_markup
        )
        return
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "📦 لیست محصولات:\nلطفاً محصول مورد نظر خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    user_data = db.data['users'][user_id]
    
    # محاسبه رنک کاربر
    points = user_data.get('points', 0)
    if points >= 10000:
        rank = "💎 الماس"
    elif points >= 5000:
        rank = "🏆 طلایی"
    elif points >= 2000:
        rank = "🥈 نقره‌ای"
    elif points >= 1000:
        rank = "🥉 برنزی"
    else:
        rank = "🔰 تازه‌کار"
    
    # به‌روزرسانی رنک کاربر
    user_data['rank'] = rank
    db.save_db()
    
    # محاسبه تعداد دعوت‌های موفق
    referral_count = 0
    if 'referrals' in db.data:
        for referred_id, referrer_id in db.data['referrals'].items():
            if referrer_id == user_id:
                referral_count += 1
    
    user_data['referral_count'] = referral_count
    db.save_db()
    
    # دریافت اطلاعات سفارشات
    orders_text = ""
    total_spent = 0
    for order_id in user_data['orders']:
        order = db.data['orders'][order_id]
        orders_text += f"\n🆔 سفارش {order_id}:\n"
        orders_text += f"💰 مبلغ: {order['total_price']} تومان\n"
        orders_text += f"📅 تاریخ: {order['created_at']}\n"
        orders_text += f"📊 وضعیت: {order['status']}\n"
        total_spent += order['total_price']
    
    # ساخت لینک دعوت
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    profile_text = f"""
👤 پروفایل شما:

👤 نام کاربری: {user_data['first_name']}
📅 تاریخ عضویت: {user_data['join_date']}
🏆 رنک: {rank}
💎 امتیازات: {points}
👥 تعداد دعوت‌های موفق: {referral_count}
💰 مجموع خرید: {total_spent:,} تومان
📦 تعداد سفارشات: {len(user_data['orders'])}

🔗 لینک دعوت شما:
{invite_link}

📋 تاریخچه سفارشات:
{orders_text}
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(profile_text, reply_markup=reply_markup)

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "لطفاً پیام خود را برای پشتیبانی ارسال کنید:",
        reply_markup=reply_markup
    )
    context.user_data['waiting_for_support_message'] = True

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    help_text = """
📚 راهنمای استفاده از ربات:

1️⃣ برای مشاهده محصولات، روی گزینه "محصولات" کلیک کنید
2️⃣ برای استفاده از کد تخفیف، آن را در زمان سفارش وارد کنید
3️⃣ برای ارتباط با پشتیبانی، از بخش "پشتیبانی" استفاده کنید
4️⃣ برای مشاهده سفارشات خود، به بخش "پروفایل من" مراجعه کنید
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(help_text, reply_markup=reply_markup)

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    about_text = """
ℹ️ درباره ما:

ما یک فروشگاه آنلاین هستیم که با هدف ارائه خدمات بهتر به مشتریان عزیز فعالیت می‌کنیم.

✅ مزایای خرید از ما:
- قیمت‌های مناسب
- کیفیت بالا
- پشتیبانی 24 ساعته
- ارسال سریع
- ضمانت اصالت کالا

💫 چشم‌انداز ما:
ارائه بهترین خدمات به مشتریان و تبدیل شدن به برند برتر در زمینه فروش آنلاین
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(about_text, reply_markup=reply_markup)

async def show_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    contact_text = """
📞 تماس با ما:

📱 تلگرام: @support
📧 ایمیل: support@example.com
☎️ تلفن: 021-12345678

⏰ ساعات پاسخگویی:
شنبه تا چهارشنبه: 9 صبح تا 9 شب
پنجشنبه: 9 صبح تا 6 عصر
جمعه: تعطیل

📍 آدرس:
تهران، خیابان ولیعصر، پلاک 123
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(contact_text, reply_markup=reply_markup)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rules_text = """
📜 قوانین و مقررات:

1️⃣ شرایط خرید:
   - حداقل مبلغ خرید: 50,000 تومان
   - حداکثر مبلغ خرید: 5,000,000 تومان
   - زمان پردازش سفارش: 24 ساعت

2️⃣ شرایط ارسال:
   - ارسال به سراسر کشور
   - زمان تحویل: 2 تا 4 روز کاری
   - هزینه ارسال: رایگان برای خریدهای بالای 500,000 تومان

3️⃣ شرایط بازگشت کالا:
   - مهلت بازگشت: 7 روز
   - شرایط بازگشت: عدم استفاده و سالم بودن کالا
   - هزینه بازگشت: به عهده مشتری

4️⃣ شرایط استفاده از کد تخفیف:
   - هر کد تخفیف فقط یکبار قابل استفاده است
   - کد تخفیف قابل ترکیب با سایر تخفیف‌ها نیست
   - اعتبار کد تخفیف: 30 روز
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(rules_text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    user_id = str(update.effective_user.id)
    
    # بارگذاری مجدد دیتابیس
    db.load_db()
    
    # بررسی مسدود بودن کاربر
    if user_id in db.data['users'] and db.data['users'][user_id].get('is_blocked', False):
        keyboard = [[InlineKeyboardButton("📞 پشتیبانی", callback_data='support')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=reply_markup
        )
        return

    if context.user_data.get('waiting_for_support_message'):
        # پردازش پیام پشتیبانی
        await handle_support_message(update, context)
    elif context.user_data.get('waiting_for_receipt'):
        # پردازش رسید پرداخت
        await handle_receipt(update, context)
    elif context.user_data.get('waiting_for_broadcast_message'):
        # پردازش پیام همگانی
        await handle_broadcast_message(update, context)
    elif context.user_data.get('waiting_for_product_info'):
        # پردازش اطلاعات محصول جدید
        await handle_product_info(update, context)
    elif context.user_data.get('waiting_for_edit_product'):
        # پردازش ویرایش محصول
        await handle_edit_product_info(update, context)
    elif context.user_data.get('waiting_for_discount_info'):
        # پردازش اطلاعات کد تخفیف
        await handle_discount_info(update, context)
    elif context.user_data.get('editing_price_product_id'):
        # پردازش ویرایش قیمت
        await handle_quick_price_input(update, context)
    else:
        # پیام عادی
        keyboard = [
            [InlineKeyboardButton("🛍 محصولات", callback_data='products')],
            [InlineKeyboardButton("👤 پروفایل من", callback_data='profile')],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')],
            [InlineKeyboardButton("❓ راهنما", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "لطفاً از منوی زیر استفاده کنید:",
            reply_markup=reply_markup
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_receipt'):
        await handle_receipt(update, context)
    else:
        await update.message.reply_text(
            "لطفاً فقط در زمان ارسال رسید پرداخت، عکس ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]])
        )

async def handle_product_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # بارگذاری مجدد دیتابیس برای اطمینان از داشتن آخرین تغییرات
    db.load_db()
    product_id = query.data.split('_')[1]
    product = db.data['products'].get(product_id)
    
    if not product:
        await query.message.edit_text(
            "محصول مورد نظر یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست محصولات", callback_data='products')]])
        )
        return
    
    product_text = f"""
{product['name']}

💰 قیمت: {product['price']} تومان

📝 توضیحات:
{product['description']}
    """
    
    keyboard = [
        [InlineKeyboardButton("💳 خرید", callback_data=f'buy_{product_id}')],
        [InlineKeyboardButton("🎟 وارد کردن کد تخفیف", callback_data=f'discount_{product_id}')],
        [InlineKeyboardButton("🔙 بازگشت به لیست محصولات", callback_data='products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(product_text, reply_markup=reply_markup)

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 آمار و گزارشات", callback_data='admin_stats')],
        [InlineKeyboardButton("📦 مدیریت محصولات", callback_data='admin_products')],
        [InlineKeyboardButton("🎟 مدیریت کد تخفیف", callback_data='admin_discounts')],
        [InlineKeyboardButton("📨 ارسال پیام همگانی", callback_data='admin_broadcast')],
        [InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data='admin_advanced')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💼 پنل مدیریت\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

def main():
    application = Application.builder().token(TOKEN).build()

    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Admin handlers
    application.add_handler(CallbackQueryHandler(handle_admin_products, pattern='^admin_products$'))
    application.add_handler(CallbackQueryHandler(handle_edit_product, pattern='^edit_product$'))
    application.add_handler(CallbackQueryHandler(handle_edit_product_selected, pattern='^edit_product_'))
    application.add_handler(CallbackQueryHandler(handle_delete_product, pattern='^delete_product$'))
    application.add_handler(CallbackQueryHandler(handle_delete_product_confirm, pattern='^delete_product_'))
    application.add_handler(CallbackQueryHandler(handle_admin_discounts, pattern='^admin_discounts$'))
    application.add_handler(CallbackQueryHandler(handle_admin_stats, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(handle_admin_broadcast, pattern='^admin_broadcast$'))
    application.add_handler(CallbackQueryHandler(handle_admin_advanced, pattern='^admin_advanced$'))
    application.add_handler(CallbackQueryHandler(handle_manage_orders, pattern='^manage_orders$'))
    application.add_handler(CallbackQueryHandler(handle_manage_users, pattern='^manage_users$'))
    application.add_handler(CallbackQueryHandler(handle_manage_support, pattern='^manage_support$'))
    application.add_handler(CallbackQueryHandler(handle_backup_database, pattern='^backup_database$'))
    application.add_handler(CallbackQueryHandler(handle_block_user, pattern='^block_user$'))
    application.add_handler(CallbackQueryHandler(handle_unblock_user, pattern='^unblock_user$'))
    application.add_handler(CallbackQueryHandler(handle_block_user_confirm, pattern='^block_user_'))
    application.add_handler(CallbackQueryHandler(handle_unblock_user_confirm, pattern='^unblock_user_'))
    application.add_handler(CallbackQueryHandler(handle_confirm_order, pattern='^confirm_order$'))
    application.add_handler(CallbackQueryHandler(handle_confirm_order_action, pattern='^confirm_order_'))
    application.add_handler(CallbackQueryHandler(handle_cancel_order, pattern='^cancel_order$'))
    application.add_handler(CallbackQueryHandler(handle_cancel_order_action, pattern='^cancel_order_'))
    # New admin handlers
    application.add_handler(CallbackQueryHandler(handle_quick_edit_price, pattern='^quick_edit_price$'))
    application.add_handler(CallbackQueryHandler(handle_quick_price_selected, pattern='^quick_price_'))
    application.add_handler(CallbackQueryHandler(handle_toggle_product, pattern='^toggle_product$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_product_action, pattern='^toggle_'))
    application.add_handler(CallbackQueryHandler(handle_product_stats, pattern='^product_stats$'))
    application.add_handler(CallbackQueryHandler(handle_sort_products, pattern='^sort_'))
    application.add_handler(CommandHandler("admin", handle_admin))
    application.add_handler(CallbackQueryHandler(handle_add_product, pattern='^add_product$'))
    application.add_handler(CallbackQueryHandler(handle_bulk_add_products, pattern='^bulk_add_products$'))
    application.add_handler(CallbackQueryHandler(handle_export_products, pattern='^export_products$'))
    application.add_handler(CallbackQueryHandler(handle_import_products, pattern='^import_products$'))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_import_file))
    application.add_handler(CallbackQueryHandler(handle_bulk_products_info, pattern='^bulk_products_info$'))

    # شروع ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 