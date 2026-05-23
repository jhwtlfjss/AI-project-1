from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from companion_ai.knowledge import KnowledgeBase


DEFAULT_USER_AGENT = "MyCompanionAI/0.1 (+local private learning)"
SENTENCE_RE = re.compile(r"(?<=[。！？.!?])\s+|\n+")


@dataclass
class LearnedDocument:
    title: str
    text: str
    url: str
    source_type: str
    language: str = "unknown"


class ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        data = html.unescape(data).strip()
        if not data:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self.text_parts.append(data)

    @property
    def title(self) -> str:
        return normalize_space(" ".join(self.title_parts))

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def due_to_run(config: dict, state: dict, force: bool = False) -> bool:
    if force:
        return True
    interval = int(config.get("learning_interval_minutes", 720)) * 60
    last_run = float(state.get("last_run_at", 0))
    return time.time() - last_run >= interval


def run_learning_cycle(config_path: Path, knowledge_path: Path, state_path: Path, force: bool = False) -> dict:
    config = load_config(config_path)
    state = load_state(state_path)
    if not config.get("enabled", True):
        return {"status": "disabled", "added_or_updated": 0}
    if not due_to_run(config, state, force=force):
        return {"status": "not_due", "added_or_updated": 0}

    kb = KnowledgeBase.load(knowledge_path)
    max_items = int(config.get("max_items_per_source", 4))
    max_summary_chars = int(config.get("max_summary_chars", 900))
    blocked = set(config.get("blocked_domains", []))
    allowed = set(config.get("allowed_domains", []))
    added = 0
    errors: list[str] = []

    for topic in config.get("topics", []):
        if not topic.get("enabled", True):
            continue
        topic_name = str(topic.get("name", "untitled"))
        keywords = [str(x) for x in topic.get("keywords", [])]
        for source in topic.get("sources", []):
            try:
                docs = fetch_source(source, max_items, blocked, allowed)
            except Exception as exc:
                errors.append(f"{topic_name}: {source.get('url', source.get('query', 'source'))}: {exc}")
                continue
            for doc in docs:
                summary = summarize_for_topic(doc.text, keywords, max_summary_chars)
                if not summary:
                    continue
                kb.add_or_update(
                    topic=topic_name,
                    title=doc.title or doc.url,
                    summary=summary,
                    source_url=doc.url,
                    source_type=doc.source_type,
                    language=doc.language,
                    tags=keywords[:12],
                )
                added += 1

    kb.clean_noise()
    kb.save(knowledge_path)
    state["last_run_at"] = time.time()
    state["last_result"] = {"added_or_updated": added, "errors": errors[-20:]}
    save_state(state_path, state)
    return {"status": "ok", "added_or_updated": added, "errors": errors}


def fetch_source(source: dict, max_items: int, blocked: set[str], allowed: set[str]) -> list[LearnedDocument]:
    source_type = str(source.get("type", "url")).lower()
    if source_type == "url":
        url = str(source["url"])
        assert_domain_allowed(url, blocked, allowed)
        title, text, final_url = fetch_readable_url(url)
        return [LearnedDocument(title=title, text=text, url=final_url, source_type="url", language=guess_language(text))]
    if source_type in {"rss", "atom"}:
        url = str(source["url"])
        assert_domain_allowed(url, blocked, allowed)
        return fetch_feed(url, max_items, blocked, allowed)
    if source_type == "wikipedia":
        lang = str(source.get("lang", "en"))
        query = str(source["query"])
        url = wikipedia_page_url(lang, query)
        assert_domain_allowed(url, blocked, allowed)
        title, text, final_url = fetch_wikipedia_summary(lang, query)
        return [LearnedDocument(title=title or query, text=text, url=final_url, source_type="wikipedia", language=lang)]
    raise ValueError(f"unsupported source type: {source_type}")


def fetch_readable_url(url: str) -> tuple[str, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "")
        raw = response.read(2_000_000)
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type)
    if match:
        charset = match.group(1)
    text = raw.decode(charset, errors="replace")
    parser = ReadableHTMLParser()
    parser.feed(text)
    title = parser.title or final_url
    body = parser.text
    return title, body, final_url


def fetch_wikipedia_summary(lang: str, query: str) -> tuple[str, str, str]:
    api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
    request = urllib.request.Request(api_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read(1_000_000).decode("utf-8", errors="replace"))
    title = normalize_space(str(data.get("title", query)))
    extract = normalize_space(str(data.get("extract", "")))
    page_url = (
        data.get("content_urls", {})
        .get("desktop", {})
        .get("page", wikipedia_page_url(lang, query))
    )
    return title, extract, page_url


def wikipedia_page_url(lang: str, query: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(query.replace(' ', '_'))}"


def fetch_feed(url: str, max_items: int, blocked: set[str], allowed: set[str]) -> list[LearnedDocument]:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(2_000_000)
    root = ET.fromstring(raw)
    docs: list[LearnedDocument] = []
    items = root.findall(".//item")
    if items:
        for item in items[:max_items]:
            title = text_of(item, "title")
            link = text_of(item, "link")
            desc = text_of(item, "description")
            if link:
                assert_domain_allowed(link, blocked, allowed)
            docs.append(
                LearnedDocument(
                    title=title,
                    text=html_to_text(desc),
                    url=link or url,
                    source_type="rss",
                    language=guess_language(desc),
                )
            )
        return docs

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns)[:max_items]:
        title = child_text(entry, "{http://www.w3.org/2005/Atom}title")
        summary = child_text(entry, "{http://www.w3.org/2005/Atom}summary")
        link = ""
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        if link_el is not None:
            link = link_el.attrib.get("href", "")
        if link:
            assert_domain_allowed(link, blocked, allowed)
        docs.append(
            LearnedDocument(
                title=title,
                text=html_to_text(summary),
                url=link or url,
                source_type="atom",
                language=guess_language(summary),
            )
        )
    return docs


def summarize_for_topic(text: str, keywords: list[str], max_chars: int) -> str:
    cleaned = normalize_space(text)
    if not cleaned:
        return ""
    sentences = [s.strip() for s in SENTENCE_RE.split(cleaned) if len(s.strip()) >= 24]
    if not sentences:
        return cleaned[:max_chars]
    lowered_keywords = [k.lower() for k in keywords if k]
    scored: list[tuple[int, int, str]] = []
    for idx, sentence in enumerate(sentences[:300]):
        lower = sentence.lower()
        score = sum(3 for kw in lowered_keywords if kw in lower)
        score += min(len(sentence), 240) // 80
        scored.append((score, idx, sentence))
    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    picked = sorted(scored[:6], key=lambda item: item[1])
    summary = " ".join(sentence for _, _, sentence in picked)
    return summary[:max_chars].strip()


def assert_domain_allowed(url: str, blocked: set[str], allowed: set[str]):
    domain = urllib.parse.urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    if allowed and domain not in allowed:
        raise ValueError(f"domain not in allowlist: {domain}")
    if domain in blocked:
        raise ValueError(f"domain blocked: {domain}")


def text_of(node: ET.Element, name: str) -> str:
    found = node.find(name)
    return normalize_space(found.text or "") if found is not None else ""


def child_text(node: ET.Element, name: str) -> str:
    found = node.find(name)
    return normalize_space(found.text or "") if found is not None else ""


def html_to_text(raw_html: str) -> str:
    parser = ReadableHTMLParser()
    parser.feed(raw_html)
    return parser.text or normalize_space(re.sub(r"<[^>]+>", " ", raw_html))


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def guess_language(text: str) -> str:
    if any("\u3040" <= ch <= "\u30ff" for ch in text):
        return "ja"
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"
