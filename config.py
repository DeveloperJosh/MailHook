import discord
from discord.ext import commands

TICKET_CATEGORY=882235464583626795
GUILD_ID=781601403432992818
STAFF_ROLE=856186043131756564
STAFF_EMOJI='<:staff:878346853857501184>'
PREFIXES=['<', '?']
STATUS='My Dms'

async def get_cog_help(cog, context):
    cog = context.bot.get_cog(cog)

    embed = discord.Embed(title=f"{cog.qualified_name.title()} Category", color=discord.Color.blurple())

    cmd_info = ""
    cmds = cog.get_commands()

    for info in cmds:
        cmd_info += f"`{context.clean_prefix}{info.name}`\n"

    embed.description = f"To get info help, please use `{context.clean_prefix}help <command>`\n\n**Description:**\n`{cog.description}`\n\n**Commands:**\n{cmd_info}"

    return embed

class MyHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        help_reply = self.context
        embed = discord.Embed(title="help command", color=discord.Color.blurple())
        embed.set_thumbnail(url=self.context.bot.user.avatar.url)
        embed.set_footer(text=f"Requested by {self.context.author}", icon_url=self.context.author.avatar.url)
        embed.add_field(name="Prefix", value=f"`{help_reply.clean_prefix}`", inline=False)
        for cog, cmds in mapping.items():
         if cog is not None and cog.qualified_name.lower() == cog.qualified_name:
              value = f', {help_reply.clean_prefix}'.join([cmd.name for cmd in cmds])
              if len(cmds) != 0:
                if cog.qualified_name == 'nsfw' and not self.context.channel.is_nsfw():
                     pass
                else:
                 embed.add_field(
                    name=f"{cog.qualified_name.title()} [ `{len(cmds)}` ]",
                    value=f"{help_reply.clean_prefix}{value}",
                    inline=False
                    )
              else:
                pass

        await help_reply.send(embed=embed)

    async def send_command_help(self, command):
        help_command = self.context.send
        embed = discord.Embed(title="Command Information", color=discord.Color.blurple())
        embed.add_field(name="Usage", value=f"```{self.get_command_signature(command)}```")
        alias = command.aliases
        des = command.help
        time = command._buckets._cooldown
        if alias:
            embed.add_field(name="Aliases", value=f"```{alias}```", inline=False)
        if des:
            embed.add_field(name="Description", value=f"```{des}```", inline=False)
        if time:
            embed.add_field(name="Cooldown", value=f"```{time.per} seconds```", inline=False)
        await help_command(embed=embed)


    async def send_cog_help(self, cog):
        help_cog = self.context
        await help_cog.send(embed=await get_cog_help(cog.qualified_name, help_cog))
