import discord
from discord.ext import commands
from handler import slash_command, user_command, InteractionContext
from handler import SlashCommandOption as Option
from typing import Union
from utils.bot import ModMail
from utils.exceptions import *
from utils.message import wait_for_msg
from utils.tickets_core import start_modmail_thread, get_webhook, send_modmail_message


class ModMailCog(commands.Cog):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.command(help="Setup modmail for your server.")
    @commands.bot_has_permissions(administrator=True)
    @slash_command(help="Setup modmail for your server.")
    async def setup(self, ctx: Union[InteractionContext, commands.Context]):
        if not ctx.author.guild_permissions.administrator:
            raise NotAdmin()
        final = {}
        main_msg = await ctx.reply(f"Modmail setup!\n\nPlease enter a staff role.\nThis will be the role that will be able to access modmail channels and use the modmail commands.")
        main_msg = main_msg or await ctx.original_message()
        staff_role_msg = await wait_for_msg(ctx, 60, main_msg)
        if staff_role_msg is None:
            return
        try:
            staff_role = await commands.RoleConverter().convert(ctx, staff_role_msg.content)
            if staff_role.position >= ctx.guild.me.top_role.position:
                return await main_msg.edit(content=f"Hey, that role seems to be above my top role.\nPlease give me a higher role and try again.")
            final.update({"staff_role": staff_role.id})
        except commands.RoleNotFound:
            return await main_msg.edit(content=f"That doesn't seem like a role.\nPlease re-run the command and try again.")
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            staff_role: discord.PermissionOverwrite(read_messages=True)
        }
        await main_msg.edit(content=f"Modmail setup!\n\nPlease enter a category channel.\nThis will be the modmail category under which the modmail channels will be created.")
        category_msg = await wait_for_msg(ctx, 60, main_msg)
        if category_msg is None:
            return
        try:
            category = await commands.CategoryChannelConverter().convert(ctx, category_msg.content)
            final.update({"category": category.id})
        except commands.ChannelNotFound:
            return await main_msg.edit(f"I wasn't able to find that category.\nPlease re-run the command and try again.")
        await category.edit(overwrites=overwrites)
        transcripts = await category.create_text_channel('transcripts', topic="Modmail transcripts will be saved here.", overwrites=overwrites)
        final.update({"transcripts": transcripts.id})
        await self.bot.mongo.set_guild_data(ctx.guild.id, **final)
        await main_msg.edit(content="Setup complete.")

    @commands.command(name='start-ticket', help="Start a ticket with a user.")
    @slash_command(
        name="start-ticket", help="Start a ticket with a user.",
        options=[
            Option(name="user", type=6, description="Select a user to start the ticket with.", required=True),
            Option(name="reason", type=3, description="A reason for starting the ticket.", required=False)
        ]
    )
    @user_command(name="Start ticket")
    async def start_ticket(self, ctx: Union[InteractionContext, commands.Context], user: discord.Member = None, *, reason: str = "No reason provided."):
        guild_data = await self.bot.mongo.get_guild_data(ctx.guild.id)
        staff_role = ctx.guild.get_role(guild_data['staff_role'])
        if staff_role is None:
            raise ModRoleNotFound()
        if staff_role not in ctx.author.roles:
            raise NotStaff()
        user = user or ctx.target
        if user is None:
            ctx.command.reset_cooldown(ctx)
            return await ctx.reply(f"Please provide a user.\nCorrect Usage: `{ctx.clean_prefix}start-ticket @user`")
        if user.bot:
            raise NoBots()
        channel = await start_modmail_thread(self.bot, ctx.guild.id, user.id, guild_data)
        webhook = await get_webhook(self.bot, channel.id)
        try:
            await user.send(f"""
Hey there, A modmail ticket has been started by a staff member.

**Staff Member:** {ctx.author.mention}
**Server:** {ctx.guild.name}
**Reason:** {reason}

You can respond to this modmail ticket by messaging here
All your messages will be send to the staff team.
                            """)
        except discord.Forbidden:
            raise DMsDisabled(user)
        await webhook.send(f"📩 {staff_role.mention} A modmail ticket has been opened by staff member: {ctx.author.mention}")
        await ctx.reply(f"Please go to {channel.mention}")

    @commands.Cog.listener('on_message')
    async def modmail_dm(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is not None:
            return
        modmail_thread = await self.bot.mongo.get_user_modmail_thread(message.author.id)
        if modmail_thread is None:
            channel = await start_modmail_thread(self.bot, self.bot.get_guild(884470177176109056).id, message.author.id)
        else:
            channel = self.bot.get_channel(modmail_thread['channel_id'])
        if channel is None:
            await message.channel.send(f"Looks like the modmail thread no longer exists.\nPlease send the message again to start a new one.")
            return await self.bot.mongo.delete_user_modmail_thread(message.author.id)
        await send_modmail_message(self.bot, channel, message)
        await message.add_reaction('✔️')

    @commands.Cog.listener('on_message')
    async def modmail_reply(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if not message.channel.name.startswith("ticket-"):
            return
        try:
            ticket_user = self.bot.get_user(int(message.channel.name[7:]))
            if ticket_user is None:
                return
            modmail_thread = await self.bot.mongo.get_channel_modmail_thread(message.channel.id)
            if modmail_thread is None:
                return
        except ValueError:
            return
        try:
            data = await self.bot.mongo.get_guild_data(message.guild.id)
        except NotSetup:
            return
        if message.guild.get_role(data['staff_role']) not in message.author.roles:
            return
        await ticket_user.send(
            message.content,
            files=[await attachment.to_file() for attachment in message.attachments],
            embed=discord.Embed().set_author(name=message.author, icon_url=message.author.display_avatar.url
                                             ).set_footer(text=f"Server: {message.guild.name}")
        )
        await message.add_reaction('✔️')


def setup(bot: ModMail):
    bot.add_cog(ModMailCog(bot))
