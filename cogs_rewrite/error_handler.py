import traceback
from discord.ext import commands
from handler import InteractionContext
from utils.exceptions import *
from utils.bot import ModMail
from humanfriendly import format_timespan


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
        elif isinstance(error, NotSetup):
            await ctx.reply("Looks like the server is not setup for modmail.\nPlease use `/setup` to set it up.")
        elif isinstance(error, NotStaff):
            await ctx.reply("You need to be a staff member to run this command.")
        elif isinstance(error, NotAdmin):
            await ctx.reply("You need to be an Admin to run this command.")
        elif isinstance(error, ModRoleNotFound):
            await ctx.reply("Uh oh! Looks like the modrole was not found!\nMaybe the role was deleted.\nPlease use `/edit` to edit one of the configurations.")
        elif isinstance(error, TicketCategoryNotFound):
            await ctx.reply("Uh oh! Looks like the ticket category was not found!\nMaybe the category was deleted.\nPlease use `/edit` to edit one of the configurations.")
        elif isinstance(error, TranscriptChannelNotFound):
            await ctx.reply("Uh oh! Looks like the transcripts channel was not found!\nMaybe the channel was deleted.\nPlease use `/edit` to edit one of the configurations.")
        elif isinstance(error, UserAlreadyInAModmailThread):
            await ctx.reply(f"Hey there, looks like `{error.user}` is already in a different modmail thread either from this server or another server.\nPlease contact them via DMs or some other method.")
        elif isinstance(error, DMsDisabled):
            await ctx.reply(f"I am unable to dm {error.user} because their DMs are disabled.\nPlease ask them to enable their DMs.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply(f"I was unable to find the member: `{error.argument}`")
        elif isinstance(error, commands.UserNotFound):
            await ctx.reply(f"I was unable to find the user: `{error.argument}`")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.reply(f"I was unable to find the channel: `{error.argument}`")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.reply(f"I was unable to find the role: `{error.argument}`")
        elif isinstance(error, NoBots):
            await ctx.reply("Sorry, you cannot use this command on bots.\nPlease try it on a human being.")
        elif isinstance(error, GuildOnlyPls):
            await ctx.reply("This command cannot be used in DMs.")
        else:
            traceback.print_exception(etype=type(error), value=error, tb=error.__traceback__)

    @commands.Cog.listener('on_app_command_error')
    async def on_app_command_error(self, ctx: InteractionContext, error):
        await self.on_command_error(ctx, error)


def setup(bot: ModMail):
    bot.add_cog(ErrorHandling(bot))
