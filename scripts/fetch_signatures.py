"""Fetch every rostered player's most played champions from gol.gg and write them to
app/game/signatures.json, the source of signature champions.

    python -m scripts.fetch_signatures

gol.gg's player list for the current season gives each player's id, and their career page
(all seasons) lists how many games they have played on every champion. The script waits a
few seconds between requests, so a full run takes about five minutes. Champions outside
the game's pool are skipped, and each player keeps their ten most played. Players already
in the file are skipped, so an interrupted run picks up where it stopped."""

import json
import re
import time
from datetime import date
from pathlib import Path

import httpx

from app.game.data import CHAMPIONS, TEAMS

BASE = "https://gol.gg"
SEASON = "S16"  # 2026
HEADERS = {"User-Agent": "Mozilla/5.0 (riftlike signature fetch, personal fan project)"}
OUT = Path(__file__).resolve().parent.parent / "app" / "game" / "signatures.json"
KEEP = 10
PAUSE = 3  # seconds between requests

PLAYER_LINK = re.compile(r"""href=['"]\./player-stats/(\d+)/[^'"]*['"][^>]*>([^<]+)</a>""")
CHAMPION_ROW = re.compile(
    r"""champion-stats/\d+/[^'"]*['"]><img[^>]*alt=['"]([^'"]+)['"][^>]*>[^<]*</a></td>\s*<td[^>]*>(\d+)</td>"""
)


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# gol.gg writes some champions the way the game client does internally.
_ALIASES = {"monkeyking": "Wukong", "nunu": "Nunu & Willump", "renata": "Renata Glasc"}
_BY_KEY = {_key(name): name for name in CHAMPIONS} | {k: v for k, v in _ALIASES.items() if v in CHAMPIONS}


def get(client: httpx.Client, path: str) -> str:
    response = client.get(BASE + path)
    response.raise_for_status()
    time.sleep(PAUSE)
    return response.text


def player_ids(client: httpx.Client) -> dict[str, str]:
    html = get(client, f"/players/list/season-{SEASON}/split-ALL/tournament-ALL/")
    ids: dict[str, str] = {}
    for player_id, name in PLAYER_LINK.findall(html):
        ids.setdefault(name.strip().lower(), player_id)
    return ids


def career(client: httpx.Client, player_id: str) -> list[tuple[str, int]]:
    """Champions this player has played across their whole career, most played first."""
    html = get(client, f"/players/player-stats/{player_id}/season-ALL/split-ALL/tournament-ALL/")
    picks = [(_BY_KEY.get(_key(champ)), int(games)) for champ, games in CHAMPION_ROW.findall(html)]
    picks = [(champ, games) for champ, games in picks if champ]
    picks.sort(key=lambda cg: -cg[1])
    return picks


def save(players: dict) -> None:
    payload = {"source": "gol.gg career champion pools", "fetched": str(date.today()), "players": players}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    players: dict = existing.get("players", {})
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as client:
        ids = player_ids(client)
        for team in TEAMS:
            for role, player in team.players.items():
                if player in players:
                    continue
                player_id = ids.get(player.lower())
                if player_id is None:
                    print(f"{team.code} {role} {player}: not in the {SEASON} player list", flush=True)
                    players[player] = {"gol_id": None, "role": role, "champions": []}
                else:
                    picks = career(client, player_id)[:KEEP]
                    players[player] = {"gol_id": player_id, "role": role, "champions": picks}
                    print(f"{team.code} {role} {player}: {', '.join(f'{c} {g}' for c, g in picks)}", flush=True)
                save(players)
    print("done", flush=True)


if __name__ == "__main__":
    main()
