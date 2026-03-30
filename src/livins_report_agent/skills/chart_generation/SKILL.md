---
name: "Chart Generation"
description: "图表类型选择与样式规范"
---

# Chart Generation

## When to Use
- 数据查询完成后，需要可视化展示分析结果
- 用户明确要求图表或报告中需要配图

## Chart Type Selection

| 分析场景 | 推荐图表 | matplotlib 方法 |
|----------|----------|-----------------|
| 时间趋势（月租金变化） | 折线图 Line | `plt.plot()` |
| 区域/类别对比（各区均价） | 柱状图 Bar | `plt.bar()` / `plt.barh()` |
| 占比分布（房型分布） | 饼图 Pie | `plt.pie()` |
| 价格分布 | 直方图 Histogram | `plt.hist()` |
| 两变量关系（面积vs价格） | 散点图 Scatter | `plt.scatter()` |
| 多维对比 | 分组柱状图 Grouped Bar | 多次 `plt.bar()` + offset |
| 范围展示（价格区间） | 箱线图 Box | `plt.boxplot()` |

## Style Specs

### Color Palette
- Primary: `#c8956c` (amber gold)
- Secondary: `['#4A90D9', '#D94A4A', '#50C878', '#9B59B6', '#F39C12']`
- Background: `#1a1a1a` (dark) or `#ffffff` (light)

### Typography
- Title: 14pt, bold
- Axis labels: 11pt
- Tick labels: 9pt

### Layout Rules
- Always include title and axis labels
- Use `plt.tight_layout()` to prevent label clipping
- Set figure size: `figsize=(10, 6)` for single chart, `figsize=(12, 8)` for complex
- DPI: 150 for report embedding
- Format large numbers with commas: `${:,.0f}`
- Rotate x-axis labels 45° if > 5 categories

### Code Template
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
# ... plot data ...
ax.set_title('Title', fontsize=14, fontweight='bold')
ax.set_xlabel('X Label', fontsize=11)
ax.set_ylabel('Y Label', fontsize=11)
plt.tight_layout()
plt.savefig('chart.png', dpi=150, bbox_inches='tight')
plt.close()
```

## Multiple Charts
- 对比分析：生成 2-3 张图（趋势 + 对比 + 分布）
- 单一分析：1 张图即可
- 每张图单独保存为 PNG，在 PDF 报告中引用
