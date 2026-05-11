import discord
from discord.ext import commands
import config
import os
import sys

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{config.PREFIX}help"
    ))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        await ctx.send(f"An error occurred: {error}")
        raise error


async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog)
                print(f"Loaded: {cog}")
            except Exception as e:
                print(f"Failed to load {cog}: {e}", file=sys.stderr)


async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())