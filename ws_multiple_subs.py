import asyncio

from typing import Dict

from eth_typing import HexStr
from web3 import AsyncWeb3, WebSocketProvider
from web3.types import SubscriptionType
from websockets import ConnectionClosedError, ConnectionClosed


class SubscriptionHandler:
    w3_socket: AsyncWeb3 = None
    # Dictionary containing callbacks for each subscription id
    callbacks: Dict[HexStr, callable] = {}

    def __init__(self, wss_url):
        self.wss_url = wss_url

    async def process_subscriptions(self) -> None:
        """
        Performs the websocket connection and processes the subscriptions and calls the callbacks
        :return: None
        """
        async for self.w3_socket in AsyncWeb3(WebSocketProvider(self.wss_url)):
            try:
                async for message in self.w3_socket.socket.process_subscriptions():
                    try:
                        self.callbacks[message["subscription"]](message["result"])
                    except ValueError as e:
                        try:
                            print(f"Callback for {message['subscription']} not found")
                        except ValueError as e:
                            print(f"Unexpected response from RPC: {e}")
            except (ConnectionClosedError, ConnectionClosed) as e:
                continue
            except asyncio.CancelledError:
                print("Cancelling subscriptions")
                for sub_id in self.callbacks.keys():
                    await self.w3_socket.eth.unsubscribe(sub_id)
                break

    async def subscribe(
        self, callback: callable, event_type: SubscriptionType, **event_params
    ) -> HexStr:
        """
        Subscribes to the given event type with the given callback.
        Must be called while process_subscriptions() task is running

        :param callback: The function to call when the event is received
        :param event_type: The event type to subscribe to
        :param event_params: Additional parameters to pass to the subscription
        :return: The subscription ID
        """
        if self.is_connected():
            sub_id = await self.w3_socket.eth.subscribe(event_type, event_params)
            print(f"Subscribed to {sub_id}")
            self.callbacks[sub_id] = callback
            return sub_id
        else:
            raise RuntimeError(
                "Websocket connection not established, it's not possible to subscribe"
            )

    async def unsubscribe(self, sub_id: HexStr) -> None:
        """
        Unsubscribes from a subscription identified by sub_id.
        Must be called while process_subscriptions() task is running

        :param sub_id: The subscription ID to unsubscribe from
        :return: None
        """
        if self.is_connected():
            await self.w3_socket.eth.unsubscribe(sub_id)
            self.callbacks.pop(sub_id)
        else:
            raise RuntimeError(
                "Websocket connection not established, it's not possible to unsubscribe"
            )

    def is_connected(self) -> bool:
        return self.w3_socket is not None


def callback_logs(message):
    print(f"New log received: {message}")


def callback_heads(message):
    print(f"New header received: {message}")


async def main():
    subs_handler = SubscriptionHandler("wss://eth.drpc.org")
    # Connects to the RPC wss
    sub_task = asyncio.create_task(subs_handler.process_subscriptions())
    # Waits for the connection to be established
    while not subs_handler.is_connected():
        await asyncio.sleep(1)
    # Subscribes to desired events
    await subs_handler.subscribe(
        callback_logs, "logs", address="0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
    )
    new_heads_id = await subs_handler.subscribe(callback_heads, "newHeads")
    try:
        await asyncio.sleep(10)
        # Unsubscribe from new heads after 10 seconds (test unsubscribe)
        await subs_handler.unsubscribe(new_heads_id)
        while True:
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        sub_task.cancel()
        await sub_task


if __name__ == "__main__":
    asyncio.run(main())
