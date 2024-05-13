import signal
import logging
import asyncio
from os import environ

import websockets

import telegram.error
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, filters, MessageHandler
from web3 import AsyncWeb3, WebsocketProviderV2

CHAT_ID = ""
CHAT_ID = environ.get("CHAT_ID", CHAT_ID)
TOKEN = ""
TOKEN = environ.get("BOT_TOKEN", TOKEN)
WSS_URL = "wss://eth.drpc.org"
WSS_URL = environ.get("WSS_URL", WSS_URL)

logger = logging.getLogger(__name__)
c_handler = logging.StreamHandler()
c_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(c_handler)
logger.setLevel(logging.DEBUG)

application = ApplicationBuilder().token(TOKEN).build()

exit = False


def signal_handler(self, sig, frame):
    logger.info("Caught signal: %s", sig)
    exit = True


async def asend_message(message):
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
    except telegram.error.RetryAfter:
        await asend_message(message)


signal.signal(signal.SIGINT, signal_handler)


async def create_subscription(event_type, event_params):
    while not exit:
        async for w3_socket in AsyncWeb3.persistent_websocket(WebsocketProviderV2(WSS_URL)):
            subscription_id = await w3_socket.eth.subscribe(event_type, event_params)
            logger.debug(f"Subscribed to {event_type}, subscription_id: {subscription_id}")

            try:
                async for response in w3_socket.ws.process_subscriptions():
                    logger.debug(f"{response=}")
                    await asyncio.sleep(0.5)
                    if exit:
                        await w3_socket.eth.unsubscribe(subscription_id)
                        break
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError) as e:
                logger.debug(f"Connection closed: {e}. Reconnecting...")
                await asyncio.sleep(5)  # Wait for 5 seconds before reconnecting
            # asyncio.CancelledError is not a subclass of Exception starting Py3.8, see https://docs.python.org/3.11/library/asyncio-exceptions.html#asyncio.CancelledError
            # Note that there might be more elecant solutions than to simply catch all BaseExceptions, but I would see this rather as a question on the websocket handling, nothing PTB related
            except BaseException as e:  # Catch all other exceptions, including asyncio.CancelledError
                logger.debug(e)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def run():
    await asend_message("Starting...")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    await application.initialize()
    await application.start()

    await application.updater.start_polling(drop_pending_updates=True)
    subs_tasks = set()

    subs_tasks.add(
        application.create_task(create_subscription('logs', {'address': '0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc'})))
    subs_tasks.add(
        application.create_task(create_subscription('logs', {'address': '0x12d6867fa648d269835cf69b49f125147754b54d'})))

    try:
        await asyncio.gather(*subs_tasks, return_exceptions=True)
    finally:
        # Ensure that gracefull shutdown is always called
        await asend_message("Stopping...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        # after shutdown, the networking backend is no longer available to make requests to TG
        logger.info("Stopped.")


if __name__ == "__main__":
    asyncio.run(run())
