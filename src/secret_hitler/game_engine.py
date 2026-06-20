import asyncio
import json
import os

import discord
from discord.ext import commands
from discord.ext.commands import Context

from .game_handler import Game
from .players_manager import Players
from .static_data import colours, images


class Engine(commands.Cog):
    def __init__(self, bot):
        self.__currentGames: dict = {}
        self.__currentUsers: dict = {}   # channelID -> {userID: dmChannelID}
        self.__userChannel: dict = {}    # userID -> channelID (reverse index)
        self.__bot = bot
        self.__bot.remove_command("help")

    def checkGames(self, channelID: int) -> bool:
        return channelID in self.__currentGames

    def checkActiveUser(self, userID: int) -> bool:
        return userID in self.__userChannel

    def getGame(self, userID: int) -> int:
        return self.__userChannel.get(userID, 0)

    async def inGameChannel(self, ctx):
        if not ctx.guild:
            await ctx.send(
                f"Sorry {ctx.author.name}, this game action can only be performed via a valid sever text channel"
            )
        elif not self.checkGames(ctx.channel.id):
            await ctx.send(f"Sorry {ctx.author.name}, no active game in this channel")
        else:
            return True
        return False

    async def validSourceChannel(self, ctx) -> bool:
        channel_id = self.__userChannel.get(ctx.author.id)
        if channel_id is None or channel_id not in self.__currentGames:
            await ctx.send(f"Sorry {ctx.author.name}, you don't seem to be in a game")
            return False
        dm_channel_id = self.__currentUsers[channel_id].get(ctx.author.id)
        if ctx.channel.id == channel_id or ctx.channel.id == dm_channel_id:
            return True
        await ctx.send(
            f"Sorry {ctx.author.name}, correspondence through this channel is not allowed"
        )
        return False

    def _do_reset(self, channel_id: int) -> None:
        game = self.__currentGames.pop(channel_id, None)
        if game:
            game.cancel_inactivity_timer()
        if channel_id in self.__currentUsers:
            for userID in self.__currentUsers.pop(channel_id):
                self.__userChannel.pop(userID, None)
        for template in (images["currentboard.png"], images["newbase.png"]):
            path = template.replace("<channelID>", str(channel_id))
            if os.path.exists(path):
                os.remove(path)

    async def closeGame(self, ctx, returnFlag) -> bool:
        if returnFlag:
            await ctx.send("Thanks for playing!")
            await self.reset(ctx)

    # Events:

    @commands.Cog.listener()
    async def on_ready(self):
        print("Time to fight fascism")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an unrecognized command. Please enter sh!help to view the list of valid commands"
            )

    # Commands:

    @commands.command(
        name="test", description="Test command to check your connection to the bot"
    )
    async def test(self, ctx: Context):
        welcome_embed = discord.Embed(
            title="***\t Welcome to Secret Hitler! ***", colour=colours["BLUE"]
        )
        file_embed = discord.File(
            images["welcome.png"], filename="welcome.png")
        welcome_embed.set_image(url="attachment://welcome.png")
        welcome_embed.set_footer(
            text=f"@{ctx.author.name}, your Ping is: {round(self.__bot.latency * 1000)}ms"
        )
        await ctx.send(file=file_embed, embed=welcome_embed)

    @commands.command(name="reset", description="Reset any active game on the channel")
    async def reset(self, ctx):
        self._do_reset(ctx.channel.id)
        await ctx.send(f"Game has been reset on #{ctx.channel.name}")

    @commands.command(
        name="launch", description="To launch a session of the game on the channel"
    )
    async def launch(self, ctx: Context):
        if not ctx.guild:
            await ctx.send(
                f"Sorry {ctx.author.name}, the game can only be started sever text channel"
            )
        elif self.checkGames(ctx.channel.id):
            await ctx.send(
                f"Sorry {ctx.author.name}, a game is currently in-progress in this channel"
            )
        else:
            channel_id = ctx.channel.id
            channel = ctx.channel

            async def on_timeout():
                self._do_reset(channel_id)

            self.__currentGames[channel_id] = Game(channel, ctx.author, on_timeout)
            self.__currentUsers[channel_id] = dict()
            await self.__currentGames[channel_id].launch()

    @commands.command(name="join", description="To join a game on the channel")
    async def join(self, ctx: Context):
        if not await self.inGameChannel(ctx):
            return
        elif self.checkActiveUser(ctx.author.id):
            await ctx.send(
                f"Sorry {ctx.author.name}, you already seem to be active in a game"
            )
        elif await self.__currentGames[ctx.channel.id].join(ctx.author):
            if not ctx.author.dm_channel:
                await ctx.author.create_dm()
            self.__currentUsers[ctx.channel.id][ctx.author.id] = ctx.author.dm_channel.id
            self.__userChannel[ctx.author.id] = ctx.channel.id

    @commands.command(
        name="begin", description="To start a launched game on the channel"
    )
    async def begin(self, ctx: Context):
        if not await self.inGameChannel(ctx):
            return
        await self.__currentGames[ctx.channel.id].begin(ctx.author)

    @commands.command(
        name="p", description="To pick people/cards during an active game"
    )
    async def p(self, ctx: Context, arg: str):
        if await self.validSourceChannel(ctx) and self.getGame(ctx.author.id):
            gameChannel = self.getGame(ctx.author.id)
            await self.__currentGames[gameChannel].pick(ctx, arg)

    @p.error
    async def pick_error(self, ctx: Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argument to pick")
        elif isinstance(error, commands.TooManyArguments):
            await ctx.send("Thats too many parameters")

    @commands.command(
        name="v",
        description="To vote during an active game. Valid parameters: Ja/Nein",
    )
    async def v(self, ctx: Context, arg: str):
        if await self.validSourceChannel(ctx) and self.getGame(ctx.author.id):
            gameChannel = self.getGame(ctx.author.id)
            await self.__currentGames[gameChannel].vote(ctx, arg)

    @v.error
    async def vote_error(self, ctx: Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argument to pick")
        elif isinstance(error, commands.TooManyArguments):
            await ctx.send("Thats too many parameters")

    @commands.command(name="see", description="To see the top 3 cards in the draw pile")
    async def see(self, ctx: Context):
        if await self.validSourceChannel(ctx) and self.getGame(ctx.author.id):
            gameChannel = self.getGame(ctx.author.id)
            await self.__currentGames[gameChannel].see(ctx)

    @commands.command(
        name="veto", description="To veto this round and proceed to the next one"
    )
    async def veto(self, ctx: Context):
        if await self.validSourceChannel(ctx) and self.getGame(ctx.author.id):
            gameChannel = self.getGame(ctx.author.id)
            await self.__currentGames[gameChannel].veto(ctx)

    @commands.command(name="status", description="Show the current game phase and state")
    async def status(self, ctx: Context):
        if not await self.inGameChannel(ctx):
            return
        await self.__currentGames[ctx.channel.id].send_status(ctx.channel)

    @commands.command(name="kick", description="Kick a player from the lobby (owner only, before game starts)")
    async def kick(self, ctx: Context, arg: str):
        if not await self.inGameChannel(ctx):
            return
        game = self.__currentGames[ctx.channel.id]
        if ctx.author.id != game.owner.id:
            await ctx.send(f"Sorry {ctx.author.name}, only the game owner can kick players")
            return
        user_id = Players.parse_mention(arg)
        if user_id is None:
            await ctx.send("Please mention a valid player, e.g. `sh!kick @user`")
            return
        if user_id == ctx.author.id:
            await ctx.send("You can't kick yourself")
            return
        kicked_name = await game.kick(user_id)
        if kicked_name is None:
            await ctx.send("That player isn't in the lobby, or the game is already in progress")
            return
        self.__currentUsers[ctx.channel.id].pop(user_id, None)
        self.__userChannel.pop(user_id, None)
        await ctx.send(f"**{kicked_name}** has been removed from the lobby")

    @kick.error
    async def kick_error(self, ctx: Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `sh!kick @user`")
        elif isinstance(error, commands.TooManyArguments):
            await ctx.send("Too many arguments — usage: `sh!kick @user`")

    @commands.command(
        name="help", description="Help command to display all valid commands"
    )
    async def help(self, ctx: Context):
        help_embed = discord.Embed(
            title="***\t List of valid commands ***",
            description="For any feedbacks regarding the game please reach out to *bot0.secrethitler@gmail.com* or *bot1.secrethitler@gmail.com*",
            colour=colours["LUMINOUS_VIVID_PINK"],
        )
        for cmd in self.get_commands():
            help_embed.add_field(name=cmd.name, value=cmd.description)
        help_embed.set_footer(
            text="Commands p and v require 1 mandatory parameter")
        await ctx.send(embed=help_embed)


async def main():
    # message_content and members are privileged intents — enable both in the
    # Discord Developer Portal (Bot → Privileged Gateway Intents) before running.
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="sh!", intents=intents)

    async with bot:
        await bot.add_cog(Engine(bot))
        with open("./auth.json", "r") as auth_file:
            token = json.load(auth_file)["token"]
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
