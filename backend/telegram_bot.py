import asyncio
from telegram import Bot
BOT_TOKEN = "8176628567:AAEpjmTTKnry8p7NguW5fNhzRHFN1dImdyM"
CHAT_ID = "5798312780"

async def main():
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(
        chat_id=CHAT_ID,
        text="Hello from Python!"
    )

asyncio.run(main())