from discord.ext import commands

from const import ADVANCED_USERS
from database.database import session
from database.models import DiscordUser, RedditUser


async def is_verified(ctx: commands.Context):
    if session.query(DiscordUser).join(
            RedditUser).filter(DiscordUser.user_id == ctx.author.id).first():
        return True
    return False


async def advanced_user(ctx: commands.Context):
    return ctx.author.id in ADVANCED_USERS
