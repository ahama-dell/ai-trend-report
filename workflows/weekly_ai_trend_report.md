# 워크플로우: 주간 AI 트렌드 리포트

## 목표
매주 일요일 20:00(KST)에 실행되어, AI 분야 유튜브 톱 채널의 이번 주 인기 콘텐츠를 분석하고,
데이터 기반 트렌드 요약과 콘텐츠 주제 추천을 담은 브랜드 PDF 리포트를 만들어 Gmail로 발송하고,
모든 원본 데이터를 Notion에 누적 저장한다.

## 사전 조건
- `.env`에 `YOUTUBE_API_KEY` 설정되어 있어야 함
- Notion 데이터베이스가 이미 생성되어 있고, 그 data source ID가 아래 "설정값"에 채워져 있어야 함
- Python 패키지 설치: `python -m pip install -r tools/requirements.txt`

## 설정값
- NOTION_DATA_SOURCE_ID: `c61335ed-0ac1-4098-aca1-ec3d2e5e3da4` (Notion DB "AI 유튜브 트렌드")
- 리포트 수신 이메일: `chnsk.ahn@gmail.com`

## 단계

### 1. 채널/영상 데이터 수집
```
python tools/fetch_weekly_videos.py
```
`.tmp/weekly_videos.json` 생성. 내부적으로 `discover_channels.py`가 톱 채널을
발굴/캐싱(`.tmp/known_channels.json`)하고, YouTube Data API로 최근 7일 영상과
조회수/좋아요/댓글수를 가져온다.

### 2. 주제 분석 & 추천 작성 (LLM 추론 단계 — 스크립트 아님)
`.tmp/weekly_videos.json`의 영상 제목/설명을 읽고 직접 판단해서:
- 영상들을 주제별로 클러스터링 (예: "에이전트", "이미지 생성", "로컬 LLM" 등, 3~7개 그룹)
- 주제별 `total_views` 합계와 소속 영상 ID 목록 계산
- 데이터에 기반한 "이번 주 요약" 문단 작성 (수치 근거 포함)
- "이번 주 콘텐츠 주제 추천" 3~5개 작성 (왜 지금 이 주제가 좋은지 데이터 근거 한 줄씩)

결과를 아래 형식 그대로 `.tmp/analysis.json`에 저장:
```json
{
  "summary": "이번 주는 ...",
  "topics": [
    {"name": "에이전트", "total_views": 4500000, "video_ids": ["abc123", "def456"]}
  ],
  "recommendations": [
    "예: 'n8n으로 만드는 AI 에이전트' — 관련 영상 5건이 이번 주 합산 300만 뷰, 참여도 상위권"
  ]
}
```

### 3. Notion 페이지 데이터 준비
```
python tools/notion_sync.py
```
`.tmp/notion_pages.json` 생성 (2단계 analysis.json의 topic 분류가 각 영상에 매핑됨).

### 4. Notion에 저장
`.tmp/notion_pages.json`의 각 항목을 `notion-create-pages` 툴로 전송한다.
- parent: `{"type": "data_source_id", "data_source_id": "<NOTION_DATA_SOURCE_ID>"}`
- 같은 영상(URL property 기준)이 이미 존재하면 skip — `notion-query-data-sources`로 먼저 확인

### 5. PDF 리포트 생성
```
python tools/generate_report.py
```
`.tmp/weekly_ai_trend_report.pdf` 생성 (표지, 이번 주 요약, 주제별 조회수 차트,
Top 10 영상 표, 콘텐츠 주제 추천 순).

### 6. Gmail 발송
`.tmp/weekly_ai_trend_report.pdf`를 base64로 읽어 `mcp__claude_ai_Gmail__send_message`로 발송.
- to: `chnsk.ahn@gmail.com`
- subject: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}`
- body: 이번 주 요약 3줄 정도
- attachments: 위 PDF (mimeType `application/pdf`)

## 실패 시
- YouTube API 쿼터 초과(403 quotaExceeded) → 태평양시 기준 자정 이후 재시도 안내, 이번 주는 건너뛴다
- 특정 채널에 이번 주 신규 영상이 없어도 정상 동작 (해당 채널만 스킵)
- Notion/Gmail 호출 실패 → 재시도하지 않고 에러 내용을 그대로 사용자에게 보고
