from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

async def handle_product_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    query = update.callback_query
    product_id = query.data.split('_')[1]
    product = db.data['products'].get(product_id)
    
    if not product:
        await query.message.reply_text("محصول مورد نظر یافت نشد.")
        return
    
    product_text = f"""
📦 {product['name']}

💰 قیمت: {product['price']} تومان

📝 توضیحات:
{product['description']}
    """
    
    keyboard = [
        [InlineKeyboardButton("💳 خرید", callback_data=f'buy_{product_id}')],
        [InlineKeyboardButton("🎟 وارد کردن کد تخفیف", callback_data=f'discount_{product_id}')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(product_text, reply_markup=reply_markup)

async def handle_discount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    query = update.callback_query
    product_id = query.data.split('_')[1]
    product = db.data['products'].get(product_id)
    
    if not product:
        await query.message.reply_text("محصول مورد نظر یافت نشد.")
        return
    
    await query.message.edit_text(
        "🎟 لطفاً کد تخفیف خود را وارد کنید:"
    )
    context.user_data['waiting_for_discount'] = True
    context.user_data['discount_product_id'] = product_id

async def handle_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, logger
    if not context.user_data.get('waiting_for_discount'):
        return
    
    try:
        discount_code = update.message.text.strip().upper()
        
        # بارگذاری مجدد دیتابیس
        db.load_db()
        
        discount = db.data['discount_codes'].get(discount_code)
        product_id = context.user_data['discount_product_id']
        product = db.data['products'].get(product_id)
        
        if not product:
            await update.message.reply_text("محصول مورد نظر یافت نشد.")
            return
        
        if not discount:
            await update.message.reply_text(
                "❌ کد تخفیف نامعتبر است.\n"
                "آیا می‌خواهید دوباره تلاش کنید؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ بله", callback_data=f'discount_{product_id}')],
                    [InlineKeyboardButton("❌ خیر", callback_data=f'product_{product_id}')]
                ])
            )
            context.user_data['waiting_for_discount'] = False
            return
        
        # بررسی تاریخ انقضا
        if datetime.fromisoformat(discount['expiry_date']) < datetime.now():
            await update.message.reply_text(
                "❌ این کد تخفیف منقضی شده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f'product_{product_id}')]])
            )
            context.user_data['waiting_for_discount'] = False
            return
        
        # بررسی محدودیت استفاده
        if discount['usage_count'] >= discount['usage_limit']:
            await update.message.reply_text(
                "❌ این کد تخفیف به حداکثر تعداد مجاز استفاده رسیده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f'product_{product_id}')]])
            )
            context.user_data['waiting_for_discount'] = False
            return
        
        # اعمال تخفیف
        discount_amount = int(product['price'] * discount['percentage'] / 100)
        final_price = product['price'] - discount_amount
        
        context.user_data['discount_code'] = discount_code
        context.user_data['final_price'] = final_price
        
        await update.message.reply_text(
            f"✅ کد تخفیف با موفقیت اعمال شد\n\n"
            f"💰 قیمت اصلی: {product['price']} تومان\n"
            f"🎟 درصد تخفیف: {discount['percentage']}%\n"
            f"💰 مبلغ تخفیف: {discount_amount} تومان\n"
            f"💰 قیمت نهایی: {final_price} تومان\n\n"
            f"آیا می‌خواهید خرید را ادامه دهید؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بله", callback_data=f'buy_{product_id}')],
                [InlineKeyboardButton("❌ خیر", callback_data=f'product_{product_id}')]
            ])
        )
    except Exception as e:
        logger.error(f"Error in handle_discount_code: {e}")
        await update.message.reply_text(
            "❌ خطا در اعمال کد تخفیف. لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f'product_{product_id}')]])
        )
    
    context.user_data['waiting_for_discount'] = False

async def handle_buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, is_admin
    query = update.callback_query
    user_id = str(update.effective_user.id)
    
    # بررسی وضعیت مسدودیت کاربر
    if db.data['users'][user_id].get('is_blocked', False):
        await query.message.edit_text(
            "❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]])
        )
        return
    
    product_id = query.data.split('_')[1]
    product = db.data['products'].get(product_id)
    
    if not product:
        await query.message.edit_text(
            "❌ محصول مورد نظر یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='products')]])
        )
        return
    
    price = context.user_data.get('final_price', product['price'])
    discount_code = context.user_data.get('discount_code')
    
    payment_info = f"""
💳 اطلاعات پرداخت:

🏦 بانک: ملت
💳 شماره کارت: `6104338644476687`
👤 به نام: سبحان پرهیزکار

📦 محصول: {product['name']}
💰 مبلغ: {price} تومان
{f"🎟 کد تخفیف: {discount_code}" if discount_code else ""}

⚠️ لطفاً پس از پرداخت، تصویر رسید پرداخت را ارسال کنید.
    """
    
    context.user_data['waiting_for_receipt'] = True
    context.user_data['current_product'] = product_id
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f'product_{product_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(payment_info, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db, ADMIN_IDS, logger
    if not context.user_data.get('waiting_for_receipt'):
        return
    
    if not update.message.photo:
        await update.message.reply_text(
            "لطفاً تصویر رسید پرداخت را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]])
        )
        return
    
    try:
        # بارگذاری مجدد دیتابیس برای اطمینان از داشتن آخرین تغییرات
        db.load_db()
        
        product_id = context.user_data['current_product']
        product = db.data['products'].get(product_id)
        if not product:
            await update.message.reply_text(
                "❌ خطا: محصول مورد نظر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]])
            )
            return

        user_id = str(update.effective_user.id)
        price = context.user_data.get('final_price', product['price'])
        discount_code = context.user_data.get('discount_code')
        
        # ارسال پیام به ادمین‌ها
        admin_message = f"""
📨 سفارش جدید:

👤 کاربر: {update.effective_user.first_name} (@{update.effective_user.username})
🆔 شناسه کاربر: {user_id}
📦 محصول: {product['name']}
💰 مبلغ: {price} تومان
{f"🎟 کد تخفیف: {discount_code}" if discount_code else ""}
        """
        
        receipt_sent = False
        for admin_id in ADMIN_IDS:
            try:
                # ارسال عکس رسید به ادمین
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=update.message.photo[-1].file_id,
                    caption=admin_message
                )
                receipt_sent = True
            except Exception as e:
                logger.error(f"Error sending receipt to admin {admin_id}: {e}")
        
        if not receipt_sent:
            await update.message.reply_text(
                "❌ خطا در ارسال رسید به ادمین. لطفاً دوباره تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]])
            )
            return
        
        # افزایش تعداد استفاده از کد تخفیف
        if discount_code and discount_code in db.data['discount_codes']:
            db.data['discount_codes'][discount_code]['usage_count'] += 1
            logger.info(f"Discount code {discount_code} usage count increased to {db.data['discount_codes'][discount_code]['usage_count']}")
            db.save_db()
        
        # ایجاد سفارش
        order_id = str(len(db.data['orders']) + 1)
        order = {
            'user_id': user_id,
            'product_id': product_id,
            'total_price': price,
            'discount_code': discount_code,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'receipt_photo_id': update.message.photo[-1].file_id
        }
        
        db.data['orders'][order_id] = order
        if user_id not in db.data['users']:
            db.data['users'][user_id] = {
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'join_date': datetime.now().isoformat(),
                'orders': [],
                'support_messages': []
            }
        db.data['users'][user_id]['orders'].append(order_id)
        db.save_db()
        
        # پاک کردن وضعیت
        context.user_data.pop('waiting_for_receipt', None)
        context.user_data.pop('current_product', None)
        context.user_data.pop('discount_code', None)
        context.user_data.pop('final_price', None)
        
        await update.message.reply_text(
            "✅ سفارش شما با موفقیت ثبت شد\n"
            "ممنون از اینکه مارو انتخاب کردی",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]])
        )
    except Exception as e:
        logger.error(f"Error in handle_receipt: {e}")
        await update.message.reply_text(
            "❌ خطا در ثبت سفارش. لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]])
        )

async def handle_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    query = update.callback_query
    product_id = query.data.split('_')[3]
    user_id = str(update.effective_user.id)
    
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []
    
    context.user_data['cart'].append(product_id)
    
    keyboard = [
        [InlineKeyboardButton("🛒 مشاهده سبد خرید", callback_data='view_cart')],
        [InlineKeyboardButton("🔙 بازگشت به محصولات", callback_data='products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "✅ محصول به سبد خرید اضافه شد",
        reply_markup=reply_markup
    )

async def handle_view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    query = update.callback_query
    cart = context.user_data.get('cart', [])
    
    if not cart:
        await query.message.edit_text(
            "🛒 سبد خرید شما خالی است",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='products')]])
        )
        return
    
    total_price = 0
    cart_text = "🛒 سبد خرید شما:\n\n"
    
    for product_id in cart:
        product = db.data['products'][product_id]
        cart_text += f"📦 {product['name']}\n💰 {product['price']} تومان\n\n"
        total_price += product['price']
    
    cart_text += f"\n💰 مجموع: {total_price} تومان"
    
    keyboard = [
        [InlineKeyboardButton("💳 ثبت سفارش", callback_data='checkout')],
        [InlineKeyboardButton("🗑 خالی کردن سبد", callback_data='clear_cart')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(cart_text, reply_markup=reply_markup)

async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    query = update.callback_query
    cart = context.user_data.get('cart', [])
    
    if not cart:
        await query.message.edit_text("سبد خرید شما خالی است.")
        return
    
    await query.message.edit_text(
        "💳 ثبت سفارش\n\n"
        "آیا می‌خواهید کد تخفیف وارد کنید؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data='enter_discount')],
            [InlineKeyboardButton("❌ خیر", callback_data='confirm_order')]
        ])
    )

async def handle_enter_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        "🎟 لطفاً کد تخفیف خود را وارد کنید:"
    )
    context.user_data['waiting_for_discount'] = True

async def handle_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    query = update.callback_query
    user_id = str(update.effective_user.id)
    cart = context.user_data.get('cart', [])
    
    if not cart:
        await query.message.edit_text("سبد خرید شما خالی است.")
        return
    
    # ایجاد سفارش
    order_id = str(len(db.data['orders']) + 1)
    order = {
        'user_id': user_id,
        'products': cart,
        'total_price': context.user_data.get('final_price', sum(db.data['products'][pid]['price'] for pid in cart)),
        'discount_code': context.user_data.get('discount_code'),
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    
    db.data['orders'][order_id] = order
    db.data['users'][user_id]['orders'].append(order_id)
    db.save_db()
    
    # پاک کردن سبد خرید
    context.user_data['cart'] = []
    context.user_data.pop('discount_code', None)
    context.user_data.pop('final_price', None)
    
    await query.message.edit_text(
        f"✅ سفارش شما با موفقیت ثبت شد\n\n"
        f"🆔 شماره سفارش: {order_id}\n"
        f"💰 مبلغ کل: {order['total_price']} تومان\n"
        f"📅 تاریخ: {order['created_at']}\n\n"
        f"به زودی با شما تماس خواهیم گرفت.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]])
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import db
    user_id = str(update.effective_user.id)
    
    # بارگذاری مجدد دیتابیس
    db.load_db()
    
    # بررسی وضعیت مسدودیت کاربر
    if db.data['users'][user_id].get('is_blocked', False):
        await update.message.reply_text(
            "❌ شما از استفاده از ربات مسدود شده‌اید. لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]])
        )
        return
    
    if context.user_data.get('waiting_for_support_message'):
        await handle_support_message(update, context)
    elif context.user_data.get('waiting_for_receipt'):
        await handle_receipt(update, context)
    elif context.user_data.get('waiting_for_broadcast_message'):
        await handle_broadcast_message(update, context)
    elif context.user_data.get('waiting_for_product_info'):
        await handle_product_info(update, context)
    elif context.user_data.get('waiting_for_edit_product'):
        await handle_edit_product_info(update, context)
    elif context.user_data.get('waiting_for_discount_info'):
        await handle_discount_info(update, context)
    elif context.user_data.get('waiting_for_discount'):
        await handle_discount_code(update, context) 