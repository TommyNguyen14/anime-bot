class Config:
    # Bot settings
    PREFIX = ";"
    DEFAULT_COLOR = 0x000000  # Changed to black
    
    # Command names - use exact names as in the commands
    CHAR_COMMAND = "c"
    CHAR_END_COMMAND = "c_end"
    CHAR_LIST_COMMAND = "clist"
    
    # Navigation emojis
    NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    LEFT_ARROW = "⬅️"
    RIGHT_ARROW = "➡️"
    SEARCH = "🔍"
    
    # Help messages
    HELP_TITLE = "🎮 Anime Character Guessing Game"
    HELP_DESCRIPTION = "Test your anime knowledge by guessing characters!"
    
    @classmethod
    def get_command(cls, command_name: str) -> str:
        """Get full command with prefix"""
        return f"{cls.PREFIX}{command_name}"
    
    @classmethod
    def get_commands_help(cls) -> str:
        """Get formatted commands help text"""
        return (
            f"`{cls.CHAR_COMMAND}` - Start a character guessing game\n"
            f"`{cls.CHAR_END_COMMAND}` - End the current game\n"
            f"`{cls.CHAR_LIST_COMMAND} <anime>` - List characters from an anime\n"
            "`help` - Show this help message"
        )
    
    @classmethod
    def get_gameplay_help(cls) -> str:
        """Get formatted gameplay help text"""
        return (
            f"1️⃣ Start a game using `{cls.get_command(cls.CHAR_COMMAND)}`\n"
            f"2️⃣ Use {cls.LEFT_ARROW} {cls.RIGHT_ARROW} to navigate between characters\n"
            f"3️⃣ Type `{cls.get_command(cls.CHAR_COMMAND)} <character name>` to make a guess\n"
            "4️⃣ Use number emojis to quickly switch characters"
        )
    
    @classmethod
    def get_tips(cls) -> str:
        """Get formatted tips text"""
        return (
            f"• Use `{cls.get_command(cls.CHAR_LIST_COMMAND)}` to see characters from a specific anime\n"
            f"• You can use slash commands like `/{cls.CHAR_COMMAND}` and `/{cls.CHAR_LIST_COMMAND}`\n"
            "• Navigate through characters using reactions"
        ) 