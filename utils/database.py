import discord
import motor.motor_asyncio as motor
from utils.exceptions import NotSetup, UserAlreadyInAModmailThread
from typing import Optional


class Database:
    def __init__(self, url: str):
        self.cluster = motor.AsyncIOMotorClient(url)
        self.db = self.cluster['cluster0']
        self.guild_data = self.db['guild_data']
        self.modmail_data = self.db['modmail_data']

    async def get_guild_data(self, guild_id: int) -> Optional[dict]:
        data = await self.guild_data.find_one({"_id": guild_id})
        if data is None:
            raise NotSetup()
        return data

    async def set_guild_data(self, guild_id: int, **kwargs):
        return await self.guild_data.update_one(
            filter={"_id": guild_id},
            update={"$set": kwargs},
            upsert=True
        )

    async def get_user_modmail_thread(self, user_id: int) -> Optional[dict]:
        return await self.modmail_data.find_one({"_id": user_id})

    async def get_channel_modmail_thread(self, channel_id: int) -> Optional[dict]:
        return await self.modmail_data.find_one({"channel_id": channel_id})

    async def set_user_modmail_thread(self, user_id: int, **kwargs):
        if (await self.get_user_modmail_thread(user_id)) is None:
            return await self.modmail_data.update_one(
                filter={"_id": user_id},
                update={"$set": kwargs},
                upsert=True
            )
        else:
            raise UserAlreadyInAModmailThread(discord.Object(id=user_id))

    async def delete_user_modmail_thread(self, user_id: int):
        return await self.modmail_data.delete_one({"_id": user_id})
