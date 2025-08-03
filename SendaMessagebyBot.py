import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder

BOT_TOKEN = '8020928937:AAElhu5BE995M1w9nvJQZSl3kY8R3SeU-PU'
CHANNEL_USERNAME = '@vonartis'  # Your channel username

async def post_buttons_message(app):
    keyboard = [
    [InlineKeyboardButton("Open Bot Menu", url="https://t.me/Harry_Von_Bot?start=mainmenu")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)   

    await app.bot.send_message(
        chat_id=CHANNEL_USERNAME,
        text="👋 Welcome. Please click the button below to interact with our Bot and get further information and help.",
        reply_markup=reply_markup
    )
    print("Message sent! Now go to your channel and pin it manually.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    async def runner():
        await post_buttons_message(app)
        # Stop the bot after sending the message
        await app.shutdown()

    asyncio.run(runner())

if __name__ == "__main__":
    main()
