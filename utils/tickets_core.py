import discord
from discord.ext import commands
from utils.bot import ModMail
from typing import Optional, Dict
from utils.exceptions import UserAlreadyInAModmailThread


webhook_cache: Dict[int, discord.Webhook] = {}


async def start_modmail_thread(bot: ModMail, guild_id: int, user_id: int, guild_data: Optional[dict] = None) -> Optional[discord.TextChannel]:
    data = guild_data or await bot.mongo.get_guild_data(guild_id)
    user_mail_thread = await bot.mongo.get_user_modmail_thread(user_id)
    if user_mail_thread is not None:
        raise UserAlreadyInAModmailThread(bot.get_user(user_id))
    category = bot.get_channel(data['category'])
    if category is None:
        return
    channel = await category.create_text_channel(f'ticket-{user_id}')
    things = {
        "channel_id": channel.id,
        "guild_id": guild_id,
    }
    await bot.mongo.set_user_modmail_thread(user_id, **things)
    return channel


async def send_modmail_message(bot: ModMail, channel: discord.TextChannel, message: discord.Message):
    webhook = await get_webhook(bot, channel.id)
    await webhook.send(
        content=message.content,
        username=f"{message.author}",
        avatar_url=message.author.display_avatar.url,
        files=[await attachment.to_file() for attachment in message.attachments],
        allowed_mentions=discord.AllowedMentions.none()
    )


async def get_webhook(bot: ModMail, channel_id: int) -> discord.Webhook:
    webhook = webhook_cache.get(channel_id)
    if webhook is None:
        channel = bot.get_channel(channel_id)
        if channel is None:
            raise commands.ChannelNotFound(str(channel_id))
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name=bot.user.name, user=bot.user)
        if webhook is None:
            webhook = await channel.create_webhook(name=bot.user.name, avatar=await bot.user.display_avatar.read())
        webhook_cache[channel_id] = webhook
    return webhook
