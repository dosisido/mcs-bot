import asyncio
import os
import re
from typing import Callable, Awaitable


from bot import MinecraftBot
from listener import start_subscriber

TOKEN = os.getenv('DISCORD_BOT_TOKEN') or ''
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID') or ''
GUILD_ID = os.getenv('DISCORD_GUILD_ID') or ''
VERIFIED_ROLE_ID = os.getenv('DISCORD_VERIFIED_ROLE_ID') or ''
COMMAND_CHANNEL_ID = os.getenv('DISCORD_COMMAND_CHANNEL_ID') or ''
RCON_HOST = os.getenv('RCON_HOST') or ''
RCON_PORT = os.getenv('RCON_PORT') or ''
RCON_PASSWORD = os.getenv('RCON_PASSWORD') or ''
WHITELIST_STORE_PATH = os.getenv('WHITELIST_STORE_PATH') or '/data/discord_mappings.json'
HOST = '0.0.0.0'
PORT = 9999




def process_line(minecraft_bot: MinecraftBot) -> Callable[[str], Awaitable[None]]:

    async def inner(line: str):
        print(f"Received Line: {line}")
        line = line.strip()
        match = re.search(r"\[Server thread/INFO\]: <(\w+)> (.*)", line)
        if match:
            username = match.group(1)
            message = match.group(2)
            # print(f"Verified Chat -> {username}: {message}")
            try:
                await minecraft_bot.log_chat(username, message, True)
            except Exception as e:
                print(f"Error logging chat: {e}")
            return
        
        match = re.search(r"\[Server thread/INFO\]: (\w+) joined the game", line)
        if match:
            username = match.group(1)
            try:
                await minecraft_bot.logon(username)
            except Exception as e:
                print(f"Error logging chat: {e}")
            return
    
        match = re.search(r"\[Server thread/INFO\]: (\w+) left the game", line)
        if match:
            username = match.group(1)
            try:
                await minecraft_bot.logoff(username)
            except Exception as e:
                print(f"Error logging chat: {e}")
            return

        match = re.search(r"\[Server thread/INFO\]: ([\w ]+)", line)
        if match:
            ignore_messages = [
                "lost connection: Disconnected",
                "logged in with entity id",
                "Server empty for "
            ]

            message = line.split("[Server thread/INFO]:")[-1].strip()
            if not( message.startswith('[') and message.endswith(']')) and all(ignore not in message for ignore in ignore_messages):
                try:
                    await minecraft_bot.log_chat(None, message, False)
                except Exception as e:
                    print(f"Error logging chat: {e}")
                return

    return inner


async def main():
    required_env = {
        'DISCORD_BOT_TOKEN': TOKEN,
        'DISCORD_CHANNEL_ID': CHANNEL_ID,
        'DISCORD_GUILD_ID': GUILD_ID,
        'DISCORD_VERIFIED_ROLE_ID': VERIFIED_ROLE_ID,
        'DISCORD_COMMAND_CHANNEL_ID': COMMAND_CHANNEL_ID,
        'RCON_HOST': RCON_HOST,
        'RCON_PORT': RCON_PORT,
        'RCON_PASSWORD': RCON_PASSWORD,
    }

    missing = [name for name, value in required_env.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    minecraft_bot = MinecraftBot(
        TOKEN,
        CHANNEL_ID,
        GUILD_ID,
        VERIFIED_ROLE_ID,
        COMMAND_CHANNEL_ID,
        RCON_HOST,
        RCON_PORT,
        RCON_PASSWORD,
        WHITELIST_STORE_PATH,
    )

    bot = minecraft_bot.start()

    await asyncio.gather(
        bot,
        start_subscriber(HOST, PORT, process_line(minecraft_bot))
    )

if __name__ == "__main__":
    asyncio.run(main())