"""
AI Sculpt Review - MVP
上传参考图和模型截图，AI 分析还原度并给出 ZBrush 修模建议。
支持 Real AI Mode 和 Demo Mode（无 API Key 时自动启用）。
"""

import streamlit as st
import os
import base64
from openai import OpenAI

# ============================================================
# 配置
# ============================================================
MODEL_NAME = "gpt-4o"  # 可根据需要改为 gpt-4.1 或其他兼容模型

# ============================================================
# 常量
# ============================================================
DEMO_REPORT = """# AI Sculpt Review Report

## Overall Score
72 / 100

## Score Breakdown
- Silhouette: 18 / 30
- Facial Landmarks: 16 / 25
- Volume Structure: 14 / 20
- Proportion Accuracy: 11 / 15
- Detail Match: 7 / 10

## Main Problems
### Critical
1. 头部整体轮廓与参考图仍有明显差距，脸部宽度偏大。
2. 下巴长度不足，导致脸型不够接近参考图。

### Major
1. 眼窝深度不足，眉弓结构不够明确。
2. 鼻梁和鼻尖体积不足，侧面轮廓偏平。
3. 颧骨位置和体积需要进一步调整。

### Minor
1. 嘴角结构还不够自然。
2. 皮肤细节暂时不用加强，应先修大形。
3. 耳朵位置和体积需要后续检查。

## ZBrush Fix Instructions
1. 使用 Move 笔刷从正面收窄脸颊两侧，让脸型更接近参考图。
2. 从侧面拉长下巴，并加强下颌角。
3. 使用 Clay Buildup 增加鼻梁到鼻尖的体积。
4. 使用 Dam Standard 加深眼窝和眉弓下方结构。
5. 调整颧骨位置，让面部大形更有骨性结构。
6. 暂时不要加皮肤毛孔和细节，先把大形和五官比例修准。

## Highest Priority Next Step
先修正头部大形：收窄脸颊、拉长下巴、加强鼻梁侧面轮廓。

## Client-Friendly Summary
当前模型已经有基础人头结构，但与参考图相比，大形、脸型和五官体积还需要进一步调整。建议先集中修改整体轮廓和面部结构，再进入细节阶段。"""

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
# 页面设置
# ============================================================
st.set_page_config(
    page_title="AI Sculpt Review",
    page_icon="🎨",
    layout="wide"
)

# ============================================================
# 图片处理
# ============================================================
def encode_image_to_base64(image_file) -> str:
    """将上传的图片文件转为 base64 字符串"""
    if image_file is not None:
        return base64.b64encode(image_file.read()).decode("utf-8")
    return None


# ============================================================
# 主函数
# ============================================================
def main():
    # 检测 API Key
    api_key = os.environ.get("OPENAI_API_KEY")
    is_demo_mode = not bool(api_key)

    # 顶部模式提示
    st.title("AI Sculpt Review")

    if is_demo_mode:
        st.info("🔰 **Demo Mode** — No API key detected. Using sample report. "
                "Set `OPENAI_API_KEY` env var to enable real AI analysis.")
    else:
        st.success("✅ **Real AI Mode** — API key detected. Real AI analysis enabled.")

    st.markdown(
        "上传客户参考图和当前模型截图，AI 会判断还原度、比例、结构问题，并给出 ZBrush 修模建议。"
    )
    st.divider()

    # 上传区域
    st.subheader("📤 上传图片")

    col1, col2, col3 = st.columns(3)
    with col1:
        reference = st.file_uploader(
            "Reference Image（参考图）*",
            type=["jpg", "jpeg", "png", "webp"],
            help="客户提供的目标角色参考图"
        )
    with col2:
        front = st.file_uploader(
            "Model Front View（正面图）*",
            type=["jpg", "jpeg", "png", "webp"],
            help="当前模型的正面截图"
        )
    with col3:
        side = st.file_uploader(
            "Model Side View（侧面图，可选）",
            type=["jpg", "jpeg", "png", "webp"],
            help="当前模型的侧面截图，帮助分析轮廓"
        )

    # 预览已上传的图片
    if reference or front or side:
        preview_cols = st.columns([1, 1, 1] if side else [1, 1])
        idx = 0
        if reference:
            with preview_cols[idx]:
                st.image(reference, caption="Reference（参考图）", use_container_width=True)
            idx += 1
        if front:
            with preview_cols[idx]:
                st.image(front, caption="Model Front（正面图）", use_container_width=True)

    st.divider()

    # 分析按钮
    _, center, _ = st.columns([2, 1, 2])
    with center:
        analyze = st.button("🔍 Analyze", type="primary", use_container_width=True)

    # 分析逻辑
    if analyze:
        if not reference:
            st.warning("⚠️ 请上传 Reference Image（参考图）！")
            st.stop()
        if not front:
            st.warning("⚠️ 请上传 Model Front View（正面图）！")
            st.stop()

        # ========== Demo Mode ==========
        if is_demo_mode:
            with st.spinner("正在生成 Demo 报告..."):
                st.divider()
                st.subheader("📋 Demo Report")
                st.markdown(DEMO_REPORT)
                st.download_button(
                    "📥 Download Report",
                    data=DEMO_REPORT,
                    file_name="sculpt_review_report_demo.md",
                    mime="text/markdown"
                )
            st.info("💡 这是 Demo 报告。如需真实 AI 分析，请设置 OPENAI_API_KEY 环境变量。")

        # ========== Real AI Mode ==========
        else:
            with st.spinner("正在分析，请稍候（可能需要 10-30 秒）..."):
                try:
                    client = OpenAI(api_key=api_key)

                    # 准备消息
                    content_list = [
                        {
                            "type": "text",
                            "text": ANALYSIS_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encode_image_to_base64(reference)}"
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encode_image_to_base64(front)}"
                            }
                        }
                    ]

                    if side:
                        content_list.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encode_image_to_base64(side)}"
                            }
                        })

                    messages = [{"role": "user", "content": content_list}]

                    # 调用 API
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        max_tokens=2048
                    )

                    report = response.choices[0].message.content

                    # 输出结果
                    st.divider()
                    st.markdown(report)
                    st.download_button(
                        "📥 Download Report",
                        data=report,
                        file_name="sculpt_review_report.md",
                        mime="text/markdown"
                    )

                except Exception as e:
                    st.error(f"❌ 分析失败：{e}")
                    st.info("💡 提示：请检查网络连接、API Key 是否有效、图片是否过大。")

    # 底部
    st.divider()
    mode_label = "Demo Mode (No API Key)" if is_demo_mode else f"Real AI Mode ({MODEL_NAME})"
    st.caption(
        f"Mode: {mode_label} · "
        "API Key 仅从环境变量 OPENAI_API_KEY 读取 · "
        "不保存任何数据"
    )


# ============================================================
if __name__ == "__main__":
    main()