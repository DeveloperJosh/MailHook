import discord
from discord.ext import commands
from typing import Union, Optional, List


class PaginatorView(discord.ui.View):
    def __init__(self, ctx: commands.Context, embeds: List[discord.Embed]):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.embeds = embeds
        self.current = 0

    async def edit(self, msg, pos):
        em = self.embeds[pos]
        em.set_footer(text=f"Page: {pos+1}/{len(self.embeds)}")
        await msg.edit(embed=em)

    @discord.ui.button(emoji='◀️', style=discord.ButtonStyle.blurple)
    async def bac(self, b, i):
        if self.current == 0:
            return
        await self.edit(i.message, self.current - 1)
        self.current -= 1

    @discord.ui.button(emoji='⏹️', style=discord.ButtonStyle.blurple)
    async def stap(self, b, i):
        await i.message.delete()

    @discord.ui.button(emoji='▶️', style=discord.ButtonStyle.blurple)
    async def nex(self, b, i):
        if self.current + 1 == len(self.embeds):
            return
        await self.edit(i.message, self.current + 1)
        self.current += 1

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message("Not your command ._.", ephemeral=True)


class Confirm(discord.ui.View):
    def __init__(self, context: commands.Context, timeout: Optional[int] = 300, user: Optional[Union[discord.Member, discord.User]] = None):
        super().__init__(timeout=timeout)
        self.value = None
        self.context = context
        self.user = user or self.context.author

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, b, i):
        self.value = True
        self.stop()

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def no(self, b, i):
        self.value = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("You cannot interact in other's commands.", ephemeral=True)
            return False
        return True


class ServersDropdown(discord.ui.Select):
    def __init__(self, servers: List[discord.Guild]):
        options = [discord.SelectOption(label=server.name, value=str(server.id), description=f"Server ID: {server.id}") for server in servers]
        super().__init__(placeholder="Please select a guild to start a modmail thread with.", options=options, row=0)


class ServersDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.yes = False

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.blurple, row=1)
    async def c(self, b, i):
        if not self.children[2].values:
            return await i.response.send_message("Please select a server first.", ephemeral=True)
        self.yes = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def c_(self, b, i):
        self.stop()
