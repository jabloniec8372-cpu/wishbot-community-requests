"""WishBot: Telegram long-polling runner. Usage: python bot.py config.json"""
import json
import sys
import time
import urllib.parse
import urllib.request

from core import RequestFlow, Store
from forms import make_submitter
from preview import fetch_title


def tg(token, method, **params):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode({k: str(v) for k, v in params.items()}).encode()
    with urllib.request.urlopen(url, data=data, timeout=70) as response:
        return json.loads(response.read().decode())


def main(config_path: str) -> None:
    with open(config_path, encoding="utf-8") as handle:
        cfg = json.load(handle)
    token, chat_id = cfg["telegram_token"], str(cfg["allowed_chat_id"])
    flow = RequestFlow(
        Store(cfg.get("db_path", "wishbot.db")),
        fetch_title,
        make_submitter(cfg["google_form"]),
    )
    offset = None
    print("WishBot is running. Ctrl+C to stop.")
    while True:
        try:
            params = {"timeout": 50}
            if offset is not None:
                params["offset"] = offset
            for update in tg(token, "getUpdates", **params).get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                if str(message.get("chat", {}).get("id")) != chat_id:
                    continue  # ignore every other chat
                sender = message.get("from", {})
                reply = flow.handle(sender.get("id"), sender.get("first_name", "member"), message.get("text", ""))
                tg(token, "sendMessage", chat_id=chat_id, text=reply)
        except Exception as exc:  # network hiccup: log and keep going
            print("Error:", exc)
            time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python bot.py config.json")
    main(sys.argv[1])
