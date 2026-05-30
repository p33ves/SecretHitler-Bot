import json
import os

import discord
from discord.ext import commands
from discord.ext.commands import Context

from game_handler import Game
from static_data import colours, images


class Engine(commands.Cog):
    def __init__(self, bot):
        self.__currentGames = dict()
        self.__currentUsers = dict()
        self.__bot = bot
        self.__bot.remove_command("help")

    def checkGames(self, channelID: int) -> bool:
        return channelID in self.__currentGames.keys()

    def checkActiveUser(self, userID: int) -> bool:
        for users in self.__currentUsers.values():
            if userID in users.keys():
                return True
        return False

    def getGame(self, userID: int) -> int:
        for channelID, users in self.__currentUsers.items():
            if userID in users.keys():
                return channelID
        return 0

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
        validUser = False
        for channelID, users in self.__currentUsers.items():
            if (
                ctx.author.id in users.keys()
                and channelID in self.__currentGames.keys()
            ):
                validUser = True
                if (
                    ctx.channel.id == channelID
                    or ctx.channel.id == users[ctx.author.id]
                ):
                    return True
        if validUser:
            await ctx.send(
                f"Sorry {ctx.author.name}, correspondence through this channel is not allowed"
            )
        else:
            await ctx.send(f"Sorry {ctx.author.name}, you don't seem to be in a game")
        return False

    async def closeGame(self, ctx, returnFlag) -> bool:
        if returnFlag:
            await ctx.send("Thanks for playing!")
            self.reset(ctx)

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
        # TODO Allow reset only by owners/ autoreset after a timeout
        if ctx.channel.id in self.__currentGames.keys():
            del self.__currentGames[ctx.channel.id]
        if ctx.channel.id in self.__currentUsers.keys():
            del self.__currentUsers[ctx.channel.id]
        if os.path.exists(
            images["currentboard.png"].replace(
                "<channelID>", f"{ctx.channel.id}")
        ):
            os.remove(
                images["currentboard.png"].replace(
                    "<channelID>", f"{ctx.channel.id}")
            )
        if os.path.exists(
            images["newbase.png"].replace("<channelID>", f"{ctx.channel.id}")
        ):
            os.remove(images["newbase.png"].replace(
                "<channelID>", f"{ctx.channel.id}"))
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
            self.__currentGames[ctx.channel.id] = Game(ctx.channel, ctx.author)
            self.__currentUsers[ctx.channel.id] = dict()
            await self.__currentGames[ctx.channel.id].launch()

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
        elif len(ctx.args) > 1:
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
        elif len(ctx.args) > 1:
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


def main():
    with open("./auth.json", "r") as _authFile:
        token = json.load(_authFile)["token"]
    bot = commands.Bot(command_prefix="sh!")
    bot.add_cog(Engine(bot))
    bot.run(token)


if __name__ == "__main__":
    main()
