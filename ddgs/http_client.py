"""HTTP client."""

import logging
from collections.abc import Mapping
from functools import cached_property
from typing import Any
from urllib.parse import urlparse

from httpcloak import HTTPCloakError, Session  # type: ignore[import-untyped]
from lxml import html
from markdownify import markdownify

from .exceptions import DDGSException, TimeoutException

logger = logging.getLogger(__name__)

DEFAULT_PRESET = "chrome-latest"


class Response:
    """HTTP response."""

    def __init__(self, resp: Any) -> None:  # noqa: ANN401
        self.status_code = resp.status_code
        self.content = resp.content
        self.text = resp.text

    @cached_property
    def text_markdown(self) -> str:
        """Get response body as Markdown text."""
        return markdownify(self.text) or ""

    @cached_property
    def text_plain(self) -> str:
        """Get response body as plain text."""
        tree = html.fromstring(self.text)
        for elem in tree.iter():
            if elem.tag in ("script", "style"):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
        return " ".join("".join(map(str, tree.itertext())).split())

    @cached_property
    def text_rich(self) -> str:
        """Get response body as rich text (approximated with Markdown)."""
        return markdownify(self.text, heading_style="ATX") or ""


class HttpClient:
    """HTTP client."""

    def __init__(self, proxy: str | None = None, timeout: int | None = 10, *, verify: bool | str = True) -> None:
        """Initialize the HttpClient object.

        Args:
            proxy (str, optional): proxy for the HTTP client, supports http/https/socks5 protocols.
                example: "http://user:pass@example.com:3128". Defaults to None.
            timeout (int, optional): Timeout value for the HTTP client. Defaults to 10.
            verify: (bool | str):  True to verify, False to skip. Defaults to True.

        """
        if isinstance(verify, str):
            logger.warning("Custom CA paths are not supported by httpcloak; falling back to verify=True")
            verify = True
        self.client = Session(
            preset=DEFAULT_PRESET,
            proxy=proxy,
            timeout=timeout,
            verify=verify,
        )
        self._headers: dict[str, str] = {}

    def headers_update(self, headers: Mapping[str, str]) -> None:
        """Update the persistent request headers."""
        self._headers.update(headers)

    def set_cookies(self, url: str, cookies: dict[str, str]) -> None:
        """Set cookies for the given URL's domain."""
        host = urlparse(url if "://" in url else f"https://{url}").hostname
        for name, value in cookies.items():
            self.client.set_cookie(name, value, domain=host or "")

    def request(self, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Make a request to the HTTP client."""
        headers = {**self._headers, **kwargs.pop("headers", {})}
        try:
            resp = self.client.request(*args, headers=headers, **kwargs)
            return Response(resp)
        except HTTPCloakError as ex:
            if "timed out" in f"{ex}".lower():
                raise TimeoutException(ex) from ex
            msg = f"{type(ex).__name__}: {ex!r}"
            raise DDGSException(msg) from ex

    def get(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Make a GET request to the HTTP client."""
        return self.request("GET", url, *args, **kwargs)

    def post(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Make a POST request to the HTTP client."""
        return self.request("POST", url, *args, **kwargs)
