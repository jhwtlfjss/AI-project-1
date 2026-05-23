from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from companion_ai.autonomous_learning import assert_domain_allowed, normalize_space
from companion_ai.knowledge import KnowledgeBase


DEFAULT_USER_AGENT = "MyCompanionAI/0.1 (+local realtime tools)"
COORD_RE = re.compile(r"(-?\d{1,2}(?:\.\d+)?)\s*[,，]\s*(-?\d{1,3}(?:\.\d+)?)")


@dataclass
class RealtimeResult:
    title: str
    summary: str
    source_url: str
    source_type: str


class RealtimeDataClient:
    def __init__(self, config: dict):
        self.config = config
        self.enabled = bool(config.get("enabled", True))
        self.cache_tool_results = bool(config.get("cache_tool_results", True))
        self.max_results = int(config.get("max_results", 3))
        self.default_location = str(config.get("default_location", "")).strip()
        self.triggers = [str(x).lower() for x in config.get("triggers", [])]
        self.allowed_domains = set(config.get("allowed_domains", []))
        self.blocked_domains = set(config.get("blocked_domains", []))

    @classmethod
    def load(cls, path: Path) -> "RealtimeDataClient":
        if not path.exists():
            return cls({})
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def should_run(self, text: str) -> bool:
        if not self.enabled:
            return False
        lowered = text.lower()
        return bool(COORD_RE.search(text)) or any(trigger in lowered for trigger in self.triggers)

    def context_for_prompt(self, text: str) -> tuple[str, list[RealtimeResult]]:
        if not self.should_run(text):
            return "", []
        try:
            results = self.lookup(text)
            return render_realtime_results(results), results
        except Exception as exc:
            return f"实时数据查询失败: {exc}", []

    def lookup(self, text: str) -> list[RealtimeResult]:
        wants_weather = has_weather_intent(text)
        coord = extract_coordinates(text)
        results: list[RealtimeResult] = []

        if coord:
            lat, lon = coord
            address = self.reverse_geocode(lat, lon)
            if address:
                results.append(address)
            if wants_weather:
                weather = self.weather(lat, lon, address.title if address else "当前位置")
                if weather:
                    results.append(weather)
            return results[: self.max_results]

        place = extract_place_query(text) or self.default_location
        if not place:
            if wants_weather:
                return [
                    RealtimeResult(
                        title="需要地点",
                        summary="要查询天气或地址，需要提供城市、地点、地址或经纬度。",
                        source_url="",
                        source_type="realtime:hint",
                    )
                ]
            return []

        places = self.geocode(place)
        results.extend(places[: self.max_results])
        if wants_weather and places:
            lat_lon = parse_lat_lon_from_summary(places[0].summary)
            if lat_lon:
                weather = self.weather(lat_lon[0], lat_lon[1], places[0].title)
                if weather:
                    results.insert(0, weather)
        return results[: self.max_results]

    def geocode(self, place: str) -> list[RealtimeResult]:
        query = urllib.parse.urlencode(
            {
                "format": "jsonv2",
                "q": place,
                "limit": str(self.max_results),
                "addressdetails": "1",
            }
        )
        url = f"https://nominatim.openstreetmap.org/search?{query}"
        assert_domain_allowed(url, self.blocked_domains, self.allowed_domains)
        data = get_json(url)
        results: list[RealtimeResult] = []
        for item in data:
            title = normalize_space(str(item.get("display_name", "")))
            lat = str(item.get("lat", ""))
            lon = str(item.get("lon", ""))
            if title and lat and lon:
                results.append(
                    RealtimeResult(
                        title=title,
                        summary=f"地址/地点: {title}. 经纬度: {lat}, {lon}.",
                        source_url=osm_url(lat, lon),
                        source_type="realtime:geocode",
                    )
                )
        return results

    def reverse_geocode(self, lat: float, lon: float) -> RealtimeResult | None:
        query = urllib.parse.urlencode({"format": "jsonv2", "lat": str(lat), "lon": str(lon), "addressdetails": "1"})
        url = f"https://nominatim.openstreetmap.org/reverse?{query}"
        assert_domain_allowed(url, self.blocked_domains, self.allowed_domains)
        data = get_json(url)
        title = normalize_space(str(data.get("display_name", "")))
        if not title:
            return None
        return RealtimeResult(
            title=title,
            summary=f"坐标 {lat}, {lon} 对应的地址大约是: {title}.",
            source_url=osm_url(lat, lon),
            source_type="realtime:reverse_geocode",
        )

    def weather(self, lat: float, lon: float, place_name: str) -> RealtimeResult | None:
        query = urllib.parse.urlencode(
            {
                "latitude": str(lat),
                "longitude": str(lon),
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{query}"
        assert_domain_allowed(url, self.blocked_domains, self.allowed_domains)
        data = get_json(url)
        current = data.get("current", {})
        if not current:
            return None
        temp = current.get("temperature_2m")
        feels = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        precip = current.get("precipitation")
        wind = current.get("wind_speed_10m")
        code = weather_code_text(current.get("weather_code"))
        time = current.get("time", "")
        summary = (
            f"{place_name} 当前天气: {code}, 气温 {temp}°C, 体感 {feels}°C, "
            f"湿度 {humidity}%, 降水 {precip} mm, 风速 {wind} km/h. 更新时间: {time}."
        )
        return RealtimeResult(title=f"{place_name} 当前天气", summary=summary, source_url=url, source_type="realtime:weather")

    def cache_results(self, knowledge: KnowledgeBase, results: list[RealtimeResult]):
        if not self.cache_tool_results:
            return
        for result in results:
            knowledge.add_or_update(
                topic="realtime_data",
                title=result.title,
                summary=result.summary,
                source_url=result.source_url,
                source_type=result.source_type,
                language=guess_language(result.summary),
                tags=["realtime", "address", "weather", "实时数据"],
            )


def get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read(1_000_000).decode("utf-8", errors="replace"))


def render_realtime_results(results: list[RealtimeResult], max_chars: int = 900) -> str:
    lines: list[str] = []
    used = 0
    for result in results:
        line = f"- {result.title}: {result.summary}"
        if result.source_url:
            line += f" 来源: {result.source_url}"
        if used + len(line) > max_chars:
            remaining = max_chars - used
            if remaining <= 60:
                break
            line = line[:remaining].rstrip() + "..."
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


def extract_coordinates(text: str) -> tuple[float, float] | None:
    match = COORD_RE.search(text)
    if not match:
        return None
    lat = float(match.group(1))
    lon = float(match.group(2))
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


def extract_place_query(text: str) -> str:
    cleaned = COORD_RE.sub(" ", text)
    remove_words = [
        "查一下",
        "查",
        "搜索",
        "搜",
        "地址",
        "位置",
        "地点",
        "在哪里",
        "在哪",
        "附近",
        "坐标",
        "经纬度",
        "地图",
        "天气",
        "怎么样",
        "怎样",
        "如何",
        "怎么",
        "住所",
        "場所",
        "地図",
        "天気",
        "ですか",
        "location",
        "address",
        "where is",
        "map",
        "weather",
        "please",
    ]
    lowered = cleaned.lower()
    for word in remove_words:
        lowered = lowered.replace(word.lower(), " ")
    lowered = re.sub(r"[\?\?!？！。.,，:：;；]+", " ", lowered)
    return normalize_space(lowered)[:160]


def has_weather_intent(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ["天气", "天気", "weather"])


def parse_lat_lon_from_summary(summary: str) -> tuple[float, float] | None:
    match = re.search(r"经纬度:\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)", summary)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def osm_url(lat, lon) -> str:
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"


def weather_code_text(code) -> str:
    mapping = {
        0: "晴朗",
        1: "大致晴朗",
        2: "局部多云",
        3: "阴天",
        45: "雾",
        48: "霜雾",
        51: "小毛毛雨",
        53: "中等毛毛雨",
        55: "较强毛毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        80: "小阵雨",
        81: "中等阵雨",
        82: "强阵雨",
        95: "雷暴",
    }
    try:
        return mapping.get(int(code), f"天气代码 {code}")
    except (TypeError, ValueError):
        return "未知"


def guess_language(text: str) -> str:
    if any("\u3040" <= ch <= "\u30ff" for ch in text):
        return "ja"
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"
