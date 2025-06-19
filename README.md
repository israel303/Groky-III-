# Shared Books Bot

בוט טלגרם שמאפשר תרומת ספרים לקהילה שיתופית. הבוט מקבל קבצי ספרים (PDF, DOC, וכו'), מוסיף להם תמונת תצוגה, ומפרסם אותם בערוץ טלגרם מוגדר.

## התקנה

1. **דרישות**:
   - Python 3.8+
   - חשבון Render (או שרת אחר תואם Webhook)
   - טוקן בוט מטלגרם (מ-@BotFather)
   - תמונת thumbnail בשם `thumbnail.jpg`

2. **הגדרת משתני סביבה**:
   - `TELEGRAM_TOKEN`: טוקן הבוט.
   - `BASE_URL`: כתובת האפליקציה (למשל, `https://your-app.onrender.com`).
   - `CHANNEL_ID`: מזהה ערוץ טלגרם (למשל, `@TestChannel`).
   - `PORT`: פורט ה-Webhook (ברירת מחדל: 8443).

3. **התקנת תלות**:
   ```bash
   pip install -r requirements.txt