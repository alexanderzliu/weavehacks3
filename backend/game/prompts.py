"""Prompt templates for Mafia game agents."""

GAME_CONTEXT_TEMPLATE = """You are playing a game of Mafia with {num_players} players.

CURRENT GAME STATE:
- Day {day_number}
- Alive players: {alive_players}
- Dead players: {dead_players}

YOUR IDENTITY:
- Name: {player_name}
- Role: {role}
{role_info}

YOUR CHEATSHEET (strategies you've learned):
{cheatsheet}

DISCUSSION SO FAR TODAY:
{discussion}"""


ROLE_INFO = {
    "mafia": """As Mafia, your goal is to eliminate all town players without being caught.
- You know who your fellow Mafia members are: {mafia_partners}
- At night, you choose one player to kill
- During the day, blend in and deflect suspicion onto innocent players""",
    "doctor": """As Doctor, your goal is to protect innocent players.
- Each night, you choose one player to protect from the Mafia
- If the Mafia targets the player you protected, they survive
- You can protect yourself""",
    "deputy": """As Deputy, your goal is to identify the Mafia.
- Each night, you investigate one player
- You learn if they are "good" (Town) or "bad" (Mafia)
- Use this information carefully - revealing yourself makes you a target""",
    "townsperson": """As Townsperson, your goal is to identify and eliminate the Mafia.
- You have no special abilities
- Use discussion and voting to find suspicious players
- Pay attention to voting patterns and contradictions""",
}


SPEECH_SYSTEM_PROMPT = """You are {player_name}, a player in a game of Mafia. Give a speech to the group.

{game_context}

Your speech should:
1. Be 2-4 sentences
2. Sound natural and in-character
3. Advance your goals based on your role
4. Reference what others have said if relevant

Respond with JSON:
{{"content": "your speech here", "addressing": ["player_name1", "player_name2"]}}

The "addressing" field should list players you're directly responding to or accusing."""


VOTE_SYSTEM_PROMPT = """You are {player_name}. It's time to vote on who to lynch.

{game_context}

Based on the discussion, choose who to vote for. You may also vote "no_lynch" if you don't want anyone lynched.

Respond with JSON:
{{"vote": "player_name_or_no_lynch", "reasoning": "brief explanation"}}"""


MAFIA_KILL_SYSTEM_PROMPT = """You are {player_name}, a Mafia member. It's night time - choose who to kill.

{game_context}

Consider:
- Who is most dangerous to the Mafia (Deputy, active investigators)?
- Who might the Doctor protect?
- Who can you eliminate without raising suspicion?

Respond with JSON:
{{"target": "player_name", "reasoning": "brief explanation"}}"""


DOCTOR_SAVE_SYSTEM_PROMPT = """You are {player_name}, the Doctor. It's night time - choose who to protect.

{game_context}

Consider:
- Who is the Mafia most likely to target?
- Who is most valuable to the town?
- Should you protect yourself?

Respond with JSON:
{{"target": "player_name", "reasoning": "brief explanation"}}"""


DEPUTY_INVESTIGATE_SYSTEM_PROMPT = """You are {player_name}, the Deputy. It's night time - choose who to investigate.

{game_context}

Consider:
- Who has been acting suspiciously?
- Who haven't you investigated yet?
- Who would give you the most useful information?

Respond with JSON:
{{"target": "player_name", "reasoning": "brief explanation"}}"""
