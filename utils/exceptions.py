import discord
from typing import Optional, Union
from discord.ext.commands import CommandError


class NotSetup(CommandError):
    pass


class ModRoleNotFound(CommandError):
    pass


class TicketCategoryNotFound(CommandError):
    pass


class TranscriptChannelNotFound(CommandError):
    pass


class UserAlreadyInAModmailThread(CommandError):
    def __init__(self, user: Optional[Union[discord.Member, discord.User]]):
        self.user = user


class DMsDisabled(CommandError):
    def __init__(self, user: discord.Member):
        self.user = user


class NotStaff(CommandError):
    pass


class NotAdmin(CommandError):
    pass


class NoBots(CommandError):
    pass


class GuildOnlyPls(CommandError):
    pass
