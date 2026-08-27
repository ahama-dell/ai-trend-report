"""YouTube Data API v3 얇은 wrapper.

쿼터 비용: search.list=100, channels.list/playlistItems.list/videos.list=1 (요청당,
최대 50개 배치). search는 신규 채널 발굴에만 아껴서 쓰고, 나머지는 1유닛 호출로 처리한다.
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(RuntimeError):
    pass


def _get_api_key() -> str:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise YouTubeAPIError("YOUTUBE_API_KEY가 설정되어 있지 않습니다. .env 파일에 추가하세요.")
    return key


def _request(endpoint: str, params: dict) -> dict:
    params = {**params, "key": _get_api_key()}
    resp = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=30)
    if resp.status_code != 200:
        raise YouTubeAPIError(f"{endpoint} 호출 실패 ({resp.status_code}): {resp.text[:500]}")
    return resp.json()


def search_channels(query: str, max_results: int = 10) -> list[dict]:
    """search.list (100 units) — 신규 채널 발굴용."""
    data = _request(
        "search",
        {"part": "snippet", "q": query, "type": "channel", "order": "relevance", "maxResults": max_results},
    )
    return [
        {"channelId": item["snippet"]["channelId"], "title": item["snippet"]["channelTitle"]}
        for item in data.get("items", [])
    ]


def get_channel_stats(channel_ids: list[str]) -> dict[str, dict]:
    """channels.list (1 unit/호출, 최대 50개) — 구독자/조회수/업로드 재생목록 ID."""
    stats: dict[str, dict] = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i : i + 50]
        if not batch:
            continue
        data = _request("channels", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)})
        for item in data.get("items", []):
            stats[item["id"]] = {
                "channelId": item["id"],
                "title": item["snippet"]["title"],
                "subscriberCount": int(item["statistics"].get("subscriberCount", 0)),
                "viewCount": int(item["statistics"].get("viewCount", 0)),
                "uploadsPlaylistId": item["contentDetails"]["relatedPlaylists"]["uploads"],
            }
    return stats


def get_playlist_video_ids(playlist_id: str, published_after: str | None = None, max_pages: int = 3) -> list[str]:
    """playlistItems.list (1 unit/페이지, 최대 50개) — 채널 업로드 영상 ID 목록."""
    video_ids: list[str] = []
    page_token = None
    for _ in range(max_pages):
        params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        data = _request("playlistItems", params)
        stop = False
        for item in data.get("items", []):
            published_at = item["contentDetails"].get("videoPublishedAt", "")
            if published_after and published_at and published_at < published_after:
                stop = True
                continue
            video_ids.append(item["contentDetails"]["videoId"])
        page_token = data.get("nextPageToken")
        if not page_token or stop:
            break
    return video_ids


def get_video_stats(video_ids: list[str]) -> list[dict]:
    """videos.list (1 unit/호출, 최대 50개) — 조회수/좋아요/댓글수/제목/설명."""
    videos: list[dict] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        if not batch:
            continue
        data = _request("videos", {"part": "snippet,statistics", "id": ",".join(batch)})
        for item in data.get("items", []):
            s = item["statistics"]
            videos.append(
                {
                    "videoId": item["id"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"].get("description", ""),
                    "channelId": item["snippet"]["channelId"],
                    "channelTitle": item["snippet"]["channelTitle"],
                    "publishedAt": item["snippet"]["publishedAt"],
                    "viewCount": int(s.get("viewCount", 0)),
                    "likeCount": int(s.get("likeCount", 0)),
                    "commentCount": int(s.get("commentCount", 0)),
                    "url": f"https://www.youtube.com/watch?v={item['id']}",
                }
            )
    return videos
