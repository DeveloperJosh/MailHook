import os
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
            command_prefix=commands.when_mentioned_or(*self.config.prefixes),
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

    async def blacklist_check(self, ctx: commands.Context):
        if ctx.author.id in self.mongo.blacklist_cache:
            return False
        return True

    async def connect_listener(self):
        await self.mongo.get_blacklist_cache()
