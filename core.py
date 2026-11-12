"""Core logic of WishBot: confirmation flow, duplicate catalog and strike system.

Pure Python (stdlib only). All network access is injected, so the flow is easy to test.
"""
import re
import sqlite3

URL_RE = re.compile(r"https?://\S+")
YES = {"yes", "y", "tak", "ok"}
NO = {"no", "n", "nie", "cancel"}


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation and collapse spaces, so near-identical titles match."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title.lower())).strip()


class Store:
    """SQLite storage: catalog of already requested/available titles and strikes per member."""

    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog (key TEXT PRIMARY KEY, title TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS strikes (user_id TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0);
            """
        )

    def in_catalog(self, title: str) -> bool:
        row = self.db.execute("SELECT 1 FROM catalog WHERE key = ?", (normalize_title(title),)).fetchone()
        return row is not None

    def add_title(self, title: str) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO catalog (key, title) VALUES (?, ?)", (normalize_title(title), title)
        )
        self.db.commit()

    def catalog_size(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM catalog").fetchone()[0]

    def strikes(self, user_id: str) -> int:
        row = self.db.execute("SELECT count FROM strikes WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row else 0

    def add_strike(self, user_id: str) -> int:
        self.db.execute(
            "INSERT INTO strikes (user_id, count) VALUES (?, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET count = count + 1",
            (user_id,),
        )
        self.db.commit()
        return self.strikes(user_id)


class RequestFlow:
    """Member message -> title -> confirmation -> duplicate check -> form submission."""

    def __init__(self, store: Store, fetch_title, submit_form, strike_limit: int = 3):
        self.store = store
        self.fetch_title = fetch_title  # callable(url) -> title
        self.submit_form = submit_form  # callable(title, url, member_name) -> None
        self.strike_limit = strike_limit
        self.pending = {}  # user_id -> (title, url)

    def handle(self, user_id, member_name: str, text: str) -> str:
        user_id = str(user_id)
        text = (text or "").strip()
        if not text:
            return "Send me a title or a link to request it."

        if self.store.strikes(user_id) >= self.strike_limit:
            return "Requests are paused for you (too many strikes). Please contact the admin."

        if user_id in self.pending:
            answer = text.lower()
            if answer in YES:
                return self._confirm(user_id, member_name)
            if answer in NO:
                del self.pending[user_id]
                return "Cancelled. Send another title or link any time."
            del self.pending[user_id]  # a new request replaces the old one

        return self._start(user_id, text)

    def _start(self, user_id: str, text: str) -> str:
        match = URL_RE.search(text)
        url = match.group(0) if match else ""
        if url:
            try:
                title = (self.fetch_title(url) or "").strip()
            except Exception:
                return "I could not read that link. Please send the title as text."
        else:
            title = text
        if not title:
            return "I could not find a title there. Please send it as text."

        if self.store.in_catalog(title):
            count = self.store.add_strike(user_id)
            return (
                f"'{title}' is already in the catalog. Please check it before requesting. "
                f"Strike {count}/{self.strike_limit}."
            )

        self.pending[user_id] = (title, url)
        return f"Is this what you mean?\n{title}\nReply YES to submit or NO to cancel."

    def _confirm(self, user_id: str, member_name: str) -> str:
        title, url = self.pending[user_id]
        try:
            self.submit_form(title, url, member_name)
        except Exception:
            return "The request could not be submitted right now. Reply YES to try again."
        self.store.add_title(title)
        del self.pending[user_id]
        return f"Submitted: {title}"
