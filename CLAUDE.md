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
