import pytest

from tunnel import TUNNEL_RE


@pytest.mark.parametrize(
    "line,expected",
    [
        (
            "2025-01-01T00:00:00Z INF https://foo-bar.trycloudflare.com",
            "https://foo-bar.trycloudflare.com",
        ),
        (
            "Your quick tunnel has been created at: https://abc-123.trycloudflare.com",
            "https://abc-123.trycloudflare.com",
        ),
        ("no url here", None),
    ],
)
def test_tunnel_url_regex(line, expected):
    match = TUNNEL_RE.search(line)
    assert (match.group(0) if match else None) == expected
