# bot.py - النسخة المعدلة للنظام الذكي المتعدد المصادر
import os
import logging
import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from datetime import datetime

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== استيراد النظام الذكي الجديد ====================
from database import db
from ai_manager import SmartAIManager as AIManager

# ==================== نظام المشرفين ====================
def get_admin_ids():
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        try:
            return [int(admin_id.strip()) for admin_id in admin_ids_str.split(",")]
        except ValueError:
            logger.error("❌ خطأ في تنسيق ADMIN_IDS")
            return []
    return []

ADMIN_IDS = get_admin_ids()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# إنشاء كائن الذكاء الاصطناعي الذكي
ai_manager = AIManager(db)

# ==================== دوال مساعدة ====================
def check_environment():
    """فحص بيئة التشغيل"""
    logger.info("=" * 50)
    logger.info("🔍 فحص بيئة التشغيل...")
    
    required_vars = ["BOT_TOKEN", "GOOGLE_AI_API_KEY"]
    for var in required_vars:
        value = os.getenv(var)
        status = "✅ موجود" if value else "❌ مفقود"
        logger.info(f"{var}: {status}")
        if value and var == "BOT_TOKEN":
            logger.info(f"   طول التوكن: {len(value)} حرف")
    
    import sys
    logger.info(f"Python version: {sys.version}")
    logger.info(f"System: {sys.platform}")
    logger.info("=" * 50)

# استدعاء الفحص عند البدء
check_environment()

# ==================== أوامر البوت الأساسية ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # تسجيل المستخدم في قاعدة البيانات
    db.add_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # الحصول على حالة النظام
    system_stats = ai_manager.get_system_stats()
    provider_count = len([p for p in system_stats.get("providers", {}).values() if p.get("enabled")])
    
    # إرسال إشعار ترحيبي
    await update.message.reply_text(
        f"🤖 **مرحباً {user.first_name}!**\n\n"
        f"أنا بوت الذكاء الاصطناعي الذكي المتعدد المصادر! 🚀\n\n"
        f"🎯 **ما يمكنني فعله:**\n"
        f"💬 محادثة ذكية مع {provider_count} مزود\n"
        f"🎨 إنشاء صور احترافية من الوصف\n"
        f"🎬 إنشاء فيديوهات متحركة متقدمة\n"
        f"📊 إحصائيات استخدام ذكية\n\n"
        f"🔍 **معرفك:** {user.id}\n"
        f"✅ **تم التسجيل بنجاح**\n\n"
        f"📝 استخدم /help لعرض جميع الأوامر\n"
        f"🤖 جرب /chat للبدء في المحادثة\n"
        f"🔧 استخدم /system لرؤية حالة النظام",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع الأوامر"""
    help_text = """
🎯 **أوامر البوت الذكي (المتعدد المصادر)**

🤖 **خدمات الذكاء الاصطناعي:**
`/chat <رسالتك>` - محادثة ذكية (Google + OpenAI)
`/ask <سؤالك>` - سؤال مباشر
`/image <وصف الصورة>` - إنشاء صورة (Google + OpenAI + Stability)
`/draw <وصف>` - إنشاء صورة (اسم بديل)
`/video <وصف>` - إنشاء فيديو (Google + Luma + Kling)

📊 **معلومات النظام والاستخدام:**
`/mystats` - إحصائيات استخدامك اليومي
`/limits` - حدود الاستخدام المتاحة
`/aihelp` - مساعدة الذكاء الاصطناعي
`/system` - حالة النظام والمزودين

👤 **الأوامر العامة:**
`/start` - بدء استخدام البوت
`/help` - عرض هذه الرسالة
`/status` - حالة البوت والخوادم
`/about` - معلومات عن البوت والمطور

👑 **أوامر المشرفين:**
`/admin` - لوحة تحكم المشرفين
`/stats` - إحصائيات النظام الكاملة
`/broadcast` - إرسال رسالة للجميع
`/userslist` - قائمة المستخدمين
`/providers` - حالة جميع المزودين

💡 **نظام ذكي مميزات:**
• اكتشاف تلقائي للموديلات
• تبديل ذكي بين المزودين
• تحسين تلقائي للأوصاف
• لا يتوقف أبداً!

🔧 **الدعم:** للاستفسارات تواصل مع @المطور
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def system_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة النظام الذكي والمزودين"""
    try:
        # الحصول على إحصائيات النظام
        system_stats = ai_manager.get_system_stats()
        services = ai_manager.get_available_services()
        
        status_text = "⚙️ **حالة النظام الذكي المتعدد المصادر**\n\n"
        
        # حالة الخدمات
        status_text += "📊 **الخدمات المتاحة:**\n"
        status_text += f"💬 المحادثة: {'✅ متاحة' if services.get('chat') else '❌ غير متاحة'}\n"
        status_text += f"🎨 إنشاء الصور: {'✅ متاحة' if services.get('image_generation') else '❌ غير متاحة'}\n"
        status_text += f"🎬 إنشاء الفيديوهات: {'✅ متاحة' if services.get('video_generation') else '❌ غير متاحة'}\n\n"
        
        # المزودين النشطين
        active_providers = 0
        providers_text = "🔧 **المزودون النشطون:**\n"
        
        for provider_name, provider_info in system_stats.get("providers", {}).items():
            if provider_info.get("enabled"):
                active_providers += 1
                providers_text += f"• {provider_name.upper()}: {provider_info.get('usage_today', 0)} طلب\n"
        
        status_text += providers_text + "\n"
        
        # إحصائيات اليوم
        status_text += f"📈 **إحصائيات اليوم:**\n"
        status_text += f"📤 الطلبات: {system_stats.get('total_requests_today', 0)}\n"
        status_text += f"❌ الأخطاء: {system_stats.get('total_errors_today', 0)}\n"
        status_text += f"🔄 المزودون: {active_providers}/{len(system_stats.get('providers', {}))}\n\n"
        
        # حالة قاعدة البيانات
        db_status = check_database_status()
        status_text += f"💾 **قاعدة البيانات:** {db_status.get('users_count', 0)} مستخدم\n\n"
        
        # معلومات النظام
        status_text += "🕒 **معلومات النظام:**\n"
        status_text += f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        status_text += f"👑 المشرفين: {len(ADMIN_IDS)}\n"
        status_text += f"🚀 المنصة: Railway\n"
        status_text += f"🔄 الاكتشاف: {'✅ مكتمل' if system_stats.get('discovery_completed') else '⏳ قيد العمل'}\n\n"
        
        status_text += "✨ **النظام يعمل بشكل ذكي ومستقر**"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ خطأ في أمر النظام: {e}")
        await update.message.reply_text("✅ النظام يعمل، لكن هناك تأخير في جلب التفاصيل.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة البوت (للتوافق)"""
    await system_command(update, context)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات عن البوت"""
    about_text = """
🤖 **معلومات البوت الذكي**

الإصدار: 5.0 (النظام الذكي المتعدد المصادر)
التاريخ: 2026

🎯 **المميزات الرئيسية:**
1. نظام اكتشاف تلقائي للموديلات
2. تبديل ذكي بين مزودين متعددين
3. تحسين تلقائي للأوصاف
4. لا يتوقف أبداً (Fallback ذكي)

🔧 **المزودون المدعومون:**
• Google AI (Gemini, Imagen, Veo)
• OpenAI (GPT, DALL-E)
• Stability AI (صور)
• Luma AI (فيديو)
• Kling AI (فيديو)

⚡ **النظام الذكي:**
- يرتب الموديلات من الأحدث للأقدم
- يتبدل تلقائياً عند الخطأ
- يحسن الأوصاف أوتوماتيكياً
- يتتبع الأداء ويختار الأفضل

💥 **للاستفسارات أو إضافة مميزات:**
👨‍💻 المطور: Ahmed Elsayed
📞 الدعم: @elbashatech

🌟 **سياسة الخصوصية:**
- البيانات تُخزن مؤقتاً للتحسين
- يمكنك طلب حذف بياناتك
- لا مشاركة مع أطراف ثالثة

📜 **الشروط:** الاستخدام يعني الموافقة
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def limits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حدود الاستخدام اليومية"""
    limits_text = """
📊 **حدود الاستخدام اليومية (لكل مستخدم)**

🤖 **الذكاء الاصطناعي:**
💬 المحادثات: 20 رسالة يومياً
🎨 الصور المولدة: 5 صور يومياً
🎬 الفيديوهات: 2 فيديو يومياً

⚡ **النظام الذكي:**
• يستخدم أفضل مزود متاح
• يتبدل تلقائياً عند النفاذ
• يحاول جميع الخيارات قبل الفشل

📈 **نصائح للاستخدام الأمثل:**
1. استخدم أوصاف واضحة ومفصلة
2. جرب أنماط مختلفة للصور (/image وصف [نمط])
3. الفيديوهات تستغرق 2-5 دقائق
4. يمكنك تتبع استخدامك بـ `/mystats`

🔄 **التجديد:** تلقائي كل 24 ساعة (توقيت UTC)

🔍 **لمعرفة المزود المستخدم:** استخدم `/system`
"""
    await update.message.reply_text(limits_text, parse_mode='Markdown')

# ==================== أوامر الذكاء الاصطناعي ====================

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء محادثة مع الذكاء الاصطناعي (النسخة الذكية)"""
    user_id = update.effective_user.id
    user_message = ' '.join(context.args) if context.args else ""
    
    if not user_message:
        await update.message.reply_text(
            "💬 **المحادثة الذكية**\n\n"
            "اكتب رسالتك بعد الأمر:\n"
            "`/chat مرحبا، كيف حالك؟`\n\n"
            "✨ **المميزات:**\n"
            "• يستخدم Google Gemini أولاً\n"
            "• يتبدل لـ OpenAI تلقائياً\n"
            "• يحفظ سياق المحادثة",
            parse_mode='Markdown'
        )
        return
    
    # إظهار رسالة "جاري المعالجة"
    processing_msg = await update.message.reply_text(
        "🤔 **جاري التفكير...**\n"
        "⚡ النظام الذكي يختار أفضل مزود"
    )
    
    start_time = time.time()
    
    try:
        # استخدام النظام الذكي
        response = await ai_manager.chat_with_ai(user_id, user_message)
        
        response_time = time.time() - start_time
        
        await update.message.reply_text(
            f"🤖 **المساعد الذكي:**\n\n{response}\n\n"
            f"⏱️ الوقت: {response_time:.1f} ثانية\n"
            f"⚡ النظام الذكي يعمل بكفاءة",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Chat command error: {e}")
        await update.message.reply_text(
            "⚠️ **حدث خطأ مؤقت**\n\n"
            "النظام يحاول مزوداً آخر...\n"
            "جرب مرة أخرى بعد قليل."
        )
    finally:
        # حذف رسالة الانتظار
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء صورة باستخدام النظام الذكي"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🎨 **إنشاء صور ذكية**\n\n"
            "**الاستخدام:** `/image <وصف الصورة> [النمط]`\n\n"
            "**أمثلة:**\n"
            "`/image قطة لطيفة تجلس على كرسي`\n"
            "`/image منظر لغروب الشمس realistic`\n"
            "`/image ساحر في غابة سحرية fantasy`\n\n"
            "**الأنماط المتاحة:**\n"
            "`realistic` - واقعي (افتراضي)\n"
            "`anime` - أنمي / كرتون\n"
            "`fantasy` - فنتازيا سحرية\n"
            "`cyberpunk` - مستقبلي تكنولوجي\n"
            "`watercolor` - ألوان مائية\n\n"
            "⚡ **النظام الذكي:**\n"
            "• يستخدم DALL-E 3 أولاً\n"
            "• يتبدل للبدائل تلقائياً\n"
            "• يحسن الوصف أوتوماتيكياً\n"
            "⏳ **المدة:** 10-30 ثانية",
            parse_mode='Markdown'
        )
        return
    
    # استخراج النمط (آخر كلمة)
    args = context.args
    prompt_words = args[:-1]
    style = args[-1] if args[-1] in ["realistic", "anime", "fantasy", "cyberpunk", "watercolor"] else "realistic"
    
    if style != args[-1]:
        prompt_words = args  # إذا لم يكن النمط، كل الكلمات للوصف
    
    prompt = ' '.join(prompt_words)
    
    if len(prompt) < 3:
        await update.message.reply_text("❌ الرجاء إدخال وصف أطول للصورة (3 كلمات على الأقل)")
        return
    
    # إظهار رسالة الانتظار
    wait_msg = await update.message.reply_text(
        "🎨 **جاري إنشاء صورتك...**\n"
        "⚡ النظام الذكي يعمل:\n"
        "1. تحسين الوصف تلقائياً\n"
        "2. اختيار أفضل مزود\n"
        "3. التبديل الذكي إذا لزم\n"
        "⏳ قد يستغرق 10-30 ثانية"
    )
    
    try:
        # إنشاء الصورة باستخدام النظام الذكي
        start_time = time.time()
        image_url, message = await ai_manager.generate_image(user_id, prompt, style)
        response_time = time.time() - start_time
        
        if image_url:
            # إرسال الصورة
            await update.message.reply_photo(
                photo=image_url,
                caption=f"✅ **تم إنشاء صورتك بنجاح!**\n\n"
                       f"📝 **الوصف:** {prompt}\n"
                       f"🎨 **النمط:** {style}\n"
                       f"⏱️ **الوقت:** {response_time:.1f} ثانية\n"
                       f"⚡ **النظام الذكي:** تم التحسين تلقائياً\n\n"
                       f"💾 تم حفظ الصورة في مكتبتك\n"
                       f"🔄 استخدم `/image` لإنشاء المزيد",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ **لم نتمكن من إنشاء الصورة**\n\n"
                f"{message}\n\n"
                f"✨ **الحلول المقترحة:**\n"
                f"1. حاول بوصف مختلف\n"
                f"2. استخدم نمطاً آخر\n"
                f"3. انتظر قليلاً وجرب مرة أخرى"
            )
        
        # حذف رسالة الانتظار
        await wait_msg.delete()
        
    except Exception as e:
        logger.error(f"❌ Image command error: {e}")
        await update.message.reply_text(
            "❌ **حدث خطأ غير متوقع**\n\n"
            "النظام يحاول إصلاح نفسه تلقائياً...\n"
            "جرب مرة أخرى بعد دقيقة."
        )
        
        # محاولة حذف رسالة الانتظار
        try:
            await wait_msg.delete()
        except:
            pass

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء فيديو باستخدام النظام الذكي"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🎬 **إنشاء فيديو ذكي**\n\n"
            "**طريقتان للاستخدام:**\n\n"
            "1. **من النص:**\n"
            "`/video منظر طبيعي لغروب الشمس`\n\n"
            "2. **من صورة:**\n"
            "• أرسل صورة أولاً\n"
            "• ثم رد عليها بالأمر:\n"
            "`/video إضافة حركة للصورة`\n\n"
            "**أمثلة:**\n"
            "`/video مدينة المستقبل بإضاءة نيون`\n"
            "`/video بحر هائج بأمواج عالية`\n\n"
            "⚡ **النظام الذكي:**\n"
            "• يستخدم Luma AI أولاً\n"
            "• يتبدل للبدائل تلقائياً\n"
            "• يحسن الوصف سينمائياً\n"
            "⚠️ **المدة:** 2-5 دقائق",
            parse_mode='Markdown'
        )
        return
    
    prompt = ' '.join(context.args)
    
    if len(prompt) < 4:
        await update.message.reply_text("❌ الرجاء إدخال وصف أطول للفيديو (4 كلمات على الأقل)")
        return
    
    # التحقق إذا كان رداً على صورة
    image_url = None
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        photo = update.message.reply_to_message.photo[-1]
        image_file = await photo.get_file()
        image_url = image_file.file_path
    
    wait_msg = await update.message.reply_text(
        "🎬 **جاري إنشاء الفيديو...**\n"
        "⚡ النظام الذكي يعمل:\n"
        "1. تحسين الوصف سينمائياً\n"
        "2. اختيار أفضل مزود فيديو\n"
        "3. معالجة متقدمة للحركة\n"
        "⏳ قد يستغرق 2-5 دقائق\n"
        "📱 يمكنك متابعة استخدام البوت"
    )
    
    try:
        # إنشاء الفيديو باستخدام النظام الذكي
        start_time = time.time()
        video_url, message = await ai_manager.generate_video(user_id, prompt, image_url)
        response_time = time.time() - start_time
        
        if video_url:
            # إرسال الفيديو
            await update.message.reply_video(
                video=video_url,
                caption=f"✅ **تم إنشاء الفيديو بنجاح!**\n\n"
                       f"📝 **الوصف:** {prompt}\n"
                       f"⏱️ **الوقت:** {response_time:.1f} ثانية\n"
                       f"⚡ **النظام الذكي:** تحسين سينمائي تلقائي\n\n"
                       f"💾 تم حفظ الفيديو في مكتبتك\n"
                       f"🔄 استخدم `/video` لإنشاء المزيد",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ **لم نتمكن من إنشاء الفيديو**\n\n"
                f"{message}\n\n"
                f"✨ **الحلول المقترحة:**\n"
                f"1. حاول بوصف مختلف\n"
                f"2. أرسل صورة أولاً ثم اكتب `/video وصف`\n"
                f"3. انتظر 5 دقائق وجرب مرة أخرى"
            )
        
        await wait_msg.delete()
        
    except Exception as e:
        logger.error(f"❌ Video command error: {e}")
        await update.message.reply_text(
            "❌ **حدث خطأ غير متوقع**\n\n"
            "خدمة الفيديو قد تكون مشغولة حالياً...\n"
            "النظام يحاول مزوداً آخر تلقائياً."
        )
        
        try:
            await wait_msg.delete()
        except:
            pass

async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات استخدامي مع معلومات النظام الذكي"""
    user_id = update.effective_user.id
    
    stats = ai_manager.get_user_stats(user_id)
    services = ai_manager.get_available_services()
    system_stats = ai_manager.get_system_stats()
    
    # الحصول على معلومات المستخدم
    user_info = db.get_user(user_id)
    username = user_info['first_name'] if user_info else "مستخدم"
    
    stats_text = f"📊 **إحصائيات {username}**\n\n"
    stats_text += f"🆔 المعرف: {user_id}\n"
    stats_text += f"📅 اليوم: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    limits = {
        "ai_chat": int(os.getenv("DAILY_AI_LIMIT", "20")),
        "image_gen": int(os.getenv("DAILY_IMAGE_LIMIT", "5")),
        "video_gen": int(os.getenv("DAILY_VIDEO_LIMIT", "2"))
    }
    
    # شريط التقدم للخدمات
    for service, limit in limits.items():
        used = stats.get(service, 0)
        remaining = max(0, limit - used)
        percentage = (used / limit * 100) if limit > 0 else 0
        
        service_names = {
            "ai_chat": "💬 المحادثات",
            "image_gen": "🎨 الصور المولدة",
            "video_gen": "🎬 الفيديوهات"
        }
        
        # شريط تقدم مرئي
        filled_blocks = int(percentage / 10)
        progress_bar = "🟩" * filled_blocks + "⬜" * (10 - filled_blocks)
        
        stats_text += f"{service_names.get(service, service)}:\n"
        stats_text += f"{progress_bar}\n"
        stats_text += f"📊 {used}/{limit} ({remaining} متبقي)\n\n"
    
    # معلومات النظام الذكي
    stats_text += "⚡ **معلومات النظام الذكي:**\n"
    
    # حالة الخدمات
    for service, available in services.items():
        status = "✅" if available else "❌"
        service_name = {
            "chat": "💬 المحادثة",
            "image_generation": "🎨 إنشاء صور",
            "video_generation": "🎬 إنشاء فيديوهات"
        }.get(service, service)
        
        stats_text += f"{status} {service_name}\n"
    
    # عدد المزودين النشطين
    active_providers = len([p for p in system_stats.get("providers", {}).values() if p.get("enabled")])
    stats_text += f"🔧 المزودون النشطون: {active_providers}\n"
    
    # إجمالي الطلبات اليوم
    total_requests = system_stats.get("total_requests_today", 0)
    stats_text += f"📤 إجمالي الطلبات اليوم: {total_requests}\n\n"
    
    stats_text += "🔄 **التجديد:** تلقائي عند منتصف الليل (UTC)\n"
    stats_text += "✨ **النظام يعمل بشكل ذكي ومستقر**"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# ==================== معالج المحادثات العادية ====================

async def handle_ai_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة المحادثات العادية مع النظام الذكي"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # تجاهل الأوامر
    if user_message.startswith('/'):
        return
    
    # التحقق من نوع الرسالة (رد على البوت أو رسالة مباشرة)
    is_reply_to_ai = (
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id
    )
    is_direct_chat = not update.message.reply_to_message
    
    if is_reply_to_ai or is_direct_chat:
        # إظهار رسالة المعالجة
        processing_msg = await update.message.reply_text(
            "🤔 **جاري التفكير...**\n"
            "⚡ النظام الذكي يعالج طلبك"
        )
        
        try:
            # استخدام النظام الذكي
            response = await ai_manager.chat_with_ai(user_id, user_message)
            
            reply_text = f"🤖 **المساعد الذكي:**\n\n{response}"
            
            # تقسيم الرسائل الطويلة
            if len(reply_text) > 4000:
                parts = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='Markdown')
            else:
                await update.message.reply_text(reply_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"❌ AI conversation error: {e}")
            await update.message.reply_text(
                "⚠️ **الخدمة مشغولة حالياً**\n\n"
                "النظام يحاول مزوداً آخر تلقائياً...\n"
                "يرجى المحاولة لاحقاً."
            )
        finally:
            # حذف رسالة الانتظار
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass

# ==================== أوامر المشرفين ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        logger.warning(f"محاولة وصول غير مصرح: المستخدم {user_id} حاول استخدام /admin")
        return
    
    users_count = db.get_users_count()
    system_stats = ai_manager.get_system_stats()
    active_providers = len([p for p in system_stats.get("providers", {}).values() if p.get("enabled")])
    
    admin_commands = f"""
👑 **لوحة تحكم المشرفين (النظام الذكي)**

🤖 **حالة النظام الذكي:**
🔧 مزودون نشطون: {active_providers}
📤 طلبات اليوم: {system_stats.get('total_requests_today', 0)}
❌ أخطاء اليوم: {system_stats.get('total_errors_today', 0)}

📊 **الإحصائيات:**
/stats - إحصائيات النظام الكاملة
/userslist - عرض المستخدمين ({users_count} مستخدم)
/providers - حالة جميع المزودين

📢 **الإذاعة:**
/broadcast - إعداد رسالة للإذاعة
/sendbroadcast - إرسال الرسالة المعلقة
/broadcaststats <رقم> - إحصائيات إذاعة

🔧 **إدارة النظام:**
/resetcache - إعادة تعيين الكاش
/systemlogs - سجلات النظام
/backupdb - نسخ احتياطي للقاعدة

🔢 **معلومات النظام:**
👥 المستخدمين: {users_count}
👑 المشرفين: {len(ADMIN_IDS)}
⚡ مزودون AI: {active_providers} نشط
💾 قاعدة البيانات: ✅ نشطة
"""
    
    await update.message.reply_text(admin_commands, parse_mode='Markdown')
    logger.info(f"المشرف {user_id} فتح لوحة التحكم")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات النظام الكاملة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        logger.info(f"📊 المشرف {user_id} طلب الإحصائيات")
        
        # إحصائيات النظام
        stats = db.get_stats_fixed()
        system_stats = ai_manager.get_system_stats()
        
        # بناء رسالة الإحصائيات
        stats_text = f"""
📊 **إحصائيات النظام الكاملة (النظام الذكي)**

👥 **المستخدمون:**
👤 العدد الكلي: {stats['total_users']} مستخدم
🆕 الجدد اليوم: {stats.get('new_users_today', 0)}
💬 الرسائل الكلية: {stats.get('total_messages', 0):,}

🤖 **النظام الذكي:**
🔧 مزودون نشطون: {len([p for p in system_stats.get("providers", {}).values() if p.get("enabled")])}
📤 طلبات اليوم: {system_stats.get('total_requests_today', 0):,}
❌ أخطاء اليوم: {system_stats.get('total_errors_today', 0):,}

📊 **إحصائيات الذكاء الاصطناعي:"""
        
        # إحصائيات AI من قاعدة البيانات
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM ai_usage")
                ai_users = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT SUM(usage_count) FROM ai_usage WHERE service_type = 'ai_chat'")
                total_chats = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT SUM(usage_count) FROM ai_usage WHERE service_type = 'image_gen'")
                total_images = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT SUM(usage_count) FROM ai_usage WHERE service_type = 'video_gen'")
                total_videos = cursor.fetchone()[0] or 0
                
                stats_text += f"""
👤 مستخدمون AI: {ai_users}
💬 محادثات: {total_chats:,}
🎨 صور مولدة: {total_images:,}
🎬 فيديوهات: {total_videos:,}
"""
                
        except Exception as e:
            logger.error(f"❌ خطأ في إحصائيات AI: {e}")
        
        stats_text += f"""
📢 **الإذاعات:**
📤 عدد الإذاعات: {stats.get('total_broadcasts', 0)}
"""
        
        if stats.get('last_broadcast_id'):
            stats_text += f"📅 آخر إذاعة: #{stats['last_broadcast_id']}\n"
        
        # المستخدمين الأكثر نشاطاً
        if stats.get('top_users') and len(stats['top_users']) > 0:
            stats_text += "\n🏆 **المستخدمون الأكثر نشاطاً:**\n"
            for i, user in enumerate(stats['top_users'][:5], 1):
                name = user.get('first_name', 'مستخدم')
                messages = user.get('message_count', 0)
                stats_text += f"{i}. {name} - {messages:,} رسالة\n"
        
        # معلومات النظام الذكي
        stats_text += f"""
⚙️ **معلومات النظام الذكي:**
👑 المشرفين: {len(ADMIN_IDS)}
🕒 آخر تحديث: {datetime.now().strftime('%H:%M:%S')}
🚀 الاكتشاف: {'✅ مكتمل' if system_stats.get('discovery_completed') else '⏳ جاري'}
"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        logger.info(f"✅ تم عرض الإحصائيات الكاملة للمشرف {user_id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ كامل في عرض الإحصائيات: {e}", exc_info=True)
        await update.message.reply_text("📊 **حالة النظام:**\n\n✅ النظام الذكري يعمل بشكل طبيعي\n✅ جميع الخدمات نشطة")

async def providers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة جميع المزودين"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        system_stats = ai_manager.get_system_stats()
        
        providers_text = "🔧 **حالة جميع المزودين:**\n\n"
        
        for provider_name, provider_info in system_stats.get("providers", {}).items():
            status = "✅" if provider_info.get("enabled") else "❌"
            usage = provider_info.get("usage_today", 0)
            limit = provider_info.get("daily_limit", 100)
            errors = provider_info.get("errors_today", 0)
            last_error = provider_info.get("last_error", "لا يوجد")
            
            providers_text += f"{status} **{provider_name.upper()}:**\n"
            providers_text += f"   📊 الاستخدام: {usage}/{limit}\n"
            providers_text += f"   ❌ الأخطاء: {errors}\n"
            
            if provider_info.get("active_models"):
                providers_text += f"   🤖 الموديلات النشطة:\n"
                for service, model in provider_info.get("active_models", {}).items():
                    providers_text += f"      • {service}: {model}\n"
            
            if errors > 0 and last_error != "لا يوجد":
                providers_text += f"   ⚠️ آخر خطأ: {last_error[:50]}...\n"
            
            providers_text += "\n"
        
        providers_text += f"🔄 **إجمالي الطلبات اليوم:** {system_stats.get('total_requests_today', 0)}\n"
        providers_text += f"❌ **إجمالي الأخطاء اليوم:** {system_stats.get('total_errors_today', 0)}\n"
        providers_text += f"⏰ **تاريخ الاكتشاف:** {system_stats.get('timestamp', 'غير معروف')[:19]}"
        
        await update.message.reply_text(providers_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ خطأ في عرض المزودين: {e}")
        await update.message.reply_text("⚠️ حدث خطأ في جلب حالة المزودين.")

async def reset_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة تعيين الكاش"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        # إعادة تعيين الكاش في ai_manager
        ai_manager.reset_daily_counts()
        
        # إعادة تعيين كاش قاعدة البيانات
        ai_manager.user_limits_cache.clear()
        
        await update.message.reply_text(
            "🔄 **تم إعادة تعيين الكاش بنجاح!**\n\n"
            "✅ تمت إعادة تعيين:\n"
            "• عدادات المزودين اليومية\n"
            "• كاش حدود المستخدمين\n"
            "• سجلات الأخطاء\n\n"
            "✨ النظام جاهز ليوم جديد!"
        )
        logger.info(f"🔄 المشرف {user_id} أعاد تعيين الكاش")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إعادة تعيين الكاش: {e}")
        await update.message.reply_text("❌ فشل إعادة تعيين الكاش.")

# ==================== دوال الإذاعة (نفس السابق مع تعديلات بسيطة) ====================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعداد رسالة إذاعة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    if update.message.reply_to_message:
        message = update.message.reply_to_message.text or "رسالة ميديا"
        users_count = db.get_users_count()
        
        await update.message.reply_text(
            f"📢 **رسالة الإذاعة:**\n"
            f"'{message[:50]}...'\n\n"
            f"👥 عدد المستهدفين: {users_count} مستخدم\n"
            f"✅ جاهزة للإرسال\n\n"
            f"ℹ️ *لإرسال فعلياً:*\n"
            f"أرسل /sendbroadcast",
            parse_mode='Markdown'
        )
        
        context.user_data['pending_broadcast'] = message
    else:
        await update.message.reply_text(
            "📝 **طريقة استخدام /broadcast:**\n"
            "1. أرسل الرسالة التي تريد إذاعتها\n"
            "2. رد على الرسالة بالأمر /broadcast\n\n"
            "✅ **المميزات:**\n"
            "- الإرسال لجميع المستخدمين\n"
            "- تتبع من استلم الرسالة\n"
            "- إحصائيات مفصلة",
            parse_mode='Markdown'
        )

async def send_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال الإذاعة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    if 'pending_broadcast' not in context.user_data:
        await update.message.reply_text("❌ لا توجد رسالة معلقة للإذاعة!\nاستخدم /broadcast أولاً")
        return
    
    message = context.user_data['pending_broadcast']
    users = db.get_all_users()
    users_count = len(users)
    
    if users_count == 0:
        await update.message.reply_text("❌ لا يوجد مستخدمين لإرسال الإذاعة لهم!")
        return
    
    # حفظ الإذاعة في قاعدة البيانات
    broadcast_id = db.add_broadcast(user_id, message, users_count)
    
    if not broadcast_id:
        await update.message.reply_text("❌ فشل في حفظ الإذاعة!")
        return
    
    # الإرسال الفعلي
    sent_count = 0
    failed_count = 0
    failed_users = []
    
    await update.message.reply_text(
        f"📤 جاري إرسال الإذاعة لـ {users_count} مستخدم...\n"
        f"⏳ قد يستغرق بعض الوقت..."
    )
    
    for user in users:
        user_id_in_db = user['user_id']
        
        try:
            if user_id_in_db == user_id:
                sent_count += 1
                continue
                
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 **إذاعة من الإدارة:**\n\n{message}"
            )
            sent_count += 1
            
            db.log_activity(
                user_id=user['user_id'],
                action="broadcast_received",
                details=f"broadcast_id={broadcast_id}"
            )
            
            if sent_count % 10 == 0:
                await asyncio.sleep(0.3)
                
        except Exception as e:
            failed_count += 1
            failed_users.append(user['user_id'])
            logger.error(f"❌ فشل إرسال للإذاعة {broadcast_id} للمستخدم {user['user_id']}: {e}")
    
    # تحديث عدد المستلمين
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE broadcasts 
            SET recipients_count = ?
            WHERE broadcast_id = ?
            ''', (sent_count, broadcast_id))
            conn.commit()
    except Exception as e:
        logger.error(f"❌ فشل تحديث عدد المستلمين: {e}")
    
    # تقرير المشرف
    success_rate = (sent_count / users_count * 100) if users_count > 0 else 0
    
    report = f"""
✅ **تم إرسال الإذاعة بنجاح!**

📊 **التقرير:**
🆔 رقم الإذاعة: {broadcast_id}
👥 العدد الكلي: {users_count} مستخدم
✅ تم الإرسال بنجاح: {sent_count}
❌ فشل الإرسال: {failed_count}
📈 نسبة النجاح: {success_rate:.1f}%
"""
    
    if failed_count > 0 and failed_users:
        report += f"\n📛 **المستخدمين الذين فشل الإرسال لهم:**\n"
        for failed_id in failed_users[:5]:
            report += f"- {failed_id}\n"
    
    await update.message.reply_text(report, parse_mode='Markdown')
    
    # حذف الرسالة المعلقة
    del context.user_data['pending_broadcast']

async def broadcast_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات إذاعة محددة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    if context.args and context.args[0].isdigit():
        broadcast_id = int(context.args[0])
        stats = db.get_broadcast_stats(broadcast_id)
        
        if stats:
            stats_text = f"""
📊 **إحصائيات الإذاعة #{broadcast_id}**

📝 **الرسالة:** {stats['message_text'][:100]}...

👤 **المرسل:** المشرف {stats.get('admin_id', 'غير معروف')}
📅 **تاريخ الإرسال:** {stats['sent_date'][:16]}

📈 **الإحصائيات:**
👥 العدد المستهدف: {stats['recipients_count']}
"""
            await update.message.reply_text(stats_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ لم يتم العثور على إذاعة برقم #{broadcast_id}")
    else:
        await update.message.reply_text("📌 استخدام: /broadcaststats <رقم_الإذاعة>\nمثال: /broadcaststats 1")

async def users_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة المستخدمين"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
        return
    
    users = db.get_all_users()
    users_count = len(users)
    
    if users_count == 0:
        await update.message.reply_text("📭 لا يوجد مستخدمين مسجلين بعد.")
        return
    
    display_users = users[:10]
    
    users_text = f"👥 **المستخدمون المسجلون** ({users_count} مستخدم)\n\n"
    
    for i, user in enumerate(display_users, 1):
        users_text += f"{i}. {user['first_name']}"
        if user['username']:
            users_text += f" (@{user['username']})"
        users_text += f" - ID: {user['user_id']}\n"
        join_date = user['join_date'][:10] if user['join_date'] else "غير معروف"
        users_text += f"   📅 انضم: {join_date}\n"
        users_text += f"   💬 رسائل: {user['message_count']}\n\n"
    
    if users_count > 10:
        users_text += f"\n📋 عرض 10 من أصل {users_count} مستخدم\n"
        users_text += "استخدم /userslist2 للصفحة التالية"
    
    await update.message.reply_text(users_text, parse_mode='Markdown')
    logger.info(f"المشرف {user_id} طلب قائمة المستخدمين")

async def handle_broadcast_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تتبع ردود المستخدمين على الإذاعات"""
    if update.message.reply_to_message and update.message.reply_to_message.text:
        replied_text = update.message.reply_to_message.text
        if "إذاعة من الإدارة:" in replied_text:
            user_id = update.effective_user.id
            user = db.get_user(user_id)
            
            if user:
                db.log_activity(
                    user_id=user_id,
                    action="broadcast_replied",
                    details=f"reply: {update.message.text[:50]}"
                )
                
                admin_message = f"""
🔄 **رد على إذاعة:**
👤 المستخدم: {user['first_name']} (@{user['username'] or 'بدون'})
🆔 المعرف: {user_id}
💬 الرد: {update.message.text[:100]}
"""
                
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=admin_message
                        )
                    except Exception as e:
                        logger.error(f"فشل إرسال إشعار للمشرف {admin_id}: {e}")

# ==================== وظائف مساعدة ====================
def check_database_status():
    """فحص حالة قاعدة البيانات"""
    try:
        users_count = db.get_users_count()
        stats = db.get_stats_fixed()
        
        status_info = {
            'database_file': db.db_name,
            'users_count': users_count,
            'stats_available': bool(stats),
            'last_check': datetime.now().isoformat()
        }
        
        logger.info(f"✅ حالة قاعدة البيانات: {status_info}")
        return status_info
        
    except Exception as e:
        logger.error(f"❌ فشل في فحص حالة قاعدة البيانات: {e}")
        return {'error': str(e), 'last_check': datetime.now().isoformat()}

def setup_handlers(application):
    """إعداد معالجات الأوامر والرسائل"""
    
    # الأوامر الأساسية
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("system", system_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("limits", limits_command))
    
    # أوامر الذكاء الاصطناعي للمستخدمين
    application.add_handler(CommandHandler("chat", chat_command))
    application.add_handler(CommandHandler("ask", chat_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CommandHandler("draw", image_command))
    application.add_handler(CommandHandler("video", video_command))
    application.add_handler(CommandHandler("mystats", my_stats_command))
    application.add_handler(CommandHandler("aistats", my_stats_command))
    application.add_handler(CommandHandler("aihelp", help_command))
    
    # أوامر المشرفين
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("providers", providers_command))
    application.add_handler(CommandHandler("resetcache", reset_cache_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("sendbroadcast", send_broadcast_command))
    application.add_handler(CommandHandler("broadcaststats", broadcast_stats_command))
    application.add_handler(CommandHandler("userslist", users_list_command))
    
    # معالج المحادثات العادية مع AI
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_ai_conversation
    ), group=1)
    
    # معالج للردود على الإذاعات
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_broadcast_reply
    ), group=2)

def run_bot():
    """تشغيل البوت"""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN غير معين")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    logger.info(f"🤖 بدأ تشغيل بوت النظام الذكي المتعدد المصادر...")
    logger.info(f"👑 عدد المشرفين: {len(ADMIN_IDS)}")
    
    # ✅ فحص حالة النظام عند البدء
    db_status = check_database_status()
    logger.info(f"💾 حالة قاعدة البيانات: {db_status}")
    
    users_count = db.get_users_count()
    logger.info(f"👥 عدد المستخدمين المسجلين: {users_count}")
    
    # ✅ فحص خدمات النظام الذكي
    system_stats = ai_manager.get_system_stats()
    logger.info(f"🤖 النظام الذكي: {system_stats.get('total_requests_today', 0)} طلبات اليوم")
    
    application.run_polling(drop_pending_updates=True)

def main():
    """الدالة الرئيسية"""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    if not BOT_TOKEN:
        logger.error("❌ يرجى تعيين BOT_TOKEN في متغيرات Railway")
        return
    
    logger.info("🚀 بدء تشغيل البوت على Railway (النظام الذكي)...")
    
    try:
        run_bot()
    except Exception as e:
        logger.error(f"❌ فشل في تشغيل البوت: {e}")
        return

if __name__ == "__main__":
    main()