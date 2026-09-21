"""Entry point. Run with: python main.py"""

from __future__ import annotations

import logging

from antinuke.bot import AntiNukeBot
from antinuke.config import ConfigError, load_settings


def main() -> None:
    """Load the configuration, set up logging and start the bot."""
    try:
        settings = load_settings()
    except ConfigError as error:
        raise SystemExit(f"Configuration error: {error}") from error

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    bot = AntiNukeBot(settings)
    # log_handler=None: our own logging setup above is used instead of discord.py's.
    bot.run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
