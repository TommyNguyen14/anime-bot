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
from difflib import SequenceMatcher
import traceback

class CharacterGuess(commands.Cog):
    """Character guessing game commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.active_games = {}  # Channel-based games
        self.user_games = {}    # Track which users have active games
        self._locks = {}
        self.END_GAME = "❌"
        self.PLAY_AGAIN = "🔄"
        self.EMBED_COLOR = Config.DEFAULT_COLOR
        self.correct_guesses = {}  # Track correct guesses per channel
        print("CharacterGuess cog initialized!")

    def string_similarity(self, a, b):
        """Get similarity ratio between two strings"""
        return SequenceMatcher(None, a, b).ratio()

    def normalize_name(self, name):
        """Normalize name for comparison"""
        # Remove special characters, spaces, and convert to lowercase
        return ''.join(c.lower() for c in name if c.isalnum())

    def names_match(self, guess, correct_name):
        """Check if names match with smart comparison"""
        # Print debug info
        print(f"\nGuess attempt:")
        print(f"Original guess: {guess}")
        print(f"Correct name: {correct_name}")
        
        # Normalize names
        norm_guess = self.normalize_name(guess)
        norm_correct = self.normalize_name(correct_name)
        
        print(f"Normalized guess: {norm_guess}")
        print(f"Normalized correct: {norm_correct}")
        
        # Direct match
        if norm_guess == norm_correct:
            print("✓ Direct match!")
            return True
            
        # High similarity match
        similarity = self.string_similarity(norm_guess, norm_correct)
        print(f"Full name similarity: {similarity:.2f}")
        if similarity > 0.85:
            print("✓ High similarity match!")
            return True
            
        # First name match
        guess_parts = norm_guess.split()
        correct_parts = norm_correct.split()
        if len(guess_parts) > 0 and len(correct_parts) > 0:
            first_name_similarity = self.string_similarity(guess_parts[0], correct_parts[0])
            print(f"First name similarity: {first_name_similarity:.2f}")
            if first_name_similarity > 0.85:
                print("✓ First name match!")
                return True
                
        # Check if guess is contained in correct name
        if norm_guess in norm_correct:
            print("✓ Substring match!")
            return True
            
        print("✗ No match found")
        return False

    @commands.command(name="c")
    async def char(self, ctx, difficulty: str = None):
        """Start a new character guessing game"""
        # Check if user already has an active game
        if ctx.author.id in self.user_games:
            active_channel = self.bot.get_channel(self.user_games[ctx.author.id])
            if active_channel:
                await ctx.send(f"You already have an active game in {active_channel.mention}! End it first with `;c end`")
            else:
                await ctx.send("You already have an active game! End it first with `;c end`")
            return

        if difficulty and difficulty.lower() not in ['easy', 'medium', 'hard']:
            await ctx.send("Invalid difficulty! Use 'easy', 'medium', or 'hard'.")
            return

        print(f"\nStarting new game:")
        print(f"User: {ctx.author.name}")
        print(f"Requested difficulty: {difficulty if difficulty else 'Any'}")
        
        await self.start_new_game(ctx, difficulty)

    @commands.command(aliases=["c end"])
    async def c_end(self, ctx):
        """End the current character guessing game"""
        channel_id = ctx.channel.id
        user_id = ctx.author.id

        # Check if user has a game in a different channel
        if user_id in self.user_games and self.user_games[user_id] != channel_id:
            active_channel = self.bot.get_channel(self.user_games[user_id])
            if active_channel:
                await ctx.send(f"Your active game is in {active_channel.mention}! Go there to end it.")
            return

        if channel_id not in self.active_games:
            await ctx.send("No active game in this channel!")
            return
            
        game = self.active_games[channel_id]
        if user_id != game['started_by'] and not ctx.author.guild_permissions.manage_messages:
            await ctx.send("Only the game starter or moderators can end the game!")
            return
            
        await self.end_game(ctx, show_summary=True)

    async def get_character(self, difficulty=None):
        """Get a random character for the game"""
        try:
            # Print total characters in database for debugging
            print(f"\nTotal characters in database: {len(self.db.characters)}")
            print("Available difficulties:", set(char.get('difficulty', 'Unknown') for char in self.db.characters))

            # If difficulty is specified, filter by it
            if difficulty:
                difficulty = difficulty.lower()
                chars = [
                    char for char in self.db.characters
                    if char.get('difficulty', '').lower() == difficulty
                ]
                print(f"Characters found for difficulty {difficulty}: {len(chars)}")
            else:
                # No difficulty specified, use all characters
                chars = list(self.db.characters)  # Convert to list to ensure random.choice works
                print("Using all characters")

            if not chars:
                print("No characters found!")
                return None

            # Select random character
            selected_char = random.choice(chars)
            
            # Debug info
            print(f"\nSelected character:")
            print(f"Name: {selected_char['name']}")
            print(f"Anime: {selected_char['anime_data']['title']}")
            print(f"Difficulty: {selected_char.get('difficulty', 'Unknown')}")
            
            return selected_char

        except Exception as e:
            print(f"Error getting character: {e}")
            traceback.print_exc()  # Print full error traceback
            return None

    async def create_character_embed(self, game_data, show_summary=False):
        """Create the character embed with game state"""
        if show_summary:
        embed = discord.Embed(
                title="Game Summary",
                color=self.EMBED_COLOR
            )
            
            # Calculate statistics
            total_chars = len(game_data['history'])
            solved_chars = sum(1 for char in game_data['history'] if char.get('solved', False))
            
            # Add statistics at the top
            stats_text = (
                f"**Final Score:** {solved_chars}/{total_chars}\n"
                f"**Total Guesses:** {game_data.get('total_guesses', 0)}\n"
                "─────────────────────────"
            )
            
            # Create summary of all characters played
            summary_text = ""
            for idx, char in enumerate(game_data['history'], 1):
                result = '✅' if char.get('solved', False) else '❌'
                summary_text += f"\n{idx}. {char['name']} ({char['anime_data']['title']}) {result}"
            
            if not game_data['history']:
                summary_text = "\nNo characters played"
            
            embed.description = f"{stats_text}\n{summary_text}"
            embed.set_footer(text="🔄 Play Again | ❌ Exit")
        return embed

        # Regular game embed
        char = game_data['character']
        embed = discord.Embed(
            title="Character Guessing Game",
            color=self.EMBED_COLOR
        )
        
        embed.description = f"**Guesses:** {game_data['guesses']}"
        
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
        
        if char.get('image_url'):
            embed.set_image(url=char['image_url'])
        
        embed.set_footer(text="Type character name to guess | 🔄 Skip/New | ❌ End")
        
        return embed

    async def show_summary(self, game_data):
        """Show game summary and add reactions"""
        embed = await self.create_character_embed(game_data, show_summary=True)
        await game_data['message'].edit(embed=embed)
        await game_data['message'].clear_reactions()
        await game_data['message'].add_reaction(self.PLAY_AGAIN)
        await game_data['message'].add_reaction(self.END_GAME)

    async def get_characters(self, difficulty=None, count=5):
        """Get multiple characters for the game"""
        try:
            chars = []
            available_chars = [
                char for char in self.db.characters
                if not difficulty or char.get('difficulty', '').lower() == difficulty.lower()
            ]
            
            if not available_chars:
                return None
                
            return random.sample(available_chars, min(count, len(available_chars)))
            
        except Exception as e:
            print(f"Error getting characters: {e}")
            return None

    async def clear_correct_guesses(self, channel_id):
        """Clear correct guesses for a channel"""
        if channel_id in self.correct_guesses:
            messages = self.correct_guesses[channel_id]
            for msg in messages:
                try:
                    await msg.delete()
                except:
                    pass
            self.correct_guesses[channel_id] = []

    async def start_new_game(self, ctx, difficulty=None):
        """Start a new game"""
        channel_id = ctx.channel.id
        user_id = ctx.author.id
        
        try:
            # Clean up any existing game in this channel
            if channel_id in self.active_games:
                old_game = self.active_games[channel_id]
                old_user_id = old_game.get('started_by')
                try:
                    await old_game['message'].delete()
                except:
                    pass
                del self.active_games[channel_id]
                if old_user_id in self.user_games:
                    del self.user_games[old_user_id]
            
            # Clear any existing correct guesses
            await self.clear_correct_guesses(channel_id)
            
            # Start new game
            char = await self.get_character(difficulty)
            if not char:
                await ctx.send("No characters available!")
                return

            game_data = {
                'character': char,
                'started_by': user_id,
                'guesses': 0,
                'history': [],
                'ended': False,
                'difficulty': difficulty
            }

            embed = await self.create_character_embed(game_data)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(self.PLAY_AGAIN)
            await msg.add_reaction(self.END_GAME)

            game_data['message'] = msg
            self.active_games[channel_id] = game_data
            self.user_games[user_id] = channel_id  # Track user's game

        except Exception as e:
            print(f"Error starting game: {e}")
            await ctx.send("An error occurred while starting the game.")
            if channel_id in self.active_games:
                del self.active_games[channel_id]
            if user_id in self.user_games:
                del self.user_games[user_id]

    async def delete_message_after_delay(self, message, delay=3):
        """Delete a message after a delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except:
            pass

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
        guess = message.content
        correct_name = current_char['name']
        
        print(f"\nNew guess from {message.author.name}:")
        print(f"Character: {correct_name}")
        print(f"Guess: {guess}")
        
        game['guesses'] += 1
        
        # Check for match
        is_correct = self.names_match(guess, correct_name)
        
        if is_correct:
            print(f"✓ Correct guess by {message.author.name}!")
            # Mark current character as solved
            current_char['solved'] = True
            current_char['guesses_taken'] = game['guesses']
            
            # Add to history
            game['history'].append({
                'name': current_char['name'],
                'anime_data': current_char['anime_data'],
                'solved': True,
                'guesses_taken': game['guesses']
            })
            
            # Add reaction
            await message.add_reaction('✅')
            
            # Track correct guess
            if channel_id not in self.correct_guesses:
                self.correct_guesses[channel_id] = []
            self.correct_guesses[channel_id].append(message)
            
            # Clear messages if we have 3 correct guesses
            if len(self.correct_guesses[channel_id]) >= 3:
                await self.clear_correct_guesses(channel_id)
            
            # Get new character (maintain difficulty if set)
            try:
                difficulty = current_char.get('difficulty', None)
                new_char = await self.get_character(difficulty)
                if new_char:
                    game['character'] = new_char
                    game['guesses'] = 0
                    
                    # Update embed
                    embed = await self.create_character_embed(game)
                    await game['message'].edit(embed=embed)
            except Exception as e:
                print(f"Error getting new character: {e}")
                await self.end_game(await self.bot.get_context(message))
        else:
            print(f"✗ Incorrect guess by {message.author.name}")
            # Add reaction and delete message
            await message.add_reaction('❌')
            asyncio.create_task(self.delete_message_after_delay(message))
            
            # Update embed with new guess count
            embed = await self.create_character_embed(game)
            await game['message'].edit(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction adds"""
        if user.bot:
            return
            
        channel_id = reaction.message.channel.id
        message_id = reaction.message.id
            
            try:
                await reaction.remove(user)
            except:
                pass

        # Handle play again/skip reaction
        if str(reaction.emoji) == self.PLAY_AGAIN:
            # Check if user has a game in a different channel
            if user.id in self.user_games and self.user_games[user.id] != channel_id:
                active_channel = self.bot.get_channel(self.user_games[user.id])
                if active_channel:
                    ctx = await self.bot.get_context(reaction.message)
                    await ctx.send(f"You already have an active game in {active_channel.mention}!")
                return

            if channel_id in self.active_games:
                game = self.active_games[channel_id]
                if game['message'].id == message_id:
                    if user.id != game['started_by'] and not user.guild_permissions.manage_messages:
                        return  # Only game starter or mods can skip/restart
                    try:
                        # Add current character to history if not solved
                        if not game['character'].get('solved', False):
                            game['history'].append({
                                'name': game['character']['name'],
                                'anime_data': game['character']['anime_data'],
                                'solved': False
                            })
                        
                        # Get new character using stored difficulty
                        new_char = await self.get_character(game.get('difficulty'))
                        if new_char:
                            game['character'] = new_char
                            game['guesses'] = 0
                            embed = await self.create_character_embed(game)
                            await game['message'].edit(embed=embed)
                    except Exception as e:
                        print(f"Error getting new character: {e}")
                        traceback.print_exc()
                        ctx = await self.bot.get_context(reaction.message)
                        await self.end_game(ctx, show_summary=True)
            else:
                ctx = await self.bot.get_context(reaction.message)
                if user.id not in self.user_games:  # Only allow if user doesn't have an active game
                    await self.start_new_game(ctx)
            return

        if channel_id not in self.active_games:
            return

        game = self.active_games[channel_id]
        if reaction.message.id != game['message'].id:
            return
            
        # Handle end game reaction
        if str(reaction.emoji) == self.END_GAME:
            if user.id == game['started_by'] or user.guild_permissions.manage_messages:
                ctx = await self.bot.get_context(reaction.message)
                if not game['character'].get('solved', False):
                    game['history'].append({
                        'name': game['character']['name'],
                        'anime_data': game['character']['anime_data'],
                        'solved': False
                    })
                await self.end_game(ctx, show_summary=True)

    async def end_game(self, ctx, show_summary=False):
        """End the current game"""
        channel_id = ctx.channel.id
        try:
            if channel_id in self.active_games:
                game = self.active_games[channel_id]
                game['ended'] = True
                
                # Clean up user game tracking
                user_id = game['started_by']
                if user_id in self.user_games:
                    del self.user_games[user_id]
                
                # Clear any remaining correct guesses
                await self.clear_correct_guesses(channel_id)
                
                # Calculate total guesses
                game['total_guesses'] = sum(1 for char in game['history'] if not char.get('solved', False))
                for char in game['history']:
                    if char.get('solved', False):
                        game['total_guesses'] += char.get('guesses_taken', 1)
                
                if show_summary:
                    embed = await self.create_character_embed(game, show_summary=True)
                    await game['message'].edit(embed=embed)
                    await game['message'].clear_reactions()
                    await game['message'].add_reaction(self.PLAY_AGAIN)
                    await game['message'].add_reaction(self.END_GAME)
                
                del self.active_games[channel_id]
                if channel_id in self.correct_guesses:
                    del self.correct_guesses[channel_id]
                
        except Exception as e:
            print(f"Error ending game: {e}")
            await ctx.send("An error occurred while ending the game.")
            if channel_id in self.active_games:
                del self.active_games[channel_id]

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