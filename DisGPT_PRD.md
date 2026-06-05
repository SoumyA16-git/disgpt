# 🤖 DisGPT — Product Requirements Document
**Version:** 2.0 | **Date:** June 2025 | **Status:** Draft — Ready for Development

| | |
|---|---|
| **AI Commands** | `/modify` (natural language — no fixed syntax) |
| **AI Chat** | `@DisGPT` or `/ask` (all users) |
| **AI Model** | NVIDIA Nemotron-3 Super 120B (Free API) |
| **Hosting** | Render.com (Free Tier) |
| **Language** | Python 3.11+ |

from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)


completion = client.chat.completions.create(
  model="nvidia/nemotron-3-super-120b-a12b",
  messages=[{"role":"user","content":""}],
  temperature=1,
  top_p=0.95,
  max_tokens=16384,
  extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384},
  stream=True
)

for chunk in completion:
  if not chunk.choices:
    continue
  reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
  if reasoning:
    print(reasoning, end="")
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")

---

## 1. Overview

DisGPT is a Discord bot with two main jobs:

- **AI Chat for everyone** — Any user can mention the bot or use `/ask` to chat with an AI (powered by NVIDIA Nemotron). It works exactly like ChatGPT.
- **Natural Language Server Management** — Admins and Moderators use ONE command: `/modify` — then write in plain English (or any language) what they want to do. The AI understands the intent and executes the action on the server.

> 💡 **Key Design:** There are NO memorizable mod commands. Just type `/modify` and describe what you want — the AI figures out what to do.

---

## 2. How `/modify` Works (The Core Feature)

When an Admin or Moderator types `/modify` followed by a plain-language instruction, the bot:

| Step | What Happens | Detail |
|------|-------------|--------|
| 1 | **Permission Check** | Bot immediately checks if the user is Admin or Moderator. If not → blocked. |
| 2 | **AI Understands** | The message is sent to NVIDIA Nemotron with a system prompt that tells the AI to parse the intent (create role, kick user, etc.) |
| 3 | **Action Extracted** | AI returns a structured JSON: what action to take, on which target, with what parameters |
| 4 | **Bot Executes** | Bot calls the Discord API to perform the exact action on the server |
| 5 | **Confirmation** | Bot replies with a success message, and logs the action to the audit channel |

### Real Examples

**Role Management**
```
/modify  create a role called "VIP" with gold color
/modify  make a Moderator role with permission to kick and ban members
/modify  give @Rahul the VIP role
/modify  remove the Member role from @Sneha
/modify  delete the "OldRole" role
```

**Member Actions**
```
/modify  kick @SpamUser he was posting ads
/modify  ban @ToxicUser permanently for harassment
/modify  mute @John for 30 minutes, reason: spamming
/modify  unmute @John
/modify  warn @Mike stop sharing links without permission
```

**Channel & Server Actions**
```
/modify  create a text channel called "announcements"
/modify  create a voice channel for gaming
/modify  delete the "old-chat" channel
/modify  lock the current channel
/modify  set slowmode to 10 seconds in this channel
/modify  post an announcement in #general: Server maintenance at 9pm tonight
```

**Info Queries**
```
/modify  show me info about @Rahul
/modify  how many members does this server have
/modify  list all roles on this server
```

> ✅ The bot understands different phrasings of the same intent. Whether you write "kick John", "remove John from server", or "throw out @John", the AI understands it's a kick action.

---

## 3. User Roles & Permissions

| Role | AI Chat (`/ask`) | `/modify` Command | Admin Settings |
|------|:---:|:---:|:---:|
| **Admin** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Moderator** | ✅ Yes | ✅ Yes | ❌ No |
| **Regular User** | ✅ Yes | ❌ No | ❌ No |

> ❌ If a regular user types `/modify`, the bot instantly replies: **"You don't have permission to use this command."** — No AI call is made, no action is taken.

### Admin-Only Actions (inside `/modify`)

Even within `/modify`, some actions only Admins can trigger:

- Changing the bot's command prefix
- Setting the audit log channel
- Clearing another user's AI memory
- Banning users *(Mods can only kick/mute)*

---

## 4. AI Chat (All Users)

Every user — regardless of role — can use the bot as a ChatGPT-style assistant.

| Setting | Value |
|---------|-------|
| **Trigger** | `@DisGPT [message]` or `/ask [question]` |
| **AI Model** | NVIDIA Nemotron-3 Super 120B |
| **Thinking Mode** | Enabled — AI reasons before answering complex questions |
| **Streaming** | Yes — typing indicator shown while AI is generating |
| **Memory** | Last 10 messages of context per user per channel |
| **Long Responses** | Auto-split into multiple messages if over 2000 characters |
| **Rate Limit** | 10 AI requests per user per minute |
| **Clear Memory** | `/ask clear my memory` or `/forget` |

---

## 5. NVIDIA Nemotron API Settings

| Parameter | Value |
|-----------|-------|
| **Model** | `nvidia/nemotron-3-super-120b-a12b` |
| **Base URL** | `https://integrate.api.nvidia.com/v1` |
| **Thinking Mode** | Enabled (`enable_thinking: True`) |
| **Max Tokens** | 16,384 |
| **Temperature** | 1.0 |
| **Top P** | 0.95 |
| **Reasoning Budget** | 16,384 tokens |
| **Streaming** | Yes — real-time response chunks |

### Two AI System Prompts

The bot uses two different system prompts depending on the situation:

**System Prompt 1 — For `/modify` (server actions)**
```
You are a Discord server management assistant.
Parse the user's plain-language instruction and return ONLY a JSON object:
{
  "action": "kick | ban | mute | create_role | delete_role | give_role |
             remove_role | create_channel | delete_channel | lock |
             unlock | slowmode | warn | announce | server_info | user_info",
  "target": "@username or role_name or channel_name",
  "params": { "reason": "...", "duration": 30, "color": "#FFD700", ... }
}
If the instruction is unclear, set action to "clarify" and ask for more info.
```

**System Prompt 2 — For `/ask` (normal chat)**
```
You are DisGPT, a helpful AI assistant inside a Discord server.
Answer questions clearly and helpfully. You have memory of the last
10 messages in this conversation. Do not perform any server actions.
```

> ⚠️ **Security Note:** The API key is NEVER in the code. It is stored only in Render's Environment Variables dashboard so it stays private and secure.

---

## 6. Bot Behavior Rules

| # | Rule | Detail |
|---|------|--------|
| 1 | **Permission first** | Permission is checked BEFORE any AI call. Regular users are blocked instantly. |
| 2 | **Clarification** | If `/modify` instruction is ambiguous, bot asks: "Did you mean...?" before acting |
| 3 | **Confirmation** | Before destructive actions (ban, delete channel), bot asks for confirmation |
| 4 | **Audit log** | Every `/modify` action is logged to the audit channel with: who, what, when, why |
| 5 | **Typing indicator** | Bot shows `typing...` while AI is generating a response |
| 6 | **Error handling** | If NVIDIA API fails, bot shows friendly error message and retries once |
| 7 | **Rate limiting** | Max 10 AI requests per user per minute to prevent API abuse |
| 8 | **No hallucination acting** | If AI is unsure what action to take, it asks — never guesses and acts |

---

## 7. Technical Stack & File Structure

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **Discord Library** | discord.py v2.x (slash commands support) |
| **AI API Client** | openai Python library (NVIDIA-compatible) |
| **Hosting** | Render.com — Free Web Service |
| **Keep-Alive** | Flask web server (prevents Render from sleeping the bot) |
| **Secrets** | Render Environment Variables — never in code |

### File Structure

```
DisGPT/
├── bot.py              ← Entry point, loads all modules
├── modify_handler.py   ← /modify command — AI parses + executes server actions
├── ai_chat.py          ← /ask and @mention — normal ChatGPT chat
├── discord_actions.py  ← All Discord API calls (kick, ban, create role, etc.)
├── permissions.py      ← Role checking (Admin / Mod / User)
├── audit_log.py        ← Logs all /modify actions to audit channel
├── keep_alive.py       ← Flask server for Render uptime
├── requirements.txt    ← Python dependencies
└── .env                ← Local secrets (NOT uploaded to GitHub)
```

---

## 8. Environment Variables (Render Settings)

Set these in your Render dashboard under **Environment**. Never put them in your code files.

| Variable Name | What to Put Here |
|---------------|-----------------|
| `DISCORD_TOKEN` | Your Discord bot token (from Discord Developer Portal) |
| `NVIDIA_API_KEY` | Your NVIDIA API key (starts with `nvapi-...`) |
| `LOG_CHANNEL_ID` | Discord channel ID where audit logs are posted |
| `ADMIN_ROLE_NAME` | Exact name of your Admin role on the server (e.g. `Admin`) |
| `MOD_ROLE_NAME` | Exact name of your Moderator role (e.g. `Moderator`) |

---

## 9. Deploying on Render.com

| Step | Where | Action |
|------|-------|--------|
| 1 | GitHub | Create free account → upload bot code as new repository |
| 2 | Render.com | Sign up free → New → Web Service → connect your GitHub repo |
| 3 | Render Settings | Set Start Command: `python bot.py` |
| 4 | Render Env Vars | Add all 5 environment variables from Section 8 |
| 5 | Discord Portal | Enable all Privileged Gateway Intents (Members, Messages, Presence) |
| 6 | Deploy | Click Deploy — bot goes live in ~2 minutes |
| 7 | Verify | Type `/ask hello` in your server — bot should reply |

> ✅ The Flask keep-alive server pings itself every 5 minutes so Render's free tier never puts the bot to sleep.

---

## 10. Success Criteria

The bot is considered successfully built when all of the following are true:

- [ ] `/modify` works with plain English — no memorizing command syntax needed
- [ ] Regular users are fully blocked from `/modify` with a clear message
- [ ] AI correctly identifies intent from varied phrasings
- [ ] Bot asks for confirmation before destructive actions (ban, delete)
- [ ] All `/modify` actions are logged to the audit channel
- [ ] AI Chat (`/ask`) works for all users with memory context
- [ ] Bot stays online 24/7 on Render without manual restarts
- [ ] Bot handles API errors gracefully without crashing

---

*DisGPT v2.0 — Natural Language Server Manager — June 2025*
