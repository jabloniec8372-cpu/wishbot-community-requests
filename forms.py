"""Submits a request to a Google Form (formResponse endpoint)."""
import urllib.parse
import urllib.request


def make_submitter(form_config: dict):
    """Returns submit(title, url, member_name) bound to the form from config.json."""
    action_url = form_config["action_url"]
    fields = form_config["fields"]  # {"title": "entry.123", "url": "entry.456", "member": "entry.789"}

    def submit(title: str, url: str, member_name: str) -> None:
        data = urllib.parse.urlencode(
            {fields["title"]: title, fields["url"]: url, fields["member"]: member_name}
        ).encode()
        request = urllib.request.Request(action_url, data=data, method="POST")
        with urllib.request.urlopen(request, timeout=30):
            pass

    return submit
