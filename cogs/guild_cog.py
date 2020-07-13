from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from const import EMOJIS
from database.database import session
from database.models import DiscordUser, Guild

if TYPE_CHECKING:
    from main import Reddify


class GuildCog(commands.Cog):
    def __init__(self, bot: 'Reddify'):
        self.bot = bot

    @commands.command(
        help="Set the guild's subreddit which is used when calling `!substats` when the optional `sub` parameter is ommitted.")
    @commands.has_permissions(administrator=True)
    async def setguildsub(self, ctx: commands.Context, sub: str):
        guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()

        if not guild:
            guild = Guild(guild_id=ctx.guild.id)
            session.add(guild)
            session.commit()

        try:
            s = await self.bot.reddit.subreddit(sub)
        except BaseException:
            await ctx.send("❗ /r/{} doesn't exist or isn't visible to me!".format(sub))
        else:
            guild.subreddit = sub
            session.commit()
            await ctx.send(f"<{EMOJIS['CHECK']}> Successfully set /r/{sub} as this guild's subreddit!")

    @commands.Cog.listener
    async def on_guild_join(self, guild: discord.Guild):
        guild = session.query(Guild).filter(Guild.guild_id == guild.id).first()

        if not guild:
            guild = Guild(guild_id=guild.id)
            session.add(guild)
            session.commit()

    @commands.Cog.listener
    async def on_member_join(self, member: discord.Member):
        guild = session.query(Guild).filter(Guild.guild_id == member.guild.id).first()
        discord_user = session.query(DiscordUser).filter(DiscordUser.user_id == member.id).first()

        if guild and discord_user:
            await self.bot.update_guild_user(guild, discord_user)

    @commands.command(help="Check which features of the bot are enabled/disabled.")
    async def status(self, ctx: commands.Context):
        guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()

        if not guild:
            guild = Guild(guild_id=ctx.guild.id)
            session.add(guild)
            session.commit()

        set_role = "on" if guild.set_role else "off"
        set_username = "on" if guild.set_username else "off"
        set_nickname = "on" if guild.custom_nick else "off"
        role_name = ctx.guild.get_role(guild.role).name if guild.role else None

        await ctx.channel.send(f"Adding '{role_name}' role: {set_role}\n" +
                               f"Changing nickname to /u/username: {set_username}\n" +
                               f"Allowing custom nicknames: {set_nickname}")
