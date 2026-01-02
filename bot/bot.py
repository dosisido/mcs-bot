import asyncio
import datetime
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional, Tuple, Union

import discord
from discord import ui
from mcrcon import MCRcon


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
should_output: bool = False


@dataclass
class VerificationSession:
    member_id: int
    channel_id: int
    minecraft_name: Optional[str] = None
    confirmation_message_id: Optional[int] = None


class MinecraftBot:
    def __init__(
        self,
        token: str,
        channel_id: Union[str, int],
        guild_id: Union[str, int],
        verified_role_id: Union[str, int],
        command_channel_id: Union[str, int],
        rcon_host: str,
        rcon_port: Union[str, int],
        rcon_password: str,
        whitelist_store_path: str,
    ):
        self.__token = token
        self.__channel_id = int(channel_id)
        self.__guild_id = int(guild_id)
        self.__verified_role_id = int(verified_role_id)
        self.__command_channel_id = int(command_channel_id)
        self.__rcon_host = rcon_host
        self.__rcon_port = int(rcon_port)
        self.__rcon_password = rcon_password
        self.__store_path = Path(whitelist_store_path)
        self.__store_path.parent.mkdir(parents=True, exist_ok=True)
        self._mappings: Dict[str, Any] = self._load_mappings()

        self._file_lock = asyncio.Lock()
        self._sessions_by_member: Dict[int, VerificationSession] = {}
        self._sessions_by_channel: Dict[int, VerificationSession] = {}
        self._rcon_lock = asyncio.Lock()

        self._client = discord.Client(intents=intents)
        self._register_events()
    
    async def log_chat(self, player: Optional[str], message: str, chat_message: bool = False) -> None:
        global should_output
        if message.strip() == "RCON running on 0.0.0.0:25575":
            should_output = True
            return
        if not should_output:
            return

        if message.strip() == "Stopping server":
            should_output = False
            return

        if message.strip().startswith("Starting minecraft server"):
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
            if not channel:
                return
            await channel.send(embed=embed, silent=chat_message)
    
    async def logon(self, player: str) -> None:
        global should_output
        should_output = True
        embed = discord.Embed(
            description=f":green_circle: **{player}** has joined the game.",
            color=0x2ecc71 
        )
        avatar_url = f"https://mc-heads.net/avatar/{player}/64"
        embed.set_author(name=player, icon_url=avatar_url)
        async with self.__get_channel() as channel:
            if not channel:
                return
            await channel.send(embed=embed, silent=True)

    async def logoff(self, player: str) -> None:
        embed = discord.Embed(
            description=f":red_circle: **{player}** has left the game.",
            color=0xe74c3c 
        )
        avatar_url = f"https://mc-heads.net/avatar/{player}/64"
        embed.set_author(name=player, icon_url=avatar_url)
        async with self.__get_channel() as channel:
            if not channel:
                return
            await channel.send(embed=embed, silent=True)
    
    @asynccontextmanager
    async def __get_channel(self) -> AsyncIterator[Optional[discord.TextChannel]]:
        await self._client.wait_until_ready()
        channel = self._client.get_channel(self.__channel_id)
        if not isinstance(channel, discord.TextChannel):
            print(f"Error: Channel {self.__channel_id} not found or is not a TextChannel.")
            yield None
            return
        yield channel

    async def __get_guild(self) -> Optional[discord.Guild]:
        await self._client.wait_until_ready()
        guild = self._client.get_guild(self.__guild_id)
        if not guild:
            print(f"Error: Guild {self.__guild_id} not found.")
        return guild

    async def wait_start(self):
        await self._client.wait_until_ready()

    async def start(self):
        await self._client.start(self.__token)

    def _register_events(self) -> None:
        @self._client.event
        async def on_ready():
            print('Bot is ready')
            # await self._announce_start()
            await self._bootstrap_existing_members()

        @self._client.event
        async def on_member_join(member: discord.Member):
            await self._handle_member_join(member)

        @self._client.event
        async def on_message(message: discord.Message):
            await self._handle_message(message)

    async def _announce_start(self) -> None:
        async with self.__get_channel() as channel:
            if channel:
                await channel.send("**Minecraft Bot has started!** :robot:")

    async def _handle_member_join(self, member: discord.Member) -> None:
        await self._ensure_verification(member, welcome=True)

    async def _handle_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self._client.user and message.author.id == self._client.user.id:
            return
        if message.channel.id == self.__command_channel_id:
            await self._handle_command_channel_message(message)
            return
        session = self._sessions_by_channel.get(message.channel.id)
        if not session:
            return
        if message.author.id != session.member_id:
            return

        content = message.content.strip()
        if not session.minecraft_name:
            if not self._is_valid_minecraft_name(content):
                await message.channel.send(
                    "That does not look like a valid Minecraft username. Usernames must be 3-16 characters and contain only letters, numbers, or underscores."
                )
                return
            session.minecraft_name = content
            channel_obj = message.channel
            if not isinstance(channel_obj, discord.TextChannel):
                await message.channel.send(
                    "Verification is unavailable in this channel. Please contact a moderator for assistance."
                )
                return
            await self._prompt_confirmation(channel_obj, session)
            return

        await message.channel.send(
            "Thanks! Use the buttons above to confirm or deny the username, or type a new name to replace it."
        )

    def _is_valid_minecraft_name(self, name: str) -> bool:
        return 3 <= len(name) <= 16 and name.replace('_', '').isalnum()

    async def _prompt_confirmation(self, channel: discord.TextChannel, session: VerificationSession) -> None:
        assert session.minecraft_name
        guild = channel.guild
        if not guild:
            await channel.send("Verification temporarily unavailable. Please contact a moderator.")
            return
        view = self._build_confirmation_view(guild, session)
        embed = discord.Embed(
            description=f"Is **{session.minecraft_name}** your Minecraft username?",
            color=0x2ecc71
        )
        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{session.minecraft_name}/64")
        embed.set_image(url=f"https://mc-heads.net/body/{session.minecraft_name}")
        message = await channel.send(embed=embed, view=view)
        session.confirmation_message_id = message.id

    def _build_confirmation_view(self, guild: discord.Guild, session: VerificationSession) -> ui.View:
        bot = self

        class ConfirmationView(ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            def _disable_items(self) -> None:
                for child in self.children:
                    setattr(child, "disabled", True)

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == session.member_id

            @ui.button(label='Confirm', style=discord.ButtonStyle.success)
            async def confirm(self, interaction: discord.Interaction, _: ui.Button) -> None:
                await interaction.response.defer(ephemeral=True, thinking=True)
                self._disable_items()
                try:
                    if interaction.message:
                        await interaction.message.edit(view=self)
                except discord.HTTPException as exc:
                    print(f"Error disabling confirmation buttons: {exc}")
                try:
                    success, response_message = await bot._process_confirmation(guild, session)
                except Exception as exc:  # pragma: no cover - defensive logging
                    print(f"Error during confirmation for {session.member_id}: {exc}")
                    response_message = f"Verification failed: {exc}"
                    success = False
                try:
                    await interaction.followup.send(response_message, ephemeral=True)
                    print(f"Sent confirmation followup to {session.member_id}")
                except Exception as exc:
                    print(f"Error sending confirmation followup: {exc}")
                if success:
                    bot._client.loop.create_task(bot._post_success_cleanup(session))

            @ui.button(label='Change name', style=discord.ButtonStyle.secondary)
            async def change(self, interaction: discord.Interaction, _: ui.Button) -> None:
                session.minecraft_name = None
                session.confirmation_message_id = None
                self._disable_items()
                await interaction.response.edit_message(view=self)
                channel = guild.get_channel(session.channel_id)
                if isinstance(channel, discord.TextChannel):
                    await channel.send("Okay, please provide the correct Minecraft username.")

            @ui.button(label='Cancel', style=discord.ButtonStyle.danger)
            async def cancel(self, interaction: discord.Interaction, _: ui.Button) -> None:
                self._disable_items()
                try:
                    await interaction.response.edit_message(view=self)
                except discord.HTTPException:
                    pass
                await bot._cancel_verification(session)

        return ConfirmationView()

    async def _process_confirmation(
        self,
        guild: Optional[discord.Guild],
        session: VerificationSession,
    ) -> Tuple[bool, str]:
        print(f"Processing confirmation for member {session.member_id} with name {session.minecraft_name}")
        if not guild:
            return False, "Guild not available, please try again later."
        member = guild.get_member(session.member_id)
        if not member:
            return False, "Could not find your member record."
        if not session.minecraft_name:
            return False, "Please provide a username first."

        try:
            await self._whitelist_player(session.minecraft_name)
        except Exception as exc:
            if str(exc) in (f"Added {session.minecraft_name} to the whitelist", "Player is already whitelisted"):
                pass
            else:
                print(f"Whitelist command failed for {session.minecraft_name}: {exc}")
                return False, f"Failed to run whitelist command: {exc}"

        role = guild.get_role(self.__verified_role_id)
        if role:
            try:
                await member.add_roles(role, reason="Minecraft whitelist verification")
            except discord.HTTPException as exc:
                print(f"Error assigning role to {session.member_id}: {exc}")
        else:
            print(f"Verified role {self.__verified_role_id} not found in guild {guild.id}")

        await self._store_mapping(member.id, session.minecraft_name)
        return True, f"Great! {session.minecraft_name} has been whitelisted. Enjoy the server!"

    async def _post_success_cleanup(self, session: VerificationSession) -> None:
        try:
            print(f"Starting cleanup for member {session.member_id}")
            await self._close_session_channel(
                session,
                "you are all set. This channel will close shortly.",
                mention_member=True,
                close_reason="Verification complete"
            )
            print(f"Cleanup finished for member {session.member_id}")
        except Exception as exc:
            print(f"Cleanup failed for member {session.member_id}: {exc}")

    async def _cancel_verification(self, session: VerificationSession) -> None:
        await self._close_session_channel(
            session,
            "Verification cancelled. Contact a moderator if you need help.",
            mention_member=False,
            close_reason="Verification cancelled"
        )

    def _cleanup_session(self, session: VerificationSession) -> None:
        self._sessions_by_member.pop(session.member_id, None)
        self._sessions_by_channel.pop(session.channel_id, None)

    async def _close_session_channel(
        self,
        session: VerificationSession,
        message: Optional[str],
        *,
        mention_member: bool,
        close_reason: str,
    ) -> None:
        guild = await self.__get_guild()
        if not guild:
            print("Cleanup aborted: guild unavailable")
            return
        raw_channel = guild.get_channel(session.channel_id)
        member = guild.get_member(session.member_id)
        if not raw_channel:
            print(f"Cleanup warning: channel {session.channel_id} missing")
        if raw_channel and not isinstance(raw_channel, discord.TextChannel):
            print(f"Cleanup warning: channel {session.channel_id} is not a TextChannel")
            raw_channel = None

        channel = raw_channel
        if channel:
            if message:
                try:
                    if mention_member and member:
                        await channel.send(f"{member.mention} {message}")
                    else:
                        await channel.send(message)
                except discord.HTTPException as exc:
                    print(f"Error sending final verification message: {exc}")
            await asyncio.sleep(10)
            try:
                await channel.delete(reason=close_reason)
            except discord.HTTPException as exc:
                print(f"Error deleting verification channel: {exc}")
        self._cleanup_session(session)
        print(f"Session cleanup complete for member {session.member_id}")

    def _load_mappings(self) -> Dict[str, Any]:
        if not self.__store_path.exists():
            return {}
        try:
            return json.loads(self.__store_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not load whitelist mapping store: {exc}")
            return {}

    def _member_needs_verification(self, member: discord.Member) -> bool:
        if member.bot:
            return False
        if member.guild.id != self.__guild_id:
            return False
        return str(member.id) not in self._mappings

    async def _bootstrap_existing_members(self) -> None:
        guild = await self.__get_guild()
        if not guild:
            return
        for member in guild.members:
            await self._ensure_verification(member, welcome=False)
            await asyncio.sleep(0.2)

    async def _ensure_verification(self, member: discord.Member, welcome: bool) -> None:
        if not self._member_needs_verification(member):
            return
        role = member.guild.get_role(self.__verified_role_id)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Minecraft whitelist mapping missing")
            except discord.HTTPException as exc:
                print(f"Error removing role from {member.id}: {exc}")
        if member.id in self._sessions_by_member:
            return

        channel = await self._fetch_or_create_verification_channel(member)
        if not channel:
            return

        session = VerificationSession(member_id=member.id, channel_id=channel.id)
        self._sessions_by_member[member.id] = session
        self._sessions_by_channel[channel.id] = session

        intro = (
            f"Welcome {member.mention}! Please reply with your Minecraft username so we can whitelist you."
            if welcome else
            f"Hi {member.mention}, please reply with your Minecraft username so we can whitelist you."
        )
        try:
            await channel.send(intro)
        except discord.HTTPException as exc:
            print(f"Error prompting verification for {member.id}: {exc}")

    async def _fetch_or_create_verification_channel(self, member: discord.Member) -> Optional[discord.TextChannel]:
        guild = member.guild
        if guild.id != self.__guild_id:
            return None

        marker = f"Verification channel for {member.id}"
        existing = next(
            (c for c in guild.text_channels if c.topic == marker and isinstance(c, discord.TextChannel)),
            None
        )
        if existing:
            try:
                await existing.set_permissions(member, view_channel=True, send_messages=True)
                bot_member = guild.me
                if bot_member:
                    await existing.set_permissions(bot_member, view_channel=True, send_messages=True)
            except discord.HTTPException:
                pass
            return existing

        channel_name = f"verify-{member.display_name}-"[:80] + str(member.id)[-6:]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        bot_member = guild.me
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=marker,
                reason="Minecraft whitelist verification"
            )
            return channel
        except discord.HTTPException as exc:
            print(f"Error creating verification channel for {member.id}: {exc}")
            return None

    async def _store_mapping(self, discord_id: int, minecraft_name: str) -> None:
        payload = {
            "discord_id": discord_id,
            "minecraft_name": minecraft_name,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        async with self._file_lock:
            data: Dict[str, Any] = {}
            if self.__store_path.exists():
                try:
                    data = json.loads(self.__store_path.read_text())
                except json.JSONDecodeError:
                    data = {}
            data[str(discord_id)] = payload
            try:
                self.__store_path.write_text(json.dumps(data, indent=2))
                self._mappings = data
                print(f"Stored whitelist mapping for {discord_id} at {self.__store_path}")
                return
            except OSError as exc:
                print(f"Failed to write whitelist mapping store: {exc}")

    async def _whitelist_player(self, minecraft_name: str) -> None:
        response = await self._run_rcon_command(f"whitelist add {minecraft_name}")
        if "whitelisted" not in response.lower() and "already" not in response.lower():
            raise RuntimeError(response)

    async def _handle_command_channel_message(self, message: discord.Message) -> None:
        command = message.content.strip()
        print(f"Received message in channel {message.channel.id} from user {message.author.id}: {command}")
        if not command:
            await message.reply("Please provide a command to execute.", mention_author=False)
            return
        try:
            response = await self._run_rcon_command(command)
        except Exception as exc:
            await message.reply(f"Failed to execute command: {exc}", mention_author=False)
            return

        if not response:
            response = "(no response)"
        if len(response) > 1800:
            response = response[:1800] + "..."

        formatted = f"```\n{response}\n```"
        try:
            await message.reply(formatted, mention_author=False)
        except discord.HTTPException as exc:
            print(f"Error sending RCON response: {exc}")

    async def _run_rcon_command(self, command: str) -> str:
        async with self._rcon_lock:
            await asyncio.sleep(0)
            with MCRcon(self.__rcon_host, self.__rcon_password, port=self.__rcon_port) as connection:
                response = connection.command(command)
            await asyncio.sleep(0)
            return response
