from discord.ext import commands

from database.database import session
from database.models import DiscordUser, RedditUser


async def is_verified(ctx):
    if session.query(DiscordUser).join(
            RedditUser).filter(DiscordUser.user_id == ctx.author.id).first():
        return True
    return False
