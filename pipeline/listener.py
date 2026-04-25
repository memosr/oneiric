"""
Oneiric Telegram listener.
Polls @OneiricDreamBot for text messages, runs pipeline, sends card back.
"""
import os, sys, logging, asyncio, subprocess
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
)

sys.path.insert(0, str(Path(__file__).parent))
from main import run_pipeline, generate_dream_id

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("oneiric-listener")

TOKEN = os.environ.get("ONEIRIC_BOT_TOKEN")

ALLOWED: set[int] = set()
_raw = os.environ.get("ONEIRIC_ALLOWED_USERS", "")
if _raw:
    ALLOWED = {int(x.strip()) for x in _raw.split(",") if x.strip()}

PROJECT_ROOT = Path(__file__).parent.parent


def git_auto_commit(dream_id: str, dream_title: str) -> bool:
    """
    Stage the new dream dir + updated dreams.json, commit, push.
    Returns True if successful, False on any error.
    """
    try:
        subprocess.run(
            ["git", "add",
             f"gallery/public/dreams/{dream_id}/",
             "gallery/data/dreams.json"],
            cwd=PROJECT_ROOT, check=True, timeout=30
        )
        subprocess.run(
            ["git", "commit", "-m",
             f"feat(gallery): auto-archive {dream_id} — {dream_title}"],
            cwd=PROJECT_ROOT, check=True, timeout=30
        )
        subprocess.run(
            ["git", "push"],
            cwd=PROJECT_ROOT, check=True, timeout=60
        )
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git auto-commit failed: {e}")
        return False
    except subprocess.TimeoutExpired:
        log.error("Git push timed out")
        return False


def _is_allowed(user_id: int) -> bool:
    return not ALLOWED or user_id in ALLOWED


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌀 Welcome to Oneiric.\n\n"
        "Send me your dream as a text message. I'll turn it into a "
        "Salvador Dalí-style dream card with 3 scenes, Jungian interpretation, "
        "and symbolic analysis.\n\n"
        "Takes 3-5 minutes. Your card will arrive here when it's ready.\n\n"
        "Tip: describe your dream as a short paragraph (50-300 words). "
        "Turkish or English, both work."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Just send a dream description as a text message. "
        "Wait 3-5 minutes. Card arrives as an image.\n\n"
        "Commands:\n"
        "/start - Intro\n"
        "/dream - Prompt to describe your dream\n"
        "/help - This message"
    )


async def dream_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Tell me your dream. Write it as a text message — any length, "
        "Turkish or English. I'll paint it."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text

    if not _is_allowed(user.id):
        await update.message.reply_text(
            "Sorry, this bot is currently in private testing. "
            "Reach out to the author for access."
        )
        log.info(f"Rejected user {user.id} (@{user.username})")
        return

    if len(text) < 20:
        await update.message.reply_text(
            "Your dream seems too short. Tell me more — what did you see, "
            "who was there, how did it feel? 50+ words is ideal."
        )
        return

    if len(text) > 2000:
        await update.message.reply_text(
            "Your dream is quite long! Please keep it under 2000 characters."
        )
        return

    await update.message.reply_text(
        "🌀 Got it. Painting your dream now.\n\n"
        "Stages:\n"
        "1️⃣ Analyzing symbols (~45s)\n"
        "2️⃣ Generating 3 scenes (~2-3m)\n"
        "3️⃣ Assembling card (~15s)\n\n"
        "I'll send the card when ready."
    )

    dream_id = generate_dream_id()
    dream_dir = PROJECT_ROOT / f"gallery/public/dreams/{dream_id}"
    dreamer = f"@{user.username}" if user.username else f"tg_{user.id}"

    log.info(f"Starting pipeline for {dream_id} (user {user.id})")

    loop = asyncio.get_event_loop()
    original_cwd = Path.cwd()
    try:
        os.chdir(PROJECT_ROOT)
        result = await loop.run_in_executor(
            None,
            lambda: run_pipeline(text, dream_dir, dream_id, dreamer, user_id=str(user.id)),
        )
    except Exception as e:
        log.exception(f"Pipeline crashed for {dream_id}")
        await update.message.reply_text(
            f"❌ Something went wrong while painting your dream.\n"
            f"Error: {type(e).__name__}"
        )
        return
    finally:
        os.chdir(original_cwd)

    log.info(f"Pipeline result for {dream_id}: {result['status']} in {result['duration_sec']}s")

    if result["status"] == "success":
        card_path = Path(result["card_path"])
        if card_path.exists():
            title = result["stages"].get("analyze", {}).get("title", "Your Dream")
            with open(card_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=(
                        f"✨ *{title}*\n\n"
                        f"Archived as `{dream_id}`\n"
                        f"Pipeline: {result['duration_sec']}s"
                    ),
                    parse_mode="Markdown",
                )
            pushed = await loop.run_in_executor(
                None,
                lambda: git_auto_commit(dream_id, result["stages"].get("analyze", {}).get("title", dream_id))
            )
            if pushed:
                await update.message.reply_text(
                    "🌐 Your card is now live at oneiric-zeta.vercel.app"
                )
        else:
            await update.message.reply_text("Card was generated but file is missing.")
    elif result["status"] == "partial":
        await update.message.reply_text(
            f"⚠️ Partial success.\n\n"
            f"Illustrate: {result['stages'].get('illustrate')}\n"
            f"Error: {result.get('error')}"
        )
    else:
        await update.message.reply_text(
            f"❌ Pipeline failed.\n\n"
            f"Error: {result.get('error')}\n"
            f"Stages completed: {list(result['stages'].keys())}"
        )


def main() -> None:
    if not TOKEN:
        log.error("ONEIRIC_BOT_TOKEN not set in .env")
        sys.exit(1)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("dream", dream_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("🌀 Oneiric listener starting...")
    log.info(f"Allowed users: {ALLOWED or 'OPEN'}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
