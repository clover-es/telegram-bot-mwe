import asyncio
import contextlib
import logging
from os import environ

import websockets
from web3 import AsyncWeb3, WebsocketProviderV2

import telegram.error
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

CHAT_ID = ""
CHAT_ID = environ.get("CHAT_ID", CHAT_ID)
TOKEN = ""
TOKEN = environ.get("BOT_TOKEN", TOKEN)
WSS_URL = "wss://eth.drpc.org"
WSS_URL = environ.get("WSS_URL", WSS_URL)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("telegram.ext.Application").setLevel(logging.DEBUG)
logging.getLogger("web3").setLevel(logging.WARNING)

application = ApplicationBuilder().token(TOKEN).build()

STOP_EVENT = asyncio.Event()


def signal_handler(self, sig, frame):
    logger.info("Caught signal: %s", sig)
    STOP_EVENT.set()


async def asend_message(message):
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
    except telegram.error.RetryAfter:
        logger.info(message)


# Deactivated signals b/c I'm on windows
# signal.signal(signal.SIGINT, signal_handler)


async def create_subscription(event_type, event_params):
    while not STOP_EVENT.is_set():
        logger.info("Stop_event is not set. Creating subscription...")
        stop_task = asyncio.create_task(STOP_EVENT.wait())
        subscription_task = asyncio.create_task(_create_subscription(event_type, event_params))
        done, pending = await asyncio.wait(
            (subscription_task, stop_task), return_when=asyncio.FIRST_COMPLETED
        )
        with contextlib.suppress(asyncio.CancelledError):
            for task in pending:
                task.cancel()

        if stop_task in done:
            logger.debug("Subscription retry loop %s was cancelled", event_type)
            break


async def _create_subscription(event_type, event_params):
    async for w3_socket in AsyncWeb3.persistent_websocket(WebsocketProviderV2(WSS_URL)):
        subscription_id = await w3_socket.eth.subscribe(event_type, event_params)
        logger.debug("Subscribed to %s, subscription_id: %s", event_type, subscription_id)

        try:
            async for response in w3_socket.ws.process_subscriptions():
                logger.debug("%s", response)
                await asyncio.sleep(0.5)
                if STOP_EVENT.is_set():
                    await w3_socket.eth.unsubscribe(subscription_id)
                    break
        except (
            websockets.exceptions.ConnectionClosed,
            websockets.exceptions.ConnectionClosedError,
        ) as e:
            logger.debug("Connection closed: %s. Reconnecting...", e)
            await asyncio.sleep(5)  # Wait for 5 seconds before reconnecting
        # asyncio.CancelledError is not a subclass of Exception starting Py3.8, see
        # https://docs.python.org/3.11/library/asyncio-exceptions.html#asyncio.CancelledError
        # Note that there might be more elegant solutions than to simply catch all
        # BaseExceptions, but I would see this rather as a question on the websocket handling,
        # nothing PTB related
        except BaseException as exc:
            logger.debug("Exception in create_subscription: %s", exc, exc_info=exc)
            raise exc


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def run():
    logger.info("Starting...")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    await application.initialize()
    await application.start()

    await application.updater.start_polling(drop_pending_updates=True)
    subs_tasks = set()

    subs_tasks.add(
        application.create_task(
            create_subscription("logs", {"address": "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"})
        )
    )
    subs_tasks.add(
        application.create_task(
            create_subscription("logs", {"address": "0x12d6867fa648d269835cf69b49f125147754b54d"})
        )
    )

    try:
        await STOP_EVENT.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("KeyboardInterrupt or SystemExit caught. Stopping...")
        STOP_EVENT.set()
    except BaseException as exc:
        logger.error("Exception in run: %s", exc, exc_info=exc)
        STOP_EVENT.set()
    finally:
        # Ensure that graceful shutdown is always called
        logger.info("Stopping...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        # after shutdown, the networking backend is no longer available to make requests to TG
        logger.info("Stopped.")


if __name__ == "__main__":
    asyncio.run(run())
