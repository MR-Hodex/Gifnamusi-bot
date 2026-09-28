import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

import config
import database


def is_member(member):
    return (
        member.status in ("member", "administrator", "creator")
        or getattr(member, "is_member", False)
    )


async def delete_later(message):
    await asyncio.sleep(15)

    try:
        await message.delete()
    except TelegramError as error:
        print("Could not delete photo:", error)


async def send_photo(chat_id, token, context):
    file_id = database.get_photo(token)

    if not file_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text="این لینک معتبر نیست یا عکس پیدا نشد."
        )
        return

    message = await context.bot.send_photo(
        chat_id=chat_id,
        photo=file_id,
        protect_content=True
    )

    context.application.create_task(delete_later(message))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text(
            به ربات اصلی چنل گیف ناموسی خوش اومدی! برای دریافت گیف،لینکشو تو چنل اصلی پیدا کن و روش کلیک کن! لینک چن"ل: @gifnamusi."
        )
        return

    token = context.args[0]

    if not database.get_photo(token):
        await update.effective_message.reply_text(
            "این لینک معتبر نیست یا عکس پیدا نشد."
        )
        return

    try:
        member = await context.bot.get_chat_member(
            chat_id=config.CHANNEL,
            user_id=update.effective_user.id
        )

    except TelegramError as error:
        print("Membership check error:", error)
        await update.effective_message.reply_text(
            "برای دیدن یک گیف شاهکار اول تو چنلا جوین شو"
        )
        return

    if not is_member(member):
        channel_username = config.CHANNEL.lstrip("@")

        keyboard = [
            [
                InlineKeyboardButton(
                    "عضویت در کانال",
                    url=f"https://t.me/{channel_username}"
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
            "برای دیدن عکس، ابتدا باید عضو کانال بشی.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await send_photo(
        chat_id=update.effective_chat.id,
        token=token,
        context=context
    )


async def check_membership(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    token = query.data.removeprefix("check_")

    try:
        member = await context.bot.get_chat_member(
            chat_id=config.CHANNEL,
            user_id=query.from_user.id
        )

    except TelegramError as error:
        print("Membership check error:", error)
        await query.answer(
            "خطا در بررسی عضویت. کمی بعد دوباره تلاش کن.",
            show_alert=True
        )
        return

    if not is_member(member):
        await query.answer(
            "هنوز عضو کانال نیستی.",
            show_alert=True
        )
        return

    await query.answer("عضویت تأیید شد!")

    try:
        await query.message.delete()
    except TelegramError:
        pass

    await send_photo(
        chat_id=query.message.chat_id,
        token=token,
        context=context
    )


async def upload_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != config.ADMIN_ID:
        await update.effective_message.reply_text(
            "شما اجازه آپلود عکس ندارید."
        )
        return

    if update.effective_chat.type != "private":
        await update.effective_message.reply_text(
            "لطفاً عکس را در گفت‌وگوی خصوصی ربات ارسال کن."
        )
        return

    photo = update.effective_message.photo[-1]
    token = database.save_photo(photo.file_id)

    link = (
        f"https://t.me/{config.BOT_USERNAME}"
        f"?start={token}"
    )

    await update.effective_message.reply_text(
        f"عکس ذخیره شد! ✅\n\nلینک اختصاصی عکس:\n{link}"
    )


async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.effective_message.reply_text(
        f"آیدی عددی شما:\n{update.effective_user.id}"
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    print("Bot error:", context.error)


def main():
    database.create_database()

    app = (
        Application.builder()
        .token(config.TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", my_id))

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            upload_photo
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            check_membership,
            pattern=r"^check_"
        )
    )

    app.add_error_handler(error_handler)

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
