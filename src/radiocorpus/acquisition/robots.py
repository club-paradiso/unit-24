"""robots.txt compliance. Fetch failures are treated as 'unknown' and the caller decides; a
disallow is always honoured."""

from __future__ import annotations

from urllib import robotparser
from urllib.parse import urlparse

import httpx

_CACHE: dict[str, robotparser.RobotFileParser | None] = {}


def allowed(url: str, user_agent: str, client: httpx.Client) -> bool | None:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _CACHE:
        rp = robotparser.RobotFileParser()
        try:
            r = client.get(base + "/robots.txt", timeout=15)
            if r.status_code >= 400:
                _CACHE[base] = None
            else:
                rp.parse(r.text.splitlines())
                _CACHE[base] = rp
        except httpx.HTTPError:
            _CACHE[base] = None
    rp = _CACHE[base]
    if rp is None:
        return None
    return rp.can_fetch(user_agent, url)
