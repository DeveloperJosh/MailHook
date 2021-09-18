import os
import discord
import logging
from dotenv import load_dotenv
from discord.ext import commands
from config import PREFIXES, STATUS
from utils.database import Database
from handler import InteractionClient


class ModMail(commands.AutoShardedBot):
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        load_dotenv('.env')
        super().__init__(
            command_prefix=commands.when_mentioned_or(*PREFIXES),
            intents=discord.Intents.all(),
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            strip_after_prefix=True,
            activity=discord.Activity(type=discord.ActivityType.watching, name=STATUS),
            help_command=None
        )
        self.app_client = InteractionClient(self)
        self.mongo = Database(os.getenv('DATABASE_LINK'))
        self.load_extension("jishaku")
        self.load_cogs("./cogs_rewrite")

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

___________.__       .__         _____         .__.__   
\_   _____/|__| _____|  |__     /     \ _____  |__|  |  
 |    __)  |  |/  ___/  |  \   /  \ /  \\__  \ |  |  |  
 |     \   |  |\___ \|   Y  \ /    Y    \/ __ \|  |  |__
 \___  /   |__/____  >___|  / \____|__  (____  /__|____/
     \/            \/     \/          \/     \/         

        """)
        print(f"Logged in as {self.user}")
        print(f"Connected to: {len(self.guilds)} guilds")
        print(f"Connected to: {len(self.users)} users")
        print(f"Connected to: {len(self.cogs)} cogs")
        print(f"Connected to: {len(self.commands)} commands")
        print(f"Connected to: {len(self.emojis)} emojis")
        print(f"Connected to: {len(self.voice_clients)} voice clients")
        print(f"Connected to: {len(self.private_channels)} private_channels")
