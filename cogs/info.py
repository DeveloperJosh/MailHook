import time
from handler import *
from utils.bot import ModMail
from cogs.error_handler import EphemeralContext


class Info(commands.Cog):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.command(name="github", help="The github repo to my source code.")
    @slash_command(name="github", help="The github repo to my source code.")
    async def github(self, ctx: Union[commands.Context, InteractionContext]):
        await ctx.reply(embed=discord.Embed(title="Github", description="Star the code on [github](https://github.com/DeveloperJosh/MailHook/) it means a lot", color=discord.Color.blurple()))

    @commands.command(name="credits", help="Credits to our contributors and helpers!")
    @slash_command(name="credits", help="Credits to our contributors and helpers!")
    async def credits(self, ctx: Union[commands.Context, InteractionContext]):
        embed = discord.Embed(title="Credits", color=discord.Color.blurple()).set_footer(text="The code for this bot was made by Blue.#1270")
        embed.add_field(name="Owner", value="`Blue.#1270`", inline=False)
        embed.add_field(name="Developer(s)", value="`Nirlep_5252_#9798`", inline=False)
        embed.add_field(name="Helper(s)", value="`SylmFox#2643`", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="ping", help="Pong!")
    @slash_command(name="ping", help="Pong!")
    async def ping(self, ctx: Union[commands.Context, InteractionContext]):
        api_ping = round(self.bot.latency * 1000, 2)
        db_base_time = time.perf_counter()
        await self.bot.mongo.get_user_modmail_thread(69420)
        db_ping = round((time.perf_counter() - db_base_time) * 1000, 2)
        base_time = time.perf_counter()
        msg = await ctx.reply("Pinging...")
        msg = msg or await ctx.original_message()
        await msg.edit(content="UwU!~", embed=discord.Embed(
            title="Pong!",
            description=f"""
**API Ping:** {api_ping}ms
**Bot Ping:** {round((time.perf_counter() - base_time) * 1000, 2)}ms
**DB Ping:** {db_ping}ms
""",
            color=discord.Color.blurple()
        ))


def setup(bot):
    bot.add_cog(Info(bot))
