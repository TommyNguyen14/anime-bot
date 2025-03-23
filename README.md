# Anime Discord Bot

A Discord bot that provides anime information and a character guessing game.

## Features

### Anime Wiki Cog
- `!anime <query>` - Search for anime information from MyAnimeList
- `!random_anime` - Get a random anime recommendation

### Guessing Game Cog
- `!guess` - Start a new anime character guessing game
- `!hint` - Get a hint about the current character
- `!guess_character <name>` - Make a guess for the character
- `!end_game` - End the current game

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory with your Discord bot token:
```
DISCORD_TOKEN=your_bot_token_here
```

3. Run the bot:
```bash
python bot.py
```

## Directory Structure
```
├── bot.py              # Main bot file
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this)
├── data/
│   └── characters.json # Character data for the guessing game
└── cogs/
    ├── anime_wiki.py  # Anime information cog
    └── guessing_game.py # Character guessing game cog
```

## Adding More Characters
You can add more characters to the guessing game by editing the `data/characters.json` file. Each character should have a name and a list of hints.

## Note
Make sure to invite the bot to your server with the necessary permissions (Send Messages, Embed Links, etc.). 