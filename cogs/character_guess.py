import discord
from discord.ext import commands
import random
from PIL import Image
import io
import aiohttp
from utils.database import AnimeDatabase
import asyncio
from discord import app_commands
from utils.config import Config
from typing import List, Dict

class CharacterGuess(commands.Cog):
    """Character guessing game commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.active_games = {}
        self._locks = {}
        self.END_GAME = "❌"
        self.PLAY_AGAIN = "🔄"
        self.EMBED_COLOR = Config.DEFAULT_COLOR
        print("CharacterGuess cog initialized!")

    @commands.command(name="c")
    async def char(self, ctx, difficulty: str = None):
        """Start a new character guessing game"""
        await self.start_new_game(ctx, difficulty)

    @commands.command(aliases=["c end"])
    async def c_end(self, ctx):
        """End the current character guessing game"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_games:
            await ctx.send("No active game in this channel!")
            return
            
        game = self.active_games[channel_id]
        if ctx.author.id != game['started_by'] and not ctx.author.guild_permissions.manage_messages:
            await ctx.send("Only the game starter or moderators can end the game!")
            return
            
        await self.end_game(ctx, show_summary=True)

    async def get_character(self, difficulty=None):
        """Get a random character for the game"""
        try:
            chars = []
            for char in self.db.characters:
                if difficulty and char.get('difficulty', '').lower() != difficulty.lower():
                    continue
                chars.append(char)
            
            if not chars:
                return None
                
            return random.choice(chars)
            
        except Exception as e:
            print(f"Error getting character: {e}")
            return None

    async def create_character_embed(self, game_data):
        """Create the character embed with game state"""
        char = game_data['character']
        embed = discord.Embed(
            title="Character Guessing Game",
            color=self.EMBED_COLOR
        )
        
        # Game status
        status = "Game Over!" if game_data.get('ended', False) else "Guess the character!"
        embed.description = f"**Status:** {status}\n**Guesses:** {game_data['guesses']}"
        
        # Current character info
        anime_title = char['anime_data']['title']
        if char['anime_data'].get('english_title'):
            anime_title += f" ({char['anime_data']['english_title']})"
            
        embed.add_field(
            name="Anime Title",
            value=anime_title,
            inline=False
        )
        
        embed.add_field(
            name="Difficulty",
            value=char['difficulty'],
            inline=True
        )
        
        # Add character history if any
        if game_data.get('history', []):
            history_text = ""
            for past_char in game_data['history']:
                result = '✅' if past_char.get('solved', False) else '❌'
                history_text += f"\n{past_char['name']} ({past_char['anime_data']['title']}) {result}"
            
            embed.add_field(
                name="Previous Characters",
                value=history_text.strip() or "None",
                inline=False
            )
        
        if char.get('image_url'):
            embed.set_image(url=char['image_url'])
        
        if game_data.get('ended', False):
            embed.set_footer(text="Game Over! Click 🔄 to play again")
        else:
            embed.set_footer(text="Type character name to guess | Click ❌ to end")
        
        return embed

    async def start_new_game(self, ctx, difficulty=None):
        """Start a new game"""
        channel_id = ctx.channel.id
        
        if channel_id in self.active_games:
            await ctx.send("A game is already in progress! End it with `;c end`")
            return

        try:
            char = await self.get_character(difficulty)
            if not char:
                await ctx.send("No characters available!")
                return

            game_data = {
                'character': char,
                'started_by': ctx.author.id,
                'guesses': 0,
                'history': [],
                'ended': False
            }

            embed = await self.create_character_embed(game_data)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(self.END_GAME)

            game_data['message'] = msg
            self.active_games[channel_id] = game_data

        except Exception as e:
            print(f"Error starting game: {e}")
            await ctx.send("An error occurred while starting the game.")
            if channel_id in self.active_games:
                del self.active_games[channel_id]

    async def end_game(self, ctx, show_summary=False):
        """End the current game"""
        channel_id = ctx.channel.id
        try:
            if channel_id in self.active_games:
                game = self.active_games[channel_id]
                game['ended'] = True
                
                # Update embed with final state
                embed = await self.create_character_embed(game)
                await game['message'].edit(embed=embed)
                
                # Clear old reactions and add play again
                await game['message'].clear_reactions()
                await game['message'].add_reaction(self.PLAY_AGAIN)
                
                # Remove from active games
                del self.active_games[channel_id]
                
        except Exception as e:
            print(f"Error ending game: {e}")
            await ctx.send("An error occurred while ending the game.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message events for guesses"""
        if message.author.bot:
            return
            
        channel_id = message.channel.id
        if channel_id not in self.active_games:
            return
            
        game = self.active_games[channel_id]
        if game.get('ended', False):
            return
            
        current_char = game['character']
        
        # Check if the message is a guess
        guess = message.content.lower()
        correct_name = current_char['name'].lower()
        
        game['guesses'] += 1
        
        if guess == correct_name:
            # Mark current character as solved
            current_char['solved'] = True
            
            # Add to history
            game['history'].append({
                'name': current_char['name'],
                'anime_data': current_char['anime_data'],
                'solved': True
            })
            
            # Get new character
            try:
                new_char = await self.get_character()
                if new_char:
                    game['character'] = new_char
                    game['guesses'] = 0
                    
                    # Update embed
                    embed = await self.create_character_embed(game)
                    await game['message'].edit(embed=embed)
                    await message.add_reaction('✅')
            except Exception as e:
                print(f"Error getting new character: {e}")
                await self.end_game(await self.bot.get_context(message))
        else:
            # Update embed with new guess count
            embed = await self.create_character_embed(game)
            await game['message'].edit(embed=embed)
            await message.add_reaction('❌')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction adds"""
        if user.bot:
            return

        channel_id = reaction.message.channel.id
        
        # Handle play again reaction
        if str(reaction.emoji) == self.PLAY_AGAIN:
            ctx = await self.bot.get_context(reaction.message)
            if channel_id not in self.active_games:  # Only start if no active game
                await self.start_new_game(ctx)
            return

        if channel_id not in self.active_games:
            return

        game = self.active_games[channel_id]
        
        # Handle end game reaction
        if str(reaction.emoji) == self.END_GAME:
            if user.id == game['started_by'] or user.guild_permissions.manage_messages:
                ctx = await self.bot.get_context(reaction.message)
                # Add current character to history if not solved
                if not game['character'].get('solved', False):
                    game['history'].append({
                        'name': game['character']['name'],
                        'anime_data': game['character']['anime_data'],
                        'solved': False
                    })
                await self.end_game(ctx, show_summary=True)

async def setup(bot):
    print("Setting up CharacterGuess cog...")
    try:
        # Ensure database is initialized
        if not await bot.db.ensure_initialized():
            print("Failed to initialize database!")
            return
            
        # Add the cog
        await bot.add_cog(CharacterGuess(bot))
        print("CharacterGuess cog setup complete!")
    except Exception as e:
        print(f"Error setting up CharacterGuess cog: {str(e)}")
        raise e 