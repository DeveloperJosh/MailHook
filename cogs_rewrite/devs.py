from handler import *
from utils.bot import ModMail


class Devs(commands.Cog):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.group()
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context):
        p = ctx.clean_prefix
        if ctx.invoked_subcommand is None:
            return await ctx.reply(f"Usage: `{p}blacklist add/remove @user [reason]`")

    @blacklist.command()
    @commands.is_owner()
    async def add(self, ctx: commands.Context, user: discord.Member = None, *, reason: str = None):
        if user is None:
            return await ctx.invoke(self.bot.get_command('blacklist'))
        await self.bot.mongo.blacklist(user.id, reason)
        await ctx.message.add_reaction('👌')
        await self.bot.mongo.get_blacklist_cache()

    @blacklist.command()
    @commands.is_owner()
    async def remove(self, ctx: commands.Context, user: discord.Member = None):
        if user is None:
            return await ctx.invoke(self.bot.get_command('blacklist'))
        await self.bot.mongo.unblacklist(user.id)
        await ctx.message.add_reaction('👌')
        await self.bot.mongo.get_blacklist_cache()


def setup(bot: ModMail):
    bot.add_cog(Devs(bot))
