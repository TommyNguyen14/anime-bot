async def format_anime_data(self, anime):
    """Format anime data for storage"""
    return {
        'mal_id': anime.get('mal_id'),
        'title': anime.get('title'),
        'english_title': anime.get('title_english'),  # Add English title
        'images': anime.get('images', {}),
        'score': anime.get('score'),
        'popularity': anime.get('popularity'),
        'rank': anime.get('rank'),
        'members': anime.get('members')
    }

async def format_character_data(self, character, anime):
    """Format character data for the game"""
    char_details = await self.get_character_details(character['character']['mal_id'])
    if not char_details:
        char_details = character['character']
    
    anime_data = {
        'title': anime['title'],
        'english_title': anime.get('title_english'),  # Add English title
        'popularity': anime.get('popularity'),
        'members': anime.get('members'),
        'score': anime.get('score'),
        'rank': anime.get('rank')
    }
    
    return {
        'id': str(char_details['mal_id']),
        'name': char_details['name'],
        'image_url': char_details.get('images', {}).get('jpg', {}).get('image_url', ''),
        'anime_data': anime_data,
        'role': character.get('role', 'Unknown'),
        'favorites': char_details.get('favorites', 0)
    } 