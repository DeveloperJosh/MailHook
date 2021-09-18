import discord
from discord.ext import commands


class modmail(commands.Cog, description="Yes"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.spam_prevention = commands.CooldownMapping.from_cooldown(6, 10, commands.BucketType.user)
        self.temp_blocked = []

    @commands.Cog.listener("on_message")
    async def prefix_reply(self, message: discord.Message):
        if message.author.bot:
            return
        bot_id = self.bot.user.id
        if message.content.lower() in [f'<@{bot_id}>', f'<@!{bot_id}>']:
            prefixes = PREFIXES
            return await message.reply('My prefixes are: ' + ', '.join([f"`{prefix}`" for prefix in prefixes]))

    @commands.command(help='This does the same as reply but without a username')
    @commands.has_permissions(manage_messages=True)
    async def areply(self, ctx, *, message_reply=None):
        if message_reply is None:
            await ctx.send('You need to add text')
        else:
            user = self.bot.get_user(int(ctx.channel.topic))
            webhook = await get_webhook(self.bot, ctx.channel.id)
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


def setup(bot):
    bot.add_cog(modmail(bot=bot))
