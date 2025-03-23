import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
import random
import time
import json
import os
from datetime import datetime, timedelta

class AnimeAPI:
    def __init__(self):
        self.base_url = "https://api.jikan.moe/v4"
        self.rate_limit_delay = 1  # 1 second between requests
        self.last_request_time = 0
        self.max_retries = 3
        self.cache_dir = 'cache'
        self.cache_duration = timedelta(hours=24)
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

    async def _make_request(self, endpoint: str, params: Dict = None, force_cache: bool = False) -> Optional[Dict]:
        """Make a rate-limited request to the Jikan API with caching"""
        cache_file = os.path.join(self.cache_dir, f"{endpoint.replace('/', '_')}_{hash(str(params))}.json")
        
        # Check cache first
        if os.path.exists(cache_file) and not force_cache:
            cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - cache_time < self.cache_duration:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        try:
            # Ensure we wait enough time between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{endpoint}"
                async with session.get(url, params=params) as response:
                    self.last_request_time = time.time()
                    
                    if response.status == 200:
                        data = await response.json()
                        # Cache the response
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f)
                        return data
                    elif response.status == 429:  # Rate limited
                        if force_cache:
                            return None
                        await asyncio.sleep(2)  # Wait 2 seconds before retry
                        return await self._make_request(endpoint, params, True)
                    else:
                        print(f"API request failed: {response.status}")
                        return None
        except Exception as e:
            print(f"API request error: {e}")
            return None

    async def get_seasonal_anime(self, limit: int = 50) -> List[Dict]:
        """Get current season's anime with pagination"""
        all_anime = []
        page = 1
        
        while len(all_anime) < limit:
            response = await self._make_request("seasons/now", {"page": page})
            if not response or not response.get('data'):
                break
                
            all_anime.extend(response['data'])
            if not response.get('pagination', {}).get('has_next_page'):
                break
                
            page += 1
            await asyncio.sleep(1)  # Respect rate limiting
        
        return all_anime[:limit]

    async def get_top_anime(self, limit: int = 50) -> List[Dict]:
        """Get top-rated anime"""
        response = await self._make_request("top/anime", {"limit": limit})
        return response.get('data', []) if response else []

    async def get_anime_characters(self, anime_id: int, limit: int = 10) -> List[Dict]:
        """Get characters for an anime with limit"""
        response = await self._make_request(f"anime/{anime_id}/characters")
        if response and 'data' in response:
            # Sort by favorites and limit
            characters = sorted(response['data'], 
                             key=lambda x: x.get('favorites', 0), 
                             reverse=True)
            return characters[:limit]
        return []

    async def get_character_details(self, character_id: int) -> Optional[Dict]:
        """Get detailed information about a character"""
        response = await self._make_request(f"characters/{character_id}/full")
        return response.get('data') if response else None

    def generate_hints(self, character_data: Dict) -> List[str]:
        """Generate hints from character data"""
        hints = []
        
        # Add role hint
        if character_data.get('role'):
            hints.append(f"Role: {character_data['role']}")
        
        # Add nicknames hint
        if character_data.get('nicknames'):
            hints.append(f"Also known as: {', '.join(character_data['nicknames'][:2])}")
        
        # Add age/gender hint
        demographics = []
        if character_data.get('age'):
            demographics.append(f"Age: {character_data['age']}")
        if character_data.get('gender'):
            demographics.append(f"Gender: {character_data['gender']}")
        if demographics:
            hints.append(" | ".join(demographics))
        
        # Add description-based hint
        if character_data.get('about'):
            # Split description into sentences and pick one that doesn't contain the name
            sentences = [s.strip() for s in character_data['about'].split('.') if s.strip()]
            for sentence in sentences:
                if character_data['name'].lower() not in sentence.lower():
                    hints.append(sentence)
                    break
        
        # Add anime appearance hint
        if character_data.get('anime'):
            anime_list = [a['anime']['title'] for a in character_data['anime'][:3]]
            if len(anime_list) > 1:
                hints.append(f"Appears in: {', '.join(anime_list)}")
        
        return hints[:4]  # Return up to 4 hints

    def determine_difficulty(self, character_data: Dict) -> str:
        """Determine character difficulty based on favorites and role"""
        favorites = character_data.get('favorites', 0)
        role = character_data.get('role', '').lower()
        
        if favorites > 10000 or role == 'main':
            return "Easy"
        elif favorites > 5000 or role == 'supporting':
            return "Medium"
        else:
            return "Hard"

    async def format_character_data(self, character: Dict, anime: Dict) -> Dict:
        """Format character data for the game"""
        # Get full character details
        char_details = await self.get_character_details(character['character']['mal_id'])
        if not char_details:
            char_details = character['character']
        
        return {
            'id': str(char_details['mal_id']),
            'name': char_details['name'],
            'image_url': char_details.get('images', {}).get('jpg', {}).get('image_url', ''),
            'anime': anime['title'],
            'role': character.get('role', 'Unknown'),
            'hints': self.generate_hints(char_details),
            'difficulty': self.determine_difficulty(char_details),
            'favorites': char_details.get('favorites', 0)
        }

    async def format_opening_data(self, theme: Dict, anime: Dict) -> Dict:
        """Format opening data for the game"""
        theme_parts = theme['text'].split(' by ')
        artist = theme_parts[1] if len(theme_parts) > 1 else "Unknown"
        song_name = theme_parts[0].strip('"')
        
        return {
            'id': f"{anime['mal_id']}_{theme['text']}",
            'name': song_name,
            'artist': artist,
            'anime': anime['title'],
            'type': theme.get('type', 'OP'),
            'anime_data': {
                'title': anime['title'],
                'images': anime.get('images', {}),
                'score': anime.get('score', 0),
                'popularity': anime.get('popularity', 0)
            },
            'difficulty': "Easy" if anime.get('popularity', 0) < 100 else "Medium"
        }

    async def get_random_seasonal_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Get random characters and openings from seasonal and top anime"""
        characters = []
        openings = []
        
        # Get both seasonal and top anime
        seasonal = await self.get_seasonal_anime(30)  # Get 30 seasonal anime
        top_anime = await self.get_top_anime(20)     # Get 20 top anime
        all_anime = seasonal + top_anime
        
        # Shuffle and process anime
        random.shuffle(all_anime)
        processed_count = 0
        
        for anime in all_anime:
            try:
                if processed_count >= 10:  # Limit to 10 anime per refresh
                    break
                    
                anime_id = anime['mal_id']
                
                # Get characters
                anime_chars = await self.get_anime_characters(anime_id, 3)  # Get up to 3 characters per anime
                for char in anime_chars:
                    formatted_char = await self.format_character_data(char, anime)
                    if formatted_char:
                        characters.append(formatted_char)
                
                # Get theme songs
                anime_details = await self._make_request(f"anime/{anime_id}")
                if anime_details and 'data' in anime_details:
                    themes = anime_details['data'].get('theme', {}).get('openings', [])
                    if themes:
                        theme = themes[0]  # Take the first opening
                        formatted_opening = await self.format_opening_data({'text': theme, 'type': 'OP'}, anime)
                        openings.append(formatted_opening)
                
                processed_count += 1
                print(f"Processed anime: {anime['title']}")
                
            except Exception as e:
                print(f"Error processing anime: {e}")
                continue
        
        return characters, openings 