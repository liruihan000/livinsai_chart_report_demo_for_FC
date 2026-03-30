---
name: "Report Building"
description: "报告结构设计与PDF布局规范"
---

# Report Building

## When to Use
- 数据分析和图表生成完成后，需要组装最终报告
- 用户要求生成 PDF 报告

## Report Structure

### Standard Sections
1. **标题页** — 报告标题 + 生成日期 + 数据范围
2. **摘要** — 2-3 句关键发现（Executive Summary）
3. **数据分析** — 查询结果的文字解读 + 图表
4. **图表展示** — 嵌入生成的 PNG 图表，每张图配说明
5. **结论与建议** — 基于数据的可操作建议

### Structure by Analysis Type

| 分析类型 | 结构 |
|----------|------|
| 趋势分析 | 时间线叙事：过去 → 现在 → 预测 |
| 对比分析 | 并列结构：A区 vs B区，逐维度对比 |
| 综合报告 | 总分总：概览 → 多维分析 → 总结建议 |

## PDF Layout with reportlab

### Page Setup
```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table

doc = SimpleDocTemplate(
    'report.pdf',
    pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm,
)
```

### Typography
- Title: Helvetica-Bold 20pt
- Heading: Helvetica-Bold 14pt
- Body: Helvetica 11pt, leading=14pt
- Data/Numbers: Courier 10pt

### Image Embedding
```python
from reportlab.platypus import Image

# Charts should be saved at 150 DPI, width fits page
chart = Image('chart.png', width=16*cm, height=10*cm)
```

### Table Styling
```python
from reportlab.lib import colors

table_style = [
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c8956c')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
]
```

### Build Flow
```python
elements = []
styles = getSampleStyleSheet()

# 1. Title
elements.append(Paragraph("报告标题", styles['Title']))
elements.append(Spacer(1, 0.5*inch))

# 2. Summary
elements.append(Paragraph("摘要内容...", styles['Normal']))
elements.append(Spacer(1, 0.3*inch))

# 3. Charts
elements.append(Image('chart_trend.png', width=16*cm, height=10*cm))
elements.append(Paragraph("图表说明...", styles['Normal']))

# 4. Data Table (optional)
elements.append(Table(data, colWidths=[...], style=table_style))

# 5. Conclusion
elements.append(Paragraph("结论与建议...", styles['Normal']))

doc.build(elements)
```

## Rules
- 报告长度：1-3 页（简单分析 1 页，综合报告 2-3 页）
- 每张图表必须配文字说明
- 数字格式：价格用 `$X,XXX`，百分比保留 1 位小数
- 日期格式：`YYYY-MM` 或 `YYYY-MM-DD`
- 文件名格式：`report_{analysis_type}_{timestamp}.pdf`
