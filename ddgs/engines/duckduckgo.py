"""Duckduckgo search engine implementation."""

from collections.abc import Mapping
from typing import Any, ClassVar
from urllib.parse import parse_qs, unquote, urlparse

from ddgs.base import BaseSearchEngine
from ddgs.results import TextResult


def _extract_uddg(href: str) -> str:
    """Decode the DuckDuckGo lite redirect wrapper to the real target URL."""
    parsed = urlparse(href if "://" in href else f"https:{href}")
    if "duckduckgo" in parsed.netloc and (uddg := parse_qs(parsed.query).get("uddg")):
        return unquote(uddg[0])
    return href


class Duckduckgo(BaseSearchEngine[TextResult]):
    """Duckduckgo search engine."""

    name = "duckduckgo"
    category = "text"
    provider = "duckduckgo"

    search_url = "https://lite.duckduckgo.com/lite/"
    search_method = "GET"

    items_xpath = "//a[@class='result-link']"
    elements_xpath: ClassVar[Mapping[str, str]] = {"title": "./text()", "href": "./@href"}

    def build_payload(
        self,
        query: str,
        region: str,  # noqa: ARG002
        safesearch: str,  # noqa: ARG002
        timelimit: str | None,  # noqa: ARG002
        page: int = 1,
        **kwargs: str,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Build a payload for the search request."""
        payload: dict[str, Any] = {"q": query}
        if page > 1:
            payload["s"] = str((page - 1) * 20)
        return payload

    def post_extract_results(self, results: list[TextResult]) -> list[TextResult]:
        """Post-process search results."""
        post_results = []
        for result in results:
            result.href = _extract_uddg(result.href)
            if result.href.startswith("http"):
                post_results.append(result)
        return post_results
