"""Offline demo: runs the real request flow with fake I/O and prints a chat transcript."""
from core import RequestFlow, Store

submitted = []
store = Store()
store.add_title("Pan Tadeusz")
flow = RequestFlow(
    store,
    fetch_title=lambda url: "Solaris - Stanisław Lem" if "solaris" in url else "",
    submit_form=lambda title, url, name: submitted.append(title),
    strike_limit=3,
)

SCRIPT = [
    ("Anna", "https://books.example/solaris"),
    ("Anna", "yes"),
    ("Piotr", "pan tadeusz"),
    ("Piotr", "Quo Vadis"),
    ("Piotr", "no"),
]


def transcript():
    uid = {"Anna": 1, "Piotr": 2}
    for name, text in SCRIPT:
        yield name, text, flow.handle(uid[name], name, text)


if __name__ == "__main__":
    for name, text, reply in transcript():
        print(f"{name}: {text}\nWishBot: {reply}\n")
    print("Submitted to form:", submitted)
