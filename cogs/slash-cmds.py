from handlers.slash import SlashContext, slash_command, slash_handler
import logging
import discord
import asyncio
from discord.ext import commands
from utils.database import db
from config import (
    GUILD_ID, STAFF_EMOJI, STAFF_ROLE
)


class slash(commands.Cog, description="Slash commands"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Slash is ready')

    @slash_command(name="credit", help="Credits to our contributors and helpers!", guild_ids=[GUILD_ID])
    async def _credit(self, ctx: SlashContext):
        embed = discord.Embed(title="Credits", color=discord.Color.blurple())
        embed.add_field(name="Code Developer(s)", value="`Blue.#1270`", inline=False)
        embed.add_field(name="Helper(s)", value="`Nirlep_5252_#9798, SylmFox#3635`", inline=False)
        embed.set_footer(text="The code for this bot was made by Blue.#1270")
        await ctx.send(embed=embed)

    @slash_command(name="reply", help="Reply to a ticket", guild_ids=[GUILD_ID])
    async def _reply(self, ctx: SlashContext, arg: str):
        user = self.bot.get_user(int(ctx.channel.topic))
        await user.send(f"{STAFF_EMOJI}`{ctx.author.name}`: {arg}")
        await ctx.reply(f'{STAFF_EMOJI}`{ctx.author.name}`: {arg}')

    @slash_command(name="areply", help="Reply to a ticket without a username", guild_ids=[GUILD_ID])
    async def _areply(self, ctx: SlashContext, arg: str):
        user = self.bot.get_user(int(ctx.channel.topic))
        await user.send(f"{STAFF_EMOJI}`Staff Member`: {arg}")
        await ctx.reply(f'{STAFF_EMOJI}`Staff Member`: {arg}')

    @slash_command(name="start", help="This will start a ticket with a user", guild_ids=[GUILD_ID])
    async def _start(self, ctx: SlashContext):
        role = discord.utils.get(ctx.guild.roles, id=STAFF_ROLE)
        if role in ctx.author.roles:
            await ctx.send("WIP")
        else: #leaving this for you nirlep as the start_ticket shit is not working for me
            await ctx.send(f"You need `{role.name}` role to do that")




def setup(bot):
    bot.add_cog(slash(bot=bot))