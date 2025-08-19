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
    """تحميل الفيديو مع حلول متعددة"""
    url = update.message.text.strip()
    
    progress_msg = update.message.reply_text("🔍 جاري معالجة الرابط...")
    
    try:
        # المحاولة الأولى: مع cookies
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'socket_timeout': 60,
            'retries': 2,
        }
        
        # إضافة cookies إذا كان الملف موجوداً
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
            progress_msg.edit_text("🔐 جاري التحميل بصلاحيات كاملة...")
        else:
            progress_msg.edit_text("⏬ جاري التحميل (وضع عادي)...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # إرسال الفيديو
            with open(file_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=video_file,
                    caption=f"🎬 {info.get('title', 'فيديو')}",
                    timeout=120
                )
            
            os.remove(file_path)
            progress_msg.delete()
            
    except yt_dlp.DownloadError as e:
        if 'Sign in to confirm' in str(e):
            # المحاولة الثانية: بدون cookies (للفيديوهات العامة)
            try:
                progress_msg.edit_text("🔄 جرب طريقة بديلة...")
                
                ydl_opts_no_cookies = {
                    'format': 'worst[ext=mp4]',  # جودة أقل لتجنب الحماية
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'socket_timeout': 45,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info)
                    
                    with open(file_path, 'rb') as video_file:
                        context.bot.send_video(
                            chat_id=update.message.chat_id,
                            video=video_file,
                            caption=f"🎬 {info.get('title', 'فيديو')} (جودة منخفضة)",
                            timeout=120
                        )
                    
                    os.remove(file_path)
                    progress_msg.delete()
                    
            except Exception as e2:
                error_msg = "❌ تعذر تحميل الفيديو\n\n"
                error_msg += "• يحتاج تحديث ملف cookies\n"
                error_msg += "• أو جرب فيديو أقل شهرة\n"
                error_msg += "• أو منصات أخرى: TikTok, Twitter"
                progress_msg.edit_text(error_msg)
        else:
            progress_msg.edit_text(f"❌ خطأ تقني: {str(e)[:100]}")

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    if not TOKEN:
        logger.error("❌ لم يتم تعيين TELEGRAM_BOT_TOKEN!")
        return
def convert_to_direct_link(url):
    """تحويل الرواق إلى صيغ مباشرة"""
    if 'youtube.com/shorts/' in url:
        video_id = url.split('/shorts/')[1].split('?')[0]
        return f'https://www.youtube.com/watch?v={video_id}'
    return url
    
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

