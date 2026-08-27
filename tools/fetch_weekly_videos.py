"""지난 7일간 톱 채널들이 올린 영상과 통계를 수집해 .tmp/weekly_videos.json으로 저장한다."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from discover_channels import discover_top_channels  # noqa: E402
from youtube_client import get_playlist_video_ids, get_video_stats  # noqa: E402

TMP_DIR = Path(__file__).resolve().parents[1] / ".tmp"
OUTPUT_FILE = TMP_DIR / "weekly_videos.json"

# YouTube는 최대 3분짜리 영상도 Shorts로 취급할 수 있어, 이 기준(초) 이하는 숏폼으로 보고 제외한다.
SHORTS_MAX_SECONDS = 180


def engagement_score(video: dict) -> float:
    """조회수 대비 좋아요+댓글 비율 (댓글에 가중치 2배) x 1000."""
    views = max(video["viewCount"], 1)
    return (video["likeCount"] + video["commentCount"] * 2) / views * 1000


def fetch_weekly_videos(days: int = 7) -> dict:
    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    channels = discover_top_channels()
    all_video_ids: list[str] = []
    for ch in channels:
        video_ids = get_playlist_video_ids(ch["uploadsPlaylistId"], published_after=published_after)
        all_video_ids.extend(video_ids)

    videos = get_video_stats(all_video_ids) if all_video_ids else []
    videos = [v for v in videos if v["durationSeconds"] > SHORTS_MAX_SECONDS]
    for v in videos:
        v["engagementScore"] = round(engagement_score(v), 3)
    videos.sort(key=lambda v: v["viewCount"], reverse=True)

    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "windowDays": days,
        "channelCount": len(channels),
        "videoCount": len(videos),
        "channels": channels,
        "videos": videos,
    }

    TMP_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    data = fetch_weekly_videos()
    print(f"채널 {data['channelCount']}개, 영상 {data['videoCount']}개 수집 완료 -> {OUTPUT_FILE}")
