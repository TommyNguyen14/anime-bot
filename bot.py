import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from utils.database import AnimeDatabase
from utils.config import Config

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class AnimeBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=Config.PREFIX,
            intents=discord.Intents.all(),
            help_command=None
        )
        
        self._command_locks = {}
        
        # Initialize database
        print("Initializing database...")
        self.db = AnimeDatabase()

    async def setup_hook(self):
        """Called before the bot starts running"""
        print("Loading extensions...")
        try:
            # Initialize database first
            print("Ensuring database is initialized...")
            if not await self.db.ensure_initialized():
                print("Failed to initialize database!")
                return

            # Load extensions
            print("Loading help cog...")
            await self.load_extension('cogs.help')
            print("Loading character guess cog...")
            await self.load_extension('cogs.character_guess')
            print("Extensions loaded!")
            
        except Exception as e:
            print(f"Error during setup: {str(e)}")

    async def on_ready(self):
        """Called when the bot is ready"""
        print(f"Logged in as {self.user}")
        
        # Sync commands after bot is ready
        print("Syncing commands...")
        try:
            await self.tree.sync()
            print("Commands synced!")
        except Exception as e:
            print(f"Error syncing commands: {e}")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Game(name="anime.ahhhh | ;help")
        )
        print("Bot is ready!")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        print(f"Command error: {str(error)}")

    async def on_message(self, message):
        """Handle messages in both DMs and servers"""
        if message.author.bot:
            return
        await self.process_commands(message)

    async def load_extensions(self):
        """Load all cog extensions"""
        if self._extensions_loaded:
            return

        try:
            # Load each cog from the cogs directory
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    cog_name = f'cogs.{filename[:-3]}'
                    try:
                        await self.load_extension(cog_name)
                        print(f"Loaded extension: {cog_name}")
                    except Exception as e:
                        print(f"Failed to load extension {cog_name}: {e}")

            self._extensions_loaded = True
            print("All extensions loaded successfully")
        except Exception as e:
            print(f"Error loading extensions: {e}")

def run_bot():
    bot = AnimeBot()
    bot.run(TOKEN)

if __name__ == "__main__":
    run_bot() 