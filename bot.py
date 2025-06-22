import logging
import os
import sys
from telegram import Update, __version__ as TG_VER
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io
import asyncio

if sys.version_info < (3, 8):
    logging.error("Python 3.8 or higher is required!")
    sys.exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

THUMBNAIL_PATH = 'thumbnail.jpg'
BASE_URL = os.getenv('BASE_URL', 'https://groky-iii.onrender.com')
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.epub', '.mobi'}

logger.info(f"Using python-telegram-bot version {TG_VER}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_id = context.bot_data.get("CHANNEL_ID", "הערוץ שלנו")
    await update.message.reply_text(
        "שלום, תורם יקר!\n"
        "אני בוט שמסייע לשתף ספרים בקהילה השיתופית שלנו.\n"
        f"שלח לי קובץ ספר (PDF, DOC, וכו'), והוא יפורסם בערוץ {channel_id}.\n"
        "צריך עזרה? הקלד /help."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_id = context.bot_data.get("CHANNEL_ID", "הערוץ שלנו")
    await update.message.reply_text(
        "ברוך הבא לקהילה השיתופית שלנו!\n"
        "ככה תוכל לתרום:\n"
        "1. שלח לי קובץ ספר (PDF, DOC, DOCX, TXT, EPUB, או MOBI).\n"
        f"2. הקובץ יפורסם בערוץ {channel_id}.\n"
        "3. תקבל אישור על תרומתך.\n"
        "שאלות? שלח הודעה, ואני כאן לעזור!"
    )

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

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    file_name = document.file_name.lower()
    file_ext = os.path.splitext(file_name)[1]

    if file_ext not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(
            "הקובץ אינו ספר! אנא שלח קבצי ספרים בלבד (PDF, DOC, וכו') ואל תשלח קבצים אחרים שוב."
        )
        logger.info(f"קובץ לא תקין נשלח: {file_name}")
        return

    await update.message.reply_text("מעבד את תרומת הספר שלך, רגע אחד...")

    try:
        file_obj = await document.get_file()
        input_file = f'temp_{document.file_name}'
        await file_obj.download_to_drive(input_file)

        thumb_io = await prepare_thumbnail()

        original_filename = document.file_name
        base, ext = os.path.splitext(original_filename)
        new_filename = f"{base}_SharedBook{ext}"

        channel_id = context.bot_data.get("CHANNEL_ID")
        if not channel_id:
            logger.error("CHANNEL_ID לא הוגדר בבוט.")
            await update.message.reply_text("שגיאה פנימית: לא הוגדר ערוץ יעד.")
            return

        with open(input_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=channel_id,
                document=f,
                filename=new_filename,
                thumbnail=thumb_io if thumb_io else None
            )

        os.remove(input_file)
        await update.message.reply_text("תודה על תרומתך")

    except Exception as e:
        logger.error(f"שגיאה בטיפול בקובץ: {e}")
        await update.message.reply_text("אוי, משהו השתבש עם תרומת הספר. אנא נסה שוב!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'עדכון {update} גרם לשגיאה: {context.error}')
    if update and update.message:
        await update.message.reply_text("אוי, משהו השתבש. אנא נסה לתרום את הספר שוב!")

async def main():
    if not os.path.exists(THUMBNAIL_PATH):
        logger.error(f"קובץ thumbnail {THUMBNAIL_PATH} לא נמצא!")
        return

    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN לא הוגדר!")
        return

    channel_id = os.getenv('CHANNEL_ID')
    if not channel_id:
        logger.error("CHANNEL_ID לא הוגדר!")
        return

    webhook_url = f"{BASE_URL}/{token}"
    if not webhook_url.startswith('https://'):
        logger.error("BASE_URL חייב להתחיל ב-https://!")
        return

    application = Application.builder().token(token).build()
    application.bot_data["CHANNEL_ID"] = channel_id

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_error_handler(error_handler)

    port = int(os.getenv('PORT', 8443))
    logger.info(f"Starting webhook on port {port}")

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
        logger.info("Webhook server is running")
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