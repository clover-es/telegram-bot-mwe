# telegram-bot-mwe
Minimal working example for PTB and web3.py subscriptions.

# Instructions
* Fill `CHAT_ID` and `BOT_TOKEN` constants at `main.py` or system environment
* Install `requirements.txt`
* Run `main.py`

# The problem
## python-telegram-bot v21.1.1
Eventually (normally less than 5 minutes and depending on RPC stability) some RPC connection will fail and the following exception will throw:
```
Fetching updates got a asyncio.CancelledError. Ignoring as this task may onlybe closed via `Application.stop`.
```
The update handler will stop working.

## [python-telegram-bot@handle-system-exit branch](https://github.com/python-telegram-bot/python-telegram-bot/tree/handle-system-exit)

* Uninstall previous version: `pip uninstall python-telegram-bot`
* Install new: `pip install git+https://github.com/python-telegram-bot/python-telegram-bot.git@handle-system-exit`

Eventually (normally less than 5 minutes and depending on RPC stability) some RPC connection will fail and the following exception will throw:
```
Traceback (most recent call last):
  File "/mnt/c/Users/guill/PycharmProjects/telegram-bot-mwe/main.py", line 97, in <module>
    asyncio.run(run())
  File "/usr/lib/python3.12/asyncio/runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/mnt/c/Users/guill/PycharmProjects/telegram-bot-mwe/main.py", line 87, in run
    await asyncio.gather(*subs_tasks, return_exceptions=True)
asyncio.exceptions.CancelledError
Task exception was never retrieved
future: <Task finished name='Task-21' coro=<WebsocketProviderV2._ws_message_listener() done, defined at /home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/web3/providers/websocket/websocket_v2.py:212> exception=ConnectionClosedError(None, Close(code=<CloseCode.INTERNAL_ERROR: 1011>, reason='keepalive ping timeout'), None)>
Traceback (most recent call last):
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 1301, in close_connection
    await self.transfer_data_task
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 963, in transfer_data
    message = await self.read_message()
              ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 1033, in read_message
    frame = await self.read_data_frame(max_size=self.max_size)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 1108, in read_data_frame
    frame = await self.read_frame(max_size)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 1165, in read_frame
    frame = await Frame.read(
            ^^^^^^^^^^^^^^^^^
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/framing.py", line 68, in read
    data = await reader(2)
           ^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/streams.py", line 752, in readexactly
    await self._wait_for_data('readexactly')
  File "/usr/lib/python3.12/asyncio/streams.py", line 545, in _wait_for_data
    await self._waiter
asyncio.exceptions.CancelledError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/web3/providers/websocket/websocket_v2.py", line 236, in _ws_message_listener
    raise e
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/web3/providers/websocket/websocket_v2.py", line 223, in _ws_message_listener
    async for raw_message in self._ws:
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 498, in __aiter__
    yield await self.recv()
          ^^^^^^^^^^^^^^^^^
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 568, in recv
    await self.ensure_open()
  File "/home/clover/.virtualenvs/telegram-bot-mwe/lib/python3.12/site-packages/websockets/legacy/protocol.py", line 948, in ensure_open
    raise self.connection_closed_exc()
websockets.exceptions.ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received

Process finished with exit code 1
```
The whole application will stop working.