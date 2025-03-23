import json
import os
from utils.jikan_api import JikanAPI
import asyncio
from datetime import datetime, timedelta
import random
from pathlib import Path
from typing import Dict, List, Optional, Any

class AnimeDatabase:
    def __init__(self):
        self.api = JikanAPI()
        self.data_dir = Path("data")
        self.cache_dir = self.data_dir / "cache"
        self.stats_dir = self.data_dir / "stats"
        
        self.initialized = False
        self.characters = []
        self.openings = []
        self.user_stats = {}
        self.last_cache_update = None
        self.cache_duration = timedelta(days=7)
        self._lock = asyncio.Lock()  # Add a lock for thread safety
        
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        print("Database initialized")

    def load_data(self) -> None:
        """Load all cached data from files."""
        # Load characters
        character_file = self.cache_dir / "characters.json"
        if character_file.exists():
            with open(character_file, 'r', encoding='utf-8') as f:
                self.characters = json.load(f)
                print(f"Loaded {len(self.characters)} characters from cache")
        
        # Load openings
        opening_file = self.cache_dir / "openings.json"
        if opening_file.exists():
            with open(opening_file, 'r', encoding='utf-8') as f:
                self.openings = json.load(f)
                print(f"Loaded {len(self.openings)} openings from cache")
        
        # Load user stats
        stats_file = self.stats_dir / "user_stats.json"
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                self.user_stats = json.load(f)
                print("Loaded user stats from cache")
        else:
            self.user_stats = {}
            self.save_user_stats()

        # Load last update time
        timestamp_file = self.cache_dir / "last_update.txt"
        if timestamp_file.exists():
            with open(timestamp_file, 'r') as f:
                self.last_cache_update = datetime.fromisoformat(f.read().strip())
                print(f"Last cache update: {self.last_cache_update}")

    def save_user_stats(self) -> None:
        """Save user stats to file."""
        stats_file = self.stats_dir / "user_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_stats, f, ensure_ascii=False, indent=2)

    def get_random_character(self) -> Optional[Dict[str, Any]]:
        """Get a random character from the cached data."""
        return random.choice(self.characters) if self.characters else None

    def get_random_opening(self, difficulty: str = None) -> Optional[Dict[str, Any]]:
        """Get a random opening from the cached data."""
        if not self.openings:
            return None
        
        if difficulty:
            filtered_openings = [op for op in self.openings if op.get('difficulty', 'medium') == difficulty]
            return random.choice(filtered_openings) if filtered_openings else None
        return random.choice(self.openings)

    def update_user_stats(self, user_id: str, game_type: str, correct: bool) -> None:
        """Update user statistics."""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                "character_games": {"wins": 0, "total": 0},
                "opening_games": {"wins": 0, "total": 0}
            }
        
        stats = self.user_stats[user_id][f"{game_type}_games"]
        stats["total"] += 1
        if correct:
            stats["wins"] += 1
        
        self.save_user_stats()

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        return self.user_stats.get(user_id, {
            "character_games": {"wins": 0, "total": 0},
            "opening_games": {"wins": 0, "total": 0}
        })

    def needs_update(self) -> bool:
        """Check if the cache needs to be updated."""
        if not self.last_cache_update:
            return True
            
        # Update if last update was more than 24 hours ago
        return (datetime.now() - self.last_cache_update) > self.cache_duration

    async def load_cache(self):
        """Load data from cache files"""
        try:
            print("Loading character cache...")
            cache_file = self.cache_dir / "characters.json"
            
            if not cache_file.exists():
                print("Cache file not found!")
                return False
                
            with open(cache_file, 'r', encoding='utf-8') as f:
                self.characters = json.load(f)
                print(f"Loaded {len(self.characters)} characters from cache")
                
            return True
            
        except Exception as e:
            print(f"Error loading cache: {str(e)}")
            return False

    async def ensure_initialized(self):
        """Ensure the database is initialized with data"""
        if self.initialized:
            return True
            
        print("Initializing database...")
        try:
            cache_loaded = await self.load_cache()
            if not cache_loaded:
                print("Failed to load cache!")
                return False
                
            self.initialized = True
            print("Database initialization complete!")
            return True
            
        except Exception as e:
            print(f"Error ensuring database initialization: {str(e)}")
            return False

    async def update_cache(self):
        """Update the cache with fresh data"""
        try:
            # Update API cache
            characters, openings = await self.api.update_cache()
            
            # Update local cache
            self.characters = characters
            self.openings = openings
            self.last_cache_update = datetime.now()
            
            # Save updated data
            self.save_data()
            
            print(f"Cache updated with {len(self.characters)} characters and {len(self.openings)} openings")
            
        except Exception as e:
            print(f"Error updating cache: {e}")
            # If update fails, try to load from existing cache
            self.load_data()

    def save_data(self):
        """Save all data to files"""
        try:
            # Save characters
            with open(self.cache_dir / "characters.json", 'w', encoding='utf-8') as f:
                json.dump(self.characters, f, ensure_ascii=False, indent=2)
            
            # Save openings
            with open(self.cache_dir / "openings.json", 'w', encoding='utf-8') as f:
                json.dump(self.openings, f, ensure_ascii=False, indent=2)
            
            # Save last update time
            with open(self.cache_dir / "last_update.txt", 'w') as f:
                f.write(self.last_cache_update.isoformat())
            
            print("All data saved successfully")
        except Exception as e:
            print(f"Error saving data: {e}") 