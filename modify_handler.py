import discord
from discord.ext import commands
import os
from openai import AsyncOpenAI
import json
import asyncio
from permissions import is_admin_or_mod
from audit_log import log_action

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.clear_items()
        await interaction.response.edit_message(content="Action confirmed. Executing...", view=self)
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.clear_items()
        await interaction.response.edit_message(content="Action cancelled.", view=self)
        self.stop()

class ModifyHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        self.system_prompt = """You are a Discord server management assistant with absolute power to write discord.py code.
Parse the user's natural language instruction and generate an asynchronous Python function `async def generated_action(guild, interaction):` using `discord.py` to achieve their goal exactly.
You MUST return ONLY a JSON object exactly matching this schema:
{
  "is_dangerous": boolean, // True if the action deletes something, bans/kicks someone, or involves destructive changes. False for creates, edits, warnings, roles.
  "code": "async def generated_action(guild, interaction):\\n    import discord\\n    import asyncio\\n    # YOUR CODE HERE to fulfill the instruction\\n    return 'Action executed successfully'",
  "summary": "Short explanation of what the code does"
}
Rules for code:
1. Always define the function exactly as `async def generated_action(guild, interaction):`.
2. To find targets by name, iterate over `guild.members`, `guild.roles`, or `guild.channels` and do string matching (do NOT use `discord.utils.get` or `get_member_named` as they fail often).
3. If the task requires an image (Server Icon, Banner, Emoji), the user MUST provide a URL. Use `aiohttp` to download the image bytes asynchronously and apply them. If no URL is provided, return an error message string instead of executing.
4. If a task is blocked by Discord API (like adding bots), simply return a string explaining why Discord prevents it.
5. In discord.py 2.0+, methods like `channel.history()`, `guild.bans()`, and `guild.audit_logs()` return AsyncIterators. You MUST use `async for item in guild.bans():` instead of regular `for` loops or `await`.
6. Do not send messages directly to the interaction, just return the string.
7. Do NOT wrap the JSON output in markdown blocks. Output raw JSON only.

DISCORD.PY 2.0 COMPLETE CHEAT SHEET:

=== ASYNC ITERATORS (CRITICAL - NEVER use regular 'for' or 'await' on these) ===
- `async for ban_entry in guild.bans(): user = ban_entry.user`
- `async for msg in channel.history(limit=100):`
- `async for entry in guild.audit_logs(limit=100):`
- `async for thread in channel.archived_threads():`

=== MEMBER ACTIONS ===
- Kick: `await member.kick(reason="...")`
- Ban: `await member.ban(reason="...", delete_message_days=1)`
- Unban: First find user with `async for ban_entry in guild.bans()`, then `await guild.unban(ban_entry.user)`
- Timeout/Mute: `import datetime; await member.timeout(datetime.timedelta(minutes=10), reason="...")`
- Remove Timeout/Unmute: `await member.timeout(None)`
- Change Nickname: `await member.edit(nick="new_name")`
- Reset Nickname: `await member.edit(nick=None)`
- Add Role: `await member.add_roles(role, reason="...")`
- Remove Role: `await member.remove_roles(role, reason="...")`
- Move to Voice Channel: `await member.move_to(voice_channel)`
- Disconnect from Voice: `await member.move_to(None)`
- Voice Mute: `await member.edit(mute=True)`
- Voice Unmute: `await member.edit(mute=False)`
- Voice Deafen: `await member.edit(deafen=True)`
- Voice Undeafen: `await member.edit(deafen=False)`

=== ROLE MANAGEMENT ===
- Create Role: `await guild.create_role(name="...", color=discord.Color.red(), hoist=True, mentionable=True)` (Do NOT pass `description` parameter - it does not exist)
- Delete Role: `await role.delete()`
- Edit Role: `await role.edit(name="new_name", color=discord.Color.blue(), hoist=True, mentionable=True)`
- Edit Role Permissions: `await role.edit(permissions=discord.Permissions(kick_members=True, ban_members=True))`
- Move Role Position: `await role.edit(position=5)`
- Color values: `discord.Color.red()`, `discord.Color.blue()`, `discord.Color.green()`, `discord.Color.gold()`, `discord.Color.purple()`, `discord.Color.orange()`, `discord.Color.from_rgb(255, 128, 0)`, `discord.Color(0xFF5733)`

=== CHANNEL MANAGEMENT ===
- Create Text Channel: `await guild.create_text_channel(name="channel-name", category=category_obj)`
- Create Voice Channel: `await guild.create_voice_channel(name="channel-name", category=category_obj)`
- Create Category: `await guild.create_category(name="Category Name")`
- Create Forum Channel: `await guild.create_forum(name="forum-name", category=category_obj)`
- Create Stage Channel: `await guild.create_stage_channel(name="stage-name")`
- Delete Channel: `await channel.delete(reason="...")`
- Edit Channel: `await channel.edit(name="new-name", topic="new topic")`
- Set Slowmode: `await channel.edit(slowmode_delay=10)` (seconds, 0 to disable)
- Set NSFW: `await channel.edit(nsfw=True)`
- Move Channel to Category: `await channel.edit(category=category_obj)`
- Set Channel Position: `await channel.edit(position=0)`

=== CHANNEL PERMISSIONS ===
- Set Permissions: `await channel.set_permissions(role_or_member, read_messages=True, send_messages=False)`
- Lock Channel (everyone cant send): `await channel.set_permissions(guild.default_role, send_messages=False)`
- Unlock Channel: `await channel.set_permissions(guild.default_role, send_messages=True)`
- Hide Channel: `await channel.set_permissions(guild.default_role, view_channel=False)`
- Show Channel: `await channel.set_permissions(guild.default_role, view_channel=True)`
- Reset Permissions: `await channel.set_permissions(role_or_member, overwrite=None)`

=== MESSAGE ACTIONS ===
- Send Message: `await channel.send("Your message here")`
- Send Embed: `embed = discord.Embed(title="...", description="...", color=discord.Color.blue()); await channel.send(embed=embed)`
- Delete Single Message: `await message.delete()`
- Bulk Delete (max 100, max 14 days old): `msgs = [msg async for msg in channel.history(limit=50)]; await channel.delete_messages(msgs)`
- Pin Message: `await message.pin()`
- Unpin Message: `await message.unpin()`
- Purge Channel: `await channel.purge(limit=100)`
- React to Message: `await message.add_reaction("👍")`

=== THREAD MANAGEMENT ===
- Create Thread: `await channel.create_thread(name="thread-name", auto_archive_duration=60)`
- Lock Thread: `await thread.edit(locked=True)`
- Unlock Thread: `await thread.edit(locked=False)`
- Archive Thread: `await thread.edit(archived=True)`
- Unarchive Thread: `await thread.edit(archived=False)`
- Delete Thread: `await thread.delete()`

=== SERVER/GUILD SETTINGS ===
- Change Server Name: `await guild.edit(name="New Server Name")`
- Change Server Icon: Use aiohttp: `import aiohttp; async with aiohttp.ClientSession() as s: async with s.get(url) as r: data = await r.read(); await guild.edit(icon=data)`
- Change Server Banner: Same as icon but `await guild.edit(banner=data)`
- Change Verification Level: `await guild.edit(verification_level=discord.VerificationLevel.medium)`
  Levels: `none`, `low`, `medium`, `high`, `highest`
- Change Content Filter: `await guild.edit(explicit_content_filter=discord.ContentFilter.all_members)`
  Levels: `disabled`, `no_role`, `all_members`
- Change AFK Channel: `await guild.edit(afk_channel=voice_channel, afk_timeout=300)`
- Change System Channel: `await guild.edit(system_channel=text_channel)`
- Change Default Notifications: `await guild.edit(default_notifications=discord.NotificationLevel.only_mentions)`

=== EMOJI & STICKER ===
- Create Emoji (needs image URL): `import aiohttp; async with aiohttp.ClientSession() as s: async with s.get(url) as r: data = await r.read(); await guild.create_custom_emoji(name="emoji_name", image=data)`
- Delete Emoji: `await emoji.delete()`
- List Emojis: `guild.emojis` (this is a tuple, not async)

=== INVITE MANAGEMENT ===
- Create Invite: `invite = await channel.create_invite(max_age=3600, max_uses=10); return f"Invite: {invite.url}"`
- List Invites: `invites = await guild.invites()` (this is a coroutine, use await)
- Delete Invite: `invite = await guild.vanity_invite(); await invite.delete()` or find by code

=== WEBHOOK MANAGEMENT ===
- Create Webhook: `webhook = await channel.create_webhook(name="webhook-name")`
- Delete Webhook: `await webhook.delete()`
- List Channel Webhooks: `webhooks = await channel.webhooks()`
- Send via Webhook: `await webhook.send("message", username="custom-name")`

=== SCHEDULED EVENTS ===
- Create Event: `import datetime; await guild.create_scheduled_event(name="Event", start_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1), entity_type=discord.EntityType.voice, channel=voice_channel)`

=== FINDING THINGS (always use loops, never discord.utils.get) ===
- Find member by name: `target = None; [search for m in guild.members if name.lower() in m.name.lower() or (m.nick and name.lower() in m.nick.lower())]`
- Find channel by name: `target = None; [search for c in guild.channels if name.lower() in c.name.lower()]`
- Find role by name: `target = None; [search for r in guild.roles if name.lower() in r.name.lower()]`
- guild.default_role = the @everyone role

=== IMPORTANT GOTCHAS ===
- guild.create_role() does NOT accept `description` parameter
- channel.delete_messages() only works on messages less than 14 days old
- Bulk delete max is 100 messages at a time
- Timeout max duration is 28 days
- Bot cannot timeout/kick/ban members with higher role hierarchy
- guild.members requires Members Intent to be enabled
- Always use `reason="..."` parameter where available for audit logs"""

    @discord.app_commands.command(name="modify", description="Natural language server management")
    async def modify(self, interaction: discord.Interaction, instruction: str):
        if not is_admin_or_mod(interaction.user):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            completion = await self.client.chat.completions.create(
                model="meta/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": instruction}
                ],
                temperature=0.1,
                top_p=0.95,
                max_tokens=2048,
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Find the first { and last } to robustly extract JSON even if there is conversational text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response_text = response_text[start_idx:end_idx+1]
                
            data = json.loads(response_text)
            is_dangerous = data.get("is_dangerous", False)
            code = data.get("code", "")
            summary = data.get("summary", "No summary provided.")

            if is_dangerous:
                view = ConfirmView()
                msg = await interaction.followup.send(
                    f"⚠️ **DANGEROUS ACTION DETECTED**\n**Summary:** {summary}\nAre you sure you want to proceed?",
                    view=view,
                    wait=True
                )
                await view.wait()
                if not view.value:
                    return

            # Execute the code dynamically
            local_env = {}
            try:
                # Compile and exec the code into local_env
                exec(code, globals(), local_env)
                action_func = local_env.get('generated_action')
                if not action_func:
                    raise ValueError("The generated code did not define 'generated_action'.")
                
                result_message = await action_func(interaction.guild, interaction)
            except Exception as e:
                await interaction.followup.send(f"❌ Error executing generated code:\n```py\n{str(e)}\n```")
                return

            try:
                await interaction.followup.send(f"✅ {result_message}")
            except discord.errors.NotFound:
                pass
            
            await log_action(self.bot, interaction.guild, interaction.user, "dynamic_action", "various", summary, True)

        except json.JSONDecodeError:
            await interaction.followup.send("Failed to parse AI response into JSON. Please try rephrasing your instruction.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(ModifyHandler(bot))

