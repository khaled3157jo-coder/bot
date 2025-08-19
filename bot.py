import os
import logging
import re
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

def start(update: Update, context: CallbackContext) -> None:
    """رسالة ترحيبية"""
    try:
        welcome_msg = """
🎥 *مرحباً في بوت التحميل* 🎥

أرسل لي رابط فيديو من:
- YouTube
- TikTok  
- Twitter

⚡ يعمل 24/7 على السحابة
"""
        update.message.reply_markdown(welcome_msg)
    except Exception as e:
        logger.error(f"خطأ في الترحيب: {e}")

def download_video(update: Update, context: CallbackContext) -> None:
    """تحميل الفيديو مع إعدادات مخصصة لـ Render"""
    url = update.message.text.strip()
    
    if not re.match(r'^https?://', url):
        update.message.reply_text("⚠️ الرابط غير صحيح")
        return
    
    try:
        # إعدادات محسنة للسحابة
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloaded_video.%(ext)s',
            'socket_timeout': 30,
            'retries': 3,
            'quiet': True,
            'no_warnings': True,
        }

        progress_msg = update.message.reply_text("⏳ جاري التحميل...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = 'downloaded_video.mp4'
            
            # إرسال الفيديو
            with open(file_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=video_file,
                    caption=f"🎬 {info.get('title', 'فيديو')}",
                    timeout=120,
                    write_timeout=120,
                    connect_timeout=120
                )
            
            # تنظيف الملف
            if os.path.exists(file_path):
                os.remove(file_path)
            
            progress_msg.delete()
            
    except Exception as e:
        logger.error(f"خطأ التحميل: {e}")
        error_msg = "❌ فشل التحميل:\n"
        
        if 'Private' in str(e):
            error_msg += "- الفيديو خاص أو محمي"
        elif 'unavailable' in str(e):
            error_msg += "- الفيديو غير متاح"
        else:
            error_msg += "- حاول رابطاً آخر"
        
        update.message.reply_text(error_msg)

def main():
    """تشغيل البوت"""
    if not TOKEN:
        logger.error("❌ لم يتم تعيين التوكن!")
        return
    
    try:
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # الأوامر
        dispatcher.add_handler(CommandHandler("start", start))
        
        # معالجة الروابط
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, download_video))
        
        # بدء البوت
        updater.start_polling()
        logger.info("✅ البوت يعمل على السحابة!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ فشل التشغيل: {e}")

if __name__ == '__main__':
    main()
    
