from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import json
import os

async def handle_admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ افزودن محصول جدید", callback_data='add_product')],
        [InlineKeyboardButton("📦 افزودن گروهی محصولات", callback_data='bulk_add_products')],
        [InlineKeyboardButton("📤 خروجی گرفتن از محصولات", callback_data='export_products')],
        [InlineKeyboardButton("📥 وارد کردن محصولات", callback_data='import_products')],
        [InlineKeyboardButton("📊 آمار محصولات", callback_data='product_stats')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(
        "📦 مدیریت محصولات\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['products']:
        await query.message.edit_text(
            "❌ هیچ محصولی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    keyboard = []
    for product_id, product in db.data['products'].items():
        keyboard.append([InlineKeyboardButton(
            f"📝 {product['name']}",
            callback_data=f'edit_product_{product_id}'
        )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')])
    
    await query.message.edit_text(
        "📝 ویرایش محصول\nلطفاً محصول مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_edit_product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    product_id = query.data.split('_')[2]
    product = db.data['products'].get(product_id)
    
    if not product:
        await query.message.edit_text(
            "❌ محصول مورد نظر یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    await query.message.edit_text(
        "📝 ویرایش محصول\n"
        "لطفاً اطلاعات جدید محصول را به فرمت زیر ارسال کنید:\n\n"
        f"نام محصول: {product['name']}\n"
        f"قیمت (تومان): {product['price']}\n"
        f"توضیحات: {product['description']}"
    )
    context.user_data['waiting_for_edit_product'] = True
    context.user_data['editing_product_id'] = product_id

async def handle_edit_product_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, logger
    if not context.user_data.get('waiting_for_edit_product'):
        return
    
    try:
        lines = update.message.text.strip().split('\n')
        if len(lines) < 3:
            raise ValueError("اطلاعات ناقص است")
        
        name = lines[0].strip()
        price = int(lines[1].strip())
        description = '\n'.join(lines[2:]).strip()
        
        product_id = context.user_data['editing_product_id']
        
        # بارگذاری مجدد دیتابیس
        db.load_db()
        
        if product_id not in db.data['products']:
            raise ValueError("محصول مورد نظر یافت نشد")
        
        db.data['products'][product_id] = {
            'name': name,
            'price': price,
            'description': description,
            'created_at': db.data['products'][product_id]['created_at']
        }
        db.save_db()
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ محصول با موفقیت ویرایش شد\n"
            f"شناسه محصول: {product_id}\n"
            f"نام: {name}\n"
            f"قیمت: {price} تومان",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_edit_product_info: {e}")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ خطا در ویرایش محصول\n"
            "لطفاً اطلاعات را به درستی وارد کنید.",
            reply_markup=reply_markup
        )
    
    context.user_data.pop('waiting_for_edit_product', None)
    context.user_data.pop('editing_product_id', None)

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['products']:
        await query.message.edit_text(
            "❌ هیچ محصولی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    keyboard = []
    for product_id, product in db.data['products'].items():
        keyboard.append([InlineKeyboardButton(
            f"❌ {product['name']}",
            callback_data=f'delete_product_{product_id}'
        )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')])
    
    await query.message.edit_text(
        "❌ حذف محصول\nلطفاً محصول مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_delete_product_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        product_id = query.data.split('_')[2]
        
        # بارگذاری مجدد دیتابیس
        db.load_db()
        
        if product_id in db.data['products']:
            product_name = db.data['products'][product_id]['name']
            del db.data['products'][product_id]
            db.save_db()
            await query.message.edit_text(
                f"✅ محصول {product_name} با موفقیت حذف شد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
            )
        else:
            await query.message.edit_text(
                "❌ محصول مورد نظر یافت نشد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
            )
    except Exception as e:
        logger.error(f"Error in handle_delete_product_confirm: {e}")
        await query.message.edit_text(
            "❌ خطا در حذف محصول",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )

async def handle_admin_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ افزودن کد تخفیف", callback_data='add_discount')],
        [InlineKeyboardButton("❌ حذف کد تخفیف", callback_data='delete_discount')],
        [InlineKeyboardButton("📋 لیست کدهای تخفیف", callback_data='list_discounts')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🎟 مدیریت کدهای تخفیف\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    # محاسبه آمار
    total_users = len(db.data['users'])
    total_products = len(db.data['products'])
    total_orders = len(db.data['orders'])
    total_support_messages = len(db.data['support_messages'])
    
    stats_text = f"""
📊 آمار و گزارشات:

👥 تعداد کل کاربران: {total_users}
📦 تعداد کل محصولات: {total_products}
🛍 تعداد کل سفارشات: {total_orders}
📨 تعداد پیام‌های پشتیبانی: {total_support_messages}
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(stats_text, reply_markup=reply_markup)

async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    await query.message.edit_text(
        "📨 ارسال پیام همگانی\nلطفاً پیام خود را ارسال کنید:"
    )
    context.user_data['waiting_for_broadcast_message'] = True

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    if not context.user_data.get('waiting_for_broadcast_message'):
        return
    
    message_text = update.message.text
    sent_count = 0
    failed_count = 0
    
    for user_id in db.data['users']:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"\n\n{message_text}"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
    
    await update.message.reply_text(
        f"✅ پیام همگانی ارسال شد\n"
        f"✅ تعداد ارسال موفق: {sent_count}\n"
        f"❌ تعداد ارسال ناموفق: {failed_count}"
    )
    context.user_data['waiting_for_broadcast_message'] = False

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    await query.message.edit_text(
        "لطفا اطلاعات محصول را به این فرمت ارسال کنید:\n\n"
        "نام محصول|توضیحات|قیمت\n\n"
        "مثال:\n"
        "محصول تست|این یک محصول تستی است|100,000 تومان"
    )
    context.user_data['waiting_for_product_info'] = True

async def handle_product_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, logger
    if not context.user_data.get('waiting_for_product_info'):
        return
    
    try:
        # تقسیم متن با استفاده از |
        text = update.message.text.strip()
        parts = text.split('|')
        
        if len(parts) < 3:
            raise ValueError("اطلاعات ناقص است. لطفاً از فرمت صحیح استفاده کنید.")
        
        name = parts[0].strip()
        description = parts[1].strip()
        price_str = parts[2].strip().replace('تومان', '').replace(',', '').strip()
        
        try:
            price = int(price_str)
        except ValueError:
            raise ValueError("قیمت باید به صورت عدد باشد.")
        
        if not name or not description:
            raise ValueError("نام و توضیحات محصول نمی‌تواند خالی باشد.")
        
        if price <= 0:
            raise ValueError("قیمت محصول باید بیشتر از صفر باشد.")
        
        # بارگذاری مجدد دیتابیس
        db.load_db()
        
        product_id = str(len(db.data['products']) + 1)
        db.data['products'][product_id] = {
            'name': name,
            'price': price,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        db.save_db()
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ محصول با موفقیت اضافه شد\n\n"
            f"نام محصول: {name}\n"
            f"📝 توضیحات: {description}\n"
            f"💰 قیمت: {price:,} تومان",
            reply_markup=reply_markup
        )
    except ValueError as e:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ خطا در افزودن محصول\n{str(e)}\n\n"
            "لطفاً اطلاعات را به فرمت زیر وارد کنید:\n"
            "نام محصول|توضیحات|قیمت\n\n"
            "مثال:\n"
            "محصول تست|این یک محصول تستی است|100,000 تومان",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_product_info: {e}")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ خطا در افزودن محصول\n"
            "لطفاً اطلاعات را به درستی وارد کنید.",
            reply_markup=reply_markup
        )
    
    context.user_data['waiting_for_product_info'] = False

async def handle_add_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    await query.message.edit_text(
        "➕ افزودن کد تخفیف جدید\n"
        "لطفاً اطلاعات کد تخفیف را به فرمت زیر ارسال کنید:\n\n"
        "کد تخفیف\n"
        "درصد تخفیف\n"
        "تاریخ انقضا (YYYY-MM-DD)\n"
        "تعداد دفعات مجاز استفاده"
    )
    context.user_data['waiting_for_discount_info'] = True

async def handle_discount_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    if not context.user_data.get('waiting_for_discount_info'):
        return
    
    try:
        lines = update.message.text.strip().split('\n')
        if len(lines) < 4:
            raise ValueError("اطلاعات ناقص است")
        
        code = lines[0].strip().upper()
        percentage = int(lines[1].strip())
        expiry_date = datetime.strptime(lines[2].strip(), '%Y-%m-%d').isoformat()
        usage_limit = int(lines[3].strip())
        
        if percentage < 1 or percentage > 100:
            raise ValueError("درصد تخفیف باید بین 1 تا 100 باشد")
        
        if usage_limit < 1:
            raise ValueError("تعداد دفعات مجاز استفاده باید بیشتر از 0 باشد")
        
        db.data['discount_codes'][code] = {
            'percentage': percentage,
            'expiry_date': expiry_date,
            'created_at': datetime.now().isoformat(),
            'usage_limit': usage_limit,
            'usage_count': 0
        }
        db.save_db()
        
        await update.message.reply_text(
            f"✅ کد تخفیف با موفقیت اضافه شد\n"
            f"کد: {code}\n"
            f"درصد تخفیف: {percentage}%\n"
            f"تاریخ انقضا: {expiry_date}\n"
            f"تعداد دفعات مجاز استفاده: {usage_limit}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]])
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ خطا در افزودن کد تخفیف\n"
            "لطفاً اطلاعات را به درستی وارد کنید."
        )
    
    context.user_data['waiting_for_discount_info'] = False

async def handle_delete_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['discount_codes']:
        await query.message.edit_text(
            "❌ هیچ کد تخفیفی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]])
        )
        return

    keyboard = []
    for code in db.data['discount_codes']:
        keyboard.append([InlineKeyboardButton(f"❌ {code}", callback_data=f'delete_discount_{code}')])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')])
    
    await query.message.edit_text(
        "❌ حذف کد تخفیف\nلطفاً کد تخفیف مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_delete_discount_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    code = query.data.split('_')[2]
    if code in db.data['discount_codes']:
        del db.data['discount_codes'][code]
        db.save_db()
        await query.message.edit_text(
            f"✅ کد تخفیف {code} با موفقیت حذف شد",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]])
        )
    else:
        await query.message.edit_text(
            "❌ کد تخفیف مورد نظر یافت نشد",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]])
        )

async def handle_list_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['discount_codes']:
        await query.message.edit_text(
            "📋 هیچ کد تخفیفی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]])
        )
        return

    discounts_text = "📋 لیست کدهای تخفیف:\n\n"
    for code, discount in db.data['discount_codes'].items():
        discounts_text += f"🎟 کد: {code}\n"
        discounts_text += f"📊 درصد تخفیف: {discount['percentage']}%\n"
        discounts_text += f"📅 تاریخ انقضا: {discount['expiry_date']}\n\n"
    
    await query.message.edit_text(
        discounts_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_discounts')]])
    )

async def handle_admin_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("📝 مدیریت سفارشات", callback_data='manage_orders')],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='manage_users')],
        [InlineKeyboardButton("📨 مدیریت پیام‌های پشتیبانی", callback_data='manage_support')],
        [InlineKeyboardButton("💾 پشتیبان‌گیری از دیتابیس", callback_data='backup_database')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "⚙️ تنظیمات پیشرفته\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def handle_manage_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['orders']:
        await query.message.edit_text(
            "❌ هیچ سفارشی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]])
        )
        return

    orders_text = "📝 لیست سفارشات:\n\n"
    for order_id, order in db.data['orders'].items():
        product = db.data['products'].get(order['product_id'], {'name': 'محصول حذف شده'})
        user = db.data['users'].get(order['user_id'], {'first_name': 'کاربر ناشناس'})
        orders_text += f"🆔 سفارش {order_id}:\n"
        orders_text += f"👤 کاربر: {user['first_name']}\n"
        orders_text += f"📦 محصول: {product['name']}\n"
        orders_text += f"💰 مبلغ: {order['total_price']} تومان\n"
        orders_text += f"📅 تاریخ: {order['created_at']}\n"
        orders_text += f"📊 وضعیت: {order['status']}\n\n"

    keyboard = [
        [InlineKeyboardButton("✅ تایید سفارش", callback_data='confirm_order')],
        [InlineKeyboardButton("❌ لغو سفارش", callback_data='cancel_order')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(orders_text, reply_markup=reply_markup)

async def handle_manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['users']:
        await query.message.edit_text(
            "❌ هیچ کاربری موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]])
        )
        return

    users_text = "👥 لیست کاربران:\n\n"
    for user_id, user in db.data['users'].items():
        users_text += f"👤 کاربر: {user['first_name']}\n"
        users_text += f"🆔 شناسه: {user_id}\n"
        users_text += f"📅 تاریخ عضویت: {user['join_date']}\n"
        users_text += f"📦 تعداد سفارشات: {len(user['orders'])}\n\n"

    keyboard = [
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data='block_user')],
        [InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data='unblock_user')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(users_text, reply_markup=reply_markup)

async def handle_manage_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['support_messages']:
        await query.message.edit_text(
            "❌ هیچ پیام پشتیبانی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]])
        )
        return

    support_text = "📨 لیست پیام‌های پشتیبانی:\n\n"
    for msg_id, msg in db.data['support_messages'].items():
        user = db.data['users'].get(msg['user_id'], {'first_name': 'کاربر ناشناس'})
        support_text += f"🆔 پیام {msg_id}:\n"
        support_text += f"👤 کاربر: {user['first_name']}\n"
        support_text += f"📝 متن پیام: {msg['message']}\n"
        support_text += f"📅 تاریخ: {msg['timestamp']}\n"
        support_text += f"📊 وضعیت: {msg['status']}\n\n"

    keyboard = [
        [InlineKeyboardButton("✅ پاسخ به پیام", callback_data='reply_support')],
        [InlineKeyboardButton("❌ حذف پیام", callback_data='delete_support')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(support_text, reply_markup=reply_markup)

async def handle_backup_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        # ایجاد نسخه پشتیبان
        backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_{backup_time}.json'
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(db.data, f, ensure_ascii=False, indent=4)
        
        await query.message.edit_text(
            f"✅ نسخه پشتیبان با موفقیت ایجاد شد\n"
            f"📁 نام فایل: {backup_file}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]])
        )
    except Exception as e:
        logger.error(f"Error in backup_database: {e}")
        await query.message.edit_text(
            "❌ خطا در ایجاد نسخه پشتیبان",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_advanced')]])
        )

async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    # بارگذاری مجدد دیتابیس
    db.load_db()

    # دریافت لیست کاربران از تلگرام
    try:
        async for member in context.bot.get_chat_administrators(chat_id=update.effective_chat.id):
            user_id = str(member.user.id)
            if user_id not in db.data['users']:
                db.data['users'][user_id] = {
                    'username': member.user.username,
                    'first_name': member.user.first_name,
                    'join_date': datetime.now().isoformat(),
                    'orders': [],
                    'support_messages': []
                }
        db.save_db()
    except Exception as e:
        logger.error(f"Error getting chat members: {e}")

    if not db.data['users']:
        await query.message.edit_text(
            "❌ هیچ کاربری موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
        )
        return

    keyboard = []
    for user_id, user in db.data['users'].items():
        if not user.get('is_blocked', False):
            keyboard.append([InlineKeyboardButton(
                f"🚫 {user['first_name']} (@{user.get('username', 'بدون یوزرنیم')})",
                callback_data=f'block_user_{user_id}'
            )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')])
    
    await query.message.edit_text(
        "🚫 مسدود کردن کاربر\nلطفاً کاربر مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    # بارگذاری مجدد دیتابیس
    db.load_db()

    # دریافت لیست کاربران از تلگرام
    try:
        async for member in context.bot.get_chat_administrators(chat_id=update.effective_chat.id):
            user_id = str(member.user.id)
            if user_id not in db.data['users']:
                db.data['users'][user_id] = {
                    'username': member.user.username,
                    'first_name': member.user.first_name,
                    'join_date': datetime.now().isoformat(),
                    'orders': [],
                    'support_messages': []
                }
        db.save_db()
    except Exception as e:
        logger.error(f"Error getting chat members: {e}")

    if not db.data['users']:
        await query.message.edit_text(
            "❌ هیچ کاربری موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
        )
        return

    keyboard = []
    for user_id, user in db.data['users'].items():
        if user.get('is_blocked', False):
            keyboard.append([InlineKeyboardButton(
                f"✅ {user['first_name']} (@{user.get('username', 'بدون یوزرنیم')})",
                callback_data=f'unblock_user_{user_id}'
            )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')])
    
    await query.message.edit_text(
        "✅ آزاد کردن کاربر\nلطفاً کاربر مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['orders']:
        await query.message.edit_text(
            "❌ هیچ سفارشی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
        )
        return

    keyboard = []
    for order_id, order in db.data['orders'].items():
        if order['status'] == 'pending':
            keyboard.append([InlineKeyboardButton(
                f"✅ سفارش {order_id}",
                callback_data=f'confirm_order_{order_id}'
            )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')])
    
    await query.message.edit_text(
        "✅ تایید سفارش\nلطفاً سفارش مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_confirm_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        order_id = query.data.split('_')[2]
        if order_id in db.data['orders']:
            db.data['orders'][order_id]['status'] = 'confirmed'
            db.save_db()
            
            # ارسال پیام به کاربر
            order = db.data['orders'][order_id]
            user_id = order['user_id']
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ سفارش شما با شماره {order_id} تایید شد."
                )
            except Exception as e:
                logger.error(f"Error sending confirmation message to user {user_id}: {e}")
            
            await query.message.edit_text(
                f"✅ سفارش با موفقیت تایید شد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
            )
        else:
            await query.message.edit_text(
                "❌ سفارش مورد نظر یافت نشد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
            )
    except Exception as e:
        logger.error(f"Error in handle_confirm_order_action: {e}")
        await query.message.edit_text(
            "❌ خطا در تایید سفارش",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
        )

async def handle_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['orders']:
        await query.message.edit_text(
            "❌ هیچ سفارشی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
        )
        return

    keyboard = []
    for order_id, order in db.data['orders'].items():
        if order['status'] == 'pending':
            keyboard.append([InlineKeyboardButton(
                f"❌ سفارش {order_id}",
                callback_data=f'cancel_order_{order_id}'
            )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')])
    
    await query.message.edit_text(
        "❌ لغو سفارش\nلطفاً سفارش مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_cancel_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        order_id = query.data.split('_')[2]
        if order_id in db.data['orders']:
            db.data['orders'][order_id]['status'] = 'cancelled'
            db.save_db()
            
            # ارسال پیام به کاربر
            order = db.data['orders'][order_id]
            user_id = order['user_id']
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ سفارش شما با شماره {order_id} لغو شد."
                )
            except Exception as e:
                logger.error(f"Error sending cancellation message to user {user_id}: {e}")
            
            await query.message.edit_text(
                f"✅ سفارش با موفقیت لغو شد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
            )
        else:
            await query.message.edit_text(
                "❌ سفارش مورد نظر یافت نشد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
            )
    except Exception as e:
        logger.error(f"Error in handle_cancel_order_action: {e}")
        await query.message.edit_text(
            "❌ خطا در لغو سفارش",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_orders')]])
        )

async def handle_block_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        user_id = query.data.split('_')[2]
        
        # بارگذاری مجدد دیتابیس
        db.load_db()
        
        if user_id in db.data['users']:
            db.data['users'][user_id]['is_blocked'] = True
            db.save_db()
            
            # ارسال پیام به کاربر
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید."
                )
            except Exception as e:
                logger.error(f"Error sending block message to user {user_id}: {e}")
            
            await query.message.edit_text(
                f"✅ کاربر با موفقیت مسدود شد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
            )
        else:
            await query.message.edit_text(
                "❌ کاربر مورد نظر یافت نشد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
            )
    except Exception as e:
        logger.error(f"Error in handle_block_user_confirm: {e}")
        await query.message.edit_text(
            "❌ خطا در مسدود کردن کاربر",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
        )

async def handle_unblock_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin, logger
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        user_id = query.data.split('_')[2]
        
        # بارگذاری مجدد دیتابیس
        db.load_db()
        
        if user_id not in db.data['users']:
            await query.message.edit_text("کاربر مورد نظر یافت نشد.")
            return
        
        # آزاد کردن کاربر
        db.data['users'][user_id]['is_blocked'] = False
        db.save_db()
        
        # ارسال پیام به کاربر
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ حساب کاربری شما آزاد شد. اکنون می‌توانید از تمام امکانات ربات استفاده کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍 محصولات", callback_data='products')],
                    [InlineKeyboardButton("👤 پروفایل من", callback_data='profile')],
                    [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')],
                    [InlineKeyboardButton("❓ راهنما", callback_data='help')]
                ])
            )
        except Exception as e:
            logger.error(f"Error sending unblock message to user {user_id}: {e}")
        
        await query.message.edit_text(
            f"✅ کاربر {user_id} با موفقیت آزاد شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
        )
    except Exception as e:
        logger.error(f"Error in handle_unblock_user_confirm: {e}")
        await query.message.edit_text(
            "❌ خطا در آزاد کردن کاربر. لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_users')]])
        )

async def handle_quick_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['products']:
        await query.message.edit_text(
            "❌ هیچ محصولی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    keyboard = []
    for product_id, product in db.data['products'].items():
        keyboard.append([InlineKeyboardButton(
            f"💰 {product['name']} - {product['price']:,} تومان",
            callback_data=f'quick_price_{product_id}'
        )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')])
    
    await query.message.edit_text(
        "💰 ویرایش سریع قیمت\nلطفاً محصول مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_quick_price_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    product_id = query.data.split('_')[2]
    product = db.data['products'].get(product_id)
    
    if not product:
        await query.message.edit_text(
            "❌ محصول مورد نظر یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    context.user_data['editing_price_product_id'] = product_id
    await query.message.edit_text(
        f"💰 ویرایش قیمت محصول: {product['name']}\n"
        f"قیمت فعلی: {product['price']:,} تومان\n\n"
        "لطفاً قیمت جدید را وارد کنید:"
    )

async def handle_quick_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, logger
    if not context.user_data.get('editing_price_product_id'):
        return
    
    try:
        product_id = context.user_data['editing_price_product_id']
        price_str = update.message.text.strip().replace('تومان', '').replace(',', '').strip()
        price = int(price_str)
        
        if price <= 0:
            raise ValueError("قیمت باید بیشتر از صفر باشد.")
        
        db.data['products'][product_id]['price'] = price
        db.save_db()
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ قیمت محصول با موفقیت به‌روز شد\n"
            f"قیمت جدید: {price:,} تومان",
            reply_markup=reply_markup
        )
    except ValueError as e:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ خطا در ویرایش قیمت\n{str(e)}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_quick_price_input: {e}")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ خطا در ویرایش قیمت",
            reply_markup=reply_markup
        )
    
    context.user_data.pop('editing_price_product_id', None)

async def handle_toggle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['products']:
        await query.message.edit_text(
            "❌ هیچ محصولی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    keyboard = []
    for product_id, product in db.data['products'].items():
        status = "✅" if product.get('is_active', True) else "❌"
        keyboard.append([InlineKeyboardButton(
            f"{status} {product['name']}",
            callback_data=f'toggle_{product_id}'
        )])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')])
    
    await query.message.edit_text(
        "🔄 فعال/غیرفعال کردن محصول\nلطفاً محصول مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_toggle_product_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    try:
        product_id = query.data.split('_')[1]
        if product_id in db.data['products']:
            current_status = db.data['products'][product_id].get('is_active', True)
            db.data['products'][product_id]['is_active'] = not current_status
            db.save_db()
            
            status_text = "غیرفعال" if current_status else "فعال"
            await query.message.edit_text(
                f"✅ محصول با موفقیت {status_text} شد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
            )
        else:
            await query.message.edit_text(
                "❌ محصول مورد نظر یافت نشد",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
            )
    except Exception as e:
        logger.error(f"Error in handle_toggle_product_action: {e}")
        await query.message.edit_text(
            "❌ خطا در تغییر وضعیت محصول",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )

async def handle_product_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['products']:
        await query.message.edit_text(
            "❌ هیچ محصولی موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    # محاسبه آمار فروش
    stats_text = "📊 آمار فروش محصولات:\n\n"
    for product_id, product in db.data['products'].items():
        sales_count = sum(1 for order in db.data['orders'].values() if order['product_id'] == product_id)
        total_revenue = sum(order['total_price'] for order in db.data['orders'].values() if order['product_id'] == product_id)
        status = "✅" if product.get('is_active', True) else "❌"
        
        stats_text += f"{status} {product['name']}\n"
        stats_text += f"📦 تعداد فروش: {sales_count}\n"
        stats_text += f"💰 درآمد کل: {total_revenue:,} تومان\n"
        stats_text += f"💰 قیمت فعلی: {product['price']:,} تومان\n\n"

    keyboard = [
        [InlineKeyboardButton("🔼 مرتب‌سازی بر اساس قیمت", callback_data='sort_price')],
        [InlineKeyboardButton("📊 مرتب‌سازی بر اساس فروش", callback_data='sort_sales')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(stats_text, reply_markup=reply_markup)

async def handle_sort_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    sort_type = query.data.split('_')[1]
    products = db.data['products']
    
    if sort_type == 'price':
        sorted_products = sorted(products.items(), key=lambda x: x[1]['price'])
        sort_text = "قیمت"
    else:  # sort_sales
        product_sales = {pid: sum(1 for order in db.data['orders'].values() if order['product_id'] == pid) for pid in products}
        sorted_products = sorted(products.items(), key=lambda x: product_sales.get(x[0], 0), reverse=True)
        sort_type = "sales"
        sort_text = "تعداد فروش"

    stats_text = f"📊 آمار فروش محصولات (مرتب شده بر اساس {sort_text}):\n\n"
    for product_id, product in sorted_products:
        sales_count = sum(1 for order in db.data['orders'].values() if order['product_id'] == product_id)
        total_revenue = sum(order['total_price'] for order in db.data['orders'].values() if order['product_id'] == product_id)
        status = "✅" if product.get('is_active', True) else "❌"
        
        stats_text += f"{status} {product['name']}\n"
        stats_text += f"📦 تعداد فروش: {sales_count}\n"
        stats_text += f"💰 درآمد کل: {total_revenue:,} تومان\n"
        stats_text += f"💰 قیمت فعلی: {product['price']:,} تومان\n\n"

    keyboard = [
        [InlineKeyboardButton("🔼 مرتب‌سازی بر اساس قیمت", callback_data='sort_price')],
        [InlineKeyboardButton("📊 مرتب‌سازی بر اساس فروش", callback_data='sort_sales')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(stats_text, reply_markup=reply_markup)

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 آمار و گزارشات", callback_data='admin_stats')],
        [InlineKeyboardButton("📦 مدیریت محصولات", callback_data='admin_products')],
        [InlineKeyboardButton("🎟 مدیریت کد تخفیف", callback_data='admin_discounts')],
        [InlineKeyboardButton("📨 ارسال پیام همگانی", callback_data='admin_broadcast')],
        [InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data='admin_advanced')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "👨‍💼 پنل مدیریت\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def handle_bulk_add_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    await query.message.edit_text(
        "📦 افزودن چند محصول\n"
        "لطفاً اطلاعات محصولات را به این فرمت ارسال کنید:\n\n"
        "نام محصول 1|توضیحات 1|قیمت 1\n"
        "نام محصول 2|توضیحات 2|قیمت 2\n"
        "نام محصول 3|توضیحات 3|قیمت 3\n\n"
        "هر محصول در یک خط جدید\n"
        "حداکثر 10 محصول در یک بار"
    )
    context.user_data['waiting_for_bulk_products'] = True

async def handle_bulk_products_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, logger
    if not context.user_data.get('waiting_for_bulk_products'):
        return
    
    try:
        lines = update.message.text.strip().split('\n')
        if len(lines) > 10:
            raise ValueError("حداکثر 10 محصول در یک بار مجاز است")
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        for line in lines:
            try:
                parts = line.strip().split('|')
                if len(parts) < 3:
                    raise ValueError("اطلاعات ناقص است")
                
                name = parts[0].strip()
                description = parts[1].strip()
                price_str = parts[2].strip().replace('تومان', '').replace(',', '').strip()
                
                try:
                    price = int(price_str)
                except ValueError:
                    raise ValueError("قیمت باید به صورت عدد باشد")
                
                if not name or not description:
                    raise ValueError("نام و توضیحات محصول نمی‌تواند خالی باشد")
                
                if price <= 0:
                    raise ValueError("قیمت محصول باید بیشتر از صفر باشد")
                
                product_id = str(len(db.data['products']) + 1)
                db.data['products'][product_id] = {
                    'name': name,
                    'price': price,
                    'description': description,
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                }
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_messages.append(f"خطا در افزودن محصول {name if 'name' in locals() else 'نامشخص'}: {str(e)}")
        
        db.save_db()
        
        result_text = f"✅ عملیات افزودن محصولات با موفقیت انجام شد\n\n"
        result_text += f"✅ تعداد محصولات اضافه شده: {success_count}\n"
        if error_count > 0:
            result_text += f"❌ تعداد خطاها: {error_count}\n\n"
            result_text += "📝 جزئیات خطاها:\n"
            for msg in error_messages:
                result_text += f"- {msg}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(result_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_bulk_products_info: {e}")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ خطا در افزودن محصولات\n"
            "لطفاً اطلاعات را به درستی وارد کنید.",
            reply_markup=reply_markup
        )
    
    context.user_data.pop('waiting_for_bulk_products', None)

async def handle_export_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    if not db.data['products']:
        await query.message.edit_text(
            "❌ هیچ محصولی برای خروجی گرفتن موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]])
        )
        return

    try:
        # ایجاد فایل CSV
        export_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = f'products_export_{export_time}.csv'
        
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write("نام محصول,توضیحات,قیمت,وضعیت\n")
            for product in db.data['products'].values():
                status = "فعال" if product.get('is_active', True) else "غیرفعال"
                f.write(f"{product['name']},{product['description']},{product['price']},{status}\n")
        
        # ارسال فایل
        with open(export_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=export_file,
                caption="📦 خروجی محصولات با موفقیت ایجاد شد"
            )
        
        # حذف فایل موقت
        os.remove(export_file)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "✅ فایل خروجی با موفقیت ایجاد و ارسال شد",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_export_products: {e}")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "❌ خطا در ایجاد فایل خروجی",
            reply_markup=reply_markup
        )

async def handle_import_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("شما دسترسی به این بخش ندارید.")
        return

    await query.message.edit_text(
        "📦 وارد کردن محصولات\n"
        "لطفاً فایل CSV محصولات را ارسال کنید.\n\n"
        "فرمت فایل باید به این صورت باشد:\n"
        "نام محصول,توضیحات,قیمت,وضعیت\n"
        "محصول 1,توضیحات 1,100000,فعال\n"
        "محصول 2,توضیحات 2,200000,غیرفعال"
    )
    context.user_data['waiting_for_import_file'] = True

async def handle_import_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, logger
    if not context.user_data.get('waiting_for_import_file'):
        return
    
    try:
        # دریافت فایل
        file = await context.bot.get_file(update.message.document)
        file_path = f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        await file.download_to_drive(file_path)
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            # رد کردن خط هدر
            next(f)
            for line in f:
                try:
                    parts = line.strip().split(',')
                    if len(parts) < 4:
                        raise ValueError("اطلاعات ناقص است")
                    
                    name = parts[0].strip()
                    description = parts[1].strip()
                    price = int(parts[2].strip())
                    status = parts[3].strip() == "فعال"
                    
                    if not name or not description:
                        raise ValueError("نام و توضیحات محصول نمی‌تواند خالی باشد")
                    
                    if price <= 0:
                        raise ValueError("قیمت محصول باید بیشتر از صفر باشد")
                    
                    product_id = str(len(db.data['products']) + 1)
                    db.data['products'][product_id] = {
                        'name': name,
                        'price': price,
                        'description': description,
                        'created_at': datetime.now().isoformat(),
                        'is_active': status
                    }
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"خطا در وارد کردن محصول {name if 'name' in locals() else 'نامشخص'}: {str(e)}")
        
        db.save_db()
        
        # حذف فایل موقت
        os.remove(file_path)
        
        result_text = f"✅ عملیات وارد کردن محصولات با موفقیت انجام شد\n\n"
        result_text += f"✅ تعداد محصولات وارد شده: {success_count}\n"
        if error_count > 0:
            result_text += f"❌ تعداد خطاها: {error_count}\n\n"
            result_text += "📝 جزئیات خطاها:\n"
            for msg in error_messages:
                result_text += f"- {msg}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(result_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_import_file: {e}")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ خطا در وارد کردن محصولات\n"
            "لطفاً فایل را به درستی وارد کنید.",
            reply_markup=reply_markup
        )
    
    context.user_data.pop('waiting_for_import_file', None) 