import asyncio
from typing import Callable, Awaitable


async def start_subscriber(host: str, port: int, process_line: Callable[[str], Awaitable[None]]):
    async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        print(f"--- Minecraft Server Connected from {addr} ---")
        buffer = ""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    print("--- Minecraft Server Disconnected ---")
                    break
                buffer += data.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    await process_line(line)
        except Exception as e:
            print(f"Connection Error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle_connection, host, port)
    print(f"Listening for Minecraft data on {port}...")
    async with server:
        await server.serve_forever()

