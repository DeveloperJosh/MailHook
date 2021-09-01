import logging

import discord
from discord.ext import commands
import asyncio

import random
from utils.database import db
from config import TICKET_CATEGORY, GUILD_ID, STAFF_ROLE, MEMBER_ROLE, WELCOME_CHANNEL


class modmail(commands.Cog, description="Yes"):
    def __init__(self, bot):
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

    @commands.Cog.listener('on_message')
    async def modmail_channel(self, message):
        guild = self.bot.get_guild(GUILD_ID)
        e = db.modmail_collection.find_one({"guild_id": guild.id, "channel_user": message.author.id})
        if message.author.bot:
         return

         if guild.get_member(message.author.id) is None:
           return

        if type(message.channel) is discord.DMChannel:
         if e is None: 
          category = self.bot.get_channel(TICKET_CATEGORY)
          overwrites = {message.author: discord.PermissionOverwrite(read_messages=True), guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.get_role(STAFF_ROLE): discord.PermissionOverwrite(read_messages=True),}
          channel = await guild.create_text_channel(name=f'ticket-{random.randint(0,1000)}', category=category, overwrites=overwrites, topic=message.author.id)
          files = [await attachment.to_file() for attachment in message.attachments]
          await channel.send(f"<@&{STAFF_ROLE}> {message.author.name} ({message.author.id}) has opened a ticket")
          await channel.send(f"`{message.author.name}`: {message.content}", files=files)
          db.modmail_collection.insert_one({"_id": channel.id, "guild_id": guild.id, "channel_user": message.author.id})
          await message.channel.send("Our Staff will be with you soon!")
         else:
            r = db.modmail_collection.find_one({"guild_id": guild.id, "channel_user": message.author.id})
            channel = self.bot.get_channel(r['_id'])
            files = [await attachment.to_file() for attachment in message.attachments]
            await channel.send(f"`{message.author.name}`: {message.content}", files=files)
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
        await user.send(f"`{ctx.author.name}`: {message_reply}")
        await ctx.message.delete()
        await ctx.send(f"`{ctx.author.name}`: {message_reply}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def areply(self, ctx, *, message_reply=None):
      if message_reply is None:
          await ctx.send('You need to add text')
      else:
        user = self.bot.get_user(int(ctx.channel.topic))
        await user.send(f"`Staff Member`: {message_reply}")
        await ctx.message.delete()
        await ctx.send(f"`Staff Member`: {message_reply}")


    @close.error
    async def close_error(self, ctx: commands.Context, error: commands.CommandError):

        if isinstance(error, commands.ConversionError):
            message = str(error)
        else:
            print(f'{str(error)}')
            message = "This is not a ticket channel"

        await ctx.send(message)

    @reply.error
    async def reply_error(self, ctx: commands.Context, error: commands.CommandError):

        if isinstance(error, commands.ConversionError):
            message = str(error)
        else:
            print(f'{str(error)}')
            message = "This is not a ticket channel"

        await ctx.send(message)

def setup(bot):
    bot.add_cog(modmail(bot=bot))