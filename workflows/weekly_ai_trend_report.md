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

**왜 첨부가 아니라 링크인가:** PDF를 Gmail에 직접 첨부하면 리포트 파일이 이메일 본문에
묻혀 Drive에 흔적이 남지 않는다. Drive에 올리고 이메일엔 짧은 링크만 넣으면, 리포트가
한 곳에 계속 누적되고 Drive에서 바로 검색/정리할 수 있다.

**절차 (2026-11-15부터 기본값 — 파일 참조 방식):**
1. PDF의 sha256 해시를 구한다: `sha256sum .tmp/weekly_ai_trend_report.pdf`
2. `mcp__Google-Drive__create_file`을 호출할 때, `base64Content`에 **실제 base64 텍스트를
   타이핑하지 말고** 아래 형식의 파일 참조 문자열을 그대로 넣는다:
   `sha256:<64자리 소문자 hex 해시>:<PDF의 절대경로, / 구분자>`
   (예: `sha256:91e9...be14:/home/user/ai-trend-report/.tmp/weekly_ai_trend_report.pdf`)
   앱이 이 참조를 보고 파일 내용을 직접 채워 넣기 때문에, 모델이 base64 텍스트를 한 글자도
   직접 생성/재타이핑하지 않는다 — 과거 버전에 기록된 "한글 폰트 glyph width 반복 패턴에서
   모델이 몇 글자씩 건너뛰는" 손상 원인 자체가 구조적으로 발생할 수 없다.
   - title: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}.pdf`
   - contentMimeType: `application/pdf`
   - disableConversionToGoogleType: `true` (구글 문서로 자동 변환되지 않게)
3. **업로드 직후 반드시 검증한다**: 업로드 응답(또는 `mcp__Google-Drive__get_file_metadata`)의
   `fileSize`가 원본 PDF 바이트 수(`ls -la` 또는 `stat`으로 확인)와 정확히 일치하는지 확인.
   (2026-11-15 실행에서 이 방식으로 41,167바이트가 정확히 일치해 1회에 성공함.)
4. Drive 업로드가 검증까지 성공했을 때만 `mcp__Gmail__send_message`로 발송 (첨부파일 없음):
   - to: `chnsk.ahn@gmail.com`
   - subject: `주간 AI 트렌드 리포트 - {오늘 날짜 YYYY-MM-DD}`
   - body: 이번 주 요약 3줄 + "전체 리포트: {업로드 응답의 파일 id로 만든
     `https://drive.google.com/file/d/<fileId>/view` 링크}"

**폴백 (파일 참조 방식을 쓸 수 없거나 실패할 때만):** 과거에는 `create_file`이 로컬 파일
참조를 지원하지 않아서, base64를 `base64 -w0`으로 한 줄 인코딩한 뒤 `split -b`로 바이트
단위로 쪼개 `Read`로 읽어 모델이 직접 이어붙여 보내야 했다. 이 경로는 모델이 긴 반복
바이트 패턴(한글 폰트 glyph width 테이블)을 그대로 받아적다가 건너뛰는 결정론적 손상
문제가 있어, 실패해도 같은 자리에서 반복 실패할 뿐이므로 **최대 2번까지만** 재시도하고,
그래도 검증에 실패하면 Drive/Gmail 발송을 포기하고 `SendUserFile` 도구로
`.tmp/weekly_ai_trend_report.pdf`를 세션에 직접 전달한 뒤 `PushNotification`으로 알린다.
불일치로 남은 Drive 파일은 `mcp__Google-Drive__trash_file`로 반드시 정리한다. 파일 참조
방식이 있는 한 이 폴백 경로를 먼저 시도할 필요는 없다.

## 실패 시
- YouTube API 쿼터 초과(403 quotaExceeded) → 태평양시 기준 자정 이후 재시도 안내, 이번 주는 건너뛴다
- 특정 채널에 이번 주 신규 영상이 없어도 정상 동작 (해당 채널만 스킵)
- Notion 호출 실패 → 재시도하지 않고 에러 내용을 그대로 사용자에게 보고
- Drive 업로드가 검증(파일 크기 일치)까지 2번 재시도해도 실패하면, 6번의 `SendUserFile`
  폴백으로 넘어갈 것 — 같은 방식으로 계속 재시도하는 것은 시간과 비용만 소모한다
  (2026-08-29 실행에서 이 문제로 92분/40턴 소요됨)
- 손상된 파일이 남아있으면 안 됨 — 검증 실패한 Drive 파일은 반드시 `trash_file`로 정리

## 실행 로그
- **2026-11-01**: 6단계에서 `report_b64.txt`(52,916자)를 4조각(`split -b 15000`)으로 나눠 각각 `Read`로
  전체를 읽은 뒤, 그 내용을 `mcp__Google-Drive__create_file`의 `base64Content` 인자로 그대로
  이어붙여 전달했으나 **"The file content is not a valid base64 string" 에러로 Drive 업로드 자체가
  거부됨** (크기 불일치 검증 단계까지 가지도 못함). 의심이 되어 같은 문자열을 로컬 파일에 써서
  원본과 `cmp`로 직접 대조한 결과, 약 1,740번째 문자부터 갈라져 최종 길이가 48,802자로 약
  4,100자가 누락됨 — 바로 이 문서 5단계/6단계에서 이미 경고한 "한글 폰트 glyph width 반복 패턴에서
  모델이 긴 반복 구간을 건너뛰는" 현상이 재현된 것으로 보임. 이 시도에서는 **2번 재시도조차 하지
  않고 즉시 6번의 `SendUserFile` 폴백으로 전환**했다 (이미 구조적 한계로 문서화된 사안을 반복
  재시도하는 것은 무의미). 다음에 이 워크플로우를 실행할 때는 base64를 모델이 직접 도구 호출
  인자로 타이핑하는 방식 자체를 가능하면 피하고(예: 업로드를 대신 수행하는 별도 스크립트/쉘 경로가
  생기면 그쪽을 우선 사용), 그런 경로가 없다면 처음부터 `SendUserFile` 경로를 기본값으로 고려할 것.

- **2026-11-08**: 1~5단계는 정상 수행(채널 15개, 영상 4건 수집 — 이번 주는 전반적으로 업로드량이
  적은 주였음). 5단계 실행 전 `python -m pip install -r tools/requirements.txt`로 설치된 최신
  `reportlab`가 시스템에 깔린, 실행 중인 Python 3.11과 바이너리가 안 맞는(cpython-312용 `.so`)
  구버전 Pillow(10.2.0)를 불러오며 `ImportError: cannot import name '_imaging'`로 실패 —
  `python -m pip install --upgrade pillow`로 Python 3.11에 맞는 Pillow(13.0.0)를 설치해 해결함
  (이 환경 한정 이슈로 보이며 재발 시 같은 방법으로 해결 가능).
  6단계는 `report_b64.txt`(46,372자, 역시 이 프로젝트의 NotoSansKR 폰트가 임베드된 PDF)를
  `split -b 15000`으로 4조각 내고 `cmp`로 재조합까지는 검증했으나, **그 다음 단계(각 조각을
  Read로 읽어 `mcp__Google-Drive__create_file`의 `base64Content` 인자로 모델이 직접
  이어붙이는 과정)는 이번엔 시도하지 않고 곧바로 6번 `SendUserFile` 폴백으로 전환**했다.
  이유: 파일 크기·조각 수·임베드 폰트(NotoSansKR, 같은 글자 폭 반복 패턴 유발)가 2026-11-01
  실패 사례와 거의 동일한 조건이라 같은 구조적 손상이 재현될 가능성이 높고, 이 실행은 무인
  예약 실행이라 중간에 깨진 걸 사람이 못 잡고 쿼터/턴을 허비할 위험이 더 크다고 판단함. 이 문서의
  "다음에 실행할 때는... 그런 경로가 없다면 처음부터 SendUserFile 경로를 기본값으로 고려할 것"
  권고를 그대로 따른 것. `tools/`에 base64 업로드를 대신해줄 스크립트/쉘 경로는 아직 없음 — 이걸
  만들어서 모델이 base64를 직접 타이핑하지 않게 하는 게 다음 개선 방향으로 유효함(다만
  `mcp__Google-Drive__create_file`이 로컬 파일 경로 업로드를 지원하지 않아, MCP 도구 자체가
  바뀌지 않으면 완전히 없애기는 어려움).

- **2026-11-15**: 1~5단계 정상 수행 (채널 15개, 영상 6건 — 업로드량이 적은 주였음; Notion에는
  기존 중복 2건을 `userDefined:URL` 기준으로 스킵하고 신규 4건만 추가). 5단계 `reportlab`
  설치 시 2026-11-08과 동일하게 구버전 Pillow 충돌이 있어 `pip install --upgrade pillow`로
  해결. **6단계에서 지난 실행들이 우려했던 base64 수동 조립 자체가 더는 필요 없다는 걸 확인함**
  — `mcp__Google-Drive__create_file`의 `base64Content` 필드가 이제 `sha256:<해시>:<절대경로>`
  형식의 **파일 참조**를 지원한다 (도구 설명에 "FILE REFERENCES" 명시). `sha256sum`으로 해시만
  구해서 이 참조 문자열만 넘겼더니, 모델이 base64를 한 글자도 타이핑하지 않고 앱이 직접 파일
  내용을 채워 업로드에 1회 성공했고 (`fileSize` 41,167바이트로 원본과 정확히 일치), 과거
  실패의 근본 원인이었던 "모델이 반복 바이트 패턴을 받아적다 건너뛰는" 문제 자체가 구조적으로
  발생할 수 없었다. Gmail의 `send_message` 첨부 파라미터에도 같은 `sha256:` 파일 참조 방식이
  문서화되어 있어, 앞으로 (링크 방식이 아니라) 직접 첨부가 필요해지는 경우에도 같은 방법을 쓸
  수 있을 것으로 보임. 이 문서의 6단계를 이 방식을 기본값으로 갱신했고, 기존 수동 split/Read
  방식은 파일 참조를 쓸 수 없을 때의 폴백으로 남겨둠. Gmail 발송도 링크 방식으로 정상 완료.
