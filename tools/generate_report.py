"""수집된 데이터(.tmp/weekly_videos.json) + 분석 결과(.tmp/analysis.json)를 읽어
브랜드 PDF 리포트(.tmp/weekly_ai_trend_report.pdf)를 조립한다.

주제 클러스터링/추천 문구 같은 정성적 분석은 이 스크립트가 하지 않는다 — routine을
실행하는 Claude가 작성해서 analysis.json에 저장해두면, 이 스크립트는 그걸 읽어
레이아웃/차트로 조립만 한다 (분석 로직 있는 곳은 워크플로우 문서 참고).
"""
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / ".tmp"
VIDEOS_FILE = TMP_DIR / "weekly_videos.json"
ANALYSIS_FILE = TMP_DIR / "analysis.json"
OUTPUT_FILE = TMP_DIR / "weekly_ai_trend_report.pdf"

FONTS_DIR = Path(__file__).parent / "fonts"
FONT_REGULAR_PATH = FONTS_DIR / "NotoSansKR-Regular.ttf"
FONT_BOLD_PATH = FONTS_DIR / "NotoSansKR-Bold.ttf"
FONT_REGULAR = "NotoSansKR"
FONT_BOLD = "NotoSansKR-Bold"

ACCENT_COLOR = colors.HexColor("#5B4FE9")
DARK_TEXT = colors.HexColor("#1A1A2E")
ROW_ALT_COLOR = colors.HexColor("#F5F5FA")


def _register_fonts() -> fm.FontProperties:
    """한글 지원 폰트를 reportlab/matplotlib 양쪽에 등록한다.

    시스템 폰트에 의존하면 로컬(Windows)과 클라우드(Linux) 실행 환경에서
    렌더링이 달라지므로, 폰트 파일을 프로젝트에 번들링해 고정한다.
    """
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONT_REGULAR_PATH)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_BOLD_PATH)))
    pdfmetrics.registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD)
    fm.fontManager.addfont(str(FONT_REGULAR_PATH))
    return fm.FontProperties(fname=str(FONT_REGULAR_PATH))


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} 없음 — 먼저 데이터 수집/분석 단계를 실행하세요.")
    return json.loads(path.read_text(encoding="utf-8"))


def _topic_chart(topics: list[dict], font_prop: fm.FontProperties) -> Path:
    names = [t["name"] for t in topics]
    views = [t["total_views"] for t in topics]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.barh(names[::-1], views[::-1], color="#5B4FE9")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names[::-1], fontproperties=font_prop)
    ax.set_xlabel("Total Views", fontproperties=font_prop)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    chart_path = TMP_DIR / "topic_chart.png"
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    return chart_path


def build_report() -> Path:
    videos_data = _load(VIDEOS_FILE)
    analysis = _load(ANALYSIS_FILE)
    font_prop = _register_fonts()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleBrand", parent=styles["Title"], textColor=ACCENT_COLOR, fontName=FONT_BOLD
    )
    h2_style = ParagraphStyle(
        "H2Brand", parent=styles["Heading2"], textColor=DARK_TEXT, fontName=FONT_BOLD, spaceBefore=14
    )
    body_style = ParagraphStyle(
        "BodyBrand", parent=styles["BodyText"], textColor=DARK_TEXT, fontName=FONT_REGULAR, leading=15
    )

    doc = SimpleDocTemplate(str(OUTPUT_FILE), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = []

    today = date.today().isoformat()
    story.append(Paragraph("주간 AI 트렌드 리포트", title_style))
    story.append(
        Paragraph(
            f"{today} · 최근 {videos_data['windowDays']}일 · "
            f"채널 {videos_data['channelCount']}개 · 영상 {videos_data['videoCount']}개 분석",
            body_style,
        )
    )
    story.append(Spacer(1, 1 * cm))

    story.append(Paragraph("이번 주 요약", h2_style))
    story.append(Paragraph(analysis.get("summary", ""), body_style))

    topics = analysis.get("topics", [])
    if topics:
        story.append(Paragraph("주제별 인기도", h2_style))
        chart_path = _topic_chart(topics, font_prop)
        story.append(Image(str(chart_path), width=15 * cm, height=8 * cm))

    top_videos = videos_data["videos"][:10]
    if top_videos:
        story.append(Paragraph("이번 주 Top 10 영상", h2_style))
        table_data = [["#", "제목", "채널", "조회수", "참여도"]]
        for i, v in enumerate(top_videos, 1):
            title = v["title"] if len(v["title"]) <= 40 else v["title"][:37] + "..."
            table_data.append(
                [str(i), title, v["channelTitle"], f"{v['viewCount']:,}", f"{v['engagementScore']:.1f}"]
            )
        table = Table(table_data, colWidths=[1 * cm, 8 * cm, 4 * cm, 2.5 * cm, 2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), ACCENT_COLOR),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                    ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT_COLOR]),
                ]
            )
        )
        story.append(table)

    recommendations = analysis.get("recommendations", [])
    if recommendations:
        story.append(PageBreak())
        story.append(Paragraph("이번 주 콘텐츠 주제 추천", h2_style))
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", body_style))
            story.append(Spacer(1, 0.2 * cm))

    doc.build(story)
    return OUTPUT_FILE


if __name__ == "__main__":
    path = build_report()
    print(f"리포트 생성 완료 -> {path}")
