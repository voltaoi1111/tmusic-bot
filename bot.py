import os
import asyncio
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

# Setup
logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("BOT_TOKEN")
os.makedirs("downloads", exist_ok=True)


def clean(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except:
        pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *MP3 Music Bot*\n\n"
        "Send a song name or YouTube link!",
        parse_mode="Markdown"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    msg = await update.message.reply_text("🔍 Searching...")

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            data = await asyncio.to_thread(
                ydl.extract_info, f"ytsearch5:{query}", download=False
            )

        results = data.get("entries", [])
        if not results:
            await msg.edit_text("❌ No results.")
            return

        buttons = []
        for r in results:
            title = (r.get("title") or "?")[:40]
            vid = r.get("id")
            if vid:
                buttons.append([
                    InlineKeyboardButton(f"🎶 {title}", callback_data=f"d_{vid}")
                ])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="x")])

        await update.message.reply_text(
            "🎵 *Pick a song:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "x":
        await q.message.delete()
        return

    if not q.data.startswith("d_"):
        return

    vid = q.data[2:]
    url = f"https://www.youtube.com/watch?v={vid}"
    path = None

    await q.edit_message_text("⏳ Downloading & converting...")

    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"downloads/{vid}.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        info = await asyncio.to_thread(
            lambda: yt_dlp.YoutubeDL(opts).extract_info(url, download=True)
        )
        path = f"downloads/{vid}.mp3"

        if not os.path.exists(path):
            await q.edit_message_text("❌ Failed.")
            return

        if os.path.getsize(path) > 50 * 1024 * 1024:
            await q.edit_message_text("❌ File too big (>50MB).")
            clean(path)
            return

        await q.edit_message_text("📤 Uploading...")

        with open(path, "rb") as f:
            await context.bot.send_audio(
                chat_id=q.message.chat_id,
                audio=f,
                title=info.get("title"),
                performer=info.get("uploader"),
                caption=f"🎵 {info.get('title')}"
            )
        await q.message.delete()

    except Exception as e:
        await q.edit_message_text(f"❌ {str(e)[:100]}")
    finally:
        clean(path)


def main():
    if not TOKEN:
        print("❌ BOT_TOKEN missing!")
        return

    print("🚀 Bot running...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
