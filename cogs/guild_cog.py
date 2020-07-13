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

    @commands.command(help="Toggle setting roles/changing username on this guild.")
    @commands.has_permissions(administrator=True)
    async def toggle(self, ctx: commands.Context, toggle: str):
        guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()

        if not guild:
            guild = Guild(guild_id=ctx.guild.id)
            session.add(guild)
            session.commit()

        if toggle == "username":
            guild.set_username = not guild.set_username
            session.commit()

            if guild.set_username:
                for member in ctx.guild.members:
                    if discord_user := session.query(DiscordUser).filter(DiscordUser.user_id == member.id).first():
                        await self.bot.update_guild_user(guild, discord_user)
                await ctx.send(f"<{EMOJIS['CHECK']}> Reddit usernames enabled for this server!")
            else:
                await ctx.send(f"<{EMOJIS['CHECK']}> Reddit usernames disabled for this server!")
        elif toggle == "role":
            guild.set_role = not guild.set_role

            if guild.set_role:
                if ctx.guild.get_role(guild.role) is None:
                    role = await ctx.guild.create_role(name="Verified Redditor",
                                                       colour=discord.Colour(0).from_rgb(254, 63, 24),
                                                       mentionable=True,
                                                       reason="Verified Redditors get this role by the bot.")
                    guild.role = role.id

                for member in ctx.guild.members:
                    if discord_user := session.query(DiscordUser).filter(DiscordUser.user_id == member.id).first():
                        await self.bot.update_guild_user(guild, discord_user)

                await ctx.send(f"<{EMOJIS['CHECK']}> Custom roles enabled for this server!")
            else:
                await ctx.send(f"<{EMOJIS['CHECK']}> Custom roles disabled for this server!")

            session.commit()
        elif toggle == "nick":
            guild.custom_nick = not guild.custom_nick
            session.commit()

            if guild.custom_nick:
                await ctx.send(f"<{EMOJIS['CHECK']}> Custom nicknames enabled for this server!")
            else:
                await ctx.send(f"<{EMOJIS['CHECK']}> Custom nicknames disabled for this server!")
        else:
            await ctx.message.channel.send("❗ Invalid argument. Toggle `role`, `username` or `nick`.")
