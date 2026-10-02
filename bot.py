
import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

import database
import config


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


ALLOWED_STATUSES = {"member", "administrator", "creator"}


async def setup_channel(app: Application):
    try:
        channel = await app.bot.get_chat(config.CHANNEL)
        app.bot_data["channel_id"] = channel.id

        logger.info(
            "Channel detected: title=%s, id=%s",
            channel.title,
            channel.id
        )

        bot_member = await app.bot.get_chat_member(
            channel.id,
            app.bot.id
        )

        if bot_member.status != "administrator":
            logger.warning(
                "Bot is not an administrator in channel %s",
                channel.id
            )
        else:
            logger.info("Bot administrator access confirmed")

    except TelegramError:
        logger.exception("Channel setup failed")
        app.bot_data["channel_id"] = None


async def is_channel_member(bot, channel_id, user_id):
    member = await bot.get_chat_member(channel_id, user_id)

    if member.status in ALLOWED_STATUSES:
        return True

    if member.status == "restricted":
        return getattr(member, "is_member", False)

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text(
            "چنل اصلی: @GifNamusi"
        )
        return

    token = context.args[0]
    channel_id = context.application.bot_data.get("channel_id")

    if not channel_id:
        await update.effective_message.reply_text(
            "در حال حاضر دسترسی به کانال ممکن نیست. لطفاً بعداً تلاش کن."
        )
        return

    try:
        is_member = await is_channel_member(
            context.bot,
            channel_id,
            update.effective_user.id
        )

    except TelegramError:
        logger.exception("Membership check failed for user %s",
                         update.effective_user.id)

        await update.effective_message.reply_text(
            "فعلاً امکان بررسی عضویت وجود ندارد. لطفاً بعداً تلاش کن."
        )
        return

    if not is_member:
        keyboard = [
            [
                InlineKeyboardButton(
                    "عضویت در کانال",
                    url="https://t.me/GifNamusi"
                )
            ],
            [
                InlineKeyboardButton(
                    "بررسی عضویت",
                    callback_data=f"check_{token}"
                )
            ]
        ]

        await update.effective_message.reply_text(
            "برای دریافت فایل، ابتدا عضو کانال شو.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await send_file(update, context, token)


async def check_membership(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    token = query.data.removeprefix("check_")

    channel_id = context.application.bot_data.get("channel_id")

    if not channel_id:
        await query.answer(
            "دسترسی به کانال وجود ندارد.",
            show_alert=True
        )
        return

    try:
        is_member = await is_channel_member(
            context.bot,
            channel_id,
            query.from_user.id
        )

    except TelegramError:
        logger.exception(
            "Callback membership check failed for user %s",
            query.from_user.id
        )

        await query.answer(
            "خطا در بررسی عضویت. بعداً دوباره امتحان کن.",
            show_alert=True
        )
        return

    if not is_member:
        await query.answer(
            "هنوز عضو کانال نیستی.",
            show_alert=True
        )
        return

    await query.answer("عضویت تأیید شد.")

    try:
        await query.message.delete()
    except TelegramError:
        logger.warning("Could not delete membership prompt")

    await send_file(update, context, token)


async def send_file(update, context, token):
    file_data = database.get_photo(token)

    if not file_data:
        await update.effective_message.reply_text(
            "این لینک معتبر نیست یا فایل پیدا نشد."
        )
        return

    file_type, file_id = file_data

    if file_type == "gif":
        message = await update.effective_message.reply_animation(
            animation=file_id
        )
    else:
        message = await update.effective_message.reply_photo(
            photo=file_id
        )

    await asyncio.sleep(15)

    try:
        await message.delete()
    except TelegramError:
        logger.warning("Could not delete sent file message")


async def upload_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != config.ADMIN_ID:
        await update.effective_message.reply_text(
            "شما اجازه آپلود فایل ندارید."
        )
        return

    message = update.effective_message

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"

    elif message.animation:
        file_id = message.animation.file_id
        file_type = "gif"

    else:
        return

    try:
        token = database.save_photo(file_id, file_type)
    except Exception:
        logger.exception("File could not be saved in database")
        await message.reply_text("ذخیره فایل با خطا مواجه شد.")
        return

    link = f"https://t.me/{config.BOT_USERNAME}?start={token}"

    await message.reply_text(
        f"فایل ذخیره شد ✅\n\nلینک فایل:\n{link}"
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"آیدی عددی شما:\n{update.effective_user.id}"
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "Unhandled exception while processing update",
        exc_info=context.error
    )


def main():
    database.create_database()

    app = (
        Application.builder()
        .token(config.TOKEN)
        .post_init(setup_channel)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", my_id))

    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.ANIMATION,
            upload_file
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            check_membership,
            pattern=r"^check_"
        )
    )

    app.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
