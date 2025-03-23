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

    async def create_character_embed(self, character, guesses=0):
        """Create the character embed"""
        embed = discord.Embed(
            title="Character Guessing Game",
            description="Type the character's name to make a guess!\nUse `;c end` to end the game.",
            color=self.EMBED_COLOR
        )
        
        anime_title = character['anime_data']['title']
        if character['anime_data'].get('english_title'):
            anime_title += f" ({character['anime_data']['english_title']})"
            
        embed.add_field(
            name="Anime Title",
            value=anime_title,
            inline=False
        )
        
        embed.add_field(
            name="Difficulty",
            value=character['difficulty'],
            inline=True
        )
        
        embed.add_field(
            name="Guesses",
            value=str(guesses),
            inline=True
        )
        
        if character.get('image_url'):
            embed.set_image(url=character['image_url'])
            
        embed.set_footer(text="Click ❌ or type ;c end to end the game")
        
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

            embed = await self.create_character_embed(char)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(self.END_GAME)

            self.active_games[channel_id] = {
                'character': char,
                'message': msg,
                'started_by': ctx.author.id,
                'guesses': 0
            }

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
                
                if show_summary:
                    embed = discord.Embed(
                        title="Game Summary",
                        color=self.EMBED_COLOR
                    )
                    
                    char = game['character']
                    anime_title = char['anime_data']['title']
                    if char['anime_data'].get('english_title'):
                        anime_title += f" ({char['anime_data']['english_title']})"

                    # Format the character result
                    result_text = (
                        f"Character: {char['name']} {'✅' if game.get('solved', False) else '❌'}\n"
                        f"Anime: {anime_title}\n"
                        f"Difficulty: {char['difficulty']}\n"
                        f"Guesses Made: {game['guesses']}"
                    )
                    
                    embed.description = result_text
                    
                    if char.get('image_url'):
                        embed.set_image(url=char['image_url'])
                    
                    embed.set_footer(text="Click 🔄 to play again!")
                    
                    # Send summary and add play again reaction
                    summary_msg = await ctx.send(embed=embed)
                    await summary_msg.add_reaction(self.PLAY_AGAIN)
                    game['summary_message'] = summary_msg

                # Clean up
                if 'message' in game:
                    try:
                        await game['message'].clear_reactions()
                    except:
                        pass
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
        current_char = game['character']
        
        # Check if the message is a guess
        guess = message.content.lower()
        correct_name = current_char['name'].lower()
        
        game['guesses'] += 1
        
        # Update embed with new guess count
        try:
            new_embed = await self.create_character_embed(current_char, game['guesses'])
            await game['message'].edit(embed=new_embed)
        except:
            pass
        
        if guess == correct_name:
            await message.add_reaction('✅')
            game['solved'] = True
            
            # Send victory message
            embed = discord.Embed(
                title="Correct!",
                description=f"You guessed it! The character was {current_char['name']}",
                color=self.EMBED_COLOR
            )
            embed.add_field(
                name="Guesses",
                value=str(game['guesses']),
                inline=True
            )
            victory_msg = await message.channel.send(embed=embed)
            
            # Add reactions for end game or continue
            await victory_msg.add_reaction(self.END_GAME)
            await victory_msg.add_reaction(self.PLAY_AGAIN)
            game['victory_message'] = victory_msg
        else:
            await message.add_reaction('❌')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction adds"""
        if user.bot:
            return

        channel_id = reaction.message.channel.id
        
        # Handle play again reaction
        if str(reaction.emoji) == self.PLAY_AGAIN:
            # Start new game for the user
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