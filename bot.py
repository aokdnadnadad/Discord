import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv
from music import MusicCog
from invites import InviteTrackerCog
from moderation import ModerationCog
from bot_warnings import WarningsCog
from mute import MuteCog
from audit_log import AuditLogCog

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
intents.voice_states = True

ALLOWED_CHANNELS = ["bot-commands", "ticket-logs"]
MOD_COMMANDS = {"purge", "warn", "clearwarnings", "memberssince", "mute", "unmute"}

bot = commands.Bot(command_prefix="?", intents=intents)


@bot.check
async def restrict_to_allowed_channels(ctx):
    """Only allow commands in approved channels."""
    if ctx.command and ctx.command.name in MOD_COMMANDS:
        return True
    if ctx.channel.name in ALLOWED_CHANNELS:
        return True
    await ctx.send("Commands can only be used in #bot-commands.", delete_after=5)
    return False


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.command(name="commands")
async def commands_list(ctx):
    """Show all available bot commands."""
    embed = discord.Embed(
        title="Bot Commands",
        description="Prefix: **?** — All commands must be used in #bot-commands",
        color=discord.Color.from_rgb(255, 105, 180),
    )
    embed.add_field(
        name="Music",
        value=(
            "**?play <song>** — Play a song from YouTube\n"
            "**?skip** — Skip the current song\n"
            "**?queue** — Show the song queue\n"
            "**?np** — Show the currently playing song\n"
            "**?shuffle** — Shuffle the queue\n"
            "**?remove <#>** — Remove a song from the queue by position\n"
            "**?pause** — Pause playback\n"
            "**?resume** — Resume playback\n"
            "**?stop** — Stop and clear the queue\n"
            "**?join** — Join your voice channel\n"
            "**?leave** — Leave the voice channel"
        ),
        inline=False,
    )
    embed.add_field(
        name="Invites",
        value=(
            "**?invites** — Check your invite count\n"
            "**?invites @user** — Check someone else's invites\n"
            "\n*Invite 5 people to earn the **Pink Nametag** role!*"
        ),
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="memberssince", hidden=True)
async def members_since(ctx: commands.Context, *, date_str: str):
    """List members who joined after a given date/time. Usage: ?memberssince YYYY-MM-DD HH:MM (EST)"""
    has_owner = discord.utils.get(ctx.author.roles, name="Owner") is not None
    if not has_owner:
        return

    import datetime, pytz
    est = pytz.timezone("America/New_York")

    try:
        naive_dt = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")
        cutoff = est.localize(naive_dt).astimezone(pytz.utc).replace(tzinfo=None)
    except ValueError:
        return await ctx.send("Invalid format. Use: `?memberssince YYYY-MM-DD HH:MM` (EST)", delete_after=10)

    matched = [
        m for m in ctx.guild.members
        if not m.bot and m.joined_at and m.joined_at.replace(tzinfo=None) > cutoff
    ]
    matched.sort(key=lambda m: m.joined_at)

    if not matched:
        return await ctx.send("No members found after that date/time.", delete_after=10)

    # Split into chunks of 50 mentions to avoid hitting Discord's 2000 char limit
    chunk_size = 50
    chunks = [matched[i:i+chunk_size] for i in range(0, len(matched), chunk_size)]
    await ctx.send(f"Found **{len(matched)}** members — sending in chunks:")
    for chunk in chunks:
        await ctx.send(" ".join(m.mention for m in chunk))


async def main():
    async with bot:
        await bot.add_cog(MusicCog(bot))
        await bot.add_cog(InviteTrackerCog(bot))
        await bot.add_cog(ModerationCog(bot))
        await bot.add_cog(WarningsCog(bot))
        await bot.add_cog(MuteCog(bot))
        await bot.add_cog(AuditLogCog(bot))
        await bot.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
