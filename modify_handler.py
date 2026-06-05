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

DISCORD.PY 2.0 CHEAT SHEET FOR LLMS:
- List bans: `async for ban_entry in guild.bans(): user = ban_entry.user`
- List history: `async for msg in channel.history(limit=100):`
- Mute/Timeout: `import datetime; await member.timeout(datetime.timedelta(minutes=10), reason="...")`
- Unmute/Remove Timeout: `await member.timeout(None)`
- Kick/Ban: `await member.kick()`, `await member.ban()`
- Unban: `await guild.unban(user)`
- Change Nickname: `await member.edit(nick="new_name")`
- Move Voice: `await member.move_to(voice_channel)`
- Disconnect Voice: `await member.move_to(None)`
- Delete Multiple Messages: `await channel.delete_messages(list_of_messages)`
- Delete Role: `await role.delete()`
- Create Role: `await guild.create_role(name="...", color=discord.Color.red())` (Do NOT pass a `description` parameter, roles do not have descriptions in discord.py)
- Add Role to Member: `await member.add_roles(role)`
- Remove Role: `await member.remove_roles(role)`
- Edit Guild: `await guild.edit(name="new_name")`
- Delete Channel: `await channel.delete()`
- Edit Channel Permissions: `await channel.set_permissions(role_or_member, read_messages=True, send_messages=False)`"""

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

