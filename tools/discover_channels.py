"""매주 AI 관련 톱 유튜브 채널을 발굴/갱신한다.

쿼터 절약 전략: 이미 알고 있는 채널(.tmp/known_channels.json)은 재사용하고,
search.list(100유닛)는 정해진 키워드 목록에 대해서만 호출해 신규 채널을 추가로 찾는다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from youtube_client import get_channel_stats, search_channels  # noqa: E402

TMP_DIR = Path(__file__).resolve().parents[1] / ".tmp"
CACHE_FILE = TMP_DIR / "known_channels.json"

SEARCH_KEYWORDS = ["Claude AI 업무자동화", "ChatGPT 업무자동화", "제미나이 생태계"]
TOP_N = 15


def load_known() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_known(channels: dict) -> None:
    TMP_DIR.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(channels, ensure_ascii=False, indent=2), encoding="utf-8")


def discover_top_channels(keywords: list[str] = SEARCH_KEYWORDS, top_n: int = TOP_N) -> list[dict]:
    known = load_known()

    candidate_ids = set(known.keys())
    for kw in keywords:
        for ch in search_channels(kw, max_results=10):
            candidate_ids.add(ch["channelId"])

    stats = get_channel_stats(list(candidate_ids))
    known.update(stats)
    save_known(known)

    ranked = sorted(known.values(), key=lambda c: c["subscriberCount"], reverse=True)
    return ranked[:top_n]


if __name__ == "__main__":
    top_channels = discover_top_channels()
    print(json.dumps(top_channels, ensure_ascii=False, indent=2))
