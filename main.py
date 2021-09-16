from handlers.slash import SlashContext, slash_command, slash_handler, update_app_commands
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from config import STAFF_EMOJI, MyHelp, PREFIXES, STATUS


intents = discord.Intents(messages=True, guilds=True, reactions=True, members=True, presences=True)
bot = commands.Bot(
    owner_ids=[321750582912221184, 558861606063308822],
    command_prefix=PREFIXES,
    intents=intents,
    case_insensitive=True,
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=True, users=True, replied_user=True),
    strip_after_prefix=True,
    help_command=MyHelp()
)
logging.basicConfig(level=logging.INFO)
bot.load_extension('jishaku')

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


@bot.event
async def on_ready():
    logging.info(' __________________________________________________ ')
    logging.info('|                                                  |')
    logging.info('|                 Bot has Started                  |')
    logging.info('|                                                  |')
    logging.info('+__________________________________________________+')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=STATUS))

async def interaction_event(interaction):
    await slash_handler(interaction, bot)

async def connect_event():
    await update_app_commands(bot)

bot.add_listener(interaction_event, 'on_interaction')
bot.add_listener(connect_event, 'on_connect')

load_dotenv('.env')

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_SECRET'))
