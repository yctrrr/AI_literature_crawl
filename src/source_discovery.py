from __future__ import annotations

import time
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from src.config import NatureConfig
from src.models import Candidate
from src.utils import keyword_matches, normalize_url


class SourceDiscovery:
    def __init__(self, config: NatureConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    def discover(self, keywords: list[str]) -> list[Candidate]:
        all_candidates: list[Candidate] = []
        seen: set[str] = set()
        for keyword in keywords:
            keyword_candidates = self._discover_keyword(keyword)
            for candidate in keyword_candidates:
                if candidate.url in seen:
                    continue
                seen.add(candidate.url)
                all_candidates.append(candidate)
        return all_candidates

    def _discover_keyword(self, keyword: str) -> list[Candidate]:
        candidates: list[Candidate] = []
        if self.config.feed_first:
            candidates.extend(self._discover_from_feeds(keyword))

        if self.config.search_fallback and len(candidates) < self.config.min_results_before_search_fallback:
            candidates.extend(self._discover_from_search(keyword))

        deduped: list[Candidate] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.url in seen:
                continue
            seen.add(candidate.url)
            deduped.append(candidate)
        return deduped

    def _discover_from_feeds(self, keyword: str) -> list[Candidate]:
        candidates: list[Candidate] = []
        for feed_url in self.config.feed_urls:
            try:
                response = self.session.get(feed_url, timeout=self.config.request_timeout_seconds)
                response.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(response.text, "xml")
            items = soup.find_all(["item", "entry"])
            for item in items:
                title = self._node_text(item, "title")
                summary = self._node_text(item, "description") or self._node_text(item, "summary")
                link = self._extract_feed_link(item)
                if not link:
                    continue
                haystack = f"{title}\n{summary}"
                if not keyword_matches(keyword, haystack):
                    continue
                candidates.append(
                    Candidate(
                        url=normalize_url(link, self.config.base_url),
                        title=title or link,
                        keyword=keyword,
                        source=feed_url,
                        published=self._node_text(item, "pubDate") or self._node_text(item, "updated"),
                        summary=summary,
                    )
                )
            time.sleep(self.config.delay_seconds)
        return candidates

    def _discover_from_search(self, keyword: str) -> list[Candidate]:
        candidates: list[Candidate] = []
        for journal in self.config.journals:
            for page in range(1, self.config.search_max_pages_per_keyword + 1):
                params = {"q": keyword, "journal": journal, "page": page}
                url = f"{self.config.base_url}/search?{urlencode(params)}"
                try:
                    response = self.session.get(url, timeout=self.config.request_timeout_seconds)
                    response.raise_for_status()
                except requests.RequestException:
                    continue
                candidates.extend(self._parse_search_page(response.text, keyword, url))
                time.sleep(self.config.delay_seconds)
        return candidates

    def _parse_search_page(self, html: str, keyword: str, source_url: str) -> list[Candidate]:
        soup = BeautifulSoup(html, "html.parser")
        candidates: list[Candidate] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            if "/articles/" not in href:
                continue
            title = anchor.get_text(" ", strip=True)
            if not title or len(title) < 8:
                continue
            url = normalize_url(href, self.config.base_url)
            candidates.append(Candidate(url=url, title=title, keyword=keyword, source=source_url))
        return candidates

    @staticmethod
    def _node_text(item, name: str) -> str:
        node = item.find(name)
        return node.get_text(" ", strip=True) if node else ""

    @staticmethod
    def _extract_feed_link(item) -> str:
        link = item.find("link")
        if not link:
            return ""
        if link.get("href"):
            return link.get("href", "")
        return link.get_text(" ", strip=True)
