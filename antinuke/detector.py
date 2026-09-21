"""Listens to Discord's audit log and feeds destructive actions to the scorer."""

from __future__ import annotations

import logging
import time

import discord
from discord.ext import commands, tasks

from .models import ActionType, ThreatEvent, ThreatLevel
from .scoring import ThreatScorer

log = logging.getLogger(__name__)

# Audit-log actions that count as destructive, mapped to our own action types.
WATCHED_ACTIONS: dict[discord.AuditLogAction, ActionType] = {
    discord.AuditLogAction.channel_delete: ActionType.CHANNEL_DELETE,
    discord.AuditLogAction.role_delete: ActionType.ROLE_DELETE,
    discord.AuditLogAction.ban: ActionType.MEMBER_BAN,
    discord.AuditLogAction.kick: ActionType.MEMBER_KICK,
}

# How loudly each threat level is written to the logs.
LOG_LEVELS: dict[ThreatLevel, int] = {
    ThreatLevel.MEDIUM: logging.WARNING,
    ThreatLevel.HIGH: logging.ERROR,
    ThreatLevel.CRITICAL: logging.CRITICAL,
}


class Detector(commands.Cog):
    """Scores each actor's destructive actions and reports the dangerous ones."""

    def __init__(self, bot: commands.Bot, scorer: ThreatScorer | None = None) -> None:
        self.bot = bot
        self.scorer = scorer or ThreatScorer()

    async def cog_load(self) -> None:
        """Start the background cleanup when the extension is loaded."""
        self._prune_idle.start()

    async def cog_unload(self) -> None:
        """Stop the background cleanup when the extension is unloaded."""
        self._prune_idle.cancel()

    @tasks.loop(minutes=5)
    async def _prune_idle(self) -> None:
        """Forget actors that have been quiet, so memory does not grow forever."""
        removed = self.scorer.prune_idle(time.time())
        if removed:
            log.debug("Pruned %d idle actors", removed)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        """Called by discord.py for every new audit-log entry."""
        action = WATCHED_ACTIONS.get(entry.action)
        if action is None or entry.user_id is None:
            return
        # Ignore the bot's own actions. The server owner is NOT exempt on
        # purpose: a hijacked owner account is the worst case, so it is scored
        # and reported like anyone else (a later step will skip punishing them).
        if self.bot.user is not None and entry.user_id == self.bot.user.id:
            return

        # Use the entry's own creation time, not the moment we received it,
        # so network delays cannot distort the speed measurement.
        event = ThreatEvent(
            guild_id=entry.guild.id,
            actor_id=entry.user_id,
            action=action,
            timestamp=entry.created_at.timestamp(),
        )
        assessment = self.scorer.record(event)

        if assessment.level in LOG_LEVELS:
            log.log(
                LOG_LEVELS[assessment.level],
                "%s threat | guild=%s actor=%s score=%d | %s",
                assessment.level.name,
                event.guild_id,
                event.actor_id,
                assessment.score,
                "; ".join(assessment.reasons),
            )


async def setup(bot: commands.Bot) -> None:
    """Entry point used by ``bot.load_extension``."""
    await bot.add_cog(Detector(bot))
