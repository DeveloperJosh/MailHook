import discord
from discord.ext import commands
from utils.bot import ModMail
from typing import Optional, Dict, Union
from utils.exceptions import UserAlreadyInAModmailThread
from io import BytesIO


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


async def send_modmail_message(bot: ModMail, channel: discord.TextChannel, message: Union[discord.Message, str], anon: bool = False):
    webhook = await get_webhook(bot, channel.id)
    embeds = [discord.Embed(
        title=sticker.name,
        url=sticker.url,
        color=discord.Color.blurple(),
        description=f"Sticker ID: `{sticker.id}`"
    ).set_image(url=sticker.url) for sticker in (message.stickers if isinstance(message, discord.Message) else [])]
    await webhook.send(
        content=message.content if isinstance(message, discord.Message) else message,
        username=(f"{message.author}" if not anon else "Anonymous Reply") if isinstance(message, discord.Message) else "Anonymous Reply",
        avatar_url=(message.author.display_avatar.url if not anon else bot.user.display_avatar.url) if isinstance(message, discord.Message) else bot.user.display_avatar.url,
        files=[await attachment.to_file() for attachment in message.attachments] if isinstance(message, discord.Message) else [],
        allowed_mentions=discord.AllowedMentions.none(),
        embeds=embeds
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


async def prepare_transcript(bot: ModMail, channel_id: int, guild_id: int, guild_data: Optional[dict] = None):
    channel = bot.get_channel(channel_id)
    data = guild_data or await bot.mongo.get_guild_data(guild_id)
    transcript_channel = bot.get_channel(data['transcripts'])
    if transcript_channel is None:
        return
    text = ""
    all_msgs = await channel.history(limit=None).flatten()
    for msg in all_msgs[::-1]:
        content = msg.content.replace("\n\n", "\n‎\n")
        # TODO: attachments and stickers
        text += f"{msg.author} | {channel.name[7:] if len(str(msg.author).split('#')) == 3 else msg.author.id} | {msg.id} | {content}\n\n"
    file = discord.File(BytesIO(text.encode("utf-8")), filename=f"{channel.name}.txt")
    msg = await transcript_channel.send(content=channel.name[7:], file=file)
    await transcript_channel.send(f"You can view this ticket at https://mail-hook.site/tickets/{msg.guild.id}/{msg.channel.id}/{msg.id}")
