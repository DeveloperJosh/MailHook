from handler import *
from utils.bot import ModMail


class Info(commands.Cog):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.command(name="github", help="The github repo to my source code.")
    @slash_command(name="github", help="The github repo to my source code.")
    async def github(self, ctx: Union[commands.Context, InteractionContext]):
        await ctx.reply(embed=discord.Embed(title="Github", description="Star the code on [github](https://github.com/DeveloperJosh/Fish-Mail) it means a lot", color=discord.Color.blurple()))

    @commands.command(name="credits", help="Credits to our contributors and helpers!")
    @slash_command(name="credits", help="Credits to our contributors and helpers!")
    async def credits(self, ctx: Union[commands.Context, InteractionContext]):
        embed = discord.Embed(title="Credits", color=discord.Color.blurple()).set_footer(text="The code for this bot was made by Blue.#1270")
        embed.add_field(name="Code Developer(s)", value="`Blue.#1270`", inline=False)
        embed.add_field(name="Helper(s)", value="`Nirlep_5252_#9798, SylmFox#3635`", inline=False)
        await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(Info(bot))
