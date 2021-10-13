import discord
from discord.ext import commands
from utils.bot import ModMail
from typing import Optional, Dict, Union
from utils.exceptions import UserAlreadyInAModmailThread
from io import BytesIO
from uuid import uuid4


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

    # Creating the ticket `file`
    channel = bot.get_channel(channel_id)
    text = ""
    all_msgs = await channel.history(limit=None).flatten()
    for msg in all_msgs[::-1]:
        content = msg.content.replace("\n\n", "\n‎\n")
        text += f"{msg.author} | {channel.name[7:] if len(str(msg.author).split('#')) == 3 else msg.author.id} | {msg.id} | {content}\n\n"

    # Generating an ID for the ticket and sending the file in secret channel for storing it lolll
    randomly_generator_id = str(uuid4())
    transcript_db_channel = bot.get_channel(bot.config.transcript_db_channel)
    msg = await transcript_db_channel.send(file=discord.File(BytesIO(text.encode("utf-8")), filename=f"{channel.name}.txt"))

    # Storing the ticket ID and ticket-user ID in the database
    data = guild_data or await bot.mongo.get_guild_data(guild_id)
    ticket_transcripts = data.get("ticket_transcripts", {})
    ticket_transcripts[randomly_generator_id] = {
        "user_id": int(channel.name[7:]),
        "message_id": msg.id,
    }
    await bot.mongo.set_guild_data(guild_id, ticket_transcripts=ticket_transcripts)

    # Sending the link and the file copy in the guild transcripts channel
    guild_transcripts_channel = bot.get_channel(data['transcripts'])
    if guild_transcripts_channel is not None:
        await guild_transcripts_channel.send(content=f"You can view this ticket here: https://mail-hook.site/viewticket/{guild_id}/{randomly_generator_id}", file=discord.File(BytesIO(text.encode("utf-8")), filename=f"{channel.name}.txt"))
