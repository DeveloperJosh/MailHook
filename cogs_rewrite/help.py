from handler import *
from utils.bot import ModMail
from config import PREFIXES


async def get_bot_help(bot: ModMail) -> discord.Embed:
    embed = discord.Embed(
        title="Modmail Help",
        description=f"My prefixes for are: {', '.join(['`'+p+'`' for p in PREFIXES])}\nI recommend using my slash commands.\nIn order to setup this server please use the `/setup` command.",
        color=discord.Color.blurple()
    )
    for cog_name, cog in bot.cogs.items():
        if len(cog.get_commands()) > 0 and cog.qualified_name not in ["Jishaku", "Help"]:
            embed.add_field(
                name=cog.qualified_name,
                value=', '.join([command.qualified_name for command in cog.get_commands()]),
                inline=False
            )
    return embed


async def get_cog_help(cog: commands.Cog) -> discord.Embed:
    return discord.Embed(
        title=f"{cog.qualified_name} Help",
        description='\n'.join([f"`/{c.qualified_name}{' ' + c.signature if c.signature else ''}` - {c.help}" for c in cog.get_commands()]),
        color=discord.Color.blurple()
    )


async def get_command_help(c: commands.Command) -> discord.Embed:
    return discord.Embed(
        title=f"{c.qualified_name.title()} Help",
        description=c.help,
        color=discord.Color.blurple()
    ).add_field(name="Usage:", value=f"```/{c.qualified_name}{' ' + c.signature if c.signature else ''}```")


class Help(commands.Cog):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.command(name="help", help="Get some help.")
    @slash_command(name="help", help="Get some help.")
    async def help(self, ctx: Union[InteractionContext, commands.Context], command: str = None):
        if command is None:
            return await ctx.reply(embed=await get_bot_help(self.bot))
        maybe_cog = self.bot.get_cog(command.lower().title())
        if maybe_cog is not None:
            return await ctx.reply(embed=await get_cog_help(maybe_cog))
        maybe_command = self.bot.get_command(command.lower())
        if maybe_command is not None:
            return await ctx.reply(embed=await get_command_help(maybe_command))
        return await ctx.reply(f"No command named `{command}` found.")


def setup(bot: ModMail):
    bot.add_cog(Help(bot))
