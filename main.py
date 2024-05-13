import signal
import logging
import asyncio
import websockets

import telegram.error
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, filters, MessageHandler
from web3 import AsyncWeb3, WebsocketProviderV2

CHAT_ID = ""
TOKEN = ""
WSS_URL = ""

logger = logging.getLogger(__name__)
c_handler = logging.StreamHandler()
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
            except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
                logger.debug(f"Connection closed: {e}. Reconnecting...")
                await asyncio.sleep(5)  # Wait for 5 seconds before reconnecting
            except Exception as e:
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

    await asyncio.gather(*subs_tasks, return_exceptions=True)

    await asend_message("Stopping...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    await asend_message("Stopped.")


if __name__ == "__main__":
    asyncio.run(run())
