import os
import discord

def is_admin(member: discord.Member) -> bool:
    admin_role_name = os.getenv("ADMIN_ROLE_NAME", "Admin")
    # Also check for server ownership or Administrator permission as a fallback
    if member.guild.owner_id == member.id or member.guild_permissions.administrator:
        return True
    return any(role.name == admin_role_name for role in member.roles)

def is_mod(member: discord.Member) -> bool:
    mod_role_name = os.getenv("MOD_ROLE_NAME", "Moderator")
    if is_admin(member):
        return True
    return any(role.name == mod_role_name for role in member.roles)

def is_admin_or_mod(member: discord.Member) -> bool:
    return is_mod(member)
