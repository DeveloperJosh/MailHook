from discord.ext.commands import Converter, Context, CommandError


class SettingConverter(Converter):
    async def convert(self, ctx: Context, argument: str):
        if argument.lower() in ['transcripts_channel', 'category', 'staff_role']:
            return argument.lower()
        else:
            raise CommandError()
