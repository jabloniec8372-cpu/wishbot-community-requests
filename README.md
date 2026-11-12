# WishBot: Community Request Bot (demo project)

A Telegram bot for community admins who collect requests from group members (here: a book club).
This is a personal demo project, not client work.

## How it works
1. A member posts a title or a link in the group.
2. The bot reads the link preview (Open Graph title) and asks: "Is this what you mean?"
3. After the member confirms, the bot checks a local catalog to prevent duplicates.
4. New requests are submitted automatically through a Google Form.
5. A strike system discourages members from requesting items that already exist.
   After the limit, requests are paused for that member.

## Stack
Python 3 (standard library only), Telegram Bot API, SQLite, Google Forms.

## Run
```
cp config.example.json config.json   # add your token, chat ID and form fields
python bot.py config.json
python -m unittest                    # run the tests
```

The bot answers only in the chat set in `allowed_chat_id`.
