from typing import TYPE_CHECKING

import apraw
from discord.ext import commands
from sqlalchemy import func
from sqlalchemy.sql.expression import and_, false

from const import EMOJIS, MAINTAINER
from database.database import session
from database.models import DiscordUser, Guild, RedditUser

if TYPE_CHECKING:
    from main import Reddify


class UserCog(commands.Cog):
    def __init__(self, bot: 'Reddify'):
        self.bot = bot

    @commands.command(help="Sends a PM to the Reddit user to await confirmation of the account ownership.")
    async def verify(self, ctx: commands.Context, user: str):
        user = user.replace("u/", "").replace("/", "").strip().lower()

        if not session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first():
            discord_user = DiscordUser(user_id=ctx.author.id)
            session.add(discord_user)
            session.commit()

        if session.query(RedditUser).filter(and_(func.lower(RedditUser.username) == user,
                                                 RedditUser.discord_user != ctx.author.id)).first():
            await ctx.message.channel.send(
                f"❗ /u/{user} is already linked to another Discord account! " +
                f"If you believe this is an error, please contact {MAINTAINER}.")
            return

        if session.query(RedditUser).filter(and_(func.lower(RedditUser.username) == user,
                                                 RedditUser.discord_user == ctx.author.id)).first():
            await ctx.message.channel.send(f"❗ /u/{user} is already linked to your Discord account!")
            return

        if reddit_user := session.query(RedditUser).filter(and_(RedditUser.discord_user ==
                                                                ctx.author.id, RedditUser.verified == false())).first():
            await ctx.message.channel.send(
                f"❗ /u/{reddit_user.username} is still awaiting verification on Reddit. " +
                f"If you would like to unlink it, use `!unverify {reddit_user.username}`.")
            return

        try:
            redditor = await self.bot.reddit.redditor(user)
        except Exception as e:
            await ctx.message.channel.send(f"❌ Redditor /u/{user} doesn't exist!\n\nError:{e}")
        else:
            await redditor.message("Account Ownership Confirmation",
                                   f"Please reply to this message with 'verify' to confirm that you are Discord user '{ctx.message.author}'.")
            msg = await ctx.message.channel.send(
                f"Check your Reddit PMs to verify you are the owner of /u/{redditor.name} by responding with `verify`!")

            reddit_user = RedditUser(user_id=redditor.fullname, discord_user=ctx.author.id, username=redditor.name)
            session.add(reddit_user)

            auth_user = await self.bot.reddit.user.me()
            async for message in auth_user.unread.stream(skip_existing=True):
                if not isinstance(message, apraw.models.Message):
                    continue
                if not "Account Ownership Confirmation" in message.subject:
                    continue

                try:
                    author = await message.author()
                    if author.name.lower() != reddit_user.username.lower():
                        continue
                except Exception as e:
                    await self.bot.send_error(e)

                if "verify" in message.body.lower() and not "unverify" in message.body.lower():
                    reddit_user.verified = True
                    user = self.bot.get_user(reddit_user.discord_user)
                    if user is not None:
                        await msg.add_reaction(EMOJIS["CHECK"])
                        await message.reply(f"Confirmation of {user} successful!")

                        for guild in session.query(Guild).all():
                            await self.bot.update_guild_user(guild, discord_user)
                else:
                    message.reply(
                        "Discord user unlinked from your Reddit account. " +
                        "Please run `!verify` again if this is an error and respond to the new PM.")
                    session.delete(reddit_user)

                break

            session.commit()

    @commands.command(help="Unlink a Reddit account from your Discord handle.")
    async def unverify(self, ctx: commands.Context, user: str):
        if reddit_user := session.query(RedditUser).filter(and_(func.lower(RedditUser.username) == user,
                                                                RedditUser.discord_user == ctx.author.id)).first():
            session.delete(reddit_user)
            session.commit()

            guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()
            if not guild:
                guild = Guild(guild_id=ctx.guild.id)
                session.add(guild)
                session.commit()

            if discord_user := session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first():
                self.bot.update_guild_user(guild, discord_user)

            await ctx.channel.send(f"<{EMOJIS['CHECK']}> Successfully unlinked /u/{user}!")
        else:
            await ctx.channel.send(f"<{EMOJIS['XMARK']}> /u/{user} isn't linked to your account!")

    @commands.command(help="Get your (un)verified Reddit accounts.")
    async def me(self, ctx: commands.Context):
        if discord_user := session.query(DiscordUser).join(
                RedditUser).filter(DiscordUser.user_id == ctx.author.id).first():
            accounts = [f"/u/{acc.username}" for acc in discord_user.reddit_accounts if acc.verified]
            msg = f"**{ctx.author.mention}'s Accounts**\n\nVerified Accounts: {', '.join(accounts)}"
            unverified_accounts = [f"/u/{acc.username}" for acc in discord_user.reddit_accounts if not acc.verified]
            if unverified_accounts:
                msg += f"\nUnverified Account: /u/{unverified_accounts[0]}"
            await ctx.message.channel.send(msg)
            guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()
            self.bot.update_guild_user(guild, discord_user)
        elif discord_user := session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first():
            await ctx.message.channel.send("You haven't verified any Reddit accounts with Reddify yet!")


def setup(bot: 'Reddify'):
    bot.add_cog(UserCog(bot))
