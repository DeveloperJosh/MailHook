import discord
import asyncio
from discord.ext import commands
from typing import Optional


async def wait_for_msg(ctx: commands.Context, timeout: int, msg_to_edit: discord.Message) -> Optional[discord.Message]:
    def c(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg: discord.Message = await ctx.bot.wait_for("message", timeout=timeout, check=c)
        try:
            await msg.delete()
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass
        if msg.content.lower() == 'cancel':
            await msg_to_edit.edit(
                content="",
                embed=discord.Embed(
                    title="Cancelled!",
                    color=0xFF0000
                )
            )
            return
    except asyncio.TimeoutError:
        await msg_to_edit.edit(
            content="Too late! You didn't respond in time.",
            embed=None,
            view=None
        )
        return
    return msg
