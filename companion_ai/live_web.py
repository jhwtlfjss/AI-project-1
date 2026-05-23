from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from companion_ai.autonomous_learning import (
    assert_domain_allowed,
    fetch_readable_url,
    fetch_wikipedia_summary,
    normalize_space,
)
from companion_ai.knowledge import KnowledgeBase


URL_RE = re.compile(r"https?://[^\s<>'\")]+")
DEFAULT_USER_AGENT = "MyCompanionAI/0.1 (+local live web lookup)"


@dataclass
class LiveWebResult:
    title: str
    summary: str
    url: str
    source_type: str


@dataclass
class SearchCandidate:
    title: str
    url: str


class LiveWebClient:
    def __init__(self, config: dict):
        self.config = config
        self.enabled = bool(config.get("live_web_enabled", True))
        self.auto_lookup = bool(config.get("auto_lookup", True))
        self.cache_live_results = bool(config.get("cache_live_results", True))
        self.max_results = int(config.get("max_results", 3))
        self.max_search_links = int(config.get("max_search_links", max(8, self.max_results * 4)))
        self.max_context_chars = int(config.get("max_context_chars", 1000))
        self.search_engine = normalize_search_engine(str(config.get("search_engine", "google")))
        self.custom_search_url = str(config.get("custom_search_url", "")).strip()
        self.triggers = [str(x).lower() for x in config.get("lookup_triggers", [])]
        self.allowed_domains = set(config.get("allowed_domains", []))
        self.blocked_domains = set(config.get("blocked_domains", []))

    @classmethod
    def load(cls, path: Path) -> "LiveWebClient":
        if not path.exists():
            return cls({})
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def with_overrides(self, overrides: dict | None) -> "LiveWebClient":
        if not overrides:
            return self
        config = dict(self.config)
        if "enabled" in overrides:
            config["live_web_enabled"] = bool(overrides["enabled"])
        if "auto_lookup" in overrides:
            config["auto_lookup"] = bool(overrides["auto_lookup"])
        if "search_engine" in overrides:
            config["search_engine"] = normalize_search_engine(str(overrides["search_engine"]))
        if "custom_search_url" in overrides:
            config["custom_search_url"] = str(overrides["custom_search_url"]).strip()
        return LiveWebClient(config)

    def public_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_lookup": self.auto_lookup,
            "search_engine": self.search_engine,
            "custom_search_url": self.custom_search_url,
        }

    def should_lookup(self, text: str) -> bool:
        if not self.enabled:
            return False
        if extract_urls(text):
            return True
        if not self.auto_lookup:
            return False
        lowered = text.lower()
        return any(trigger in lowered for trigger in self.triggers)

    def lookup(self, text: str) -> list[LiveWebResult]:
        if not self.should_lookup(text):
            return []
        results: list[LiveWebResult] = []
        seen: set[str] = set()

        for url in extract_urls(text):
            result = self.fetch_url(url)
            if result and result.url not in seen:
                results.append(result)
                seen.add(result.url)
            if len(results) >= self.max_results:
                return results

        query = clean_query(text)
        if query:
            for result in self.search_web(query):
                if result.url not in seen:
                    results.append(result)
                    seen.add(result.url)
                if len(results) >= self.max_results:
                    return results

            for result in self.wikipedia_search(query):
                if result.url not in seen:
                    results.append(result)
                    seen.add(result.url)
                if len(results) >= self.max_results:
                    return results
        return results

    def context_for_prompt(self, text: str) -> str:
        context, _ = self.lookup_context(text)
        return context

    def lookup_context(self, text: str) -> tuple[str, list[LiveWebResult]]:
        try:
            results = self.lookup(text)
            return render_live_web_results(results, max_chars=self.max_context_chars), results
        except Exception as exc:
            return f"网络查询失败: {exc}", []

    def cache_results(self, knowledge: KnowledgeBase, results: list[LiveWebResult], topic: str = "live_web"):
        if not self.cache_live_results:
            return
        for result in results:
            knowledge.add_or_update(
                topic=topic,
                title=result.title,
                summary=result.summary,
                source_url=result.url,
                source_type=result.source_type,
                language=guess_result_language(result.summary),
                tags=["live_web", "实时查询", "network"],
            )

    def fetch_url(self, url: str) -> LiveWebResult | None:
        assert_domain_allowed(url, self.blocked_domains, self.allowed_domains)
        title, body, final_url = fetch_readable_url(url)
        assert_domain_allowed(final_url, self.blocked_domains, self.allowed_domains)
        summary = summarize_text(body, max_chars=450)
        if not summary:
            return None
        return LiveWebResult(title=title or final_url, summary=summary, url=final_url, source_type="url")

    def search_web(self, query: str) -> list[LiveWebResult]:
        search_url = build_search_url(self.search_engine, query, self.custom_search_url)
        if not search_url:
            return []
        candidates = fetch_search_candidates(search_url, self.search_engine, self.max_search_links)
        results: list[LiveWebResult] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.url in seen:
                continue
            seen.add(candidate.url)
            try:
                result = self.fetch_url(candidate.url)
            except Exception:
                result = None
            if result:
                result.source_type = self.search_engine
                if is_relevant(query, f"{result.title} {result.summary}"):
                    results.append(result)
            elif is_relevant(query, candidate.title):
                results.append(
                    LiveWebResult(
                        title=candidate.title or candidate.url,
                        summary=f"搜索结果: {candidate.title or candidate.url}",
                        url=candidate.url,
                        source_type=f"{self.search_engine}:search-result",
                    )
                )
            if len(results) >= self.max_results:
                return results
        return results

    def duckduckgo_instant(self, query: str) -> list[LiveWebResult]:
        api = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        )
        request = urllib.request.Request(api, headers={"User-Agent": DEFAULT_USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read(1_000_000).decode("utf-8", errors="replace"))

        results: list[LiveWebResult] = []
        title = normalize_space(str(data.get("Heading", "")))
        summary = normalize_space(str(data.get("AbstractText", "")))
        url = normalize_space(str(data.get("AbstractURL", "")))
        if summary and url:
            assert_domain_allowed(url, self.blocked_domains, self.allowed_domains)
            if is_relevant(query, f"{title} {summary}"):
                results.append(LiveWebResult(title=title or query, summary=summary, url=url, source_type="duckduckgo"))

        for item in flatten_related_topics(data.get("RelatedTopics", [])):
            if len(results) >= self.max_results:
                break
            text = normalize_space(str(item.get("Text", "")))
            first_url = normalize_space(str(item.get("FirstURL", "")))
            if text and first_url:
                assert_domain_allowed(first_url, self.blocked_domains, self.allowed_domains)
                title = text.split(" - ", 1)[0][:120]
                if is_relevant(query, text):
                    results.append(
                        LiveWebResult(
                            title=title,
                            summary=text,
                            url=first_url,
                            source_type="duckduckgo",
                        )
                    )
        return results

    def wikipedia_search(self, query: str) -> list[LiveWebResult]:
        results: list[LiveWebResult] = []
        for lang in guess_wikipedia_languages(query):
            api = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": self.max_results,
                }
            )
            request = urllib.request.Request(api, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read(1_000_000).decode("utf-8", errors="replace"))
            for item in data.get("query", {}).get("search", []):
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                page_title, extract, page_url = fetch_wikipedia_summary(lang, title)
                assert_domain_allowed(page_url, self.blocked_domains, self.allowed_domains)
                if extract and is_relevant(query, f"{page_title} {extract}"):
                    results.append(
                        LiveWebResult(
                            title=page_title or title,
                            summary=extract,
                            url=page_url,
                            source_type=f"wikipedia:{lang}",
                        )
                    )
                if len(results) >= self.max_results:
                    return results
        return results


def render_live_web_results(results: list[LiveWebResult], max_chars: int = 1000) -> str:
    lines: list[str] = []
    used = 0
    for result in results:
        line = f"- {result.title}: {result.summary} 来源: {result.url}"
        if used + len(line) > max_chars:
            remaining = max_chars - used
            if remaining <= 60:
                break
            line = line[:remaining].rstrip() + "..."
        lines.append(line)
        used += len(line)
        if used >= max_chars:
            break
    return "\n".join(lines)


class SearchPageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[SearchCandidate] = []
        self.current_href = ""
        self.current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() != "a":
            return
        attrs_dict = {name.lower(): value for name, value in attrs if value is not None}
        href = attrs_dict.get("href", "").strip()
        if href:
            self.current_href = urllib.parse.urljoin(self.base_url, href)
            self.current_text = []

    def handle_data(self, data: str):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag: str):
        if tag.lower() != "a" or not self.current_href:
            return
        title = normalize_space(" ".join(self.current_text))
        url = normalize_search_result_url(self.current_href)
        if title and url and is_search_candidate_url(url):
            self.links.append(SearchCandidate(title=title[:160], url=url))
        self.current_href = ""
        self.current_text = []


def normalize_search_engine(value: str) -> str:
    value = value.strip().lower()
    aliases = {
        "google": "google",
        "谷歌": "google",
        "baidu": "baidu",
        "百度": "baidu",
        "custom": "custom",
        "自定义": "custom",
    }
    return aliases.get(value, "google")


def build_search_url(engine: str, query: str, custom_search_url: str = "") -> str:
    encoded = urllib.parse.quote_plus(query)
    if engine == "google":
        return "https://www.google.com/search?" + urllib.parse.urlencode({"q": query, "num": "8", "hl": "zh-CN"})
    if engine == "baidu":
        return "https://www.baidu.com/s?" + urllib.parse.urlencode({"wd": query})
    if engine == "custom":
        if not custom_search_url:
            return ""
        if "{query}" in custom_search_url:
            return custom_search_url.replace("{query}", encoded)
        if "%s" in custom_search_url:
            return custom_search_url.replace("%s", encoded)
        separator = "&" if "?" in custom_search_url else "?"
        return f"{custom_search_url}{separator}q={encoded}"
    return ""


def fetch_search_candidates(search_url: str, engine: str, limit: int) -> list[SearchCandidate]:
    request = urllib.request.Request(search_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read(2_000_000).decode("utf-8", errors="replace")
        final_url = response.geturl()
    parser = SearchPageParser(final_url)
    parser.feed(html)
    candidates: list[SearchCandidate] = []
    seen: set[str] = set()
    for item in parser.links:
        if item.url in seen:
            continue
        if is_search_engine_internal_url(item.url, engine):
            continue
        candidates.append(item)
        seen.add(item.url)
        if len(candidates) >= limit:
            break
    return candidates


def normalize_search_result_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if parsed.netloc.endswith("google.com") and parsed.path == "/url" and query.get("q"):
        return query["q"][0]
    if parsed.netloc.endswith("google.com") and parsed.path == "/search":
        return ""
    return url


def is_search_candidate_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    lowered = url.lower()
    blocked_bits = [
        "javascript:",
        "accounts.google.",
        "policies.google.",
        "support.google.",
        "preferences?hl=",
        "baidu.com/s?",
        "baidu.com/#",
        "passport.baidu.",
    ]
    return not any(bit in lowered for bit in blocked_bits)


def is_search_engine_internal_url(url: str, engine: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if engine == "google":
        return host.endswith("google.com") or host.endswith("google.co.jp")
    if engine == "baidu":
        return host.endswith("baidu.com") and not parsed.path.startswith("/link")
    return False


def extract_urls(text: str) -> list[str]:
    return [match.group(0).rstrip(".,;，。；)") for match in URL_RE.finditer(text)]


def clean_query(text: str) -> str:
    text = URL_RE.sub(" ", text)
    remove_words = [
        "查一下",
        "查",
        "搜索",
        "搜",
        "联网",
        "最新",
        "今天",
        "现在",
        "ニュース",
        "調べて",
        "調べ",
        "検索",
        "今日",
        "今",
        "search for",
        "search",
        "look up",
        "latest",
        "today",
        "current",
        "news",
        "weather",
        "please",
    ]
    lowered = text.lower()
    for word in remove_words:
        lowered = lowered.replace(word.lower(), " ")
    lowered = re.sub(r"[\?\?!？！。.,，:：;；]+", " ", lowered)
    return normalize_space(lowered)[:160]


def summarize_text(text: str, max_chars: int = 450) -> str:
    cleaned = normalize_space(text)
    if len(cleaned) <= max_chars:
        return cleaned
    sentence_parts = re.split(r"(?<=[。！？.!?])\s+", cleaned)
    out = ""
    for sentence in sentence_parts:
        if len(out) + len(sentence) > max_chars:
            break
        out += sentence + " "
    return normalize_space(out) or cleaned[:max_chars]


def flatten_related_topics(items) -> list[dict]:
    flat: list[dict] = []
    for item in items:
        if "Topics" in item:
            flat.extend(flatten_related_topics(item.get("Topics", [])))
        elif isinstance(item, dict):
            flat.append(item)
    return flat


def guess_wikipedia_languages(query: str) -> list[str]:
    if any("\u3040" <= ch <= "\u30ff" for ch in query):
        return ["ja", "zh", "en"]
    if any("\u4e00" <= ch <= "\u9fff" for ch in query):
        return ["zh", "ja", "en"]
    return ["en", "zh", "ja"]


def guess_result_language(text: str) -> str:
    if any("\u3040" <= ch <= "\u30ff" for ch in text):
        return "ja"
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"


def is_relevant(query: str, text: str) -> bool:
    terms = meaningful_terms(query)
    if not terms:
        return True
    lowered = text.lower()
    return any(term in lowered for term in terms)


def meaningful_terms(query: str) -> set[str]:
    lowered = query.lower()
    terms = {word for word in re.findall(r"[a-zA-Z0-9_]+", lowered) if len(word) >= 3}
    cjk = [
        ch
        for ch in lowered
        if "\u4e00" <= ch <= "\u9fff"
        or "\u3040" <= ch <= "\u30ff"
        or "\uac00" <= ch <= "\ud7af"
    ]
    stop_bigrams = {
        "一下",
        "什么",
        "是什",
        "怎么",
        "如何",
        "最新",
        "新闻",
        "天气",
        "今日",
        "今天",
    }
    for i in range(len(cjk) - 1):
        bigram = "".join(cjk[i : i + 2])
        if bigram not in stop_bigrams:
            terms.add(bigram)
    return terms
