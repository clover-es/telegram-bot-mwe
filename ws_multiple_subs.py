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

    async def process_subscriptions(self):
        async for self.w3_socket in AsyncWeb3(WebSocketProvider(self.wss_url)):
            print(f"process subs {self.w3_socket}")
            try:
                async for message in self.w3_socket.socket.process_subscriptions():
                    print(f"{message=}")
                    try:
                        self.callbacks[message['subscription']](message['result'])
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

    async def subscribe(self, callback: callable,
                        event_type: SubscriptionType, **event_params):
        if self.w3_socket is not None:
            sub_id = await self.w3_socket.eth.subscribe(event_type, event_params)
            print(f"Subscribed to {sub_id}")
            self.callbacks[sub_id] = callback
        else:
            raise RuntimeError("Websocket connection not established, it's not possible to subscribe")

    async def unsubscribe(self, sub_id: HexStr):
        if self.w3_socket is not None:
            await self.w3_socket.eth.unsubscribe(sub_id)
            self.callbacks.pop(sub_id)
        else:
            raise RuntimeError("Websocket connection not established, it's not possible to unsubscribe")

    def is_connected(self):
        print(f"{self.w3_socket=}")
        return self.w3_socket is not None


def callback_logs(message):
    print(f"New log received: {message}")

def callback_heads(message):
    print(f"New header received: {message}")

async def main():
    subs_handler = SubscriptionHandler("wss://eth.drpc.org")
    sub_task = asyncio.create_task(subs_handler.process_subscriptions())
    while not subs_handler.is_connected():
        await asyncio.sleep(1)
    await subs_handler.subscribe(callback_logs, 'logs', address='0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc')
    await subs_handler.subscribe(callback_heads, 'newHeads')
    try:
        while True:
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        sub_task.cancel()
        await sub_task

if __name__ == '__main__':
    asyncio.run(main())
