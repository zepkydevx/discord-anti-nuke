"""Bot class definition."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .config import Settings

log = logging.getLogger(__name__)


def build_intents() -> discord.Intents:
    """Return only the intents the anti-nuke modules actually need.

    Starting from ``Intents.none()`` follows the principle of least privilege:
    nothing is received unless it is enabled explicitly below.
    """
    intents = discord.Intents.none()
    intents.guilds = True       # channel, role and webhook events
    intents.moderation = True   # ban/unban events and audit-log entries
    intents.members = True      # privileged: enable "Server Members Intent" in the portal
    return intents


class AntiNukeBot(commands.Bot):
    """Discord client that hosts the anti-nuke modules."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=build_intents(),
        )
        self.settings = settings

    async def setup_hook(self) -> None:
        """Run once before the bot connects; extensions are loaded here."""
        # Detector, restorer and logging extensions will be registered here.
        log.info("Setup complete")

    async def on_ready(self) -> None:
        """Log a short message once the bot is connected."""
        if self.user is None:
            return
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
