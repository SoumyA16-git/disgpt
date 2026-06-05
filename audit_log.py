import os
import discord
from datetime import datetime

async def log_action(bot: discord.Client, guild: discord.Guild, moderator: discord.Member, action: str, target: str, reason: str = None, success: bool = True):
    log_channel_id = os.getenv("LOG_CHANNEL_ID")
    if not log_channel_id:
        return
    
    try:
        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            return

        embed = discord.Embed(
            title="Moderation Action Log",
            color=discord.Color.green() if success else discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Action", value=action.capitalize(), inline=True)
        embed.add_field(name="Target", value=target, inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        embed.set_footer(text=f"DisGPT • Status: {'Success' if success else 'Failed'}")
        
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to log action: {e}")
