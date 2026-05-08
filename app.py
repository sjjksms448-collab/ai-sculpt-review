"""
AI Sculpt Review - Premium Apple-Inspired UI
Supports Real AI Mode and Demo Mode.
"""

import streamlit as st
import os
import base64
import re
from openai import OpenAI

# ============================================================
# 配置
# ============================================================
MODEL_NAME = "gpt-4o"

# ============================================================
# Demo 报告（结构化数据）
# ============================================================
DEMO_REPORT = {
    "overall_score": 72,
    "score_breakdown": {
        "Silhouette":          {"score": 18, "max": 30},
        "Facial Landmarks":    {"score": 16, "max": 25},
        "Volume Structure":    {"score": 14, "max": 20},
        "Proportion Accuracy": {"score": 11, "max": 15},
        "Detail Match":        {"score":  7, "max": 10},
    },
    "critical": [
        "头部整体轮廓与参考图仍有明显差距，脸部宽度偏大。",
        "下巴长度不足，导致脸型不够接近参考图。",
    ],
    "major": [
        "眼窝深度不足，眉弓结构不够明确。",
        "鼻梁和鼻尖体积不足，侧面轮廓偏平。",
        "颧骨位置和体积需要进一步调整。",
    ],
    "minor": [
        "嘴角结构还不够自然。",
        "皮肤细节暂时不用加强，应先修大形。",
        "耳朵位置和体积需要后续检查。",
    ],
    "zbrush_steps": [
        "使用 Move 笔刷从正面收窄脸颊两侧，让脸型更接近参考图。",
        "从侧面拉长下巴，并加强下颌角。",
        "使用 Clay Buildup 增加鼻梁到鼻尖的体积。",
        "使用 Dam Standard 加深眼窝和眉弓下方结构。",
        "调整颧骨位置，让面部大形更有骨性结构。",
        "暂时不要加皮肤毛孔和细节，先把大形和五官比例修准。",
    ],
    "priority": "先修正头部大形：收窄脸颊、拉长下巴、加强鼻梁侧面轮廓。",
    "client_summary": "当前模型已经有基础人头结构，但与参考图相比，大形、脸型和五官体积还需要进一步调整。建议先集中修改整体轮廓和面部结构，再进入细节阶段。",
}

ANALYSIS_PROMPT = """你是专业角色建模主管、ZBrush 雕刻导师、手办/游戏角色审稿人。
请严格对比参考图和当前模型截图。
不要只说泛泛建议，要指出具体哪里不像。

重点判断：
- 头部大形是否接近
- 脸型是否接近
- 五官位置是否准确
- 眼窝、鼻梁、嘴部、下巴、颧骨是否合理
- 侧面轮廓是否合理
- 结构是否像真实头颅
- 是否适合继续细化
- 当前最应该先修哪里

评分规则（总分 100）：
- 大形轮廓 Silhouette: 0-30
- 五官位置 Facial Landmarks: 0-25
- 结构体积 Volume Structure: 0-20
- 比例准确 Proportion Accuracy: 0-15
- 细节还原 Detail Match: 0-10

输出格式必须严格遵守以下 Markdown 结构，不要省略任何部分：

# AI Sculpt Review Report

## Overall Score
xx / 100

## Score Breakdown
- Silhouette: xx / 30
- Facial Landmarks: xx / 25
- Volume Structure: xx / 20
- Proportion Accuracy: xx / 15
- Detail Match: xx / 10

## Main Problems
### Critical
1. [具体问题描述]
2. [具体问题描述]

### Major
1. [具体问题描述]
2. [具体问题描述]

### Minor
1. [具体问题描述]
2. [具体问题描述]

## ZBrush Fix Instructions
1. [具体修复步骤]
2. [具体修复步骤]
3. [具体修复步骤]
4. [具体修复步骤]
5. [具体修复步骤]

## Highest Priority Next Step
[一句话说明下一步最应该先修什么]

## Client-Friendly Summary
[用适合给客户看的方式总结当前模型还原情况，保持专业且易于理解]"""

# ============================================================
# 报告解析（从 Markdown 文本解析为结构化字典）
# ============================================================
def parse_report(report_text: str) -> dict:
    """将 Markdown 报告文本解析为结构化字典，解析失败时优雅降级。"""

    def extract_int(pattern: str, default: int = 0) -> int:
        m = re.search(pattern, report_text)
        return int(m.group(1)) if m else default

    def extract_section(header: str) -> list:
        pattern = re.compile(
            re.escape(header) + r"\s*\n((?:\d+\..+\n?)+)", re.MULTILINE
        )
        m = pattern.search(report_text)
        if not m:
            return []
        items = re.findall(r"\d+\.\s*(.+?)(?=\n\d+\.|\n##|\Z)", m.group(1), re.DOTALL)
        return [i.strip().replace("**", "") for i in items if i.strip()]

    def extract_lines(header: str) -> list:
        pattern = re.compile(
            re.escape(header) + r"\s*\n((?:- .+\n?)+)", re.MULTILINE
        )
        m = pattern.search(report_text)
        if not m:
            return []
        return [l.strip().lstrip("- ").strip() for l in m.group(1).split("\n") if l.strip()]

    def extract_after(header: str) -> str:
        m = re.search(re.escape(header) + r"\s*\n(.+?)(?=\n##|\Z)", report_text, re.DOTALL)
        return m.group(1).strip() if m else ""

    report = {
        "overall_score": extract_int(r"## Overall Score\s*\n(\d+)"),
        "score_breakdown": {},
        "critical": [],
        "major": [],
        "minor": [],
        "zbrush_steps": [],
        "priority": "",
        "client_summary": "",
    }

    # Score Breakdown
    for label, pattern in [
        ("Silhouette",          r"Silhouette\s*:?\s*(\d+)\s*/\s*30"),
        ("Facial Landmarks",    r"Facial Landmarks\s*:?\s*(\d+)\s*/\s*25"),
        ("Volume Structure",    r"Volume Structure\s*:?\s*(\d+)\s*/\s*20"),
        ("Proportion Accuracy", r"Proportion Accuracy\s*:?\s*(\d+)\s*/\s*15"),
        ("Detail Match",       r"Detail Match\s*:?\s*(\d+)\s*/\s*10"),
    ]:
        score = extract_int(pattern)
        max_map = {"Silhouette": 30, "Facial Landmarks": 25,
                   "Volume Structure": 20, "Proportion Accuracy": 15, "Detail Match": 10}
        report["score_breakdown"][label] = {"score": score, "max": max_map.get(label, 10)}

    # Problem sections
    report["critical"] = extract_section("### Critical")
    report["major"]    = extract_section("### Major")
    report["minor"]    = extract_section("### Minor")

    # ZBrush steps
    step_lines = re.findall(
        r"(?<!#)\d+\.\s+(.+?)(?=\n\d+\.|\n##|\Z)",
        report_text,
        re.DOTALL,
    )
    if step_lines:
        report["zbrush_steps"] = [s.strip() for s in step_lines if s.strip()]
    if not report["zbrush_steps"]:
        steps_text = extract_after("## ZBrush Fix Instructions")
        if steps_text:
            steps = re.findall(r"\d+\.\s*(.+)", steps_text)
            report["zbrush_steps"] = [s.strip() for s in steps if s.strip()]

    report["priority"]       = extract_after("## Highest Priority Next Step")
    report["client_summary"] = extract_after("## Client-Friendly Summary")

    # Fallback: if overall_score is 0, treat as parse failure
    if report["overall_score"] == 0 and "Overall Score" in report_text:
        m = re.search(r"(\d+)\s*/\s*100", report_text)
        if m:
            report["overall_score"] = int(m.group(1))

    return report


# ============================================================
# 报告渲染（Apple 风格）
# ============================================================
def render_report(report: dict, is_demo: bool = False):
    """以 Apple 风格渲染结构化报告。"""

    # ── Overall Score Hero ──────────────────────────────────
    score = report.get("overall_score", 0)
    st.markdown(f"""
    <div style="text-align:center; margin: 40px 0 16px;">
        <div style="display:inline-flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:13px; font-weight:500; color:#86868b; letter-spacing:0.02em;">Overall Score</span>
            {f'<span style="font-size:11px; background:#F5F5F7; color:#86868b; padding:2px 10px; border-radius:999px; border:1px solid #D2D2D7;">Demo</span>' if is_demo else ''}
        </div>
        <div style="font-size:80px; font-weight:800; color:#1D1D1F; line-height:1; letter-spacing:-0.03em;">
            {score}<span style="font-size:36px; font-weight:400; color:#86868b; margin-left:4px;">/ 100</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Score Breakdown ─────────────────────────────────────
    breakdown = report.get("score_breakdown", {})
    if breakdown:
        # CSS grid 2x3 layout
        cards_html = ""
        for label, data in breakdown.items():
            pct = data["score"] / data["max"] if data["max"] else 0
            bar_w = int(pct * 100)
            cards_html += f"""
        <div class="score-card">
            <div class="score-label">{label}</div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{bar_w}%"></div>
            </div>
            <div class="score-value">{data['score']} <span>/ {data['max']}</span></div>
        </div>"""

        st.markdown(f"""
        <div class="section-title">Score Breakdown</div>
        <div class="score-grid">{cards_html}
        </div>""", unsafe_allow_html=True)

    # ── Main Problems ───────────────────────────────────────
    problems_layout = []
    for header, key, color in [
        ("Critical", "critical", "#E8392A"),
        ("Major",    "major",    "#F5A623"),
        ("Minor",    "minor",    "#6E6E73"),
    ]:
        items = report.get(key, [])
        if not items:
            continue
        items_html = "".join(
            f'<div class="problem-item"><span class="problem-dot" style="background:{color}"></span><span>{it}</span></div>'
            for it in items
        )
        problems_layout.append(f"""
        <div class="problem-col">
            <div class="problem-header">{header}</div>
            <div class="problem-list">{items_html}</div>
        </div>""")

    if problems_layout:
        st.markdown(f"""
        <div class="section-title">Main Problems</div>
        <div class="problems-grid">{"".join(problems_layout)}</div>""", unsafe_allow_html=True)

    # ── ZBrush Fix Instructions ─────────────────────────────
    steps = report.get("zbrush_steps", [])
    if steps:
        steps_html = "".join(
            f'<div class="step-item"><div class="step-num">{i}</div><div class="step-text">{s}</div></div>'
            for i, s in enumerate(steps, 1)
        )
        st.markdown(f"""
        <div class="section-title">ZBrush Fix Instructions</div>
        <div class="steps-list">{steps_html}</div>""", unsafe_allow_html=True)

    # ── Highest Priority ────────────────────────────────────
    priority = report.get("priority", "").strip()
    if priority:
        st.markdown(f"""
        <div class="priority-card">
            <div class="priority-label">Highest Priority Next Step</div>
            <div class="priority-text">{priority}</div>
        </div>""", unsafe_allow_html=True)

    # ── Client-Friendly Summary ──────────────────────────────
    summary = report.get("client_summary", "").strip()
    if summary:
        st.markdown(f"""
        <div class="section-title">Client-Friendly Summary</div>
        <div class="summary-card">{summary}</div>""", unsafe_allow_html=True)


# ============================================================
# 页面设置
# ============================================================
st.set_page_config(
    page_title="AI Sculpt Review",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# Apple 风格 CSS
# ============================================================
st.markdown("""
<style>
/* ── Reset & Base ───────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #F5F5F7;
    color: #1D1D1F;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Streamlit overrides ─────────────────────────────────── */
header[data-testid="stHeader"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stToolbarActions"] { display: none !important; }

/* Main content */
div[data-testid="stMainBlockContainer"] {
    max-width: 1160px !important;
    padding: 0 40px !important;
    margin: 0 auto !important;
}

/* Markdown */
p, li { color: #6E6E73; font-size: 15px; line-height: 1.65; }

/* ── Hero ───────────────────────────────────────────────── */
.hero {
    text-align: center;
    padding: 80px 0 16px;
}
.hero h1 {
    font-size: clamp(44px, 6vw, 72px);
    font-weight: 800;
    color: #1D1D1F;
    letter-spacing: -0.03em;
    line-height: 1.05;
    margin-bottom: 20px;
}
.hero .subtitle {
    font-size: clamp(15px, 2vw, 18px);
    color: #6E6E73;
    max-width: 680px;
    margin: 0 auto 14px;
    line-height: 1.6;
    font-weight: 400;
}
.hero .tagline {
    font-size: 13px;
    color: #86868b;
    letter-spacing: 0.01em;
}

/* ── Mode Pill ───────────────────────────────────────────── */
.mode-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(255,255,255,0.72);
    border: 1px solid #D2D2D7;
    border-radius: 999px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #6E6E73;
    margin: 0 auto 52px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}
.mode-pill .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
.mode-pill .dot.demo  { background: #F5A623; }
.mode-pill .dot.real  { background: #30D158; }

/* ── Section title ───────────────────────────────────────── */
.section-title {
    font-size: 11px;
    font-weight: 600;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 44px 0 18px;
}

/* ── Upload Cards ───────────────────────────────────────── */
.upload-section-label {
    font-size: 11px;
    font-weight: 600;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 16px;
}
.upload-label-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}
.upload-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #1D1D1F;
}
.tag-required {
    font-size: 10px;
    font-weight: 600;
    color: #E8392A;
    background: #FFF0EE;
    padding: 2px 7px;
    border-radius: 999px;
    letter-spacing: 0.03em;
}
.tag-optional {
    font-size: 10px;
    font-weight: 600;
    color: #86868b;
    background: #F5F5F7;
    padding: 2px 7px;
    border-radius: 999px;
    border: 1px solid #D2D2D7;
    letter-spacing: 0.03em;
}
.upload-desc {
    font-size: 13px;
    color: #86868b;
    margin-top: 6px;
    line-height: 1.5;
}

/* Override Streamlit file uploader */
div[data-testid="stFileUploadDropzone"] {
    background: #F5F5F7 !important;
    border: 1.5px dashed #D2D2D7 !important;
    border-radius: 14px !important;
    padding: 18px 14px !important;
    margin-top: 10px !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stFileUploadDropzone"]:hover {
    border-color: #0071E3 !important;
}

/* ── Analyze Button ─────────────────────────────────────── */
div[data-testid="stMainBlockContainer"] > div:last-child {
    padding-bottom: 60px;
}

/* Streamlit primary button override */
button[kind="primary"] {
    background: #0071E3 !important;
    border: none !important;
    border-radius: 999px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 14px 40px !important;
    color: white !important;
    letter-spacing: 0.01em;
    width: 100% !important;
    max-width: 320px !important;
    transition: background 0.2s !important;
}
button[kind="primary"]:hover {
    background: #0077ED !important;
}
button[kind="primary"]:active {
    background: #005BB5 !important;
}

.analyze-btn-wrap {
    text-align: center;
    margin: 32px 0 0;
}
.analyze-hint {
    text-align: center;
    font-size: 12px;
    color: #ACACB0;
    margin-top: 10px;
}

/* ── Divider ─────────────────────────────────────────────── */
hr {
    border: none;
    border-top: 1px solid #D2D2D7;
    margin: 40px 0;
}

/* ── Overall Score ──────────────────────────────────────── */
.section-title:first-of-type { margin-top: 0; }

/* ── Score Breakdown Grid ───────────────────────────────── */
.score-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 8px;
}
.score-card {
    background: #FFFFFF;
    border-radius: 20px;
    padding: 20px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    border: 1px solid #E5E5EA;
}
.score-label {
    font-size: 12px;
    font-weight: 500;
    color: #86868b;
    margin-bottom: 10px;
    letter-spacing: 0.01em;
}
.score-bar-bg {
    height: 5px;
    background: #F5F5F7;
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 10px;
}
.score-bar-fill {
    height: 100%;
    background: #0071E3;
    border-radius: 999px;
    transition: width 0.6s cubic-bezier(0.16,1,0.3,1);
}
.score-value {
    font-size: 26px;
    font-weight: 700;
    color: #1D1D1F;
    line-height: 1;
}
.score-value span {
    font-size: 14px;
    font-weight: 400;
    color: #ACACB0;
}

/* ── Problems Grid ──────────────────────────────────────── */
.problems-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
    margin-bottom: 8px;
}
.problem-col {
    background: #FFFFFF;
    border-radius: 20px;
    padding: 22px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    border: 1px solid #E5E5EA;
}
.problem-header {
    font-size: 11px;
    font-weight: 700;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 14px;
}
.problem-list { display: flex; flex-direction: column; gap: 10px; }
.problem-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 14px;
    color: #1D1D1F;
    line-height: 1.55;
}
.problem-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 6px;
}

/* ── Steps ───────────────────────────────────────────────── */
.steps-list { display: flex; flex-direction: column; gap: 10px; }
.step-item {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    background: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 16px;
    padding: 16px 20px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
.step-num {
    font-size: 12px;
    font-weight: 700;
    color: #0071E3;
    background: #F0F7FF;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.step-text {
    font-size: 14px;
    color: #1D1D1F;
    line-height: 1.6;
    padding-top: 2px;
}

/* ── Priority Card ──────────────────────────────────────── */
.priority-card {
    background: #EAF3FF;
    border: 1px solid #BBD7FF;
    border-radius: 20px;
    padding: 24px 28px;
    margin: 16px 0;
}
.priority-label {
    font-size: 11px;
    font-weight: 700;
    color: #0071E3;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 10px;
}
.priority-text {
    font-size: 16px;
    font-weight: 600;
    color: #1D1D1F;
    line-height: 1.55;
}

/* ── Client Summary ─────────────────────────────────────── */
.summary-card {
    background: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 20px;
    padding: 24px 28px;
    font-size: 15px;
    color: #1D1D1F;
    line-height: 1.7;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    margin-bottom: 40px;
}

/* ── Preview images row ─────────────────────────────────── */
.preview-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 20px;
}
.preview-img-wrap {
    background: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
img[data-testid="stImage"] {
    border-radius: 16px !important;
}

/* ── Spinner ─────────────────────────────────────────────── */
[data-testid="stSpinner"] > div {
    border-color: #0071E3 !important;
}

/* ── Success / Error / Info ──────────────────────────────── */
div[data-testid="stAlert-success"],
div[data-testid="stAlert-error"],
div[data-testid="stAlert-info"] {
    border-radius: 14px !important;
    border: 1px solid #E5E5EA !important;
    font-size: 14px !important;
}

/* ── Download button ────────────────────────────────────── */
.stDownloadButton > button {
    background: #F5F5F7 !important;
    color: #1D1D1F !important;
    border: 1px solid #D2D2D7 !important;
    border-radius: 999px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 24px !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: #E8E8ED !important;
}

/* ── Responsive ─────────────────────────────────────────── */
@media (max-width: 768px) {
    div[data-testid="stMainBlockContainer"] {
        padding: 0 20px !important;
    }
    .hero { padding: 48px 0 12px; }
    .hero h1 { font-size: 36px; }
    .score-grid,
    .problems-grid {
        grid-template-columns: 1fr;
    }
    .preview-row {
        grid-template-columns: 1fr 1fr;
    }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 图片处理
# ============================================================
def encode_image_to_base64(image_file) -> str:
    if image_file is not None:
        return base64.b64encode(image_file.read()).decode("utf-8")
    return None


# ============================================================
# 主函数
# ============================================================
def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    is_demo = not bool(api_key)

    # ── Hero ─────────────────────────────────────────────────
    st.markdown("""
    <div class="hero">
        <h1>AI Sculpt Review</h1>
        <p class="subtitle">
            Compare your sculpt with a client reference image.<br>
            Get clear similarity scoring, proportion feedback,<br>
            and ZBrush‑ready revision steps.
        </p>
        <p class="tagline">Built for reference matching, sculpt review, and client‑ready feedback.</p>
    </div>""", unsafe_allow_html=True)

    # ── Mode Pill ─────────────────────────────────────────────
    if is_demo:
        pill_html = """<div style="text-align:center">
        <div class="mode-pill">
            <span class="dot demo"></span>
            Demo Mode · Sample review enabled
        </div>
        </div>"""
    else:
        pill_html = """<div style="text-align:center">
        <div class="mode-pill">
            <span class="dot real"></span>
            Real AI Mode · Vision analysis enabled
        </div>
        </div>"""
    st.markdown(pill_html, unsafe_allow_html=True)

    # ── Upload Section Label ───────────────────────────────────
    st.markdown("""
    <div style="max-width:1160px; margin:0 auto; padding: 0 0 16px;">
        <div class="upload-section-label">Start a sculpt review</div>
        <p style="font-size:14px; color:#86868b; max-width:560px; margin-top:-8px;">
            Upload a reference image and your current sculpt views.
            The system will evaluate likeness, proportion, structure,
            and provide actionable ZBrush revision steps.
        </p>
    </div>""", unsafe_allow_html=True)

    # ── Upload Cards ──────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    for col, (title, tag_class, tag_text, desc, key, required) in zip(
        [col1, col2, col3],
        [
            ("Reference Image",  "tag-required",  "Required",
             "Upload the client reference image.",        "reference"),
            ("Model Front View", "tag-required",  "Required",
             "Upload the current sculpt front view.",     "front"),
            ("Model Side View",  "tag-optional", "Optional",
             "Add a side view for stronger structure feedback.", "side"),
        ],
    ):
        with col:
            st.markdown(f"""
            <div class="upload-card" style="background:#fff; border-radius:24px;
                 border:1px solid #E5E5EA; padding:26px 28px; margin-bottom:12px;
                 box-shadow:0 8px 30px rgba(0,0,0,0.04);">
                <div class="upload-label-row">
                    <span class="upload-card-title">{title}</span>
                    <span class="{tag_class}">{tag_text}</span>
                </div>
                <div class="upload-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # File uploaders (overlaid on the cards via negative margin trick,
    # but we keep them below the visual card wrappers for Streamlit native rendering)
    with col1:
        reference = st.file_uploader(
            "", type=["jpg", "jpeg", "png", "webp"],
            key="ref_uploader",
            help="Reference image"
        )
    with col2:
        front = st.file_uploader(
            "", type=["jpg", "jpeg", "png", "webp"],
            key="front_uploader",
            help="Front view"
        )
    with col3:
        side = st.file_uploader(
            "", type=["jpg", "jpeg", "png", "webp"],
            key="side_uploader",
            help="Side view (optional)"
        )

    # ── Preview ───────────────────────────────────────────────
    if reference or front or side:
        cols_map = {}
        if reference: cols_map["Reference"]   = reference
        if front:    cols_map["Front View"]   = front
        if side:     cols_map["Side View"]    = side
        cols = list(cols_map.keys())
        vals = list(cols_map.values())
        n = len(vals)
        preview_cols = st.columns(n)
        for i, (label, img) in enumerate(zip(cols, vals)):
            with preview_cols[i]:
                st.image(img, caption=label, use_container_width=True)

    # ── Analyze Button ────────────────────────────────────────
    st.markdown('<div class="analyze-btn-wrap">', unsafe_allow_html=True)
    analyze = st.button("Analyze Sculpt Match", kind="primary")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="analyze-hint">Your images stay private. Demo mode uses a sample report.</p>',
        unsafe_allow_html=True,
    )

    # ── Analysis Logic ────────────────────────────────────────
    if analyze:
        if not reference:
            st.warning("Please upload a Reference Image.")
            st.stop()
        if not front:
            st.warning("Please upload a Model Front View.")
            st.stop()

        if is_demo:
            with st.spinner("Loading demo report…"):
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown(
                    '<p class="section-title" style="margin-top:0">Review report</p>',
                    unsafe_allow_html=True,
                )
                render_report(DEMO_REPORT, is_demo=True)
                st.markdown("""
                <div style="margin-top:32px; text-align:center;">
                <div class="stDownloadButton">%s</div>
                </div>""" % _demo_download_btn(),
                    unsafe_allow_html=True,
                )
        else:
            with st.spinner("Analyzing with AI… this may take up to 30 seconds."):
                try:
                    client = OpenAI(api_key=api_key)
                    content_list = [
                        {"type": "text", "text": ANALYSIS_PROMPT},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image_to_base64(reference)}"}},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image_to_base64(front)}"}},
                    ]
                    if side:
                        content_list.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encode_image_to_base64(side)}"}})

                    messages = [{"role": "user", "content": content_list}]
                    response = client.chat.completions.create(
                        model=MODEL_NAME, messages=messages, max_tokens=2048)
                    report_text = response.choices[0].message.content

                    # Parse and render
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown(
                        '<p class="section-title" style="margin-top:0">Review report</p>',
                        unsafe_allow_html=True,
                    )
                    report = parse_report(report_text)
                    render_report(report, is_demo=False)

                    # Download
                    st.markdown("""
                    <div style="margin-top:32px; text-align:center;">
                    <div class="stDownloadButton">%s</div>
                    </div>""" % _make_download_btn(report_text, "sculpt_review_report.md"),
                        unsafe_allow_html=True,
                    )

                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    st.info("Check your API key, network connection, or image file size (< 10 MB).")

    # ── Footer ─────────────────────────────────────────────────
    st.markdown("""
    <hr>
    <div style="text-align:center; font-size:12px; color:#ACACB0; padding-bottom:40px;">
        AI Sculpt Review · Your images are never stored or transmitted to any third party.
    </div>""", unsafe_allow_html=True)


def _demo_download_btn():
    import json
    text = json.dumps(DEMO_REPORT, ensure_ascii=False, indent=2)
    import urllib.parse
    encoded = urllib.parse.quote(text)
    data_uri = f"data:text/plain;charset=utf-8,{encoded}"
    return (
        f'<a href="{data_uri}" download="sculpt_review_report_demo.json">'
        f'<button style="background:#F5F5F7; color:#1D1D1F; border:1px solid #D2D2D7; '
        f'border-radius:999px; font-size:14px; font-weight:500; padding:10px 24px; cursor:pointer;">'
        f'Download Report</button></a>'
    )


def _make_download_btn(content: str, filename: str):
    import json
    encoded = urllib.parse.quote(content)
    data_uri = f"data:text/plain;charset=utf-8,{encoded}"
    return (
        f'<a href="{data_uri}" download="{filename}">'
        f'<button style="background:#F5F5F7; color:#1D1D1F; border:1px solid #D2D2D7; '
        f'border-radius:999px; font-size:14px; font-weight:500; padding:10px 24px; cursor:pointer;">'
        f'Download Report</button></a>'
    )


if __name__ == "__main__":
    main()
