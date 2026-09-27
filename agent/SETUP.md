# Your own assistant on Telegram (Hermes)

The Claude tabs in cmux are where you work at the Mac. This step gives you a second way in: a personal assistant
you can message from your phone on Telegram, any time. It runs on your Mac (later on a Mac mini that stays on),
uses the same brain files as your Claude tabs, and answers only you.

The harness is **Hermes Agent** (open source, by Nous Research, https://hermes-agent.nousresearch.com).

```
 your phone ──Telegram──► your bot ──► Hermes on your Mac ──► reads ~/.claude/CLAUDE.md, MEMORY.md, context/
                                          │
                                          └─ the model you pick in step 2 does the thinking
```

Time: about 20 minutes. You can stop after any step and continue later.

**Guide note:** every command marked *(you type)* is interactive or involves a secret. Ask the owner to run it
in a separate cmux tab and tell you when it is done. Never ask them to paste a bot token or key into this chat.

## 1. Install Hermes *(you type)*
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```
Then open a new tab and check: `hermes --version`.

## 2. Pick the model that does the thinking *(you type)*
```bash
hermes model
```
Choose the provider you already have an account with. Any of these work; pick one:
- **ChatGPT / OpenAI**: sign in with your OpenAI account.
- **Anthropic (Claude)**: an API key from https://console.anthropic.com (pay as you go).
- **Nous Portal**: one subscription that also covers web search and voice (`hermes setup --portal`).
- **OpenRouter**: one key, hundreds of models.
Test it: `hermes -z "Say hello in one sentence"`.

## 3. Create your Telegram bot *(you, on your phone)*
1. In Telegram, open **@BotFather** and send `/newbot`.
2. Give it a display name (your assistant's name) and a username ending in `bot`.
3. BotFather replies with a **token**. Keep that message; you paste it only into your terminal in step 4.
4. Open **@userinfobot** and send any message. It replies with your **Id** (a number). Note it.

## 4. Connect the bot to Hermes *(you type)*
```bash
hermes gateway setup
```
Choose Telegram, paste the bot token, and when it asks who is allowed, enter your Id from step 3.
Then run it in the background so it survives restarts:
```bash
hermes gateway install
hermes gateway status
```

## 5. Give it your assistant's personality (the guide can run this)
```bash
python3 kit.py agent
hermes gateway restart
```
This writes `~/.hermes/SOUL.md` (who the assistant is and its rules), creates its working folder, sets it to
ignore strangers, and points it at your shared brain. Edit `~/.hermes/SOUL.md` any time; send `/new` in Telegram
afterward so it rereads it.

## 6. Say hello
In Telegram, open your bot and send `/new`, then something like "Hi, what do you know about me?". It should
answer using what is in your about-me file.

## 7. Optional: a ping on your phone when a Claude tab finishes while you are away (the guide can run this)
```bash
python3 kit.py notify <your Id from step 3>
```
From then on, when a Claude tab finishes a job and your Mac has been idle for 2 minutes, your bot sends you one line.

## If something is off
- `hermes doctor` checks the install. `hermes gateway status` shows whether the bot is running.
- The bot does not answer: check the allowed user Id matches yours, then `hermes gateway restart`.
- Undo everything: `hermes gateway uninstall`, and delete the bot in @BotFather with `/deletebot`.
