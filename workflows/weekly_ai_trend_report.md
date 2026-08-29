# 워크플로우: 주간 AI 트렌드 리포트

## 목표
매주 일요일 20:00(KST)에 실행되어, AI 분야 유튜브 톱 채널의 이번 주 인기 콘텐츠를 분석하고,
데이터 기반 트렌드 요약과 콘텐츠 주제 추천을 담은 브랜드 PDF 리포트를 만들어 Google Drive에
올리고 그 링크를 Gmail로 발송하며, 모든 원본 데이터를 Notion에 누적 저장한다.

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
조회수/좋아요/댓글수를 가져온다. 3분(180초) 이하 영상은 숏폼으로 보고 제외하며,
채널 발굴 키워드는 `discover_channels.py`의 `SEARCH_KEYWORDS`에서 관리한다
(현재: "Claude AI 업무자동화", "ChatGPT 업무자동화", "제미나이 생태계" — 단일 단어
"Claude"/"Gemini"는 사람 이름·음악 채널과 겹쳐 노이즈가 컸던 경험이 있어 구체적인
문구로 구성했다).

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
- **알려진 함정 (매번 새로 겪지 않도록 미리 적어둠):**
  - `notion_pages.json`의 `"URL"` 키는 `notion-create-pages` 호출 시 그대로 쓰면 400 에러가 난다.
    이 DB에서 "URL" 속성의 실제 데이터소스 키는 **`"userDefined:URL"`** 이다 — 보내기 전에
    `notion_pages.json`을 읽어 키 이름을 `URL` → `userDefined:URL`로 바꿔서 보낼 것.
  - `"Topic"` 속성은 MULTI_SELECT이고 DB 생성 시 정해둔 옵션만 허용한다:
    `에이전트`, `이미지 생성`, `로컬 LLM`, `멀티모달`, `코딩 어시스턴트`, `기타`.
    분석 단계(2단계)에서 만든 자유 형식 주제명은 이 6개 중 가장 가까운 것으로 매핑해서 보낼 것
    (PDF 리포트 자체에는 원래의 세분화된 주제명을 그대로 써도 됨 — 매핑은 Notion 전송용).

### 5. PDF 리포트 생성
```
python tools/generate_report.py
```
`.tmp/weekly_ai_trend_report.pdf` 생성 (표지, 이번 주 요약, 주제별 조회수 차트,
Top 10 영상 표, 콘텐츠 주제 추천 순). 차트는 reportlab 벡터 드로잉으로 그린다 —
과거에 matplotlib PNG 이미지를 썼을 때, 압축된 이미지 데이터의 반복 바이트 패턴 때문에
6단계에서 base64로 옮기는 과정에 데이터가 손상되는 문제가 있었다. 이 스크립트를 수정해서
다시 래스터 이미지(PNG/JPEG)를 넣지 말 것.

### 6. Google Drive 업로드 & Gmail 발송 (링크 방식 — PDF를 이메일에 직접 첨부하지 않음)

**왜 첨부가 아니라 링크인가:** PDF를 Gmail에 직접 첨부하려면 파일 전체를 base64 텍스트로
바꿔서 그 텍스트를 통째로 하나의 도구 호출 인자로 만들어야 한다. 이 텍스트는 4만 자가
넘는, 사람이 읽을 수 없는 무작위에 가까운 문자열이라, 실행 중인 모델이 그걸 완벽하게
재현하지 못하고 몇 글자씩 틀리는 사고가 실제로 여러 번 있었다 (Gmail 첨부 자체가 30분
넘게 걸리거나 손상된 채로 보내질 뻔한 적도 있음). Drive에 올리고 이메일엔 짧은 링크만
넣으면, 그 이후 사람이 보는 이메일 본문에는 이 위험한 텍스트가 전혀 남지 않는다.

**절차:**
1. PDF를 base64로 인코딩하되 **줄바꿈 없이 한 줄로**: `base64 -w0 .tmp/weekly_ai_trend_report.pdf > .tmp/report_b64.txt`
   (`-w0`가 핵심 — `fold`나 줄바꿈이 들어간 버전을 절대 별도로 만들지 말 것. 실제로 두 번째
   테스트 실행에서 `fold -w 200`으로 줄바꿈된 파일을 조각조각 읽어 손으로 재조립하다가,
   그 결과물에 리터럴 줄바꿈 문자가 섞여 들어갔고, 로컬 MD5 검증은 통과했음에도 불구하고
   실제 `mcp__Gmail__send_message` 호출에서는 "Base64 decoding failed"가 두 번이나
   발생했다. 그러다 계정의 5시간 사용량 한도까지 소진해서 세션 자체가 강제 종료됨 (80턴,
   105분 소요, 결국 실패). **줄바꿈 없는 원본 파일을 만든 그 순간부터 다시 만들거나
   조작하지 말고 그대로 끝까지 사용해야 한다.**)
2. **한 번의 `Read` 호출로 그 파일 전체를 한 번에 읽는다** (`limit`을 파일 글자 수보다 크게
   설정). **여러 조각으로 나눠 읽거나, 다른 파일에 손으로 재조립하거나, 줄바꿈이 들어간
   중간 파일을 거치지 말 것** — 이미 검증 끝난 파일이 있는데 이걸 다시 타이핑/조합하는 건
   시간 낭비이자 손상 위험이다. 한 번에 읽은 값을 그대로 다음 단계에 전달하면 충분하다.
3. 읽은 내용을 그대로 `mcp__Google-Drive__create_file`에 전달해서 업로드:
   - title: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}.pdf`
   - base64Content: (2번에서 읽은 문자열 그대로, 다시 타이핑하거나 요약하지 말 것)
   - contentMimeType: `application/pdf`
   - disableConversionToGoogleType: `true` (구글 문서로 자동 변환되지 않게)
4. 업로드 응답에서 파일 id를 받아 보기 링크를 만든다: `https://drive.google.com/file/d/<fileId>/view`
5. `mcp__Gmail__send_message`로 발송 (첨부파일 없음):
   - to: `chnsk.ahn@gmail.com`
   - subject: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}`
   - body: 이번 주 요약 3줄 + "전체 리포트: {4번의 링크}"

## 실패 시
- YouTube API 쿼터 초과(403 quotaExceeded) → 태평양시 기준 자정 이후 재시도 안내, 이번 주는 건너뛴다
- 특정 채널에 이번 주 신규 영상이 없어도 정상 동작 (해당 채널만 스킵)
- Notion/Gmail/Drive 호출 실패 → 재시도하지 않고 에러 내용을 그대로 사용자에게 보고
- Drive 업로드 후 의심스러우면(특히 재시도를 여러 번 했다면) 업로드된 파일을
  `mcp__Google-Drive__download_file_content`나 `get_file_metadata`로 다시 확인해서
  손상 여부를 점검할 것 — 손상된 파일 링크를 그대로 보내지 말고, 확인이 안 되면 실패로 보고
