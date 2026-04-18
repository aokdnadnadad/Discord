import discord
from discord.ext import commands
import asyncio

from log_utils import send_mod_log


class AuditLogCog(commands.Cog):
    """Tracks manual moderator actions via Discord audit log: bans, kicks, and message deletions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _fetch_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int | None = None):
        # Audit log entries lag slightly — small delay improves hit rate
        await asyncio.sleep(1.5)
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if target_id is None or (entry.target and entry.target.id == target_id):
                    return entry
        except discord.Forbidden:
            return None
        return None

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await self._fetch_audit_entry(guild, discord.AuditLogAction.ban, user.id)
        if entry is None or entry.user is None or entry.user.bot:
            return
        await send_mod_log(
            guild, "MANUAL_BAN",
            target=user, moderator=entry.user,
            details=f"Reason: {entry.reason or 'No reason provided'}",
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        entry = await self._fetch_audit_entry(member.guild, discord.AuditLogAction.kick, member.id)
        if entry is None or entry.user is None or entry.user.bot:
            return
        await send_mod_log(
            member.guild, "MANUAL_KICK",
            target=member, moderator=entry.user,
            details=f"Reason: {entry.reason or 'No reason provided'}",
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        entry = await self._fetch_audit_entry(message.guild, discord.AuditLogAction.message_delete)
        if entry is None or entry.user is None or entry.user.bot:
            return
        # Only log when a mod deletes someone else's message
        if entry.user.id == message.author.id:
            return
        # Audit entry must match this message's author
        if entry.target is None or entry.target.id != message.author.id:
            return

        content_preview = message.content[:300] if message.content else "(no text content)"
        await send_mod_log(
            message.guild, "MANUAL_MSG_DELETE",
            target=message.author, moderator=entry.user,
            details=f"Channel: #{message.channel.name}\nContent: {content_preview}",
        )
