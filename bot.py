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
🎥 *مرحباً في بوت تحميل الفيديوهات* 🎥

✅ *المميزات:*
- تحميل من YouTube (مدعوم بكامل الصلاحيات)
- تحميل من TikTok و Twitter
- يعمل 24/7 على السحابة

⚡ *طريقة الاستخدام:*
1. أرسل رابط الفيديو
2. انتظر حتى يكتمل التحميل
3. استلم الفيديو مباشرة

📌 الآن يدعم تحميل جميع فيديوهات YouTube!
"""
        update.message.reply_markdown(welcome_msg)
    except Exception as e:
        logger.error(f"خطأ في الترحيب: {e}")

def download_video(update: Update, context: CallbackContext) -> None:
    """تحميل الفيديو مع استخدام cookies"""
    url = update.message.text.strip()
    
    if not re.match(r'^https?://', url):
        update.message.reply_text("⚠️ الرابط غير صحيح")
        return
    
    try:
        # إعدادات مع cookies
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'cookiefile': 'cookies.txt',  # استخدام ملف cookies
            'socket_timeout': 60,
            'retries': 5,
            'fragment_retries': 10,
            'ignoreerrors': False,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            }
        }

        progress_msg = update.message.reply_text("🔐 جاري التحضير مع الصلاحيات الكاملة...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            progress_msg.edit_text("📤 جاري إرسال الفيديو...")
            
            # إرسال الفيديو
            with open(file_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=video_file,
                    caption=f"🎬 {info.get('title', 'فيديو')}\n\n✅ تم التحميل بنجاح",
                    timeout=300,
                    write_timeout=300,
                    connect_timeout=300
                )
            
            # تنظيف الملف
            if os.path.exists(file_path):
                os.remove(file_path)
            
            progress_msg.delete()
            
    except yt_dlp.DownloadError as e:
        logger.error(f"خطأ التحميل: {e}")
        error_msg = "❌ فشل التحميل:\n"
        
        if 'cookies' in str(e):
            error_msg += "يبدو أن ملف cookies يحتاج تحديثاً"
        elif 'Private' in str(e):
            error_msg += "الفيديو خاص أو محمي"
        else:
            error_msg += f"{str(e)[:100]}..."
        
        update.message.reply_text(error_msg)
        
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        update.message.reply_text("⚠️ حدث خطأ غير متوقع، جرب رابطاً آخر")

def main():
    """تشغيل البوت"""
    if not TOKEN:
        logger.error("❌ لم يتم تعيين التوكن!")
        return
    
    # إنشاء مجلد التحميلات
    os.makedirs('downloads', exist_ok=True)
    
    # التحقق من وجود cookies
    if not os.path.exists('cookies.txt'):
        logger.warning("⚠️ ملف cookies.txt غير موجود، قد يفشل تحميل YouTube")
    
    try:
        updater = Updater(TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # الأوامر
        dispatcher.add_handler(CommandHandler("start", start))
        
        # معالجة الروابط
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, download_video))
        
        # بدء البوت
        updater.start_polling()
        logger.info("✅ البوت يعمل مع دعم cookies الكامل!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ فشل التشغيل: {e}")

if __name__ == '__main__':
    main()
