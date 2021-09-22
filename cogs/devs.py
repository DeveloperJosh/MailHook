import discord
from handler import InteractionContext
from typing import Union
from utils.bot import ModMail
from config import LOG_CHANNELS
from discord.ext import commands


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

    @commands.Cog.listener('on_command')
    async def cmd_logs(self, ctx: Union[commands.Context, InteractionContext]):
        if not ctx.guild:
            return
        channel = self.bot.get_channel(LOG_CHANNELS['cmd_logs'])
        await channel.send(embed=discord.Embed(
            title="Command used:",
            description=f"Command: `{ctx.command.name}`\nSlash?: {'True' if isinstance(ctx, InteractionContext) else 'False'}",
            color=discord.Color.blurple()
        ).set_author(name=f"{ctx.author}", icon_url=ctx.author.display_avatar.url))

    @commands.Cog.listener('on_app_command')
    async def slash_cmd_logs(self, ctx):
        await self.cmd_logs(ctx)

    @commands.Cog.listener('on_guild_join')
    async def on_guild_join(self, guild: discord.Guild):
        send_embed = discord.Embed(
            title="👋 Hey there!",
            description="""
Thanks a lot for inviting me!
You can set me up to collect DMs from members and send them directly to your staff them.
If you are a server admin then please run the `/setup` slash command to get started.

Here are some useful links:

- [Support server](https://discord.gg/TeSHENet9M_)
- [Github](https://github.com/DeveloperJosh/MailHook/)

""",
            color=discord.Color.blurple()
        ).set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
        ).set_thumbnail(url=self.bot.user.display_avatar.url)

        for channel in guild.channels:
            if "general" in channel.name:
                try:
                    return await channel.send(embed=send_embed)
                except Exception:
                    pass

        for channel in guild.channels:
            if "bot" in channel.name or "cmd" in channel.name or "command" in channel.name:
                try:
                    return await channel.send(embed=send_embed)
                except Exception:
                    pass

        for channel in guild.channels:
            try:
                return await channel.send(embed=send_embed)
            except Exception:
                pass


def setup(bot: ModMail):
    bot.add_cog(Devs(bot))
