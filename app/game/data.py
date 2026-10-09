"""Static game data: champions, duo synergies, Worlds 2026 teams and signature picks."""

from dataclasses import dataclass
from functools import lru_cache

from app.game.state import ROLES, Role

ROLE_LETTER: dict[str, Role] = {"T": "TOP", "J": "JGL", "M": "MID", "B": "BOT", "S": "SUP"}
FOCUS = {"E": "early", "M": "mid", "L": "late"}

# name | roles (first one is the main role) | focus | damage (AD, AP, MX = mixed) | class
_CHAMPIONS = """
Aatrox|T|E|AD|Fighter
Ambessa|T|M|AD|Fighter
Camille|TS|M|AD|Fighter
Cho'Gath|T|L|AP|Tank
Darius|T|E|AD|Fighter
Dr. Mundo|T|L|AD|Tank
Fiora|T|L|AD|Fighter
Gangplank|T|L|AD|Fighter
Garen|T|M|AD|Fighter
Gnar|T|M|AD|Fighter
Gragas|TJS|M|AP|Tank
Gwen|TJ|L|AP|Fighter
Irelia|TM|M|AD|Fighter
Jax|TJ|L|AD|Fighter
Jayce|TM|E|AD|Fighter
K'Sante|T|M|AD|Tank
Kayle|T|L|AP|Fighter
Kennen|T|M|AP|Mage
Kled|T|E|AD|Fighter
Malphite|TS|M|AP|Tank
Mordekaiser|T|M|AP|Fighter
Nasus|T|L|AD|Fighter
Ornn|T|L|AP|Tank
Poppy|TJS|M|AD|Tank
Renekton|T|E|AD|Fighter
Riven|T|E|AD|Fighter
Rumble|TMJ|M|AP|Mage
Shen|TS|M|AD|Tank
Sion|T|L|AD|Tank
Tahm Kench|TS|M|AP|Tank
Teemo|T|M|AP|Mage
Urgot|T|M|AD|Fighter
Volibear|TJ|E|AD|Fighter
Yorick|T|M|AD|Fighter
Zac|TJ|M|AP|Tank
Amumu|J|M|AP|Tank
Bel'Veth|J|L|AD|Fighter
Brand|JS|M|AP|Mage
Briar|J|E|AD|Fighter
Diana|JM|M|AP|Assassin
Ekko|JM|M|AP|Assassin
Elise|J|E|AP|Assassin
Evelynn|J|M|AP|Assassin
Fiddlesticks|J|M|AP|Mage
Graves|J|M|AD|Marksman
Hecarim|J|M|AD|Fighter
Ivern|J|L|AP|Enchanter
Jarvan IV|J|E|AD|Tank
Karthus|J|L|AP|Mage
Kayn|J|M|AD|Assassin
Kha'Zix|J|M|AD|Assassin
Kindred|J|L|AD|Marksman
Lee Sin|J|E|AD|Fighter
Lillia|J|M|AP|Mage
Maokai|JS|M|AP|Tank
Master Yi|J|L|AD|Assassin
Nidalee|J|E|AP|Assassin
Nocturne|J|M|AD|Assassin
Nunu & Willump|J|M|AP|Tank
Pantheon|JTMS|E|AD|Fighter
Rammus|J|M|AP|Tank
Rek'Sai|J|E|AD|Fighter
Sejuani|J|M|AP|Tank
Shyvana|J|L|MX|Fighter
Skarner|JT|M|AD|Tank
Udyr|J|M|MX|Fighter
Vi|J|E|AD|Fighter
Viego|J|M|AD|Assassin
Warwick|J|E|AD|Fighter
Wukong|JT|M|AD|Fighter
Xin Zhao|J|E|AD|Fighter
Ahri|M|M|AP|Mage
Akali|MT|M|AP|Assassin
Akshan|M|E|AD|Marksman
Anivia|M|L|AP|Mage
Annie|MS|M|AP|Mage
Aurora|MT|M|AP|Mage
Azir|M|L|AP|Mage
Cassiopeia|MT|L|AP|Mage
Corki|M|L|MX|Marksman
Galio|MS|M|AP|Tank
Hwei|MS|M|AP|Mage
Kassadin|M|L|AP|Assassin
Katarina|M|M|AP|Assassin
LeBlanc|M|E|AP|Assassin
Lissandra|M|M|AP|Mage
Mel|MS|M|AP|Mage
Naafiri|M|E|AD|Assassin
Neeko|MS|M|AP|Mage
Orianna|M|L|AP|Mage
Qiyana|MJ|E|AD|Assassin
Ryze|MT|L|AP|Mage
Swain|MSB|M|AP|Mage
Sylas|MJ|M|AP|Fighter
Syndra|M|M|AP|Mage
Taliyah|MJ|M|AP|Mage
Talon|MJ|E|AD|Assassin
Twisted Fate|M|M|AP|Mage
Vex|M|M|AP|Mage
Viktor|M|L|AP|Mage
Vladimir|MT|L|AP|Mage
Yasuo|MTB|M|AD|Fighter
Yone|MT|L|AD|Fighter
Zed|M|E|AD|Assassin
Ziggs|MB|L|AP|Mage
Zoe|M|M|AP|Mage
Aphelios|B|L|AD|Marksman
Ashe|BS|M|AD|Marksman
Caitlyn|B|E|AD|Marksman
Draven|B|E|AD|Marksman
Ezreal|B|M|AD|Marksman
Jhin|B|M|AD|Marksman
Jinx|B|L|AD|Marksman
Kai'Sa|B|L|MX|Marksman
Kalista|B|E|AD|Marksman
Kog'Maw|B|L|MX|Marksman
Lucian|BM|E|AD|Marksman
Miss Fortune|B|M|AD|Marksman
Nilah|B|M|AD|Fighter
Samira|B|E|AD|Marksman
Senna|BS|L|AD|Marksman
Sivir|B|M|AD|Marksman
Smolder|BMT|L|AD|Marksman
Tristana|BM|E|AD|Marksman
Twitch|B|L|AD|Marksman
Varus|B|M|AD|Marksman
Vayne|BT|L|AD|Marksman
Xayah|B|M|AD|Marksman
Yunara|B|L|AD|Marksman
Zeri|B|L|AD|Marksman
Alistar|S|E|AP|Tank
Bard|S|M|AP|Enchanter
Blitzcrank|S|E|AP|Tank
Braum|S|M|AP|Tank
Janna|S|L|AP|Enchanter
Karma|SM|M|AP|Enchanter
Leona|S|E|AP|Tank
Lulu|S|L|AP|Enchanter
Lux|SM|M|AP|Mage
Milio|S|L|AP|Enchanter
Morgana|SM|M|AP|Mage
Nami|S|M|AP|Enchanter
Nautilus|S|E|AP|Tank
Pyke|S|E|AD|Assassin
Rakan|S|M|AP|Enchanter
Rell|S|E|AP|Tank
Renata Glasc|S|M|AP|Enchanter
Seraphine|SB|M|AP|Mage
Sona|S|L|AP|Enchanter
Soraka|S|L|AP|Enchanter
Taric|S|M|AP|Tank
Thresh|S|M|AP|Tank
Vel'Koz|SMB|M|AP|Mage
Xerath|SM|M|AP|Mage
Yuumi|S|L|AP|Enchanter
Zilean|S|L|AP|Enchanter
Zyra|S|M|AP|Mage
"""


@dataclass(frozen=True)
class Champion:
    name: str
    roles: tuple[Role, ...]
    focus: str  # early, mid or late
    dmg: str  # AD, AP or MX
    cls: str


def _parse_champions() -> dict[str, Champion]:
    out: dict[str, Champion] = {}
    for line in _CHAMPIONS.strip().splitlines():
        name, roles, focus, dmg, cls = line.split("|")
        out[name] = Champion(
            name=name,
            roles=tuple(ROLE_LETTER[r] for r in roles),
            focus=FOCUS[focus],
            dmg=dmg,
            cls=cls,
        )
    return out


CHAMPIONS = _parse_champions()
CHAMPION_NAMES = list(CHAMPIONS)


@lru_cache
def main_role_pool(role: Role) -> tuple[str, ...]:
    return tuple(n for n, c in CHAMPIONS.items() if c.roles[0] == role)


# Pairs that do better together. Bot lane duos count x3, jungle + mid x2, anything else x1.
_SYNERGY = [
    ("Kalista", "Renata Glasc", 2),
    ("Kalista", "Rell", 1),
    ("Kalista", "Alistar", 1),
    ("Xayah", "Rakan", 2),
    ("Lucian", "Nami", 2),
    ("Lucian", "Braum", 1),
    ("Jinx", "Lulu", 1),
    ("Jinx", "Thresh", 1),
    ("Kai'Sa", "Nautilus", 1),
    ("Kai'Sa", "Rell", 1),
    ("Kai'Sa", "Alistar", 1),
    ("Ezreal", "Karma", 1),
    ("Zeri", "Yuumi", 1),
    ("Zeri", "Lulu", 1),
    ("Twitch", "Yuumi", 1),
    ("Aphelios", "Lulu", 1),
    ("Aphelios", "Thresh", 1),
    ("Varus", "Rell", 1),
    ("Caitlyn", "Lux", 1),
    ("Caitlyn", "Morgana", 1),
    ("Miss Fortune", "Leona", 1),
    ("Draven", "Leona", 1),
    ("Draven", "Nautilus", 1),
    ("Samira", "Nautilus", 2),
    ("Samira", "Rell", 1),
    ("Tristana", "Nautilus", 1),
    ("Kog'Maw", "Lulu", 2),
    ("Vayne", "Lulu", 1),
    ("Sivir", "Karma", 1),
    ("Smolder", "Milio", 1),
    ("Yunara", "Milio", 1),
    ("Senna", "Tahm Kench", 1),
    ("Ezreal", "Leona", -1),
    ("Kog'Maw", "Pyke", -1),
    ("Caitlyn", "Bard", -1),
    ("Jinx", "Pyke", -1),
    ("Jarvan IV", "Orianna", 1),
    ("Jarvan IV", "Galio", 1),
    ("Wukong", "Yasuo", 2),
    ("Diana", "Yasuo", 1),
    ("Nocturne", "Twisted Fate", 1),
    ("Vi", "Ahri", 1),
    ("Xin Zhao", "Galio", 1),
    ("Sejuani", "Galio", 1),
    ("Sejuani", "Orianna", 1),
    ("Maokai", "Orianna", 1),
    ("Nidalee", "Corki", 1),
    ("Lee Sin", "Syndra", 1),
    ("Ivern", "Kassadin", -1),
    ("Malphite", "Orianna", 1),
    ("Gragas", "Yasuo", 1),
    ("Alistar", "Yasuo", 1),
    ("Rakan", "Yone", 1),
]
_SYNERGY_MAP: dict[tuple[str, str], int] = {}
for _a, _b, _v in _SYNERGY:
    _SYNERGY_MAP[(_a, _b)] = _v
    _SYNERGY_MAP[(_b, _a)] = _v


def synergy_of(a: str, b: str) -> int:
    return _SYNERGY_MAP.get((a, b), 0)


# (classes, focuses) a champion must fit, None meaning any.
Fit = tuple[tuple[str, ...] | None, tuple[str, ...] | None]


@dataclass(frozen=True)
class Archetype:
    """A duo that works by type rather than by name, for one pair of slots."""

    name: str
    roles: tuple[Role, Role]
    first: Fit
    second: Fit
    value: int = 1

    def matches(self, a: Champion, role_a: Role, b: Champion, role_b: Role) -> bool:
        if (role_a, role_b) == self.roles:
            return _fits(a, self.first) and _fits(b, self.second)
        if (role_b, role_a) == self.roles:
            return _fits(b, self.first) and _fits(a, self.second)
        return False


def _fits(champ: Champion, fit: Fit) -> bool:
    classes, focuses = fit
    return (classes is None or champ.cls in classes) and (focuses is None or champ.focus in focuses)


# Checked only for pairs without a hand-picked value above, so a named duo always wins.
ARCHETYPES = [
    Archetype("Lane bullies", ("BOT", "SUP"), (("Marksman",), ("early",)), (("Tank",), ("early",))),
    Archetype("All-in lane", ("BOT", "SUP"), (("Marksman",), ("early",)), (("Tank",), ("mid",))),
    Archetype("Protect the carry", ("BOT", "SUP"), (("Marksman",), ("late",)), (("Enchanter",), None)),
    Archetype("Poke lane", ("BOT", "SUP"), (("Marksman",), ("mid",)), (("Mage",), None)),
    Archetype("Early skirmish", ("JGL", "MID"), (None, ("early",)), (("Assassin",), None)),
    Archetype("Engage and follow-up", ("JGL", "MID"), (("Tank",), None), (("Mage",), None)),
    Archetype("Side lane pressure", ("TOP", "JGL"), (None, ("early",)), (None, ("early",))),
    Archetype("Frontline for the carry", ("TOP", "BOT"), (("Tank",), None), (("Marksman",), ("late",))),
]


def archetype_of(a: str, role_a: Role, b: str, role_b: Role) -> Archetype | None:
    for archetype in ARCHETYPES:
        if archetype.matches(CHAMPIONS[a], role_a, CHAMPIONS[b], role_b):
            return archetype
    return None


@dataclass(frozen=True)
class League:
    code: str
    region: str
    strength: int


LEAGUES = [
    League("LCK", "Korea", 3),
    League("LPL", "China", 3),
    League("LEC", "EMEA", 2),
    League("LCS", "North America", 1),
    League("LCP", "Asia-Pacific", 1),
    League("CBLOL", "Brazil", 0),
]


@dataclass(frozen=True)
class Team:
    code: str
    name: str
    league: str
    seed: int
    play_in: bool
    color: str
    players: dict[Role, str]

    @property
    def rating(self) -> int:
        strength = next(l.strength for l in LEAGUES if l.code == self.league)
        return strength + (1 if self.seed == 1 else 0)


# code, name, league, seed, play-in, [top, jungle, mid, bot, support], badge color
_TEAMS = [
    ("GEN", "Gen.G", "LCK", 1, False, ["Kiin", "Canyon", "Chovy", "Ruler", "Duro"], "#b8913f"),
    ("HLE", "Hanwha Life Esports", "LCK", 2, False, ["Zeus", "Kanavi", "Zeka", "Gumayusi", "Delight"], "#e8732a"),
    ("T1", "T1", "LCK", 3, False, ["Doran", "Oner", "Faker", "Peyz", "Keria"], "#e0263c"),
    ("DK", "Dplus KIA", "LCK", 4, False, ["Siwoo", "Lucid", "ShowMaker", "Smash", "Career"], "#3aa7c9"),
    ("AL", "Anyone’s Legend", "LPL", 1, False, ["Breathe", "Tarzan", "Shanks", "Hope", "Kael"], "#c23b5a"),
    ("BLG", "Bilibili Gaming", "LPL", 2, False, ["Bin", "XUN", "Knight", "Viper", "ON"], "#2f8fe0"),
    ("TES", "Top Esports", "LPL", 3, False, ["ZUIAN", "Tian", "Creme", "JackeyLove", "Zhuo"], "#e85d2a"),
    ("IG", "Invictus Gaming", "LPL", 4, False, ["TheShy", "Wei", "RooKie", "JiaQi", "meiko"], "#9aa3ad"),
    ("G2", "G2 Esports", "LEC", 1, False, ["BrokenBlade", "SkewMond", "Caps", "Hans Sama", "Labrov"], "#d8d8d8"),
    ("MKOI", "Movistar KOI", "LEC", 2, False, ["Myrwn", "Elyoya", "jojopyun", "Supa", "Alvaro"], "#7a5cff"),
    ("KC", "Karmine Corp", "LEC", 3, True, ["Canna", "Yike", "Kyeahoo", "Caliste", "Busio"], "#3a6df0"),
    ("TLAW", "Team Liquid Alienware", "LCS", 1, False, ["Morgan", "Josedeodo", "Quid", "Yeon", "CoreJJ"], "#2c7be5"),
    ("LYON", "LYON", "LCS", 2, False, ["Dhokla", "Inspired", "Saint", "Berserker", "Isles"], "#d9b44a"),
    ("C9", "Cloud9 Kia", "LCS", 3, True, ["Thanatos", "Blaber", "Loki", "Tactical", "Vulcan"], "#3ab0f0"),
    ("TSW", "Team Secret Whales", "LCP", 1, False, ["Pun", "Hizto", "Dire", "Eddie", "Bie"], "#4fb3a9"),
    ("CFO", "CTBC Flying Oyster", "LCP", 2, False, ["Rest", "Shad0w", "Pout", "Doggo", "Kino"], "#e0a030"),
    ("MVK", "MVK Esports", "LCP", 3, True, ["Kratos", "Gury", "Chika", "Harky", "Siuloong"], "#c84b4b"),
    ("LOS", "LØS", "CBLOL", 1, False, ["Zest", "Curse", "Feisty", "Duduhh", "Ackerman"], "#55c27a"),
    ("FUR", "FURIA", "CBLOL", 2, True, ["Guigo", "Tatu", "Tutsz", "Ayu", "JoJo"], "#c9c9c9"),
]

TEAMS = [
    Team(code, name, league, seed, play_in, color, dict(zip(ROLES, players)))
    for code, name, league, seed, play_in, players, color in _TEAMS
]
_TEAM_BY_CODE = {t.code: t for t in TEAMS}


def team(code: str) -> Team | None:
    return _TEAM_BY_CODE.get(code)


# Hand-picked comfort champions, most iconic first (+5 down to +1).
# Players missing here get a stable list generated from their role's pool.
SIGNATURES: dict[str, list[str]] = {
    "Kiin": ["Kennen", "Jayce", "Gnar", "Camille", "Rumble"],
    "Canyon": ["Nidalee", "Graves", "Kindred", "Lee Sin", "Taliyah"],
    "Chovy": ["Azir", "Yone", "Sylas", "Corki", "Akali"],
    "Ruler": ["Jinx", "Varus", "Ezreal", "Kai'Sa", "Xayah"],
    "Duro": ["Rakan", "Nautilus", "Alistar", "Rell", "Braum"],
    "Zeus": ["Jayce", "Gnar", "Yone", "Aatrox", "Rumble"],
    "Kanavi": ["Lee Sin", "Graves", "Kha'Zix", "Nidalee", "Jarvan IV"],
    "Zeka": ["Akali", "Sylas", "Azir", "Yone", "Corki"],
    "Gumayusi": ["Jinx", "Aphelios", "Varus", "Kai'Sa", "Ezreal"],
    "Delight": ["Rell", "Alistar", "Nautilus", "Rakan", "Leona"],
    "Doran": ["Gragas", "K'Sante", "Jax", "Rumble", "Ornn"],
    "Oner": ["Lee Sin", "Viego", "Graves", "Jarvan IV", "Xin Zhao"],
    "Faker": ["Azir", "Ryze", "LeBlanc", "Galio", "Orianna"],
    "Peyz": ["Varus", "Zeri", "Aphelios", "Xayah", "Jinx"],
    "Keria": ["Rakan", "Bard", "Thresh", "Karma", "Lulu"],
    "ShowMaker": ["Syndra", "LeBlanc", "Twisted Fate", "Akali", "Zoe"],
    "Lucid": ["Viego", "Wukong", "Nidalee", "Lee Sin", "Maokai"],
    "Bin": ["Fiora", "Jax", "Gwen", "Rumble", "Jayce"],
    "Knight": ["Ahri", "Azir", "Orianna", "Syndra", "Taliyah"],
    "Viper": ["Kai'Sa", "Jinx", "Ezreal", "Varus", "Aphelios"],
    "ON": ["Rakan", "Nautilus", "Rell", "Alistar", "Thresh"],
    "Tian": ["Lee Sin", "Xin Zhao", "Nidalee", "Viego", "Graves"],
    "JackeyLove": ["Kai'Sa", "Draven", "Ezreal", "Xayah", "Varus"],
    "TheShy": ["Jayce", "Aatrox", "Camille", "Irelia", "Fiora"],
    "Wei": ["Lee Sin", "Xin Zhao", "Rek'Sai", "Viego", "Sejuani"],
    "RooKie": ["LeBlanc", "Syndra", "Orianna", "Taliyah", "Akali"],
    "meiko": ["Rakan", "Nautilus", "Leona", "Braum", "Thresh"],
    "Tarzan": ["Lee Sin", "Graves", "Viego", "Nidalee", "Kindred"],
    "BrokenBlade": ["Gwen", "K'Sante", "Jax", "Renekton", "Aatrox"],
    "Caps": ["Sylas", "LeBlanc", "Syndra", "Akali", "Orianna"],
    "Hans Sama": ["Kalista", "Lucian", "Draven", "Ezreal", "Xayah"],
    "Elyoya": ["Lee Sin", "Nidalee", "Xin Zhao", "Viego", "Wukong"],
    "jojopyun": ["Ahri", "Sylas", "Akali", "Taliyah", "LeBlanc"],
    "CoreJJ": ["Thresh", "Rakan", "Alistar", "Nautilus", "Braum"],
    "Inspired": ["Lee Sin", "Kindred", "Viego", "Elise", "Graves"],
    "Berserker": ["Zeri", "Aphelios", "Kai'Sa", "Varus", "Xayah"],
    "Blaber": ["Lee Sin", "Elise", "Kha'Zix", "Graves", "Xin Zhao"],
}
