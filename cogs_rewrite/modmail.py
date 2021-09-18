from handler import slash_command, user_command
from handler import SlashCommandOption as Option
from utils.exceptions import *
from utils.ui import *
from utils.message import wait_for_msg
from utils.tickets_core import *


dropdown_concurrency = []


class ModMailCog(commands.Cog, name="MailHook"):
    def __init__(self, bot: ModMail):
        self.bot = bot

    @commands.command(help="Setup modmail for your server.")
    @commands.bot_has_permissions(administrator=True)
    @slash_command(help="Setup modmail for your server.")
    async def setup(self, ctx: Union[InteractionContext, commands.Context]):
        if not ctx.guild:
            raise GuildOnlyPls()
        if not ctx.author.guild_permissions.administrator:
            raise NotAdmin()
        try:
            await self.bot.mongo.get_guild_data(ctx.guild.id)
            return await ctx.reply("Hey, looks like this server is already setup.\nPlease use `/show-config` to view the configuration.")
        except NotSetup:
            pass
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

    @commands.command(name='show-config', help="Get the current config.")
    @slash_command(name='show-config', help="Get the current config.")
    async def show_config(self, ctx: Union[InteractionContext, commands.Context]):
        if not ctx.guild:
            raise GuildOnlyPls()
        guild_data = await self.bot.mongo.get_guild_data(ctx.guild.id)
        staff_role = ctx.guild.get_role(guild_data['staff_role'])
        if staff_role is None:
            raise ModRoleNotFound()
        transcript_channel = ctx.guild.get_channel(guild_data['transcripts'])
        category = ctx.guild.get_channel(guild_data['category'])
        if category is None:
            raise TicketCategoryNotFound()
        embed = discord.Embed(color=discord.Color.blurple(), title="Modmail Configuration!")
        embed.add_field(name="Staff Role:", value=staff_role.mention)
        embed.add_field(name="Transcript Channel:", value=transcript_channel.mention if transcript_channel is not None else "No transcript channel. [Not Recommended]")
        embed.add_field(name="Category:", value=category.name)
        await ctx.reply(embed=embed)

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
        if not ctx.guild:
            raise GuildOnlyPls()
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

    @commands.command(name="close-ticket", help="Close this ticket.")
    @slash_command(name="close-ticket", help="Close this ticket.")
    async def close(self, ctx: Union[commands.Context, InteractionContext], channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if not ctx.guild:
            raise GuildOnlyPls()
        guild_data = await self.bot.mongo.get_guild_data(ctx.guild.id)
        if ctx.guild.get_role(guild_data['staff_role']) not in ctx.author.roles:
            raise NotStaff()
        ticket_data = await self.bot.mongo.get_channel_modmail_thread(channel.id)
        if ticket_data is None:
            return await ctx.reply("This doesn't look like an active modmail thread.\nPlease use `/modmail-tickets` to view all the modmail threads.")
        await self.bot.mongo.delete_channel_modmail_thread(channel.id)
        await prepare_transcript(self.bot, channel.id, ctx.guild.id, guild_data)
        await channel.delete()
        user = self.bot.get_user(ticket_data['_id'])
        if channel != ctx.channel:
            await ctx.reply("Ticket closed.")
        if user is not None:
            await user.send("This modmail thread has been closed by a staff member.")

    @commands.command(name='modmail-tickets', help="View all the current modmail tickets.")
    @slash_command(name='modmail-tickets', help="View all the current modmail tickets.")
    async def modmail_tickets(self, ctx: Union[commands.Context, InteractionContext]):
        if not ctx.guild:
            raise GuildOnlyPls()
        guild_data = await self.bot.mongo.get_guild_data(ctx.guild.id)
        if ctx.guild.get_role(guild_data['staff_role']) not in ctx.author.roles:
            raise NotStaff()
        modmail_threads = await self.bot.mongo.get_guild_modmail_threads(ctx.guild.id)
        embed = discord.Embed(
            title="Modmail Threads",
            description="Here are the current modmail threads:" if len(modmail_threads) != 0 else "No modmail threads are open.",
            color=discord.Color.blurple()
        )
        for thread in modmail_threads:
            channel = self.bot.get_channel(thread['channel_id'])
            user = self.bot.get_user(thread['_id'])
            embed.add_field(
                name=f"{user if user is not None else thread['_id']}",
                value=channel.mention if channel is not None else thread['channel_id'],
                inline=True
            )
        return await ctx.reply(embed=embed)

    @commands.Cog.listener('on_message')
    async def modmail_dm(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is not None:
            return
        ctx = await self.bot.get_context(message)
        if ctx.command is not None:
            return
        modmail_thread = await self.bot.mongo.get_user_modmail_thread(message.author.id)
        if modmail_thread is None:
            mutual_guilds = message.author.mutual_guilds
            if len(mutual_guilds) == 0:
                final_guild = mutual_guilds[0]
            else:
                view = ServersDropdownView()
                select = ServersDropdown(mutual_guilds)
                view.add_item(select)
                main_msg = await message.channel.send(f"Hey looks like you want to start a modmail thread.\nIf so, please select a server you want to contact and continue.", view=view)
                dropdown_concurrency.append(message.author.id)
                await view.wait()
                if not view.yes:
                    return await main_msg.delete()
                final_guild = self.bot.get_guild(int(view.children[2].values[0]))
                await main_msg.edit(view=None)
            confirm = Confirm(ctx, 60)
            m = await message.channel.send(f"Are you sure you want to send this message to {final_guild.name}'s staff?", view=confirm)
            await confirm.wait()
            if not confirm.value:
                return await m.delete()
            await m.edit(view=None)
            dropdown_concurrency.remove(message.author.id)
            channel = await start_modmail_thread(self.bot, final_guild.id, message.author.id)
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
        ctx = await self.bot.get_context(message)
        if ctx.command is not None:
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
        embeds = [discord.Embed().set_author(name=message.author, icon_url=message.author.display_avatar.url
                                             ).set_footer(text=f"Server: {message.guild.name}")]
        for sticker in message.stickers:
            embeds.append(discord.Embed(
                title=sticker.name,
                url=sticker.url,
                color=discord.Color.blurple(),
                description=f"Sticker ID: `{sticker.id}`"
            ).set_image(url=sticker.url))
        await ticket_user.send(
            message.content,
            files=[await attachment.to_file() for attachment in message.attachments],
            embeds=embeds
        )
        await message.add_reaction('✔️')


def setup(bot: ModMail):
    bot.add_cog(ModMailCog(bot))
