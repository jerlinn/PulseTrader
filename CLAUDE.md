## Script Design
- Strictly follow the KISS principle and the Zen of Python; avoid over-engineering
- Add necessary comments only for complex logic
- 不要自动运行 TrendInsigt.py
  
## Documentation Guidelines
- 每次迭代之后都要自动检查 @Read.md，对齐逻辑
- Communicate as equals; do not use any honorifics such as「您」
- If query = Chinese: punctuation style example — use full-width commas and 「corner brackets」 for quotation marks; insert one space before and after numbers and Latin letters
- Make good use of verbs that convey expressive tension

## Visualization
- Use Plotly for charts by default
- Except for main titles, use the default font without bolding
- Chart data presentation must prioritize accessibility, avoiding overlaps and ambiguity
- Labels should preferably be placed horizontally at the bottom and vertically centered with the chart

## Data
- A-shares and H-shares: akshare
- U.S. stocks: yfinance

## LLM
- Primary provider: Aihubmix
- Retrieve key from system environment variables; hardcoding is prohibited

## Project Strcture
TrendSight/
├── TrendInsigt.py              # 主程序入口（交互式股票分析）
├── analysis.py                 # AI 分析模块（GPT-5 集成）
├── plotting_component.py       # 绘图组件（对数坐标可视化）
├── rsi_component.py            # RSI 计算与背离检测
├── supertrend_component.py     # SuperTrend 指标计算
├── stock_data_provider.py      # 数据提供者接口
├── stock_cache.py              # 统一数据库管理（SQLite）
├── indicators_storage.py       # 技术指标计算和存储
├── indicators_query.py         # 数据查询和导出工具
├── cache/
│   └── stock_data.db           # SQLite 数据库（统一存储）
├── figures/                    # 生成的图表文件
├── reports/                    # AI 分析报告（Markdown）
└──analyst_prompt.md           # AI 分析师 system prompt