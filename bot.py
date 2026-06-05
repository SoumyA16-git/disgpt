import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

class DisGPT(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        
        super().__init__(
            command_prefix='!', 
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        await self.load_extension('ai_chat')
        await self.load_extension('modify_handler')
        
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        await self.change_presence(activity=discord.Game(name="/ask to chat | /modify to manage"))

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "your_discord_bot_token_here":
        print("Error: DISCORD_TOKEN not set in environment variables.")
        return

    keep_alive()
    
    bot = DisGPT()
    bot.run(token, log_handler=None)

if __name__ == '__main__':
    main()
