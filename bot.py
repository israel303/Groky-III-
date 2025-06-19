import logging
import os
from telegram import Update, __version__ as TG_VER
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io
import asyncio

# הגדרת לוגים
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# תמונת ה-thumbnail הקבועה
THUMBNAIL_PATH = 'thumbnail.jpg'

# כתובת בסיס ל-Webhook
BASE_URL = os.getenv('BASE_URL', 'https://groky.onrender.com')

# מזהה הערוץ (מוגדר כמשתנה סביבה)
CHANNEL_ID = os.getenv('CHANNEL_ID', '@chechjfdvhn')

# פורמטים מותרים של מסמכות
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.epub', '.mobi'}

# רישום גרסת python-telegram-bot
logger.info(f"Using python-telegram-bot version {TG_VER}")

# פקודת /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"שלום, תורם יקר!\n"
        f"אני בוט שמסייע לשתף ספרים בקהילה השיתופית שלנו.\n"
        f"שלח לי קובץ ספר (PDF, DOC, וכו'), והוא יפורסם בערוץ {CHANNEL_ID}.\n"
        f"צריך עזרה? הקלד /help."
    )

# פקודת /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"ברוך הבא לקהילה השיתופית שלנו!\n"
        f"ככה תוכל לתרום:\n"
        f"1. שלח לי קובץ ספר (PDF, DOC, DOCX, TXT, EPUB, או MOBI).\n"
        f"2. הקובץ יפורסם בערוץ {CHANNEL_ID}.\n"
        f"3. תקבל אישור על תרומתך.\n"
        f"שאלות? שלח הודעה, ואני כאן לעזור!"
    )

# הכנת thumbnail
async def prepare_thumbnail() -> io.BytesIO:
    try:
        with Image.open(THUMBNAIL_PATH) as img:
            img = img.convert('RGB')
            img.thumbnail((200, 300))
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            return thumb_io
    except Exception as e:
        logger.error(f"שגיאה בהכנת thumbnail: {e}")
        return None

# טיפול בקבצים
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    file_name = document.file_name.lower()
    file_ext = os.path.splitext(file_name)[1]

    # בדיקת פורמט הקובץ
    if file_ext not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(
            'הקובץ אינו ספר! אנא שלח קבצי ספרים בלבד (PDF, DOC, וכו') ואל תשלח קבצים אחרים שוב.'
        )
        logger.info(f"קובץ לא תקין נשלח: {file_name}")
        return

    await update.message.reply_text('מעבד את תרומת הספר שלך, רגע אחד...')

    try:
        # הורדת הקובץ
        file_obj = await document.get_file()
        input_file = f'temp_{document.file_name}'
        await file_obj.download_to_drive(input_file)

        # הכנת thumbnail
        thumb_io = await prepare_thumbnail()

        # הוספת "_SharedBook" לפני הסיומת
        original_filename = document.file_name
        base, ext = os.path.splitext(original_filename)
        new_filename = f"{base}_SharedBook{ext}"

        # שליחת הקובץ לערוץ ללא כיתוב
        with open(input_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=f,
                filename=new_filename,
                thumbnail=thumb_io if thumb_io else None
            )

        # ניקוי קבצים זמניים
        os.remove(input_file)

        # אישור למשתמש
        await update.message.reply_text('תודה על תרומתך')

    except Exception as e:
        logger.error(f"שגיאה בטיפול בקובץ: {e}")
        await update.message.reply_text('אוי, משהו השתבש עם תרומת הספר. אנא נסה שוב!')

# טיפול בשגיאות
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'עדכון {update} גרם לשגיאה: {context.error}')
    if update and update.message:
        await update.message.reply_text('אוי, משהו השתבש. אנא נסה לתרום את הספר שוב!')

# פונקציה ראשית
async def main():
    # בדיקת קובץ thumbnail
    if not os.path.exists(THUMBNAIL_PATH):
        logger.error(f"קובץ thumbnail {THUMBNAIL_PATH} לא נמצא!")
        return

    # קבלת הטוקן
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN לא הוגדר!")
        return

    # בדיקת מזהה הערוץ
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID לא הוגדר!")
        return

    # בניית כתובת Webhook
    webhook_url = f"{BASE_URL}/{token}"
    if not webhook_url.startswith('https://'):
        logger.error("BASE_URL חייב להתחיל ב-https://!")
        return

    # יצירת האפליקציה
    application = Application.builder().token(token).build()

    # הוספת handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_error_handler(error_handler)

    # הגדרת Webhook
    port = int(os.getenv('PORT', 8443))

    try:
        await application.initialize()
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook הוגדר לכתובת {webhook_url}")
        await application.start()
        await application.updater.start_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=token,
            webhook_url=webhook_url
        )
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"שגיאה בלולאה הראשית: {e}")
        await application.stop()
        await application.shutdown()
        raise
    finally:
        await application.stop()
        await application.shutdown()
        logger.info("הבוט נסגר")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("הבוט נעצר על ידי המשתמש")
    except Exception as e:
        logger.error(f"שגיאה קריטית: {e}")