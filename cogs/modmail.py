import discord
from discord.ext import commands
from typing import Union, Optional, Dict
from handler import slash_command, user_command, InteractionContext
from handler import SlashCommandOption as Option
from handler import SlashCommandChoice as Choice
from cogs.error_handler import EphemeralContext
from utils.exceptions import GuildOnlyPls, NotAdmin, NotSetup, NoBots, NotStaff, ModRoleNotFound, TicketCategoryNotFound, DMsDisabled
from utils.bot import ModMail
from utils.ui import ServersDropdown, ServersDropdownView, Confirm
from utils.message import wait_for_msg
from utils.tickets_core import start_modmail_thread, get_webhook, prepare_transcript, send_modmail_message
from utils.converters import SettingConverter


dropdown_concurrency = []


class Mailhook(commands.Cog, name="Mail Hook"):
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
            return await ctx.reply(embed=discord.Embed(
                title=f"{self.bot.config.emojis.yes} Already Setup!",
                description="Hey, looks like this server is already setup.\nPlease use `/show-config` to view the configuration.",
                color=discord.Color.blurple()
            ))
        except NotSetup:
            pass
        final = {}
        main_msg = await ctx.reply(embed=discord.Embed(
            title=f"{self.bot.config.emojis.loading} Modmail setup!",
            description="Please enter a staff role.\nThis will be the role that will be able to access modmail channels and use the modmail commands.",
            color=discord.Color.blurple()
        ))
        main_msg = main_msg or await ctx.original_message()
        staff_role_msg = await wait_for_msg(ctx, 60, main_msg)
        if staff_role_msg is None:
            return
        try:
            staff_role = await commands.RoleConverter().convert(ctx, staff_role_msg.content)
            if staff_role.position >= ctx.guild.me.top_role.position:
                return await main_msg.edit(content=f"{self.bot.config.emojis.no} Hey, that role seems to be above my top role.\n> Please give me a higher role and try again.", embed=None)
            final.update({"staff_role": staff_role.id})
        except commands.RoleNotFound:
            return await main_msg.edit(content=f"{self.bot.config.emojis.no} That doesn't seem like a role.\n> Please re-run the command and try again.", embed=None)
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            staff_role: discord.PermissionOverwrite(read_messages=True)
        }
        await main_msg.edit(embed=discord.Embed(
            title=f"{self.bot.config.emojis.loading} Modmail setup!",
            description="Please enter a category channel.\nThis will be the modmail category under which the modmail channels will be created.",
            color=discord.Color.blurple()
        ))
        category_msg = await wait_for_msg(ctx, 60, main_msg)
        if category_msg is None:
            return
        try:
            category = await commands.CategoryChannelConverter().convert(ctx, category_msg.content)
            final.update({"category": category.id})
        except commands.ChannelNotFound:
            return await main_msg.edit(f"{self.bot.config.emojis.no} I wasn't able to find that category.\n> Please re-run the command and try again.")
        try:
            await category.edit(overwrites=overwrites)
            transcripts = await category.create_text_channel('transcripts', topic="Modmail transcripts will be saved here.", overwrites=overwrites)
        except discord.Forbidden:
            return await main_msg.edit(embed=discord.Embed(
                title=f"{self.bot.config.emojis.no} I don't have permission to create channels.",
                description="I need the `Manage Channels` permission to create channels.\nPlease give me this permission and try again.",
                color=discord.Color.red()
            ))
        final.update({"transcripts": transcripts.id})
        await self.bot.mongo.set_guild_data(ctx.guild.id, **final)
        await main_msg.edit(embed=discord.Embed(
            title=f"{self.bot.config.emojis.yes} Setup complete.",
            color=discord.Color.blurple()
        ))

    @commands.command(name='edit-config', help="Edit the current modmail configuration.")
    @slash_command(name='edit-config', help="Edit the current modmail configuration.", options=[
        Option(name="setting", type=3, description="Please select what you want to edit.", required=True, choices=[
            Choice(name='Transcript Channel', value='transcripts_channel'),
            Choice(name="Staff Role", value='staff_role'),
            Choice(name='Modmail Category', value='category')
        ])
    ])
    async def edit_config(self, ctx: Union[InteractionContext, commands.Context], setting: Optional[SettingConverter] = None):
        if not ctx.guild:
            raise GuildOnlyPls()
        if not ctx.author.guild_permissions.administrator:
            raise NotAdmin()
        if setting is None:
            return await ctx.reply(f"Please tell me what to edit!\nYour options: `transcripts_channel`, `staff_role`, `category`\nCorrect Usage: `{ctx.clean_prefix}edit-config <setting>`")
        await self.bot.mongo.get_guild_data(ctx.guild.id)
        main_msg = await ctx.reply(f"Editing {setting.replace('_', '').title()}\n\nPlease enter a new value for it...")
        main_msg = main_msg or await ctx.original_message()
        new_msg = await wait_for_msg(ctx, 60, main_msg)
        if not new_msg:
            return
        if setting == 'transcripts_channel':
            try:
                final = await commands.TextChannelConverter().convert(ctx, new_msg.content)
            except Exception:
                return await main_msg.edit(f"I wasn't able to find any channel named `{new_msg.content}`\nPlease try again.")
        elif setting == 'staff_role':
            try:
                final = await commands.RoleConverter().convert(ctx, new_msg.content)
            except Exception:
                return await main_msg.edit(f"I wasn't able to find any role named `{new_msg.content}`\nPlease try again.")
        else:
            try:
                final = await commands.CategoryChannelConverter().convert(ctx, new_msg.content)
            except Exception:
                return await main_msg.edit(f"I wasn't able to find any category named `{new_msg.content}`\nPlease try again.")
        wew = {setting.replace("_channel", ""): final.id}
        await self.bot.mongo.set_guild_data(ctx.guild.id, **wew)
        return await main_msg.edit(content="Updated!\nPlease use `/show-config` to see the new config.")

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
        if message.author.id in self.bot.mongo.blacklist_cache:
            return
        if message.guild is not None:
            return
        ctx = await self.bot.get_context(message)
        if ctx.command is not None:
            return
        modmail_thread = await self.bot.mongo.get_user_modmail_thread(message.author.id)
        if modmail_thread is None:
            mutual_guilds = message.author.mutual_guilds
            final_mutual_guilds: Dict[discord.Guild, dict] = {}
            for guild in mutual_guilds:
                try:
                    guild_data = await self.bot.mongo.get_guild_data(guild.id)
                    final_mutual_guilds.update({guild: guild_data})
                except NotSetup:
                    pass
            if len(final_mutual_guilds) == 0:
                return
            if len(final_mutual_guilds) == 1:
                for g in final_mutual_guilds:
                    final_guild = g
            else:
                view = ServersDropdownView()
                select = ServersDropdown(list(final_mutual_guilds))
                view.add_item(select)
                main_msg = await message.channel.send("Hey looks like you want to start a modmail thread.\nIf so, please select a server you want to contact and continue.", view=view)
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
            if message.author.id in dropdown_concurrency:
                dropdown_concurrency.remove(message.author.id)
            channel = await start_modmail_thread(self.bot, final_guild.id, message.author.id)
            role = final_guild.get_role(final_mutual_guilds[final_guild]['staff_role'])
            await channel.send(
                f"{role.mention if role is not None else 'Hey moderators,'} {message.author.mention} has opened a modmail thread.",
                allowed_mentions=discord.AllowedMentions.all()
            )
            await channel.send(
                f"""
All the messages you type here, will be sent to this user's DMs.
If you want to ignore a message you can start it with {' or '.join(['`' + p + '`' for p in self.bot.config.prefixes])}
                """
            )
        else:
            channel = self.bot.get_channel(modmail_thread['channel_id'])
        if channel is None:
            await message.channel.send("Looks like the modmail thread no longer exists.\nPlease send the message again to start a new one.")
            return await self.bot.mongo.delete_user_modmail_thread(message.author.id)
        await send_modmail_message(self.bot, channel, message)
        await message.add_reaction('✔️')

    @commands.Cog.listener('on_message')
    async def modmail_reply(self, message: discord.Message):
        if message.author.bot:
            return
        if message.author.id in self.bot.mongo.blacklist_cache:
            return
        if message.guild is None:
            return
        if message.content.startswith(tuple([p for p in self.bot.config.prefixes])):
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

    @commands.command(name='anon-reply', help="Reply anonymously to a ticket.")
    @slash_command(name="anon-reply", help="Reply anonymously to a ticket.")
    async def areply(self, ctx: InteractionContext, message: str):
        if not ctx.guild:
            raise GuildOnlyPls()
        guild_data = await self.bot.mongo.get_guild_data(ctx.guild.id)
        if ctx.guild.get_role(guild_data['staff_role']) not in ctx.author.roles:
            raise NotStaff()
        if isinstance(ctx, InteractionContext):
            ctx = EphemeralContext(ctx, self.bot)
        ticket_data = await self.bot.mongo.get_channel_modmail_thread(ctx.channel.id)
        if ticket_data is None:
            return await ctx.reply("This doesn't look like an active modmail thread.\nPlease use `/modmail-tickets` to view all the modmail threads.")
        user = self.bot.get_user(ticket_data['_id'])
        try:
            await user.send(message, embed=discord.Embed().set_author(name="Anonymous reply.").set_footer(text=f"Server: {ctx.guild.name}"))
            await send_modmail_message(self.bot, ctx.channel, message, anon=True)
            if isinstance(ctx, commands.Context):
                await ctx.message.delete()
            else:
                await ctx.reply("Message sent!")
        except Exception as e:
            await ctx.reply(f"Unable to send message due to error: `{e}`")

    @commands.Cog.listener('on_message')
    async def prefix_reply(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.lower() not in [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]:
            return
        prefixes = self.bot.config.prefixes.copy()
        if not message.guild:
            return await message.reply(f"My prefixes are: {', '.join(['`' + p + '`' for p in prefixes])}")
        data = await self.bot.mongo.get_guild_data(message.guild.id, raise_error=False)
        data = data or {}
        guild_prefixes = data.get('prefixes', [])
        if not guild_prefixes:
            return await message.reply(f"My prefixes are: {', '.join(['`' + p + '`' for p in prefixes])}")
        await message.reply(f"My prefixes are: {', '.join(['`' + p + '`' for p in guild_prefixes])}")

    @commands.group(name="prefix", help="Manage the prefixes for the bot.")
    async def prefix(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            g = await self.bot.mongo.get_guild_data(ctx.guild.id, raise_error=False)
            if g is None:
                g = {}
            prefixes = g.get("prefixes", self.bot.config.prefixes.copy())
            return await ctx.reply(f"Your current prefixes are: {', '.join(['`' + prefix + '`' for prefix in prefixes])}\nYou can use the following commands to manage them:\n\n- `{ctx.clean_prefix}prefix add <prefix>`\n- `{ctx.clean_prefix}prefix remove <prefix>`")

    @prefix.command(name="add", help="Add a prefix to the bot.")
    async def prefix_add(self, ctx: commands.Context, *, prefix: str = None):
        if prefix is None:
            return await ctx.reply(f"{self.bot.config.emojis.no} Please specify a prefix to add.")
        g = await self.bot.mongo.get_guild_data(ctx.guild.id, raise_error=False)
        if g is None:
            g = {}
        prefixes = g.get("prefixes", self.bot.config.prefixes.copy())
        if len(prefixes) >= 10:
            return await ctx.reply(f"{self.bot.config.emojis.no} You can only have 10 prefixes.")
        if prefix in prefixes:
            return await ctx.reply(f"{self.bot.config.emojis.no} This prefix is already added.")
        prefixes.append(prefix)
        await self.bot.mongo.set_guild_data(ctx.guild.id, prefixes=prefixes)
        await ctx.reply(f"{self.bot.config.emojis.yes} Added `{prefix}` to your prefixes.")

    @prefix.command(name="remove", help="Remove a prefix from the bot.")
    async def prefix_remove(self, ctx: commands.Context, *, prefix: str = None):
        if prefix is None:
            return await ctx.reply(f"{self.bot.config.emojis.no} Please specify a prefix to remove.")
        g = await self.bot.mongo.get_guild_data(ctx.guild.id, raise_error=False)
        if g is None:
            g = {}
        prefixes = g.get("prefixes", self.bot.config.prefixes.copy())
        if prefix not in prefixes:
            return await ctx.reply(f"{self.bot.config.emojis.no} This prefix is not added.")
        if len(prefixes) == 1:
            return await ctx.reply(f"{self.bot.config.emojis.no} You cannot remove the last prefix.\nPlease add another one and then remove this one.")
        prefixes.remove(prefix)
        await self.bot.mongo.set_guild_data(ctx.guild.id, prefixes=prefixes)
        await ctx.reply(f"{self.bot.config.emojis.yes} Removed `{prefix}` from your prefixes.")


def setup(bot: ModMail):
    bot.add_cog(Mailhook(bot))
