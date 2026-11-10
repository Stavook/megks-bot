import discord
from discord.ext import commands
import config
import logging
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

log = logging.getLogger("megks_bot")

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{config.PREFIX}help"
    ))


async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog)
                print(f"Loaded: {cog}")
            except Exception:
                log.exception("Failed to load %s", cog)


async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())