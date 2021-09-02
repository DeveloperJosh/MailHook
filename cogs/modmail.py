import logging
import discord
import random
from discord.ext import commands
from utils.database import db
from typing import List
from config import (
    TICKET_CATEGORY, GUILD_ID, STAFF_ROLE,
    MEMBER_ROLE, WELCOME_CHANNEL, STAFF_EMOJI
)


class modmail(commands.Cog, description="Yes"):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('ModMail is ready')

    @commands.Cog.listener('on_member_join')
    async def welcome(self, member: discord.Member):
        role = member.guild.get_role(MEMBER_ROLE)
        await member.add_roles(role)
        embed = discord.Embed(title="Welcome", description=f"Welcome {member.name} have a great time!", color=discord.Color.blurple())
        channel = self.bot.get_channel(WELCOME_CHANNEL)
        await channel.send(embed=embed)

    async def get_webhook(self, channel_id: int) -> discord.Webhook:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            raise commands.ChannelNotFound(f"{channel_id}")
        webhooks: List[discord.Webhook] = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="Fish Modmail", user=self.bot.user)
        if webhook is not None:
            return webhook
        else:
            webhook = await channel.create_webhook(name="Fish Modmail")
            return webhook

    @commands.Cog.listener('on_message')
    async def modmail_channel(self, message):
        guild = self.bot.get_guild(GUILD_ID)
        e = db.modmail_collection.find_one({"guild_id": guild.id, "channel_user": message.author.id})
        b = db.collection.find_one({"_id": message.author.id})
        if message.author.bot:
            return

        if guild.get_member(message.author.id) is None:
            return

        if type(message.channel) is discord.DMChannel:
            if b is not None:
                return
            if e is None:
                category = self.bot.get_channel(TICKET_CATEGORY)
                channel = await guild.create_text_channel(name=f'ticket-{random.randint(0,1000)}', category=category, topic=message.author.id)
                files = [await attachment.to_file() for attachment in message.attachments]
                webhook = await self.get_webhook(channel.id)
                await webhook.send(f"<@&{STAFF_ROLE}> {message.author.name} ({message.author.id}) has opened a ticket")
                await webhook.send(f"`{message.author.name}`: {message.content}", files=files)
                db.modmail_collection.insert_one({"_id": channel.id, "guild_id": guild.id, "channel_user": message.author.id})
                await message.channel.send("Our Staff will be with you soon!")

            else:
                r = db.modmail_collection.find_one({"guild_id": guild.id, "channel_user": message.author.id})
                webhook = await self.get_webhook(r['_id'])
                files = [await attachment.to_file() for attachment in message.attachments]
                await webhook.send(f"`{message.author.name}`: {message.content}", files=files)
                await message.channel.send("Message sent", delete_after=1)

        else:
            return

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def close(self, ctx):
        e = db.modmail_collection.find_one({"guild_id": ctx.guild.id, "channel_user": int(ctx.channel.topic)})

        if e is None:
            await ctx.send("User has no ticket")

        else:
            a = db.modmail_collection.find_one({"guild_id": ctx.guild.id, "channel_user": int(ctx.channel.topic)})
            db.modmail_collection.delete_one(a)
            user = self.bot.get_user(int(ctx.channel.topic))
            await user.send(f"This ticket was closed by `{ctx.author.name}`")
            await ctx.channel.delete()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def reply(self, ctx, *, message_reply=None):
        if message_reply is None:
            await ctx.send('You need to add text')
        else:
            user = self.bot.get_user(int(ctx.channel.topic))
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
            await user.send(f"{STAFF_EMOJI}`{ctx.author.name}`: {message_reply}", files=files)
            await ctx.message.delete()
            await ctx.send(f"{STAFF_EMOJI}`{ctx.author.name}`: {message_reply}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def areply(self, ctx, *, message_reply=None):
        if message_reply is None:
            await ctx.send('You need to add text')
        else:
            user = self.bot.get_user(int(ctx.channel.topic))
            files = [await attachment.to_file() for attachment in ctx.message.attachments]
            await user.send(f"{STAFF_EMOJI}`Staff Member`: {message_reply}", files=files)
            await ctx.message.delete()
            await ctx.send(f"{STAFF_EMOJI}`Staff Member`: {message_reply}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def block(self, ctx, member: discord.Member):
        e = db.collection.find_one({"_id": member.id})

        if e is None:
            blacklist = {"_id": member.id}
            db.collection.insert_one(blacklist)
            await member.send("You have been blocked you can no longer send messages to the mod mail")
            await ctx.send(f"You have blacklisted {member.name}")

        else:
            await ctx.send(f"{member.name} is already blacklisted")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unblock(self, ctx, member: discord.Member):
        e = db.collection.find_one({"_id": member.id})

        if e is None:
            await ctx.send(f"{member.name} is not blacklisted")

        else:
            a = db.collection.find_one({"_id": member.id})
            db.collection.delete_one(a)
            await member.send("You have been unblocked you can now send messages to the mod mail")
            await ctx.send(f'{member.name} Has been unblacklisted')

    @close.error
    async def close_error(self, ctx: commands.Context, error: commands.CommandError):
        message = "This is not a ticket channel"
        await ctx.send(message)

    @reply.error
    async def reply_error(self, ctx: commands.Context, error: commands.CommandError):
        message = "This is not a ticket channel"
        await ctx.send(message)


def setup(bot):
    bot.add_cog(modmail(bot=bot))
