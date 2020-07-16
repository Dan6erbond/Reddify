import asyncio
from datetime import datetime
from inspect import Parameter
from typing import List, Mapping, Optional

import discord
from discord.ext import commands

import helpers.fuzzle as fuzzle

MAINTAINER = "Dan6erbond#2259"


class HelpCommand(commands.HelpCommand):

    def __init__(self, **options):
        super().__init__(**options)

    @property
    def embed(self) -> discord.Embed:
        if self.context.bot and hasattr(self.context.bot, "embed"):
            return self.context.bot.embed
        elif self.context.bot and hasattr(self.context.bot, "get_embed"):
            return self.context.bot.get_embed()
        else:
            embed = discord.Embed(
                colour=discord.Colour(0).from_rgb(64, 153, 130)
            )
            embed.set_footer(
                text=f"Help command by {MAINTAINER}",
                icon_url=self.context.bot.user.avatar_url)
            embed.timestamp = datetime.utcnow()

            return embed

    def get_cmd_string(self, cmd: commands.Command):
        params = [f"[{k}{' (optional)' if v.default != Parameter.empty else ''}]" for k,
                  v in cmd.clean_params.items()]
        return f"{self.context.bot.command_prefix}{cmd.name} {' '.join(params)}"

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        embeds = []

        for cog in mapping:
            embed = self.embed

            for cmd in mapping[cog]:
                embed.add_field(name=f"`{self.get_cmd_string(cmd)}`",
                                value=cmd.brief if cmd.brief else cmd.help,
                                inline=False)

            if not cog:
                embed.set_author(name=f"General Commands")
                embed.description = "Use `!help [command]` for more information."
                embeds = [embed, *embeds]
            else:
                embed.set_author(name=f"Commands in the {cog.qualified_name} Category")
                embed.description = "Use `!help [cog]` for more information."
                embeds.append(embed)

        for index, embed in enumerate(embeds, start=1):
            embed.set_footer(text=f"Page {index} of {len(embeds)}", icon_url=self.context.bot.user.avatar_url)

        if not embeds:
            return

        index = 0

        msg = await self.get_destination().send(embed=embeds[index])
        await msg.add_reaction("⏮")
        await msg.add_reaction("⏪")
        await msg.add_reaction("⏩")
        await msg.add_reaction("⏭")

        MAX_TIME = 5 * 60
        seconds = 0
        while seconds < MAX_TIME:
            try:
                time_started = datetime.now()
                reaction = await self.context.bot.wait_for("reaction_add",
                                                           check=lambda r, u: u.id == self.context.author.id and r.message.id == msg.id,
                                                           timeout=MAX_TIME - seconds)

                await msg.remove_reaction(reaction[0], reaction[1])

                if reaction[0].emoji == "⏮":
                    index = 0
                elif reaction[0].emoji == "⏪":
                    index = max(index - 1, 0)
                elif reaction[0].emoji == "⏩":
                    index = min(index + 1, len(embeds) - 1)
                elif reaction[0].emoji == "⏭":
                    index = len(embeds) - 1

                await msg.edit(content="", embed=embeds[index])
            except asyncio.exceptions.TimeoutError:
                pass
            finally:
                seconds += (datetime.now() - time_started).seconds

    async def send_cog_help(self, cog: commands.Cog):
        embed = self.embed
        embed.set_author(name=f"Commands in the {cog.qualified_name} Category")
        embed.description = "Use `!help [command]` for more information."

        for cmd in cog.get_commands():
            embed.add_field(name=f"`{self.get_cmd_string(cmd)}`",
                            value=cmd.brief if cmd.brief else cmd.help,
                            inline=False)

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        print("Group help:", group)
        return await super().send_group_help(group)

    async def send_command_help(self, command: commands.Command):
        embed = self.embed

        embed.add_field(name=f"`{self.get_cmd_string(command)}`",
                        value=command.help if command.help else command.brief,
                        inline=False)

        await self.get_destination().send(embed=embed)

    async def command_not_found(self, string):
        cmds = [{"key": cmd.name, "tags": cmd.aliases, "cmd": cmd} for cmd in self.context.bot.commands]
        results = fuzzle.find(cmds, string)

        top_cmds = '\n'.join([f"`{self.get_cmd_string(cmd['cmd'])}`" for cmd in results][:3])
        await self.get_destination().send(f"No command called \"{string}\" found. " +
                                          f"Maybe you meant?\n\n{top_cmds}\n\n" +
                                          "Powered by Fuzzle™.")

    async def subcommand_not_found(self, command, string):
        print("Subcommand not found:", command, string)
        return await super().subcommand_not_found(command, string)

    async def on_help_command_error(self, ctx, error):
        print("Help command error:", ctx, error)
        return await super().on_help_command_error(ctx, error)

    async def send_error_message(self, error):
        if error:
            print("Error message:", type(error), error)
            return await super().send_error_message(error)
