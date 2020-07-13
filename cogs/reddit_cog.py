from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from database.database import session
from database.models import Channel, Guild

if TYPE_CHECKING:
    from main import Reddify


class RedditCog(commands.Cog):
    def __init__(self, bot: 'Reddify'):
        self.bot = bot

    @commands.command(help="Get your subreddit's stats.")
    async def substats(self, ctx: commands.Context, sub: str = ""):
        message = await ctx.send("🕑 Please wait while we gather the data...")

        if sub:
            subname = sub.replace("r/", "").replace("/", "")
        else:
            if channel := session.query(Channel).filter(Channel.channel_id == ctx.channel.id).first():
                subname = channel.subreddit
            elif guild := session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first():
                subname = guild.subreddit

        if not subname:
            await message.edit(content="❗ Please enter the subreddit's name as well!")
            return

        try:
            sub = await self.bot.reddit.subreddit(subname)
        except Exception as e:
            await message.edit(content="❗ Oops, I can't reach /r/{}. Are you sure it's alive?".format(subname))
            await self.bot.send_error(e)
        else:
            if sub.quarantine:
                await message.edit(content="❗ Oops, it seems /r/{} is quarantined!".format(subname))
            elif sub.subreddit_type in ["archived", "employees_only", "gold_only", "gold_restricted", "private"]:
                await message.edit(
                    content="❗ Oops, /r/{} is {}, I can't access it!".format(subname, sub.subreddit_type))
            else:
                embed = self.bot.get_embed()

                embed.set_author(name=f"/r/{sub} statistics",
                                 url=f"https://www.reddit.com/r/{sub}")

                embed.title = f"{sub.subscribers} subscribers"
                embed.description = sub.public_description if sub.public_description else sub.description

                i = -1
                mods = [f"⭐{mod}" if not (i := i + 1) else f"🔸{mod}" async for mod in sub.moderators()]
                embed.add_field(name="Moderators", value="\n".join(mods), inline=False)

                age = datetime.utcnow() - sub.created_utc
                age = age.seconds / 60 / 60 + age.days * 24
                days = int(age / 24)
                hours = int(age - days * 24)
                age_string = f"{days} days {hours} hours" if days != 0 else f"{hours} hours"

                growth = int(sub.subscribers / age)

                data = f"**Age:** {age_string}\n" \
                    f"**Growth:** {growth} subscribers/hour\n" \
                    f"**NSFW:** {sub.over18}"

                embed.add_field(name="Data", value=data, inline=False)

                await message.edit(embed=embed, content="")


def setup(bot):
    bot.add_cog(RedditCog(bot))
