from typing import TYPE_CHECKING

from discord.ext import commands

from const import EMOJIS
from database.database import session
from database.models import Channel

if TYPE_CHECKING:
    from main import Reddify


class ChannelCog(commands.Cog):
    def __init__(self, bot: 'Reddify'):
        self.bot = bot

    @commands.command(
        help="Set the channel's subreddit which is used when calling `!substats` when the optional `sub` parameter is omitted.")
    @commands.has_permissions(manage_channels=True)
    async def setchannelsub(self, ctx: commands.Context, sub: str):
        s = await self.bot.reddit.subreddit(sub)

        channel = session.query(Channel).filter(Channel.channel_id == ctx.channel.id).first()

        if not channel:
            channel = Channel(channel_id=ctx.channel.id)
            session.add(channel)

        channel.subreddit = sub

        session.commit()
        await ctx.send(f"<{EMOJIS['CHECK']}> Successfully set /r/{sub} as this channels's subreddit!")


def setup(bot: 'Reddify'):
    bot.add_cog(ChannelCog(bot))
