# AI Sculpt Review 🎨

**AI 雕刻评审工具** — 上传参考图和模型截图，AI 分析还原度、比例、结构问题，并给出 ZBrush 修模建议。

---

## 功能特性

- 📊 **结构化评分** — 5 维度总分 100 分（轮廓、五官、结构、比例、细节）
- 📋 **问题分级** — Critical / Major / Minor 三级问题清单
- 🛠️ **修模建议** — 针对 ZBrush 的具体修复步骤
- 📄 **Markdown 报告** — 可下载保存
- 🔒 **本地运行** — 所有数据不离开本机
- 🤖 **双模式** — Real AI Mode + Demo Mode（无需 API Key 也能演示）

---

## 系统要求

- Python 3.10+
- Windows / macOS / Linux 均可运行
- （可选）OpenAI API Key，用于真实 AI 分析

---

## 安装与运行

### 1. 克隆 / 下载项目

```bash
git clone <your-repo-url>
cd ai_sculpt_review
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行

**方式一：无需 API Key（Demo Mode）**
```bash
streamlit run app.py
```
直接运行，自动进入 Demo Mode，显示示例报告。

**方式二：启用真实 AI 分析**
```cmd
# Windows CMD
set OPENAI_API_KEY=你的key
streamlit run app.py
```
```powershell
# Windows PowerShell
$env:OPENAI_API_KEY="你的key"
streamlit run app.py
```
```bash
# macOS / Linux
export OPENAI_API_KEY=你的key
streamlit run app.py
```

> ⚠️ 不要把 API Key 写进代码里。每次运行前确保环境变量已设置。

浏览器自动打开 http://localhost:8501

---

## 运行模式

| 模式 | 触发条件 | 说明 |
|------|----------|------|
| **Demo Mode** | 未设置 `OPENAI_API_KEY` 环境变量 | 显示固定示例报告，无需 API Key |
| **Real AI Mode** | 已设置 `OPENAI_API_KEY` 环境变量 | 使用 GPT-4o 真实分析上传的图片 |

页面顶部会显示当前模式：
- Demo Mode：`🔰 Demo Mode — No API key detected.`
- Real AI Mode：`✅ Real AI Mode — API key detected.`

---

## 使用方法

1. **上传参考图**（必填）— 客户提供目标角色的参考图
2. **上传正面图**（必填）— 当前模型的正面截图
3. **上传侧面图**（可选）— 侧面截图有助于轮廓分析
4. **点击 Analyze** — 等待分析完成（Demo 即时返回，真实 AI 约 10-30 秒）
5. **查看报告** — 评分、问题、建议一目了然
6. **下载报告** — 点击 Download Report 保存 Markdown 文件

---

## 评分说明

| 维度 | 分值 | 说明 |
|------|------|------|
| 大形轮廓 Silhouette | 30 | 头部整体形状、脸型、轮廓线 |
| 五官位置 Facial Landmarks | 25 | 眼窝、鼻梁、嘴部、下巴、颧骨位置 |
| 结构体积 Volume Structure | 20 | 块面感、体积感、结构合理性 |
| 比例准确 Proportion Accuracy | 15 | 三庭五眼、整体比例 |
| 细节还原 Detail Match | 10 | 细节特征还原度 |

总分 100 分，越高越接近参考图。

---

## 报告解读

- **Critical（严重问题）** — 必须修复的结构性错误，否则后续无法继续
- **Major（中等问题）** — 明显偏离参考图，建议下一步修复
- **Minor（小问题）** — 微调项，可留在细化阶段处理

---

## 技术栈

- **Streamlit** — 本地网页界面
- **OpenAI Python SDK** — 多模态模型调用（可选）
- **Pillow** — 图片处理（可选）

---

## 常见问题

**Q: 启动后显示 Demo Mode？**
这是正常的！说明没有设置 `OPENAI_API_KEY`。可以直接演示。设置环境变量后重启即可切换到 Real AI Mode。

**Q: 提示 "未设置 OPENAI_API_KEY"？**
```cmd
set OPENAI_API_KEY=sk-...
```
确保在运行 `streamlit run` 的同一命令行窗口执行。

**Q: API 调用失败？**
- 检查 API Key 是否有效
- 检查网络是否可访问 api.openai.com
- 图片是否太大（建议单张 < 5MB）

**Q: 模型选择？**
打开 `app.py`，修改顶部的 `MODEL_NAME`：
```python
MODEL_NAME = "gpt-4o"  # 或 "gpt-4.1", "gpt-4-turbo" 等
```

---

## 项目结构

```
ai_sculpt_review/
├── app.py              # 主程序（完整可运行）
├── requirements.txt    # 依赖列表
└── README.md           # 说明文档
```

---

*本工具仅供学习与工作辅助使用，请遵守 OpenAI 使用政策。*