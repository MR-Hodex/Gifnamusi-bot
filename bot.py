import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

import database
import config


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "چنل اصلی: @GifNamusi"
        )
        return

    token = context.args[0]

    try:
        member = await context.bot.get_chat_member(
            config.CHANNEL,
            update.effective_user.id
        )

        if member.status not in ["member", "administrator", "creator"]:
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

            await update.message.reply_text(
                "برای دیدن فایل، ابتدا باید عضو کانال بشی.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    except Exception as error:
        print("Membership check error:", error)

        await update.message.reply_text(
            "فعلاً امکان بررسی عضویت وجود ندارد."
        )
        return

    await send_file(update, context, token)


async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    token = query.data.replace("check_", "")

    try:
        member = await context.bot.get_chat_member(
            config.CHANNEL,
            query.from_user.id
        )

        if member.status not in ["member", "administrator", "creator"]:
            await query.answer(
                "هنوز عضو کانال نیستی.",
                show_alert=True
            )
            return

    except Exception as error:
        print("Membership check error:", error)

        await query.answer(
            "خطا در بررسی عضویت.",
            show_alert=True
        )
        return

    await query.message.delete()

    await send_file(query, context, token)


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
            animation=file_id,
            protect_content=True
        )
    else:
        message = await update.effective_message.reply_photo(
            photo=file_id,
            protect_content=True
        )

    await asyncio.sleep(15)

    try:
        await message.delete()
    except Exception:
        pass


async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.effective_message.reply_text(
            "شما اجازه آپلود فایل ندارید."
        )
        return

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"

    elif update.message.animation:
        file_id = update.message.animation.file_id
        file_type = "gif"

    else:
        return

    token = database.save_photo(file_id, file_type)

    link = f"https://t.me/{config.BOT_USERNAME}?start={token}"

    await update.effective_message.reply_text(
        f"فایل ذخیره شد ✅\n\nلینک فایل:\n{link}"
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"آیدی عددی شما:\n{update.effective_user.id}"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Error:", context.error)


def main():
    database.create_database()

    app = Application.builder().token(config.TOKEN).build()

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
            pattern="^check_"
        )
    )

    app.add_error_handler(error_handler)

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
