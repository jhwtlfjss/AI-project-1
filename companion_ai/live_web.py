from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
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


class LiveWebClient:
    def __init__(self, config: dict):
        self.config = config
        self.enabled = bool(config.get("live_web_enabled", True))
        self.auto_lookup = bool(config.get("auto_lookup", True))
        self.cache_live_results = bool(config.get("cache_live_results", True))
        self.max_results = int(config.get("max_results", 3))
        self.max_context_chars = int(config.get("max_context_chars", 1000))
        self.triggers = [str(x).lower() for x in config.get("lookup_triggers", [])]
        self.allowed_domains = set(config.get("allowed_domains", []))
        self.blocked_domains = set(config.get("blocked_domains", []))

    @classmethod
    def load(cls, path: Path) -> "LiveWebClient":
        if not path.exists():
            return cls({})
        return cls(json.loads(path.read_text(encoding="utf-8")))

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
            for result in self.duckduckgo_instant(query):
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
        summary = summarize_text(body, max_chars=450)
        if not summary:
            return None
        return LiveWebResult(title=title or final_url, summary=summary, url=final_url, source_type="url")

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
