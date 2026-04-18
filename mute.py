import discord
from discord.ext import commands
import datetime
import re

from log_utils import send_mod_log

# Matches duration components like "1d", "5h", "10m" — combinable with spaces
DURATION_PATTERN = re.compile(r"(\d+)\s*([dhm])", re.IGNORECASE)

# Discord's max timeout is 28 days
MAX_TIMEOUT_SECONDS = 28 * 24 * 60 * 60


def parse_duration(text: str) -> tuple[datetime.timedelta | None, str]:
    """Parse a duration string like '1d 5h 10m' into a timedelta.
    Returns (timedelta, human_readable) or (None, error_message)."""
    if not text:
        return None, "No duration provided"

    matches = DURATION_PATTERN.findall(text)
    if not matches:
        return None, "Invalid format. Use like: `10m`, `1h`, `1d 5h 10m`"

    total_seconds = 0
    parts = []
    for value, unit in matches:
        value = int(value)
        unit = unit.lower()
        if unit == "d":
            total_seconds += value * 86400
            parts.append(f"{value}d")
        elif unit == "h":
            total_seconds += value * 3600
            parts.append(f"{value}h")
        elif unit == "m":
            total_seconds += value * 60
            parts.append(f"{value}m")

    if total_seconds <= 0:
        return None, "Duration must be greater than 0"
    if total_seconds > MAX_TIMEOUT_SECONDS:
        return None, "Duration cannot exceed 28 days (Discord's limit)"

    return datetime.timedelta(seconds=total_seconds), " ".join(parts)


class MuteCog(commands.Cog):
    """Mute (timeout) users by duration. Usable by @Moderator, Owner, or Admin."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_authorized(self, member: discord.Member) -> bool:
        has_owner = discord.utils.get(member.roles, name="Owner") is not None
        has_mod = discord.utils.get(member.roles, name="Moderator") is not None
        return has_owner or has_mod or member.guild_permissions.administrator

    @commands.command(name="mute", hidden=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, *, duration_and_reason: str):
        """Mute a user. Usage: ?mute @user <duration> [reason]"""
        if not self._is_authorized(ctx.author):
            return

        # Split into duration + reason — the duration is everything up to the first non-duration token
        tokens = duration_and_reason.strip().split()
        duration_tokens = []
        reason_tokens = []
        for i, tok in enumerate(tokens):
            if DURATION_PATTERN.fullmatch(tok):
                duration_tokens.append(tok)
            else:
                reason_tokens = tokens[i:]
                break

        if not duration_tokens:
            return await ctx.send(
                "Usage: `?mute @user <duration> [reason]` — e.g. `?mute @bob 1h 30m spamming`",
                delete_after=8,
            )

        duration_str = " ".join(duration_tokens)
        reason = " ".join(reason_tokens) if reason_tokens else "No reason provided"

        delta, result = parse_duration(duration_str)
        if delta is None:
            return await ctx.send(result, delete_after=8)

        until = discord.utils.utcnow() + delta
        try:
            await member.timeout(until, reason=f"Muted by {ctx.author}: {reason}")
        except discord.Forbidden:
            return await ctx.send("I don't have permission to mute that user.", delete_after=5)
        except discord.HTTPException as e:
            return await ctx.send(f"Failed to mute: {e}", delete_after=5)

        await ctx.send(
            f"**{member}** has been muted for **{result}**. Reason: {reason}",
            delete_after=10,
        )

        try:
            await member.send(
                f"You have been muted in **{ctx.guild.name}** for **{result}**.\nReason: {reason}"
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        await send_mod_log(
            ctx.guild, "MUTE",
            target=member, moderator=ctx.author,
            details=f"Duration: {result} | Reason: {reason}",
        )

    @commands.command(name="unmute", hidden=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Unmute a user. Usage: ?unmute @user"""
        if not self._is_authorized(ctx.author):
            return

        try:
            await member.timeout(None, reason=f"Unmuted by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("I don't have permission to unmute that user.", delete_after=5)

        await ctx.send(f"**{member}** has been unmuted.", delete_after=10)
        await send_mod_log(
            ctx.guild, "UNMUTE",
            target=member, moderator=ctx.author,
            details="Timeout cleared",
        )

    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("User not found.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Usage: `?mute @user <duration> [reason]` — e.g. `?mute @bob 1h 30m spamming`",
                delete_after=8,
            )

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("User not found.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `?unmute @user`", delete_after=5)
