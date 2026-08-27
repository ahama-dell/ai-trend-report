"""수집된 데이터(.tmp/weekly_videos.json) + 분석 결과(.tmp/analysis.json)를 읽어
브랜드 PDF 리포트(.tmp/weekly_ai_trend_report.pdf)를 조립한다.

주제 클러스터링/추천 문구 같은 정성적 분석은 이 스크립트가 하지 않는다 — routine을
실행하는 Claude가 작성해서 analysis.json에 저장해두면, 이 스크립트는 그걸 읽어
레이아웃/차트로 조립만 한다 (분석 로직 있는 곳은 워크플로우 문서 참고).
"""
import json
from datetime import date
from pathlib import Path

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
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


def _register_fonts() -> None:
    """한글 지원 폰트를 reportlab에 등록한다.

    시스템 폰트에 의존하면 로컬(Windows)과 클라우드(Linux) 실행 환경에서
    렌더링이 달라지므로, 폰트 파일을 프로젝트에 번들링해 고정한다.
    """
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONT_REGULAR_PATH)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_BOLD_PATH)))
    pdfmetrics.registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD)


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} 없음 — 먼저 데이터 수집/분석 단계를 실행하세요.")
    return json.loads(path.read_text(encoding="utf-8"))


def _topic_chart(topics: list[dict]) -> Drawing:
    """주제별 조회수 막대그래프를 래스터 이미지가 아닌 PDF 벡터 드로잉으로 그린다.

    matplotlib PNG를 쓰던 예전 버전은, 단색 배경이 많은 차트 이미지의 압축 데이터에
    반복되는 바이트 패턴이 많아서 Gmail 첨부(base64 변환) 과정에서 데이터가
    미묘하게 손상되는 문제가 있었다. 벡터 드로잉은 그런 반복 바이트 블록 자체가
    생기지 않아 이 문제를 근본적으로 피한다.
    """
    names = list(reversed([t["name"] for t in topics]))
    views = list(reversed([t["total_views"] for t in topics]))

    width, height = 420, 60 + 28 * len(names)
    drawing = Drawing(width, height)

    chart = HorizontalBarChart()
    chart.x = 130
    chart.y = 20
    chart.width = width - 160
    chart.height = height - 40
    chart.data = [views]
    chart.categoryAxis.categoryNames = names
    chart.categoryAxis.labels.fontName = FONT_REGULAR
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontName = FONT_REGULAR
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = ACCENT_COLOR
    chart.bars.strokeColor = None
    chart.barLabelFormat = lambda v: f"{v:,.0f}"
    chart.barLabels.fontName = FONT_REGULAR
    chart.barLabels.fontSize = 7
    chart.barLabels.nudge = 8

    drawing.add(chart)
    return drawing


def build_report() -> Path:
    videos_data = _load(VIDEOS_FILE)
    analysis = _load(ANALYSIS_FILE)
    _register_fonts()

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
        story.append(_topic_chart(topics))

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
