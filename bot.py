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
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# إنشاء مجلد التحميلات
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def start(update: Update, context: CallbackContext) -> None:
    """رسالة ترحيبية محسنة"""
    try:
        welcome_msg = """
🎥 *مرحباً في بوت تحميل الفيديوهات* 🎥

✨ *كيفية الاستخدام:*
1. أرسل رابط الفيديو (يوتيوب، تيك توك، تويتر)
2. انتظر حتى يكتمل التحميل
3. استلم الفيديو مباشرة

📌 للمساعدة اضغط /help
"""
        update.message.reply_markdown(welcome_msg)
    except Exception as e:
        logger.error(f"خطأ في الترحيب: {traceback.format_exc()}")
        update.message.reply_text("مرحباً بك! اكتب /help للمساعدة")

def help_command(update: Update, context: CallbackContext) -> None:
    """رسالة مساعدة مفصلة"""
    try:
        help_msg = """
🛠 *دليل الاستخدام الكامل:*

1. *التحميل:*
   - أرسل رابط الفيديو مباشرة
   - مثال: https://youtu.be/xxxx

2. *الميزات:*
   - يدعم اليوتيوب (بما فيها Shorts)
   - يدعم تيك توك وتويتر
   - لا يحتاج FFmpeg

3. *استكشاف الأخطاء:*
   - إذا فشل التحميل، جرب:
     - رابطاً مختلفاً
     - اتصال إنترنت أفضل
     - الانتظار بضع دقائق
"""
        update.message.reply_markdown(help_msg)
    except Exception as e:
        logger.error(f"خطأ في المساعدة: {traceback.format_exc()}")
        update.message.reply_text("استخدم /help لعرض التعليمات")

def safe_download(ydl_opts: dict, url: str):
    """تنزيل آمن مع التعامل مع الأخطاء"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)
    except yt_dlp.DownloadError as e:
        logger.error(f"خطأ التحميل: {traceback.format_exc()}")
        raise
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {traceback.format_exc()}")
        raise

def download_video(update: Update, context: CallbackContext) -> None:
    """وظيفة التحميل الرئيسية"""
    url = update.message.text.strip()
    
    if not re.match(r'^https?://', url):
        update.message.reply_text("⚠️ الرابط يجب أن يبدأ بـ http:// أو https://")
        return
    
    progress_msg = update.message.reply_text("⏳ جاري التحضير للتحميل...")
    
    try:
        # إعدادات محسنة للتحميل
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'socket_timeout': 30,
            'retries': 3,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        info = safe_download(ydl_opts, url)
        file_path = ydl_opts['outtmpl'] % {'title': info['title'], 'ext': info['ext']}
        
        progress_msg.edit_text("📤 جاري إرسال الفيديو...")
        
        # إرسال الفيديو مع التحكم بالوقت
        with open(file_path, 'rb') as video_file:
            context.bot.send_video(
                chat_id=update.message.chat_id,
                video=video_file,
                caption=f"🎬 {info.get('title', 'فيديو')}",
                timeout=100,
                write_timeout=100,
                connect_timeout=100
            )
        
        os.remove(file_path)
        progress_msg.delete()
        
    except yt_dlp.DownloadError as e:
        error_msg = "❌ فشل التحميل:\n"
        if 'timed out' in str(e):
            error_msg += "- انتهى وقت الانتظار\n- جرب اتصال إنترنت أفضل"
        elif 'unavailable' in str(e):
            error_msg += "- الفيديو غير متاح أو محذوف"
        else:
            error_msg += "- حدث خطأ أثناء التحميل"
        
        progress_msg.edit_text(error_msg)
        
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {traceback.format_exc()}")
        progress_msg.edit_text("⚠️ حدث خطأ غير متوقع، يرجى المحاولة لاحقاً")

def main():
    """تشغيل البوت"""
    if not TOKEN:
        logger.error("لم يتم تعيين التوكن!")
        return
    
    try:
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # الأوامر
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        
        # معالجة الرسائل
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, download_video))
        
        # بدء البوت
        updater.start_polling()
        logger.info("✅ البوت يعمل بنجاح")
        updater.idle()
        
    except Exception as e:
        logger.error(f"فشل التشغيل: {traceback.format_exc()}")

if __name__ == '__main__':
    main()