import traceback

import discord
from discord.ext import commands
from handler import InteractionContext
from utils.exceptions import (
    NotSetup, NotStaff, NotAdmin, ModRoleNotFound,
    TicketCategoryNotFound, TranscriptChannelNotFound,
    UserAlreadyInAModmailThread, DMsDisabled, NoBots,
    GuildOnlyPls
)
from utils.bot import ModMail
from typing import Union
from humanfriendly import format_timespan


def e(title: str, desc: str) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=discord.Color.red())


class EphemeralContext(InteractionContext):
    async def reply(self, *args, **kwargs):
        await super().reply(*args, **kwargs, ephemeral=True)


class ErrorHandling(commands.Cog):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.Cog.listener('on_command_error')
    async def on_command_error(self, ctx: Union[commands.Context, InteractionContext], error):
        if isinstance(ctx, InteractionContext):
            ctx = EphemeralContext(ctx, ctx.bot)
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"You are on cooldown for **{format_timespan(round(error.retry_after, 2))}**", delete_after=5)
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            perms = error.missing_permissions
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Nah bro!",
                "You need **{}** perms to run this command.".format(' '.join(error.missing_permissions[0].split('_')).title())
            ))
        elif isinstance(error, commands.BotMissingPermissions):
            perms = error.missing_permissions
            if "embed_links" in perms:
                return await ctx.reply("Please give me embed link perms.")
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} I'm missing permissions!",
                "I need **{}** perms to run this command.".format(' '.join(error.missing_permissions[0].split('_')).title())
            ))
        elif isinstance(error, commands.CheckFailure):
            return
        elif isinstance(error, NotSetup):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Not Setup!",
                f"Looks like the server is not setup for modmail.\nPlease visit [**this link**](https://mail-hook.site/setup/{ctx.guild.id}) to set it up."
            ))
        elif isinstance(error, NotStaff):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Staff Only!",
                "You need to be a staff member to run this command."
            ))
        elif isinstance(error, NotAdmin):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Admin Only!",
                "You need to be an Admin to run this command."
            ))
        elif isinstance(error, ModRoleNotFound):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Not Found!",
                "Uh oh! Looks like the modrole was not found! Maybe the role was deleted.\nPlease use `/edit-config` to set a new one."
            ))
        elif isinstance(error, TicketCategoryNotFound):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Not Found!",
                "Uh oh! Looks like the ticket category was not found! Maybe the category was deleted.\nPlease use `/edit-config` to set a new one."
            ))
        elif isinstance(error, TranscriptChannelNotFound):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Not Found!",
                "Uh oh! Looks like the transcripts channel was not found! Maybe the channel was deleted.\nPlease use `/edit-config` to set a new one."
            ))
        elif isinstance(error, UserAlreadyInAModmailThread):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Already in a modmail thread!",
                f"Hey there, looks like `{error.user}` is already in a different modmail thread either from this server or another server.\nPlease contact them via DMs or some other method."
            ))
        elif isinstance(error, DMsDisabled):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Unable to DM!",
                f"I am unable to dm {error.user} because their DMs are disabled.\nPlease ask them to enable their DMs."
            ))
        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound, commands.ChannelNotFound, commands.RoleNotFound)):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} Not Found!",
                f"I was unable to find: `{error.argument}`"
            ))
        elif isinstance(error, NoBots):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} No Bots!",
                "Sorry, you cannot use this command on bots.\nPlease try it on a human being."
            ))
        elif isinstance(error, GuildOnlyPls):
            await ctx.reply(embed=e(
                f"{self.bot.config.emojis.no} No DMs!",
                "This command cannot be used in DMs."
            ))
        else:
            error_text = "".join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))[:4000]
            print(error_text)
            try:
                await ctx.channel.send(embed=e(
                    f"{self.bot.config.emojis.no} Unknown Error!",
                    f"An unknown error has occurred.\n```{error}```"
                ))
            except Exception:
                await ctx.channel.send(f"An error occured: \n\n```{error}```")
            try:
                await self.bot.get_channel(self.bot.config.logs.cmd_errs).send(embed=e("Unknown Error", f"```py\n{error_text}\n```"))
            except Exception:
                traceback.print_exception(etype=type(error), value=error, tb=error.__traceback__)

    @commands.Cog.listener('on_app_command_error')
    async def on_app_command_error(self, ctx: InteractionContext, error):
        await self.on_command_error(ctx, error)


def setup(bot: ModMail):
    bot.add_cog(ErrorHandling(bot))
