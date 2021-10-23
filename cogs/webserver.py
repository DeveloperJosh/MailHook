import logging
import asyncio
import discord
import hikari
import aiohttp_cors
import ast
from typing import List
from discord.ext import commands
from utils.bot import ModMail
from aiohttp import web, ClientSession


try:
    import uvloop
    uvloop.install()
except Exception:
    pass


class Guild:
    def __init__(self, id: str, name: str, icon: str, owner: bool, permissions: int, features: List[str], permissions_new: str):
        self.id: str = id
        self.name: str = name
        self.icon: str = icon
        self.owner: bool = owner
        self.permissions: int = permissions
        self.features: List[str] = features
        self.permissions_new: str = permissions_new
        self.invited: bool = False

    def __str__(self) -> str:
        return f"<Guild name='{self.name}' id={self.id}>"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def icon_url(self) -> str:
        return f"https://cdn.discordapp.com/icons/{self.id}/{self.icon}.png" if self.icon is not None else None


class WebServer(commands.Cog):
    def __init__(self, client: ModMail):
        self.client = client
        self.rest_api = hikari.RESTApp()
        self.api = None
        self.BASE = "https://discord.com/api"
        self.REDIRECT_URI = "https://mailhook.netlify.app/callback"
        # self.REDIRECT_URI = "http://localhost:3000/callback"
        self.cors_thing = {
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        }

    def filter_guilds(self, user_guilds: List[Guild], bot_guilds: List[discord.Guild]) -> List[Guild]:
        mutual_guilds: List[Guild] = []
        bot_guild_ids = [g.id for g in bot_guilds]
        for guild in user_guilds:
            if int(guild.id) in bot_guild_ids:
                guild.invited = True
            else:
                guild.invited = False
            mutual_guilds.append(guild)
        return [g for g in mutual_guilds if g.permissions & hikari.Permissions.MANAGE_GUILD]

    async def get_access_token(self, code: str) -> dict:
        async with ClientSession() as session:
            async with session.post(
                f"{self.BASE}/oauth2/token",
                data={
                    "client_id": str(self.client.user.id),
                    "client_secret": self.client.config.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.REDIRECT_URI,
                },
            ) as resp:
                return await resp.json()

    async def get_user(self, token: str) -> hikari.OwnUser:
        async with self.rest_api.acquire(token) as client:
            return await client.fetch_my_user()

    async def get_user_guilds(self, token: str) -> List[Guild]:
        async with ClientSession() as session:
            async with session.get(
                f"{self.BASE}/users/@me/guilds",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                data = await resp.json()
                return [Guild(**g) for g in data]

    async def callback(self, request: web.Request):
        code = (await request.json()).get("code").get("code")
        if code is None:
            raise web.HTTPBadRequest()
        data = await self.get_access_token(code)
        print(data)
        return web.json_response({"access_token": data.get("access_token")})

    async def get_own_user(self, request: web.Request):
        access_token = request.headers.get("access_token")
        if access_token is None:
            raise web.HTTPBadRequest()
        user = await self.get_user(access_token)
        return web.json_response({
            "id": str(user.id),
            "username": user.username,
            "discriminator": user.discriminator,
            "avatar": str(user.avatar_url)
        })

    async def get_guilds(self, request: web.Request):
        access_token = request.headers.get("access_token")
        if access_token is None:
            raise web.HTTPBadRequest()

        user_guilds = await self.get_user_guilds(access_token)
        bot_guilds = self.client.guilds
        final_guilds = self.filter_guilds(user_guilds, bot_guilds)

        return web.json_response({
            "guilds": [{
                "id": g.id,
                "name": g.name,
                "icon_url": g.icon_url,
                "invited": g.invited
            } for g in final_guilds]
        })

    async def update_mod_role(self, request: web.Request):
        susu = await request.json()
        role_id = susu.get("role_id")
        guild_id = susu.get("guild_id")
        access_token = susu.get("access_token")
        user = await self.get_user(access_token)
        user_id = user.id
        if role_id is None or guild_id is None:
            raise web.HTTPBadRequest()
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "Not authorized"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Not authorized"})
        role = guild.get_role(int(role_id))
        if role is None:
            return web.json_response({"error": "Role not found"})
        await self.client.mongo.set_guild_data(guild_id=int(guild_id), staff_role=role.id)
        self.client.dispatch("mod_role_update", guild, role)
        return web.json_response({"success": True})

    async def toggle_modping(self, request: web.Request):
        susu = await request.json()
        guild_id = susu.get("guild_id")
        access_token = susu.get("access_token")
        if guild_id is None or access_token is None:
            raise web.HTTPBadRequest()
        user = await self.get_user(access_token)
        user_id = user.id
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "Not authorized"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Not authorized"})
        guild_data = await self.client.mongo.get_guild_data(guild_id=int(guild_id), raise_error=False)
        await self.client.mongo.set_guild_data(guild_id=int(guild_id), ping_staff=not guild_data.get("ping_staff", True))
        return web.json_response({"success": True})

    async def update_category(self, request: web.Request):
        susu = await request.json()
        category_id = susu.get("category_id")
        guild_id = susu.get("guild_id")
        access_token = susu.get("access_token")
        user = await self.get_user(access_token)
        user_id = user.id
        if category_id is None or guild_id is None:
            raise web.HTTPBadRequest()
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "Not authorized"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Not authorized"})
        category = guild.get_channel(int(category_id))
        if category is None:
            return web.json_response({"error": "Category not found"})
        await self.client.mongo.set_guild_data(guild_id=int(guild_id), category=category.id)
        self.client.dispatch("category_update", guild, category)
        return web.json_response({"success": True})

    async def update_transcript_channel(self, request: web.Request):
        susu = await request.json()
        channel_id = susu.get("channel_id")
        guild_id = susu.get("guild_id")
        access_token = susu.get("access_token")
        user = await self.get_user(access_token)
        user_id = user.id
        if channel_id is None or guild_id is None:
            raise web.HTTPBadRequest()
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "Not authorized"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Not authorized"})
        channel = guild.get_channel(int(channel_id))
        if channel is None:
            return web.json_response({"error": "Channel not found"})
        await self.client.mongo.set_guild_data(guild_id=int(guild_id), transcripts=channel.id)
        self.client.dispatch("transcript_channel_update", guild, channel)
        return web.json_response({"success": True})

    async def check_setup(self, request: web.Request):
        guild_id = request.headers.get("guild_id")
        access_token = request.headers.get("access_token")
        if guild_id is None or access_token is None:
            raise web.HTTPBadRequest()
        user = await self.get_user(access_token)
        user_id = user.id
        try:
            guild_id = int(guild_id)
            user_id = int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid guild id"})
        guild = self.client.get_guild(guild_id)
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(user_id)
        if member is None:
            return web.json_response({"error": "You are not in the guild."})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "You need manage_guild permissions to do that."})
        guild_data = await self.client.mongo.get_guild_data(guild_id, raise_error=False)
        if guild_data is None:
            return web.json_response({"setup": False})
        return web.json_response({"setup": True})

    async def setup_guild(self, request: web.Request):
        guild_id = request.headers.get("guild_id")
        staff_role_id = request.headers.get("staff_role_id")
        category_id = request.headers.get("category_id")
        transcripts_id = request.headers.get("transcripts_id")
        prefixes: List[str] = ast.literal_eval(request.headers.get("prefixes", "[]"))
        prefixes = prefixes or self.client.config.prefixes.copy()
        access_token = request.headers.get("access_token")
        if guild_id is None or staff_role_id is None or category_id is None or transcripts_id is None or access_token is None:
            raise web.HTTPBadRequest()
        user = await self.get_user(access_token)
        user_id = user.id
        try:
            guild_id = int(guild_id)
            staff_role_id = int(staff_role_id)
            category_id = int(category_id)
            transcripts_id = int(transcripts_id)
        except ValueError:
            return web.json_response({"error": "Invalid guild id or role id or category id or transcripts id"})
        guild = self.client.get_guild(guild_id)
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(user_id)
        if member is None:
            return web.json_response({"error": "Unauthorized"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Unauthorized"})
        staff_role = guild.get_role(staff_role_id)
        if staff_role is None:
            return web.json_response({"error": "Staff role not found"})
        category = guild.get_channel(category_id)
        if category is None:
            return web.json_response({"error": "Category not found"})
        transcripts = guild.get_channel(transcripts_id)
        if transcripts is None:
            return web.json_response({"error": "Transcripts channel not found"})
        if not category.permissions_for(guild.me).manage_channels:
            return web.json_response({"error": "I don't have permissions to create channels in the category."})
        if not category.permissions_for(guild.me).manage_webhooks:
            return web.json_response({"error": "I don't have permissions to create webhooks in the category."})
        if not category.permissions_for(guild.me).read_message_history:
            return web.json_response({"error": "I don't have permissions to read message history in the category."})
        if not category.permissions_for(guild.me).use_external_emojis:
            return web.json_response({"error": "I don't have permissions to use external emojis in the category."})
        if not category.permissions_for(guild.me).add_reactions:
            return web.json_response({"error": "I don't have permissions to add reactions in the category."})
        if not category.permissions_for(guild.me).read_messages:
            return web.json_response({"error": "I don't have permissions to read messages in the category."})
        if not category.permissions_for(guild.me).send_messages:
            return web.json_response({"error": "I don't have permissions to send messages in the category."})
        if not transcripts.permissions_for(guild.me).read_messages or not transcripts.permissions_for(guild.me).send_messages:
            return web.json_response({"error": "I don't have permissions to read messages or send messages in the transcripts channel."})
        await self.client.mongo.set_guild_data(
            guild.id,
            category=category.id,
            staff_role=staff_role.id,
            transcripts=transcripts.id,
            prefixes=prefixes
        )
        return web.json_response({"success": True, "message": "Guild setup complete." if guild.me.guild_permissions.administrator else "The guild setup is complete, it is recommended that you grant me administrator permissions for the best experience."})

    async def get_guild_data(self, request: web.Request):
        guild_id = request.headers.get("guild_id")
        access_token = request.headers.get("access_token")
        if guild_id is None or access_token is None:
            raise web.HTTPBadRequest()
        try:
            user = await self.get_user(access_token)
        except hikari.UnauthorizedError:
            return web.json_response({"error": "Unauthorized"})
        user_id = user.id
        print(user_id, guild_id)
        try:
            int(guild_id)
            int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid guild id or user id"})
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "Member not found"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Insufficient permissions"})
        guild_data = await self.client.mongo.get_guild_data(guild.id, raise_error=False)
        if guild_data is not None:
            modrole = guild.get_role(guild_data['staff_role'])
            ping_staff = guild_data.get("ping_staff", True)
            ticket_category = guild.get_channel(guild_data['category'])
            transcripts_channel = guild.get_channel(guild_data['transcripts'])
            guild_transcripts = [{
                "ticketId": t_id,
                "ticketUser": (lambda user: {
                    "id": user.id if user is not None else t_data['user_id'],
                    "username": user.name if user is not None else "Unknown User",
                    "discriminator": str(user.discriminator) if user is not None else "0000",
                    "avatar": user.display_avatar.url if user is not None else "https://cdn.discordapp.com/embed/avatars/0.png"
                })(self.client.get_user(t_data['user_id'])),
            } for t_id, t_data in guild_data.get('ticket_transcripts', {}).items()]
            current_tickets = await self.client.mongo.get_guild_modmail_threads(guild.id)
            prefixes = self.client.config.prefixes.copy()
            templates = guild_data.get('templates', {})
            ticket_open_message = guild_data.get('ticket_open_message', "{staff_role_mention} {user_mention} has opened a modmail thread.")
            ticket_close_message = guild_data.get('ticket_close_message', "This modmail thread has been closed by {moderator_mention}")
            staff_ticket_open_message = guild_data.get('staff_ticket_open_message', """
Hey there, A modmail ticket has been started by a staff member.

**Staff Member:** {moderator_mention}
**Server:** {server}
**Reason:** {reason}

You can respond to this modmail ticket by messaging here
All your messages will be send to the staff team.
            """)

        return web.json_response({
            "id": str(guild.id),
            "name": guild.name,
            "description": guild.description,
            "icon": guild.icon.url if guild.icon is not None else "https://cdn.discordapp.com/embed/avatars/0.png",
            "banner": guild.banner.url if guild.banner is not None else None,
            "members": guild.member_count,
            "roles": len(guild.roles),
            "channels": len(guild.channels),
            "roleList": [{
                "id": str(r.id),
                "name": r.name,
                "color": str(r.color),
            } for r in guild.roles if r != guild.default_role][::-1],
            "categoryList": [{
                "id": str(c.id),
                "name": c.name
            } for c in guild.categories],
            "channelList": [{
                "id": str(c.id),
                "name": c.name
            } for c in guild.text_channels],
            "owner": {
                "id": str(guild.owner.id),
                "username": guild.owner.name,
                "discriminator": guild.owner.discriminator,
                "avatar": guild.owner.display_avatar.url
            } if guild.owner is not None else None,
            "settings": {
                "prefixes": guild_data.get("prefixes", prefixes) if guild_data is not None else prefixes,
                "modRole": {
                    "id": str(modrole.id),
                    "name": modrole.name,
                    "color": str(modrole.color),
                } if modrole is not None else None,
                "pingModRole": ping_staff,
                "ticketCategory": {
                    "id": str(ticket_category.id),
                    "name": ticket_category.name,
                } if ticket_category is not None else None,
                "transcriptsChannel": {
                    "id": str(transcripts_channel.id),
                    "name": transcripts_channel.name,
                } if transcripts_channel is not None else None,
                "currentTickets": [{
                    "userId": str(ticket['_id']),
                    "channelId": str(ticket['channel_id'])
                } for ticket in current_tickets],
                "guildTranscripts": guild_transcripts,
                "templates": [{"name": temp_name, "description": template['description'], "content": template['content']} for temp_name, template in templates.items()],

                "ticketOpenMessage": ticket_open_message,
                "ticketCloseMessage": ticket_close_message,
                "staffTicketOpenMessage": staff_ticket_open_message,
            } if guild_data is not None else None,
        })

    async def update_ticket_message(self, request: web.Request):
        guild_id = request.headers.get("guild_id")
        access_token = request.headers.get("access_token")
        message = request.headers.get("message")
        message_type = request.headers.get("message_type")
        if guild_id is None or access_token is None or message is None or message_type is None:
            raise web.HTTPBadRequest()
        try:
            user = await self.get_user(access_token)
        except hikari.UnauthorizedError:
            return web.json_response({"error": "Unauthorized"})
        user_id = user.id
        print(user_id, guild_id)
        try:
            int(guild_id)
            int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid guild id or user id"})
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Guild not found"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "Member not found"})
        if not member.guild_permissions.manage_guild:
            return web.json_response({"error": "Insufficient permissions"})
        if message_type == "ticket_open_message":
            await self.client.mongo.set_guild_data(guild.id, ticket_open_message=message)
        elif message_type == "ticket_close_message":
            await self.client.mongo.set_guild_data(guild.id, ticket_close_message=message)
        elif message_type == "staff_ticket_open_message":
            await self.client.mongo.set_guild_data(guild.id, staff_ticket_open_message=message)
        else:
            return web.json_response({"error": "Invalid message type"})
        return web.json_response({"success": True})

    async def bot_stats(self, request: web.Request):
        return web.json_response({
            "guilds": len(self.client.guilds),
            "users": len(self.client.users),
            "ping": round(self.client.latency * 1000, 2),
        })

    async def get_ticket_url(self, request: web.Request):
        message_url = request.headers.get("message_url")
        user_id = request.headers.get("user_id")
        if user_id is None:
            raise web.HTTPBadRequest()
        if message_url is None:
            return web.json_response({"error": "No message url provided"})
        things_of_url = message_url.replace("https://", "").replace("http://", "").split("/", 4)
        if len(things_of_url) != 5:
            return web.json_response({"error": "Invalid message url"})
        guild_id = things_of_url[2]
        channel_id = things_of_url[3]
        message_id = things_of_url[4]
        try:
            int(guild_id)
            int(channel_id)
            int(message_id)
        except ValueError:
            return web.json_response({"error": "bruh moment, enter some integers o_o"})
        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({"error": "Message URL contains invalid guild ID"})
        member = guild.get_member(int(user_id))
        if member is None:
            return web.json_response({"error": "You do not have access to view this ticket."})
        channel = guild.get_channel(int(channel_id))
        if channel is None:
            return web.json_response({"error": "Message URL contains invalid channel ID"})
        try:
            message = await channel.fetch_message(int(message_id))
            if message.author.id != self.client.user.id:
                return web.json_response({"error": "Invalid message URL"})
            if len(message.attachments) != 1:
                return web.json_response({"error": "Invalid message URL"})
            attachment = message.attachments[0]
            if not attachment.filename.endswith(".txt"):
                return web.json_response({"error": "Invalid message URL"})
        except discord.NotFound:
            return web.json_response({"error": "Invalid message URL"})
        return web.json_response({"url": f"/tickets/{guild_id}/{channel_id}/{message_id}"})

    async def get_ticket_html(self, request: web.Request):
        final = ""
        guild_id = request.headers.get("guild_id")
        user_id = request.headers.get("user_id")
        channel_id = request.headers.get("channel_id")
        msg_id = request.headers.get("msg_id")
        h1_classes = "'text-white font-bold text-center text-3xl'"
        default_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
        if guild_id is None or user_id is None or channel_id is None or msg_id is None:
            final = f"<h1 class={h1_classes}> Missing guild_id or user_id or channel_id or msg_id in the URL </h1>"
        else:
            try:
                int(guild_id)
                int(user_id)
                int(channel_id)
                int(msg_id)
            except ValueError:
                final = f"<h1 class={h1_classes}> bruh moment, the ids need to be integers ._. </h1>"
                return web.json_response({
                    "html": final
                })
            guild = self.client.get_guild(int(guild_id))
            if guild is None:
                final = f"<h1 class={h1_classes}> Guild not found </h1>"
            else:
                member = guild.get_member(int(user_id))
                if member is None:
                    final = f"<h1 class={h1_classes}> You are not the guild, hence you cannot access this guild's tickets. </h1>"
                else:
                    channel = guild.get_channel(int(channel_id))
                    if channel is None:
                        final = f"<h1 class={h1_classes}> Invalid channel ID </h1>"
                    else:
                        try:
                            message = await channel.fetch_message(int(msg_id))
                            if message.author.id != self.client.user.id:
                                final = f"<h1 class={h1_classes} > Invalid ticket ID </h1>"
                            else:
                                if len(message.attachments) != 1:
                                    final = f"<h1 class={h1_classes}> Invalid ticket ID </h1>"
                                else:
                                    attachment = message.attachments[0]
                                    if not attachment.filename.endswith(".txt"):
                                        final = f"<h1 class={h1_classes}> Invalid ticket ID </h1>"
                                    else:
                                        bytes_data = await attachment.read()
                                        text_data = bytes_data.decode()
                                        ticket_user_id = int(message.content)
                                        ticket_member = self.client.get_user(ticket_user_id)
                                        for text_line in text_data.split("\n\n"):
                                            lines = text_line.split(" | ", 3)
                                            if len(lines) >= 3:
                                                user_name = lines[0]
                                                actual_message_content = lines[3]
                                                member_id = lines[1]
                                                member = ticket_member if member_id == str(ticket_user_id) else guild.get_member(int(member_id))
                                                final += f"""
                                                    <div class='discord-message flex'>
                                                        <img class="rounded-full" height="50px" width="50px" src={member.display_avatar.url if member is not None else (default_avatar if len(user_name.split("#")) == 3 else (ticket_member.display_avatar.url if ticket_member is not None else default_avatar))} />
                                                        <div class="author-and-message flex flex-col justify-center h-full">
                                                            <h1 class="font-bold text-white text-xl">{member or user_name}</h1>
                                                            <p class="text-white">{actual_message_content}</p>
                                                        </div>
                                                    </div>
                                                """
                        except discord.NotFound:
                            final = f"<h1 class={h1_classes}> Invalid message ID </h1>"
        return web.json_response({
            "html": final
        })

    async def get_ticket_html_new(self, request: web.Request):
        final = ""
        default_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
        guild_id = request.headers.get("guild_id")
        ticket_id = request.headers.get("ticket_id")
        access_token = request.headers.get("access_token")

        def format_error(err: str) -> str:
            return f"<h1 class='text-white font-bold text-center text-3xl'> ERROR: {err} </h1>"

        if guild_id is None or ticket_id is None or access_token is None:
            final = format_error("Missing guild_id or ticket_id in the URL OR missing access_token in the headers")
            return web.json_response({"html": final})
        try:
            user = await self.get_user(access_token)
        except hikari.UnauthorizedError:
            return web.json_response({"html": format_error("Invalid access token in headers")})

        try:
            int(guild_id)
        except ValueError:
            final = format_error("Guild ID passed in the URL is not an integer")
            return web.json_response({"html": final})

        guild = self.client.get_guild(int(guild_id))
        if guild is None:
            return web.json_response({
                "html": format_error("Invalid guild ID passed in the URL, unable to find guild.")
            })

        member = guild.get_member(int(user.id))
        if member is None:
            return web.json_response({
                "html": format_error("You are not authorized to view tickets from this guild.")
            })
        ticket = await self.client.mongo.get_guild_ticket_transcript(int(guild_id), ticket_id)
        if ticket is None:
            return web.json_response({
                "html": format_error("Invalid ticket ID passed in the URL, unable to find ticket.")
            })
        if ticket['user_id'] != member.id and not member.guild_permissions.manage_guild:
            return web.json_response({
                "html": format_error("You are not authorized to view this ticket from this guild.")
            })

        transcript_db = self.client.get_channel(self.client.config.transcript_db_channel)
        ticket_message = await transcript_db.fetch_message(ticket['message_id'])
        attachment = ticket_message.attachments[0]
        bytes_data = await attachment.read()
        text_data = bytes_data.decode()
        for text_line in text_data.split("\n\n"):
            lines = text_line.split(" | ", 3)
            if len(lines) >= 3:
                user_name = lines[0]
                actual_message_content = lines[3]
                actual_message_content = actual_message_content.replace("<", "&lt;").replace(">", "&gt;")
                member_id = lines[1]
                member = guild.get_member(int(member_id))
                final += f"""
                    <div class='discord-message flex'>
                        <img class="rounded-full" height="50px" width="50px" src={member.display_avatar.url if member is not None else (default_avatar if len(user_name.split("#")) == 3 else (ticket_message.author.display_avatar.url if ticket_message.author is not None else default_avatar))} />
                        <div class="author-and-message flex flex-col justify-center h-full">
                            <h1 class="font-bold text-white text-xl">{member or user_name}</h1>
                            <p class="text-white">{actual_message_content}</p>
                        </div>
                    </div>
                """
        return web.json_response({"html": final})

    async def start_server(self):
        app = web.Application()
        cors = aiohttp_cors.setup(app)

        callback_resource = cors.add(app.router.add_resource("/oauth/callback"))
        get_own_user_resource = cors.add(app.router.add_resource("/users/me"))
        get_guilds_resource = cors.add(app.router.add_resource("/guilds"))
        get_guild_data_resource = cors.add(app.router.add_resource("/guild"))
        check_setup_resource = cors.add(app.router.add_resource("/check_setup"))
        setup_guild_resource = cors.add(app.router.add_resource("/setup_guild"))
        bot_stats_resource = cors.add(app.router.add_resource("/stats"))
        update_mod_role_resource = cors.add(app.router.add_resource("/update_mod_role"))
        update_ping_staff_resource = cors.add(app.router.add_resource("/update_ping_staff"))
        update_category_resource = cors.add(app.router.add_resource("/update_category"))
        update_transcripts_resource = cors.add(app.router.add_resource("/update_transcripts"))
        update_ticket_message_resource = cors.add(app.router.add_resource("/update_ticket_message"))
        get_ticket_html_resource = cors.add(app.router.add_resource("/get_ticket_html"))
        get_ticket_html_new_resource = cors.add(app.router.add_resource("/get_ticket_html_new"))
        get_ticket_url_resource = cors.add(app.router.add_resource("/get_ticket_url"))

        cors.add(callback_resource.add_route("POST", self.callback), self.cors_thing)
        cors.add(get_own_user_resource.add_route("GET", self.get_own_user), self.cors_thing)
        cors.add(get_guilds_resource.add_route("GET", self.get_guilds), self.cors_thing)
        cors.add(get_guild_data_resource.add_route("GET", self.get_guild_data), self.cors_thing)
        cors.add(check_setup_resource.add_route("GET", self.check_setup), self.cors_thing)
        cors.add(setup_guild_resource.add_route("GET", self.setup_guild), self.cors_thing)
        cors.add(bot_stats_resource.add_route("GET", self.bot_stats), self.cors_thing)
        cors.add(update_mod_role_resource.add_route("POST", self.update_mod_role), self.cors_thing)
        cors.add(update_ping_staff_resource.add_route("POST", self.toggle_modping), self.cors_thing)
        cors.add(update_category_resource.add_route("POST", self.update_category), self.cors_thing)
        cors.add(update_transcripts_resource.add_route("POST", self.update_transcript_channel), self.cors_thing)
        cors.add(update_ticket_message_resource.add_route("GET", self.update_ticket_message), self.cors_thing)
        cors.add(get_ticket_html_resource.add_route("GET", self.get_ticket_html), self.cors_thing)
        cors.add(get_ticket_html_new_resource.add_route("GET", self.get_ticket_html_new), self.cors_thing)
        cors.add(get_ticket_url_resource.add_route("GET", self.get_ticket_url), self.cors_thing)

        runner = web.AppRunner(app)
        await runner.setup()

        self.api = web.TCPSite(runner, host="0.0.0.0", port=8153)
        await self.client.wait_until_ready()
        await self.api.start()
        logging.info(f"Web server started at PORT: {self.api._port} HOST: {self.api._host}")

    def cog_unload(self) -> None:
        asyncio.ensure_future(self.api.stop())
        logging.info("Web server stopped")


def setup(client: ModMail):
    cog = WebServer(client)
    client.add_cog(cog)
    client.loop.create_task(cog.start_server())
