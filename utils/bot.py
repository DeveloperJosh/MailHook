from __future__ import annotations
import os
from typing import List
import discord
import logging
from dotenv import load_dotenv
from discord.ext import commands
from config import Config
from utils.database import Database
from handler import InteractionClient


class ModMail(commands.AutoShardedBot):
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        load_dotenv('.env')
        self.config = Config()
        super().__init__(
            command_prefix=self.fetch_prefix,
            intents=discord.Intents.all(),
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            strip_after_prefix=True,
            activity=discord.Activity(type=discord.ActivityType.watching, name=self.config.status),
            help_command=None
        )
        self.app_client = InteractionClient(self)
        self.mongo = Database(os.getenv('DATABASE_LINK'))
        self.load_extension("jishaku")
        self.load_cogs("./cogs")
        self.add_check(self.blacklist_check)
        self.add_listener(self.connect_listener, 'on_connect')

    def load_cogs(self, path: str):
        i = 0
        for filename in os.listdir(path):
            if filename.endswith(".py"):
                self.load_extension(f"{path[2:]}.{filename[:-3]}")
                i += 1
        logging.info(f"Loaded {i} cogs from \"{path}\"")

    def run(self) -> None:
        super().run(os.getenv('DISCORD_BOT_SECRET'))

    async def on_ready(self):
        print("""
  __  __       _ _ _    _             _
 |  \/  |     (_) | |  | |           | |
 | \  / | __ _ _| | |__| | ___   ___ | | __
 | |\/| |/ _` | | |  __  |/ _ \ / _ \| |/ /
 | |  | | (_| | | | |  | | (_) | (_) |   <
 |_|  |_|\__,_|_|_|_|  |_|\___/ \___/|_|\_\\


        """)
        print(f"Logged in as {self.user}")
        print(f"Connected to: {len(self.guilds)} guilds")
        print(f"Connected to: {len(self.users)} users")
        print(f"Connected to: {len(self.cogs)} cogs")
        print(f"Connected to: {len(self.commands)} commands")
        print(f"Connected to: {len(self.emojis)} emojis")
        print(f"Connected to: {len(self.voice_clients)} voice clients")
        print(f"Connected to: {len(self.private_channels)} private_channels")

    async def blacklist_check(self, ctx: commands.Context) -> bool:
        if ctx.author.id in self.mongo.blacklist_cache:
            return False
        return True

    async def connect_listener(self):
        await self.mongo.get_blacklist_cache()

    async def fetch_prefix(self, bot: ModMail, message: discord.Message) -> List[str]:
        prefixes = [f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "]
        if message.guild is None:
            prefixes.extend(self.config.prefixes)
            return prefixes
        data = await self.mongo.get_guild_data(message.guild.id, raise_error=False)
        guild_prefixes = data.get('prefixes', self.config.prefixes)
        prefixes.extend(guild_prefixes)
        return prefixes
