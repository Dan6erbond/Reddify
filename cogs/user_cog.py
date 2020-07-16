import re
from typing import TYPE_CHECKING

import apraw
import discord
from discord.ext import commands
from sqlalchemy import func
from sqlalchemy.sql.expression import and_, false

from const import EMOJIS, MAINTAINER
from database.database import session
from database.models import DiscordUser, Guild, RedditUser
from helpers import is_verified

if TYPE_CHECKING:
    from reddify import Reddify


class UserCog(commands.Cog):
    def __init__(self, bot: 'Reddify'):
        self.bot = bot

    @commands.command(help="Sends a PM to the Reddit user to await confirmation of the account ownership.")
    async def verify(self, ctx: commands.Context, user: str):
        user = user.replace("u/", "").replace("/", "").strip().lower()

        discord_user = session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first()

        if not discord_user:
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
                    if user:
                        await msg.add_reaction(EMOJIS["CHECK"])
                        rep = await message.reply(f"Confirmation of {user} successful!")

                        for guild in session.query(Guild).all():
                            await self.bot.update_guild_user(guild, discord_user)
                else:
                    message.reply(
                        "Discord user unlinked from your Reddit account. " +
                        "Please run `!verify` again if this is an error and respond to the new PM.")
                    session.delete(reddit_user)

                break

            session.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = session.query(Guild).filter(Guild.guild_id == member.guild.id).first()
        discord_user = session.query(DiscordUser).filter(DiscordUser.user_id == member.id).first()

        if guild and discord_user:
            await self.bot.update_guild_user(guild, discord_user)

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
                await self.bot.update_guild_user(guild, discord_user)

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
            await self.bot.update_guild_user(guild, discord_user)
        elif discord_user := session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first():
            await ctx.message.channel.send("You haven't verified any Reddit accounts with Reddify yet!")

    @commands.command(help="Get your Reddit account(s) stats.")
    @commands.check(is_verified)
    async def stats(self, ctx: commands.Context, us: str = ""):
        us = us.replace("u/", "").replace("/", "")

        user = None

        if us != "":
            id = re.search(r"(\d{18})", us)
            if id:
                id = int(id.group(1))
                user = user if (user := ctx.guild.get_member(id)) else bot.get_user(id)
            else:
                member = discord.utils.find(lambda m: m.nick == us or m.name == us or str(m) == us,
                                            ctx.guild.members)
            user_name = f"/u/{us}" if not user else user.name if not user.nick else user.nick
            wait_msg = await ctx.channel.send(f"🕑 Please wait while we gather {user_name}'s stats...")
        else:
            user = ctx.author
            user_name = user.name if not user.nick else user.nick
            wait_msg = await ctx.channel.send("🕑 Please wait while we gather your stats...")

        embed = self.bot.get_embed()

        url = f"https://www.reddit.com/u/{us}" if user is None else discord.Embed.Empty
        title = f"{user_name}'s Reddit account(s):" if user else f"{user_name}'s statistics:"
        embed.set_author(name=title, url=url)

        if user and (u := session.query(DiscordUser).filter(DiscordUser.user_id == user.id).first()):
            if not u.reddit_accounts:
                embed.description = "No verified Reddit accounts for {}!".format(user_name)

            for r in u.reddit_accounts:
                redditor = await self.bot.reddit.redditor(r.username)

                m = f"{redditor.link_karma} link | {redditor.comment_karma} comment\n"

                subscribers = 0
                subreddits = [sub async for sub in redditor.moderated_subreddits() if sub.subscribers]
                subreddits = [sub for sub in subreddits if (subscribers := subscribers + sub.subscribers)]

                amt = len(subreddits)

                subreddits = sorted(subreddits, key=lambda sub: sub.subscribers)[-10:]
                subreddits = sorted(subreddits, key=lambda sub: sub.subscribers, reverse=True)

                if len(subreddits) > 0:
                    m += "Subreddits moderated:\n"

                for subreddit in subreddits:
                    moderators = [mod async for mod in subreddit.moderators()]
                    prefix = "⭐" if r.username.lower() == str(moderators[0]).lower() else "🔸"
                    m += f"{prefix}[/r/{subreddit}](https://www.reddit.com/r/{subreddit}): {subreddit.subscribers} Subscribers\n"

                left_over = amt - len(subreddits)
                if left_over > 0:
                    m += f"...and {left_over} more subreddits.\n"

                if subscribers > 0:
                    m += f"Total: {subscribers} subscribers"

                embed.add_field(name=f"/u/{redditor}: {redditor.comment_karma + redditor.link_karma} karma",
                                value=m, inline=False)
        else:
            try:
                redditor = await self.bot.reddit.redditor(us)
            except BaseException:
                await wait_msg.edit(content=f"❗ Data for /u/{us} couldn't be loaded!")
                return

            embed.description = f"{redditor.link_karma} link | {redditor.comment_karma} comment\n"

            subscribers = 0
            subreddits = [sub async for sub in redditor.moderated_subreddits() if sub.subscribers]
            subreddits = [sub for sub in subreddits if (subscribers := subscribers + sub.subscribers)]

            amt = len(subreddits)

            subreddits = sorted(subreddits, key=lambda sub: sub.subscribers)[-10:]
            subreddits = sorted(subreddits, key=lambda sub: sub.subscribers, reverse=True)

            if len(subreddits) > 0:
                subs = list()
                for subreddit in subreddits:
                    moderators = [mod async for mod in subreddit.moderators()]
                    prefix = "⭐" if us.lower() == str(moderators[0]).lower() else "🔸"
                    subs.append(
                        f"{prefix}[/r/{subreddit}](https://www.reddit.com/r/{subreddit}): {subreddit.subscribers} Subscribers")

                left_over = amt - len(subreddits)
                left_over = f"\n...and {left_over} more subreddits." if left_over > 0 else ""

                newline = '\n'
                val = f"{newline.join(subs)}{left_over}\n\nTotal: {subscribers} subscribers"
                embed.add_field(name="Subreddits", value=val)

        await wait_msg.edit(embed=embed, content="")

    @commands.command(help="Change your nickname on the server.")
    async def nick(self, ctx: commands.Context, *, new_nick: str = ""):
        guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()
        if not guild:
            guild = Guild(guild_id=ctx.guild.id)
            session.add(guild)
            session.commit()

        if not guild.custom_nick:
            await ctx.send(f"<{EMOJIS['XMARK']}> This server has disabled custom nicknames!")
            return

        discord_user = session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first()
        verified = [acc.username for acc in discord_user.reddit_accounts]

        if new_nick != "":
            end = f"({'unverified' if len(verified) <= 0 else '/u/' + verified[0]})"
            new_nick = f"{new_nick[:32 - len(end) - 1]} {end}"
        else:
            new_nick = f"/u/{verified[0]}" if len(verified) > 0 else ctx.author.username

        try:
            await ctx.author.edit(nick=new_nick)
        except discord.errors.Forbidden:
            await ctx.send(f"<{EMOJIS['XMARK']}> I don't have the permissions to edit your nickname!")

    @commands.command(help="Change your nickname on the server.")
    async def nick(self, ctx: commands.Context, *, new_nick: str = ""):
        guild = session.query(Guild).filter(Guild.guild_id == ctx.guild.id).first()
        if not guild:
            guild = Guild(guild_id=ctx.guild.id)
            session.add(guild)
            session.commit()

        if not guild.custom_nick:
            await ctx.send(f"<{EMOJIS['XMARK']}> This server has disabled custom nicknames!")
            return

        discord_user = session.query(DiscordUser).filter(DiscordUser.user_id == ctx.author.id).first()
        verified = [acc.username for acc in discord_user.reddit_accounts]

        if new_nick != "":
            end = f"({'unverified' if len(verified) <= 0 else '/u/' + verified[0]})"
            new_nick = f"{new_nick[:32 - len(end) - 1]} {end}"
        else:
            new_nick = f"/u/{verified[0]}" if len(verified) > 0 else ctx.author.username

        try:
            await ctx.author.edit(nick=new_nick)
        except discord.errors.Forbidden:
            await ctx.send(f"<{EMOJIS['XMARK']}> I don't have the permissions to edit your nickname!")


def setup(bot: 'Reddify'):
    bot.add_cog(UserCog(bot))
