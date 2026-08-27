"""weekly_videos.json을 Notion `notion-create-pages` 툴에 바로 넣을 수 있는
page 속성 배열로 변환한다 (.tmp/notion_pages.json).

실제 Notion API 호출(및 URL 기준 중복 체크)은 이 스크립트가 아니라, 워크플로우를
실행하는 Claude가 notion-create-pages / notion-query-data-sources MCP 툴로 수행한다.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEOS_FILE = ROOT / ".tmp" / "weekly_videos.json"
ANALYSIS_FILE = ROOT / ".tmp" / "analysis.json"
OUTPUT_FILE = ROOT / ".tmp" / "notion_pages.json"


def _topic_by_video_id(analysis: dict) -> dict[str, str]:
    """analysis.json의 topics[].video_ids -> {videoId: topicName} 역매핑."""
    mapping: dict[str, str] = {}
    for topic in analysis.get("topics", []):
        for vid in topic.get("video_ids", []):
            mapping[vid] = topic["name"]
    return mapping


def build_notion_pages() -> list[dict]:
    videos_data = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    analysis = json.loads(ANALYSIS_FILE.read_text(encoding="utf-8")) if ANALYSIS_FILE.exists() else {}
    topic_by_id = _topic_by_video_id(analysis)
    week_of = videos_data["generatedAt"][:10]

    pages = []
    for v in videos_data["videos"]:
        topic = topic_by_id.get(v["videoId"])
        pages.append(
            {
                "properties": {
                    "Title": v["title"],
                    "Channel": v["channelTitle"],
                    "URL": v["url"],
                    "Published": v["publishedAt"][:10],
                    "Views": v["viewCount"],
                    "Likes": v["likeCount"],
                    "Comments": v["commentCount"],
                    "Engagement Score": v["engagementScore"],
                    "Topic": [topic] if topic else [],
                    "Week Of": week_of,
                }
            }
        )

    OUTPUT_FILE.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    return pages


if __name__ == "__main__":
    result = build_notion_pages()
    print(f"Notion pages {len(result)}건 준비 완료 -> {OUTPUT_FILE}")
