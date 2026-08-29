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
2. 이 파일을 **한 번의 `Read` 호출로 전체를 읽으려고 시도한다** (`limit`을 파일 글자 수보다
   크게 설정). PDF가 작으면 이걸로 충분하다. **하지만 실제로는 base64가 대략 26,000자를
   넘으면 (파일 크기 기준 대략 19KB 이상) Read 도구 자체의 토큰 한도(25,000 토큰)에 걸려서
   "File content exceeds maximum allowed tokens" 에러가 난다 — 이건 실패가 아니라 예상된
   상황이니 당황하지 말고 3번으로 넘어갈 것.**
3. Read가 토큰 한도에 걸리면: `split -b 15000 -d --additional-suffix=.txt report_b64.txt part_`
   처럼 **바이트 단위로(문자/줄 단위 아님)** 파일을 나눈다. **`fold`는 절대 쓰지 말 것** —
   `fold`는 줄바꿈을 삽입해서 데이터를 바꾼다. `split -b`는 원본 바이트를 그대로 유지한다.
   나눈 뒤 `cat part_* | cmp - report_b64.txt`로 재조합이 원본과 100% 일치하는지 반드시
   확인한다. 그 다음 각 조각을 `Read`로 전체를 읽어 다음 단계의 upload 호출에 그대로 이어
   붙인다.
4. 읽은 내용을 그대로 `mcp__Google-Drive__create_file`에 전달해서 업로드:
   - title: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}.pdf`
   - base64Content: (읽은 조각들을 순서대로 이어붙인 문자열 그대로, 다시 타이핑하거나
     요약하지 말 것)
   - contentMimeType: `application/pdf`
   - disableConversionToGoogleType: `true` (구글 문서로 자동 변환되지 않게)
5. **업로드 직후 반드시 검증한다**: `mcp__Google-Drive__get_file_metadata`로 `fileSize`가
   원본 PDF 바이트 수와 정확히 일치하는지 확인. 불일치하면 `mcp__Google-Drive__trash_file`로
   깨진 파일을 지우고 **최대 2번까지만** 재시도한다.
   - **알려진 근본 원인 (2026-08-29 발견):** 이 실패는 무작위 오타가 아니라 **매번 정확히
     같은 지점에서 나는 결정론적 손상**이다. 원인은 PDF에 번들된 한글 폰트(Noto Sans KR)의
     glyph width 테이블 — 많은 한글 글자가 같은 폭(예: 920)을 공유해서 base64에 `920 920
     920 920...` 같은 길게 반복되는 패턴이 생기는데, 모델이 이런 긴 반복 구간을 그대로
     받아적을 때 반복을 자기도 모르게 건너뛰는 현상이 있다. **이건 Gmail이든 Drive든 도구를
     바꾼다고 해결되지 않는다** — base64 전체를 모델이 직접 생성하는 도구 호출 인자 안에
     넣어야 하는 구조 자체의 한계다. 그러니 2번 재시도해도 안 되면 재시도를 멈출 것 (같은
     자리에서 계속 실패할 가능성이 높다).
6. 2번 재시도 후에도 검증에 실패하면 Drive/Gmail 발송을 포기하고 **`SendUserFile` 도구로
   `.tmp/weekly_ai_trend_report.pdf`를 세션에 직접 전달**하고 `PushNotification`으로
   사용자에게 알린다. `SendUserFile`은 로컬 파일 경로를 그대로 전달하는 방식이라 base64를
   모델이 다시 타이핑할 필요가 없어 이 문제 자체가 발생하지 않는다 — 완전한 최종 수단은
   아니지만(수신자가 이메일이 아니라 세션에서 파일을 받음), 리포트를 아예 잃어버리는 것보다
   낫다.
7. Drive 업로드가 검증까지 성공했을 때만 `mcp__Gmail__send_message`로 발송 (첨부파일 없음):
   - to: `chnsk.ahn@gmail.com`
   - subject: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}`
   - body: 이번 주 요약 3줄 + "전체 리포트: {업로드 응답의 파일 id로 만든
     `https://drive.google.com/file/d/<fileId>/view` 링크}"

## 실패 시
- YouTube API 쿼터 초과(403 quotaExceeded) → 태평양시 기준 자정 이후 재시도 안내, 이번 주는 건너뛴다
- 특정 채널에 이번 주 신규 영상이 없어도 정상 동작 (해당 채널만 스킵)
- Notion 호출 실패 → 재시도하지 않고 에러 내용을 그대로 사용자에게 보고
- Drive 업로드가 검증(파일 크기 일치)까지 2번 재시도해도 실패하면, 6번의 `SendUserFile`
  폴백으로 넘어갈 것 — 같은 방식으로 계속 재시도하는 것은 시간과 비용만 소모한다
  (2026-08-29 실행에서 이 문제로 92분/40턴 소요됨)
- 손상된 파일이 남아있으면 안 됨 — 검증 실패한 Drive 파일은 반드시 `trash_file`로 정리
