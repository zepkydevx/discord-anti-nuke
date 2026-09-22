# discord-anti-nuke

![Tests](https://github.com/zepkydevx/discord-anti-nuke/actions/workflows/tests.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

A Discord bot that watches a server's audit log for destructive actions
(mass channel deletions, role deletions, bans, kicks) and scores how
dangerous each actor's recent behaviour looks, in real time.

This is a **demonstration project**. It is not running publicly, and it is
not meant to be a finished product — it exists to show how I approach
security-oriented Discord bot development: threat scoring, automated
tests, and clean, typed, documented code.

## The problem

A server raid usually looks like the same person deleting several
channels or roles within a few seconds. A single deletion is normal
housekeeping; a burst of them, evenly spaced and very fast, is what an
automated nuke script looks like. The bot tells those two apart.

## How the detection works

Every destructive action an actor performs is added to a sliding time
window (`antinuke/scoring.py`). The window is scored on three signals:

- **Speed** — the average time between actions. A human takes a couple
  of seconds per deletion; a script takes milliseconds.
- **Volume** — how many destructive actions happened in the window.
- **Regularity** — how evenly spaced the actions are. Very even timing
  is a sign of a script rather than a person.

Each signal adds points (0–100 total), and the total score maps to a
threat level: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`. Every assessment
comes with a plain-text explanation of why it got that score, so the
decision is never a black box.

**The thresholds are configuration, not hardcoded rules.** A few slow,
spaced-out deletions — someone manually cleaning up unused "junk"
channels, for example — will not trip an alarm, because the speed and
regularity signals stay low. The exact numbers (how many actions, how
fast, how regular) are named constants at the top of `scoring.py`
(`SPEED_BRACKETS`, `VOLUME_BRACKETS`, `REGULARITY_MAX_VARIATION`,
`LEVEL_THRESHOLDS`), so the sensitivity can be tuned per server without
touching the detection logic itself.

## Live test results

Tested against a real Discord server using the bot's own audit-log
listener (`antinuke/detector.py`). Channels were deleted by hand at
different speeds to see how the score responds.

**Test 1 — single deletion, no alarm.** One channel deleted, then
another a while later. No line was logged: a lone or slow deletion
never reaches the `MEDIUM` threshold, by design.

**Test 2 — a few channels, seconds apart.**
```
WARNING | antinuke.detector | MEDIUM threat | score=30 | 3 actions in
the window (channel_delete x3); average 5.96s between actions (+15);
3 actions in a short time (+15)
```

**Test 3 — several channels deleted back to back.**
```
ERROR | antinuke.detector | HIGH threat | score=70 | 6 actions in the
window (channel_delete x6); average 5.62s between actions (+15);
6 actions in a short time (+35); machine-like regular timing (+20)
```

The score climbs with every additional fast action, and the "machine-like
regular timing" reason appears once the spacing becomes suspiciously even
— exactly the pattern an automated raid script leaves behind.

## Current scope

- ✅ Audit-log listener for channel/role deletions, bans and kicks
- ✅ Explainable threat scoring with a sliding time window
- ✅ Trusted-actor list (never flagged)
- ✅ 12 automated unit tests, run on every push via GitHub Actions
- 🚧 Automatic response (stripping roles / banning the actor) — scoring
  is verified first; the response step is next
- 🚧 Off-server logging (so a raid that bans the bot doesn't erase the
  evidence)

## Project structure

```
discord-anti-nuke/
├── antinuke/
│   ├── bot.py          # Discord client, minimal intents
│   ├── config.py       # Environment-based settings, no hardcoded secrets
│   ├── detector.py      # Audit-log listener → feeds the scorer
│   ├── models.py       # Shared data types
│   └── scoring.py      # The explainable threat-scoring logic
├── tests/
│   └── test_scoring.py  # 12 unit tests, no Discord connection needed
├── main.py
└── requirements.txt
```

## Running it

```bash
git clone https://github.com/zepkydevx/discord-anti-nuke
cd discord-anti-nuke
pip install -r requirements.txt
cp .env.example .env   # then add your own bot token
python main.py
```

Run the tests with:
```bash
pip install -r requirements-dev.txt
pytest
```

## Stack

Python, [discord.py](https://discordpy.readthedocs.io/), pytest, GitHub
Actions.

## License

MIT — see [LICENSE](LICENSE).
