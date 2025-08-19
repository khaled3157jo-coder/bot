import os
import logging
import re
import traceback
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv
import yt_dlp

# تهيئة التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تحميل المتغيرات البيئية
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# إنشاء مجلد التحميلات
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def check_cookies():
    """التحقق من صحة ملف cookies"""
    try:
        if not os.path.exists('cookies.txt'):
            return "❌ ملف cookies.txt غير موجود"
        
        with open('cookies.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'youtube.com' not in content:
                return "❌ ملف cookies لا يحتوي على بيانات YouTube"
            if len(content.strip()) < 100:
                return "❌ ملف cookies فارغ أو صغير جداً"
            
        return "✅ ملف cookies يبدو صالحاً"
    except Exception as e:
        return f"❌ خطأ في قراءة ملف cookies: {str(e)}"

def start(update: Update, context: CallbackContext) -> None:
    """رسالة ترحيبية مع التحقق من النظام"""
    try:
        cookies_status = check_cookies()
        
        welcome_msg = f"""
🎥 *مرحباً في بوت التحميل* 🎥

{cookies_status}

✨ *المميزات:*
- تحميل من YouTube بصلاحيات كاملة
- دعم TikTok و Twitter
- يعمل 24/7 على السحابة

⚡ *طريقة الاستخدام:*
1. أرسل رابط الفيديو
2. انتظر اكتمال التحميل
3. استلم الفيديو مباشرة

📌 *روابط اختبارية:*
- `https://www.youtube.com/watch?v=jNQXAC9IVRw`
- `https://www.youtube.com/watch?v=6Szzf2hLpWI`
"""
        update.message.reply_markdown(welcome_msg)
        logger.info(f"تم إرسال رسالة ترحيب - حالة Cookies: {cookies_status}")
    except Exception as e:
        logger.error(f"خطأ في الترحيب: {traceback.format_exc()}")
        update.message.reply_text("مرحباً! اكتب /help للمساعدة")

def help_command(update: Update, context: CallbackContext) -> None:
    """رسالة المساعدة"""
    try:
        help_msg = """
🛠 *دليل الاستخدام:*

1. *التحميل:*
   - أرسل رابط فيديو من YouTube
   - انتظر حتى يكتمل التحميل (1-3 دقائق)
   - استلم الفيديو تلقائياً

2. *استكشاف الأخطاء:*
   - إذا فشل التحميل، جرب:
     - رابطاً مختلفاً
     - فيديو أقصر
     - الانتظار بضع دقائق

3. *للإبلاغ عن مشاكل:*
   - أرسل screenshot للخطأ
   - ذكر الرابط الذي استخدمته
"""
        update.message.reply_markdown(help_msg)
    except Exception as e:
        logger.error(f"خطأ في المساعدة: {traceback.format_exc()}")

def download_video(update: Update, context: CallbackContext) -> None:
    """تحميل الفيديو مع معالجة أخطاء مفصلة"""
    url = update.message.text.strip()
    
    if not re.match(r'^https?://', url):
        update.message.reply_text("⚠️ الرابط يجب أن يبدأ بـ http:// أو https://")
        return
    
    progress_msg = update.message.reply_text("🔍 جاري التحقق من الرابط...")
    
    try:
        # التحقق من cookies
        cookies_check = check_cookies()
        if not cookies_check.startswith("✅"):
            progress_msg.edit_text(f"{cookies_check}\n\nيحتاج البوت إلى ملف cookies.txt صالح")
            return
        
        # إعدادات yt-dlp مع تفاصيل تصحيح
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'cookiefile': 'cookies.txt',
            'verbose': True,
            'socket_timeout': 120,
            'retries': 3,
            'no_warnings': False,
            'ignoreerrors': False,
        }

        progress_msg.edit_text("⏬ جاري استخراج معلومات الفيديو...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات أولاً
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'فيديو')
            
            progress_msg.edit_text(f"📥 جاري تحميل: {video_title}")
            
            # التحميل الفعلي
            ydl.download([url])
            file_path = ydl.prepare_filename(info)
            
            # التحقق من وجود الملف
            if not os.path.exists(file_path):
                progress_msg.edit_text("❌ تم التحميل ولكن الملف غير موجود")
                logger.error(f"الملف غير موجود بعد التحميل: {file_path}")
                return
            
            # إرسال الفيديو
            progress_msg.edit_text("📤 جاري إرسال الفيديو...")
            
            with open(file_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=video_file,
                    caption=f"🎬 {video_title}",
                    timeout=300,
                    write_timeout=300,
                    connect_timeout=300
                )
            
            # التنظيف
            os.remove(file_path)
            progress_msg.delete()
            logger.info(f"تم تحميل وإرسال الفيديو بنجاح: {video_title}")
            
    except yt_dlp.DownloadError as e:
        error_msg = f"❌ خطأ في التحميل:\n"
        error_msg += f"• {str(e)[:150]}\n\n"
        error_msg += "جرب:\n• رابطاً مختلفاً\n• فيديو أقصر\n• الانتظار قليلاً"
        
        progress_msg.edit_text(error_msg)
        logger.error(f"DownloadError: {traceback.format_exc()}")
        
    except Exception as e:
        error_msg = "⚠️ حدث خطأ غير متوقع\n"
        error_msg += "الرجاء المحاولة لاحقاً أو تجربة رابط آخر"
        
        progress_msg.edit_text(error_msg)
        logger.error(f"Unexpected error: {traceback.format_exc()}")

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    if not TOKEN:
        logger.error("❌ لم يتم تعيين TELEGRAM_BOT_TOKEN!")
        return
    
    # التحقق من النظام
    logger.info(f"حالة Cookies: {check_cookies()}")
    logger.info(f"مجلد التحميلات: {os.path.exists(DOWNLOAD_FOLDER)}")
    
    try:
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # تسجيل الأوامر
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        
        # معالجة الرسائل النصية
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, download_video))
        
        # بدء البوت
        updater.start_polling()
        logger.info("✅ البوت يعمل الآن على السحابة!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ فشل تشغيل البوت: {traceback.format_exc()}")

if __name__ == '__main__':
    main()
