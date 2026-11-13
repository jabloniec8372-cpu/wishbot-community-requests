import unittest

from core import RequestFlow, Store, normalize_title
from preview import parse_title


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.submitted = []
        self.store = Store()
        self.flow = RequestFlow(
            self.store,
            fetch_title=lambda url: "The Hobbit" if "hobbit" in url else "",
            submit_form=lambda title, url, name: self.submitted.append((title, url, name)),
            strike_limit=2,
        )

    def test_normalize(self):
        self.assertEqual(normalize_title("  The Hobbit!! "), normalize_title("the   hobbit"))

    def test_normalize_keeps_non_ascii_letters_apart(self):
        # Before the fix every non-ASCII letter was stripped, so these collided.
        self.assertNotEqual(normalize_title("Żmija"), normalize_title("Żółć"))
        self.assertNotEqual(normalize_title("Über"), normalize_title("Ober"))
        self.assertTrue(normalize_title("Żółć"))
        self.assertTrue(normalize_title("Война и мир"))

    def test_normalize_matches_with_and_without_accents(self):
        self.assertEqual(normalize_title("Żółw i zając"), normalize_title("zolw i zajac"))
        self.assertEqual(normalize_title("Die Verwandlung – Größe"), normalize_title("die verwandlung grosse"))

    def test_polish_title_is_detected_as_duplicate(self):
        self.store.add_title("Pan Tadeusz")
        self.assertIn("already in the catalog", self.flow.handle(1, "Anna", "pan tadeusz"))
        self.assertIn("Is this what you mean?", self.flow.handle(2, "Piotr", "Quo Vadis"))

    def test_symbols_only_is_rejected(self):
        self.assertIn("could not find a title", self.flow.handle(1, "Anna", "!!! ???"))

    def test_confirm_and_submit(self):
        reply = self.flow.handle(1, "Anna", "https://books.example/hobbit")
        self.assertIn("The Hobbit", reply)
        self.assertEqual(self.submitted, [])
        self.assertIn("Submitted", self.flow.handle(1, "Anna", "yes"))
        self.assertEqual(self.submitted, [("The Hobbit", "https://books.example/hobbit", "Anna")])
        self.assertTrue(self.store.in_catalog("the hobbit"))

    def test_cancel(self):
        self.flow.handle(1, "Anna", "Dune")
        self.assertIn("Cancelled", self.flow.handle(1, "Anna", "no"))
        self.assertEqual(self.submitted, [])

    def test_duplicate_gives_strike_then_blocks(self):
        self.store.add_title("Dune")
        self.assertIn("Strike 1/2", self.flow.handle(1, "Anna", "dune"))
        self.assertIn("Strike 2/2", self.flow.handle(1, "Anna", "DUNE!"))
        self.assertIn("paused", self.flow.handle(1, "Anna", "Emma"))
        self.assertEqual(self.submitted, [])

    def test_unreadable_link(self):
        self.assertIn("could not", self.flow.handle(1, "Anna", "https://nothing.example/x"))

    def test_submit_failure_keeps_pending(self):
        def broken(title, url, name):
            raise RuntimeError("down")

        flow = RequestFlow(Store(), lambda u: "", broken)
        flow.handle(1, "Anna", "Emma")
        self.assertIn("try again", flow.handle(1, "Anna", "yes"))
        self.assertIn(("1"), flow.pending)

    def test_parse_title_prefers_og(self):
        html = '<html><head><title>Fallback</title><meta property="og:title" content="Real Title"></head></html>'
        self.assertEqual(parse_title(html), "Real Title")
        self.assertEqual(parse_title("<title>Only Title</title>"), "Only Title")


if __name__ == "__main__":
    unittest.main()
