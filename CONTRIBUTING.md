# 贡献指南

感谢你对 PulseTrader 的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告 bug
- 💡 提出功能建议
- 📝 改进文档
- 🔧 提交代码改进
- 🧪 添加测试用例

## 快速开始

### 环境要求

- Python 3.8+
- 推荐使用虚拟环境

### 安装开发依赖

```bash
git clone https://github.com/jerlinn/PulseTrader.git
cd PulseTrader
pip install -r requirements.txt
```

### 环境配置

设置系统环境变量：

```bash
export AIHUBMIX_API_KEY="your_api_key_here"
```
运行指令使其生效
```shell
source ~/.zshrc
```

## 贡献流程

### 报告问题

使用 [GitHub Issues](https://github.com/jerlinn/PulseTrader/issues) 报告问题时，请包含：

- **问题描述**：清晰描述遇到的问题
- **复现步骤**：详细的操作步骤
- **预期行为**：期望的正确行为
- **实际行为**：实际发生的情况
- **环境信息**：Python 版本、操作系统、网络代理情况等
- **错误日志**：相关的错误信息

### 提交代码

1. **Fork 项目** 到你的 GitHub 账户
2. **创建功能分支**：
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **提交更改**：
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
4. **推送到分支**：
   ```bash
   git push origin feature/amazing-feature
   ```
5. **创建 Pull Request**

## 代码规范

### Python 代码风格

- 遵循 [PEP 8](https://pep8.org/) 规范
- 使用 4 个空格缩进
- 行长度限制为 88 字符
- 导入顺序：标准库 → 第三方库 → 本地模块

### 注释规范

```python
def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    计算 RSI（相对强弱指标）
    
    Args:
        prices: 价格序列
        period: 计算周期，默认 14
        
    Returns:
        RSI 值列表
    """
    # 只为复杂逻辑添加必要注释
    pass
```

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**类型说明**：
- `feat`: 新功能
- `fix`: bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构代码
- `test`: 添加测试
- `chore`: 构建过程或辅助工具变动

**示例**：
```
feat(rsi): add RSI divergence detection

- 实现 RSI 背离检测算法
- 添加图表标记功能
- 优化计算性能

Closes #123
```

## 项目结构

```
PulseTrader/
├── TrendInsigt.py              # 主程序入口
├── analysis.py                 # AI 分析模块
├── plotting_component.py       # 绘图组件
├── rsi_component.py            # RSI 计算与背离检测
├── supertrend_component.py     # SuperTrend 指标计算
├── stock_data_provider.py      # 数据提供者接口
├── stock_cache.py              # 数据库管理
├── indicators_storage.py       # 技术指标存储
├── indicators_query.py         # 数据查询工具
├── cache/                      # 数据缓存目录
├── figures/                    # 生成的图表
└── reports/                    # AI 分析报告
```

## 设计原则

### KISS 原则
- 保持代码简单直观
- 避免过度工程化
- 优先考虑可读性和可维护性

### 数据处理
- **A 股和港股**：使用 akshare
- **美股**：使用 yfinance
- **测试数据**：最少取 15 日数据（RSI14 计算要求）

### 可视化
- 默认使用 Plotly 创建图表
- 主标题外不使用粗体
- 优先考虑可访问性，避免重叠和歧义
- 标签水平居底，垂直居中

## 测试

运行测试前确保有足够的历史数据：

```bash
# 示例：获取 30 天数据进行测试
python -c "
from stock_data_provider import StockDataProvider
provider = StockDataProvider()
data = provider.get_stock_data('000001', days=30)
print(f'数据量: {len(data)} 条')
"
```

## 许可证

通过贡献代码，你同意你的贡献将在 [GPL-3.0](LICENSE) 许可证下发布。

## 获得帮助

- 📖 查看 [README.md](README.md) 了解项目概况
- 💬 在 [Issues](https://github.com/jerlinn/PulseTrader/issues) 中提问
- 📧 发送邮件至 [your-email@example.com](mailto:fancyexpro@gmail.com)

---

再次感谢你的贡献！每一个 PR 和 Issue 都让 PulseTrader 变得更好。🚀