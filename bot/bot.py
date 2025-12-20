import discord
from typing import *
import datetime
from contextlib import asynccontextmanager


intents = discord.Intents.default()
intents.message_content = True
should_output = False


class MinecraftBot:
    def __init__(self, token, channel_id):
        self.__token = token
        self.__channel_id = int(channel_id)
        self._client = discord.Client(intents=intents)
    
    async def log_chat(self, player: Optional[str], message: str, chat_message = False):
        global should_output
        if message.strip() == "RCON running on 0.0.0.0:25575":
            should_output = True
            return
        if not should_output: return

        if message.strip() == "Stopping server":
            should_output = False
            return


        embed = discord.Embed(
            description=f"_<{datetime.datetime.now().strftime('%H:%M:%S')}>_ - **{message}**",
            color= 0xe67a23 if chat_message else 0xffff00 if "advancement" in message else 0xcc0000
        )

        if player:
            avatar_url = f"https://mc-heads.net/avatar/{player}/64"
            embed.set_author(name=player, icon_url=avatar_url)

        async with self.__get_channel() as channel:
            await channel.send(embed=embed, silent=chat_message)
    
    async def logon(self, player: str):
        global should_output
        should_output = True
        embed = discord.Embed(
            description=f":green_circle: **{player}** has joined the game.",
            color=0x2ecc71 
        )
        avatar_url = f"https://mc-heads.net/avatar/{player}/64"
        embed.set_author(name=player, icon_url=avatar_url)
        async with self.__get_channel() as channel:
            await channel.send(embed=embed, silent=True)

    async def logoff(self, player: str):
        embed = discord.Embed(
            description=f":red_circle: **{player}** has left the game.",
            color=0xe74c3c 
        )
        avatar_url = f"https://mc-heads.net/avatar/{player}/64"
        embed.set_author(name=player, icon_url=avatar_url)
        async with self.__get_channel() as channel:
            await channel.send(embed=embed, silent=True)
    
    @asynccontextmanager
    async def __get_channel(self) -> AsyncGenerator[discord.TextChannel, None]:
        await self._client.wait_until_ready()
        channel = self._client.get_channel(self.__channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            yield channel
        else:
            print(f"Error: Channel {self.__channel_id} not found or is not a TextChannel.")

    async def wait_start(self):
        await self._client.wait_until_ready()

    async def start(self):
        @self._client.event
        async def on_ready():
            print(f'Bot is ready')

        await self._client.start(self.__token)
