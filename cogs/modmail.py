import logging
import discord
import random
from io import BytesIO
from discord.ext import commands
from utils.database import db
from typing import List, Optional, Union
from config import (
    PREFIXES, TICKET_CATEGORY, GUILD_ID, STAFF_ROLE, STAFF_EMOJI, TRANSCRIPT_CHANNEL
)


class modmail(commands.Cog, description="Yes"):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        self.spam_prevention = commands.CooldownMapping.from_cooldown(6, 10, commands.BucketType.user)
        self.temp_blocked = []

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('ModMail is ready')

    async def get_webhook(self, channel_id: int, user_id: Optional[int] = None) -> discord.Webhook:
        """
        If the channel is not found, a new channel is created and webhook is returned
        Altho, it will only create a new channel if the `user_id` is passed, else it'll just raise the error.
        """
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            if user_id is None:
                raise commands.ChannelNotFound(f"{channel_id}")
            guild = self.bot.get_guild(GUILD_ID)
            category = self.bot.get_channel(TICKET_CATEGORY)
            channel = await guild.create_text_channel(name=f'ticket-{random.randint(0,1000)}', category=category, topic=user_id)
        webhooks: List[discord.Webhook] = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name=f"{self.bot.user.name}", user=self.bot.user)
        if webhook is not None:
            return webhook
        else:
            webhook = await channel.create_webhook(name=f"{self.bot.user.name}")
            return webhook

    async def prepare_transript(self, channel: discord.TextChannel, send: bool = True) -> discord.File:
        all_msgs = await channel.history(limit=None, oldest_first=True).flatten()
        text = ""
        for msg in all_msgs:
            text += f"{msg.author} (UserID: {channel.topic}) (MsgID: {msg.id}) {msg.created_at.strftime('%m/%d/%Y, %H:%M:%S')}: {msg.content}\n\n"
        file = discord.File(BytesIO(text.encode("utf-8")), filename=f"{channel.topic}-transcript.txt")
        if send:
            await self.bot.get_channel(TRANSCRIPT_CHANNEL).send(file=file)
        return file

    async def start_ticket(
        self, user_id: int,
        attachments: Optional[List[discord.Attachment]] = [],
        message: Optional[Union[discord.Message, str]] = None,
        custom_msg: str = None
    ) -> None:
        guild = self.bot.get_guild(GUILD_ID)
        user = self.bot.get_user(user_id)
        category = self.bot.get_channel(TICKET_CATEGORY)
        channel = await guild.create_text_channel(name=f'ticket-{random.randint(0,1000)}', category=category, topic=user_id)
        files = [await attachment.to_file() for attachment in attachments]
        webhook = await self.get_webhook(channel.id)
        await webhook.send(f"<@&{STAFF_ROLE}> {user.name} (`{user_id}`) (Account made on `{user.created_at.__format__('%d/%m/%y | %H:%M:%S')}`) has opened a ticket", avatar_url=self.bot.user.display_avatar.url)
        await webhook.send(f"`{user.name}`: {message if isinstance(message, str) else message.content}", avatar_url=self.bot.user.display_avatar.url, files=files)
        db.modmail_collection.insert_one({"_id": channel.id, "guild_id": guild.id, "channel_user": user_id})
        await user.send(custom_msg or "Our Staff will be with you soon!")
        if isinstance(message, discord.Message):
            await message.add_reaction('✅')

    @commands.Cog.listener('on_message')
    async def modmail_channel(self, message: discord.Message):
        if message.author.id in self.temp_blocked:
            return
        bucket = self.spam_prevention.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            msg_ = await message.channel.send("Please stop spamming, your messages will be ignored for the next 15 seconds.")
            self.temp_blocked.append(message.author.id)
            await asyncio.sleep(15)
            self.temp_blocked.remove(message.author.id)
            return await msg_.edit(content="You can now send messages again.")
        guild = self.bot.get_guild(GUILD_ID)
        e = db.modmail_collection.find_one({"guild_id": guild.id, "channel_user": message.author.id})
        b = db.collection.find_one({"_id": message.author.id})
        if message.author.bot:
            return

        if guild.get_member(message.author.id) is None:
            return

        if type(message.channel) is discord.DMChannel:
            if b is not None:
                await message.add_reaction('❌')
                return
            if e is None:
                await self.start_ticket(message.author.id, message.attachments, message)
            else:
                r = db.modmail_collection.find_one({"guild_id": guild.id, "channel_user": message.author.id})
                webhook = await self.get_webhook(r['_id'], message.author.id)
                files = [await attachment.to_file() for attachment in message.attachments]
                await webhook.send(f"`{message.author.name}`: {message.content}", avatar_url=self.bot.user.display_avatar.url, files=files)
                await message.add_reaction('✅')

        else:
            return

    @commands.Cog.listener("on_message")
    async def prefix_reply(self, message: discord.Message):
        if message.author.bot:
            return
        bot_id = self.bot.user.id
        if message.content.lower() in [f'<@{bot_id}>', f'<@!{bot_id}>']:
            prefixes = PREFIXES
            return await message.reply('My prefixes are: ' + ', '.join([f"`{prefix}`" for prefix in prefixes]))

    @commands.command(help="Start a ticket for a user!", aliases=['start-ticket'])
    @commands.has_permissions(manage_messages=True)
    async def start(self, ctx: commands.Context, user: Optional[discord.User] = None):
        if user is None:
            return await ctx.reply("Please mention a valid user.")
        await self.start_ticket(user.id, message=f"Ticket opened by staff: `{ctx.author}`", custom_msg=f"A ticket has been started by a moderator: `{ctx.author}`")
        await ctx.message.add_reaction('✅')

    @commands.command(help='This allows you to close a ticket')
    @commands.has_permissions(manage_messages=True)
    async def close(self, ctx, reason=None):
        e = db.modmail_collection.find_one({"guild_id": ctx.guild.id, "channel_user": int(ctx.channel.topic)})

        if e is None:
            await ctx.send("User has no ticket")

        elif reason is None:
            a = db.modmail_collection.find_one({"guild_id": ctx.guild.id, "channel_user": int(ctx.channel.topic)})
            db.modmail_collection.delete_one(a)
            user = self.bot.get_user(int(ctx.channel.topic))
            await user.send(f"This ticket was closed by `{ctx.author.name}`")
            await self.prepare_transript(ctx.channel)
            await ctx.channel.delete()

        else:
            a = db.modmail_collection.find_one({"guild_id": ctx.guild.id, "channel_user": int(ctx.channel.topic)})
            db.modmail_collection.delete_one(a)
            user = self.bot.get_user(int(ctx.channel.topic))
            await user.send(f"This ticket was closed for `{reason}`")
            await self.prepare_transript(ctx.channel)
            await ctx.channel.delete()

    @commands.command(help='This allows you to reply to a ticket')
    @commands.has_permissions(manage_messages=True)
    async def reply(self, ctx, *, message_reply=None):
        if message_reply is None:
            await ctx.send('You need to add text')
        else:
            user = self.bot.get_user(int(ctx.channel.topic))
            webhook = await self.get_webhook(ctx.channel.id)
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
            await user.send(f"{STAFF_EMOJI}`{ctx.author.name}`: {message_reply}", files=files)
            await ctx.message.delete()
            await webhook.send(f"{STAFF_EMOJI}`{ctx.author.name}`: {message_reply}", avatar_url=self.bot.user.display_avatar.url, files=files)

    @commands.command(help='This does the same as reply but without a username')
    @commands.has_permissions(manage_messages=True)
    async def areply(self, ctx, *, message_reply=None):
        if message_reply is None:
            await ctx.send('You need to add text')
        else:
            user = self.bot.get_user(int(ctx.channel.topic))
            webhook = await self.get_webhook(ctx.channel.id)
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
            await user.send(f"{STAFF_EMOJI}`Staff Member`: {message_reply}", files=files)
            await ctx.message.delete()
            await webhook.send(f"{STAFF_EMOJI}`Staff Member`: {message_reply}", avatar_url=self.bot.user.display_avatar.url, files=files)

    @commands.command(help='Block a user of from using the tickets')
    @commands.has_permissions(administrator=True)
    async def block(self, ctx, member: discord.Member):
        e = db.collection.find_one({"_id": member.id})

        if e is None:
            blacklist = {"_id": member.id}
            db.collection.insert_one(blacklist)
            await member.send(f"You have been blocked from {self.bot.user.name}")
            await ctx.send(f"You have blocked {member.name}")

        else:
            await ctx.send(f"{member.name} is already blocked")

    @commands.command(help='Unblocks a user of the tickets')
    @commands.has_permissions(administrator=True)
    async def unblock(self, ctx, member: discord.Member):
        e = db.collection.find_one({"_id": member.id})

        if e is None:
            await ctx.send(f"{member.name} is not block")

        else:
            a = db.collection.find_one({"_id": member.id})
            db.collection.delete_one(a)
            await member.send(f"You have been unblocked from {self.bot.user.name}")
            await ctx.send(f'{member.name} Has been unblocked')

    @commands.command(help="Credits to our contributors and helpers!")
    async def credit(self, ctx):
        embed = discord.Embed(title="Credits", color=discord.Color.blurple())
        embed.add_field(name="Code Developer(s)", value="`Blue.#1270`", inline=False)
        embed.add_field(name="Helper(s)", value="`Nirlep_5252_#9798, SylmFox#3635`", inline=False)
        embed.set_footer(text="The code for this bot was made by Blue.#1270")
        await ctx.send(embed=embed)

    @commands.command()
    async def github(self, ctx):
        embed = discord.Embed(title="Github", description="Star the code on [github](https://github.com/DeveloperJosh/Fish-Mail) it means a lot", color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @close.error
    async def close_error(self, ctx: commands.Context, error: commands.CommandError):
        message = "This is not a ticket channel"
        await ctx.send(message)

    @reply.error
    async def reply_error(self, ctx: commands.Context, error: commands.CommandError):
        message = "This is not a ticket channel"
        await ctx.send(message)

    @areply.error
    async def areply_error(self, ctx: commands.Context, error: commands.CommandError):
        message = "This is not a ticket channel"
        await ctx.send(message)


def setup(bot):
    bot.add_cog(modmail(bot=bot))
