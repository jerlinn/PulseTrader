# TrendSight - AI 增强的量化投资工具

## 🔥 重新定义 AI 量化投资的正确方向

在当今快速变化的金融市场中，我发现了一个严重的问题：**市面上的 AI 量化工具完全走错了方向**。

### 当前市场的根本性错误
- **盲目迷信概率模型**：试图让 AI 接管所有计算和分析，忽略了金融数据的神圣性
- **数据精度的妥协**：用推理和预测来处理需要绝对准确的财务数据
- **信息过载陷阱**：追踪无穷无尽的舆情新闻，分析真假难辨的消息面
- **基本面迷信**：沉迷于复杂的财务报表，忽略了市场最直接的语言——价格和成交量
- **本末倒置**：让 AI 做计算，人做判断，这是对各自优势的严重误用

### 核心理念
> **数据神圣不可侵犯，必须用 100% 可靠的算法来承接**

我坚信：
- **精确计算是基础**：所有技术指标和数据处理必须保证 100% 的准确性
- **AI 负责洞察**：AI 应该专注于提供市场洞察和行为指引
- **量化人性是关键**：通过价格和成交量这一市场最纯粹的语言，直接量化人性的贪婪与恐惧
- **聚焦数学本质**：相对强度指标揭示市场情绪的数学规律，SuperTrend 捕捉趋势的几何特征
- **基本面终将显现**：无论多复杂的基本面，长期来看都会完整反映在量价关系中
- **化繁为简**：通过数据分析和可视化的方法沉淀，大幅降低用户负担
- **开源共享**：让更多人能够获得正确的量化投资工具和方法

通过开源这套经过实战验证的方法，我们希望：
- 推动行业的正确方向，回归数据精确性和量价分析的本质
- 帮助投资者摆脱信息过载，专注于市场最本真的信号
- 通过简洁优雅的设计降低量化投资的门槛
- 建立一个注重数学严谨性和人性洞察的投资社区

## ⚖️ 精确计算与智能洞察的完美平衡

TrendSight 采用**分离式架构设计**，确保计算的绝对精确性和 AI 辅助的智能化：

### 核心技术架构

```mermaid
graph TD
    %% 用户交互层 - 圆角矩形
    USER([输入股票名称]) --> APP([应用层<br/>TrendInsigt.py])
    
    %% 数据处理层 - 矩形
    APP --> DATA[数据层<br/>stock_data_provider]
    DATA --> CACHE[(缓存层<br/>stock_cache.py<br/>SQLite Database)]
    
    %% 计算引擎层 - 六边形
    CACHE --> SUPER{{指标层<br/>supertrend_component}}
    CACHE --> RSI{{信号层<br/>rsi_component}}
    
    %% 存储管理层 - 梯形
    SUPER --> STORE[/存储层<br/>indicators_storage\]
    RSI --> STORE
    STORE --> CACHE
    
    %% 输出层 - 圆角矩形和菱形
    STORE --> VIZ[可视化层<br/>plotting_component]
    VIZ --> CHART([交互式图表输出])
    
    %% AI 分析层 - 云形状
    STORE --> AI{{AI分析<br/>analysis.py<br/>GPT-5}}
    AI --> REPORT([智能分析报告])
    
    %% 工具层 - 圆形
    QUERY((查询工具<br/>indicators_query.py)) --> CACHE
    
    %% 用户交互层样式 - 蓝色系
    classDef userLayer fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    class USER,APP,CHART,REPORT userLayer
    
    %% 数据层样式 - 紫色系
    classDef dataLayer fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    class DATA dataLayer
    
    %% 存储层样式 - 红色系，加粗边框表示核心
    classDef storageLayer fill:#ffebee,stroke:#d32f2f,stroke-width:4px,color:#000
    class CACHE storageLayer
    
    %% 计算层样式 - 橙色系
    classDef computeLayer fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    class SUPER,RSI computeLayer
    
    %% 存储管理样式 - 绿色系
    classDef mgmtLayer fill:#e8f5e8,stroke:#388e3c,stroke-width:2px,color:#000
    class STORE,VIZ mgmtLayer
    
    %% AI层样式 - 黄色系
    classDef aiLayer fill:#fff8e1,stroke:#ffa000,stroke-width:2px,color:#000
    class AI aiLayer
    
    %% 工具层样式 - 青色系
    classDef toolLayer fill:#e0f2f1,stroke:#00695c,stroke-width:2px,color:#000
    class QUERY toolLayer
```

### 统一数据库架构（消除存储重叠）
- **一库统管**：SQLite 数据库统一存储原始数据和技术指标，消除重复存储
- **关系型设计**：6 张数据表科学设计，确保数据完整性和查询效率
- **智能缓存**：避免重复计算，支持增量更新和快速查询
- **持久化存储**：所有技术指标数据完整保存，支持历史分析和回测
- **交易日历集成**：内置交易日历缓存，避免非交易日的无效数据请求

### 精确计算引擎（100% 可靠算法）
- **严格数据验证**：每一个数据点都经过完整性和准确性检查
- **确定性算法**：使用Wilder平滑法等经典算法，确保结果的可重现性
- **零近似计算**：SuperTrend、RSI 等所有指标计算都使用精确数学公式
- **多时间框架验证**：短期、中期、长期三层验证机制过滤假信号

### 数据库表结构设计

```mermaid
erDiagram
    stock_data ||--o{ technical_indicators : symbol
    technical_indicators ||--o{ rsi_divergences : symbol
    technical_indicators ||--o{ trend_signals : symbol
    stock_data ||--|| stock_info : code
    
    stock_data {
        integer id PK
        string symbol
        string stock_name
        string date
        real open_price
        real high_price  
        real low_price
        real close_price
        integer volume
        real daily_change_pct
        datetime created_at
        datetime updated_at
        unique symbol_date "UNIQUE(symbol, date)"
    }
    
    technical_indicators {
        integer id PK
        string symbol
        string stock_name
        string date
        real rsi14
        real ma10
        real daily_change_pct
        integer trend
        real upper_band
        real lower_band
        real volume
        real vol_ratio
        datetime created_at
        datetime updated_at
        unique symbol_date "UNIQUE(symbol, date)"
    }
    
    rsi_divergences {
        integer id PK
        string symbol
        string stock_name
        string date
        string prev_date
        string type
        string timeframe
        real rsi_change
        real price_change
        real confidence
        real current_rsi
        real prev_rsi
        real current_price
        real prev_price
        datetime created_at
    }
    
    trend_signals {
        integer id PK
        string symbol
        string stock_name
        string date
        string signal_type
        real price
        real trend_value
        datetime created_at
    }
    
    stock_info {
        integer id PK
        string code
        string name
        datetime created_at
        datetime updated_at
        unique code "UNIQUE(code)"
    }
    
    trading_calendar {
        integer id PK
        string trade_date
        datetime created_at
        unique trade_date "UNIQUE(trade_date)"
    }
```

### 智能洞察层（AI 负责解读）

- **信号置信度评估**：AI量化每个交易信号的可靠性
- **市场模式识别**：基于历史数据识别相似的市场环境
- **风险评估建议**：提供个性化的风险管理指引
- **预留LLM接口**：支持自然语言解读复杂市场信号

### 化繁为简的设计理念

```mermaid
graph LR
    %% 输入层 - 圆角矩形表示复杂信息
    COMPLEX([复杂的市场信息]) --> FILTER{过滤机制}
    
    %% 过滤分支 - 菱形决策节点
    FILTER --> |基本面| NOISE1([财报迷宫])
    FILTER --> |舆  情| NOISE2([新闻噪音])
    FILTER --> |量价关系| CORE([核心信号])
    
    %% 核心分析层 - 六边形表示处理引擎
    CORE --> TREND{{趋势判断}}
    CORE --> RSI_DIV{{情绪极值}}
    
    %% 输出层 - 圆角矩形表示最终结果
    TREND --> SIGNAL([清晰的投资信号])
    RSI_DIV --> SIGNAL
    
    %% 噪音信息样式 - 红色系，表示要过滤的信息
    classDef noiseLayer fill:#ffebee,stroke:#d32f2f,stroke-width:2px,color:#000
    class COMPLEX,NOISE1,NOISE2 noiseLayer
    
    %% 过滤决策样式 - 灰色系
    classDef filterLayer fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#000
    class FILTER filterLayer
    
    %% 核心信号样式 - 绿色系，表示有价值的信息
    classDef coreLayer fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px,color:#000
    class CORE coreLayer
    
    %% 分析引擎样式 - 橙色系
    classDef engineLayer fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    class TREND,RSI_DIV engineLayer
    
    %% 最终输出样式 - 蓝色系，加粗表示重要性
    classDef outputLayer fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    class SIGNAL outputLayer
```

- **一目了然的可视化**：对数坐标系统，直观展现价格变化本质
- **量价关系主导**：以量价关系为主要量化依据，用容易理解的 SuperTrend 和相对强度做辅助，快速过滤出实用信息
- **交互式操作**：一键切换时间周期，无需复杂配置
- **渐进式学习**：从基础概念到高级策略，循序渐进

## 🧐 一个真正好用的量化投资工具

### 对数据精确性的承诺
- **100% 算法可靠性**：每个计算结果都可以手工验证和复现
- **零容忍近似值**：拒绝一切近似，LLM 推理和数据计算完全剥离
- **透明化流程**：所有计算逻辑完全开源
- **严格测试覆盖**：确保边界条件下的计算准确性

### 为普通投资者而设计
- **极简交互**：输入股票名称即可开始分析，无需追踪复杂新闻和财报
- **专业图表**：对数坐标系直观展现价格波动本质，摆脱信息噪音干扰
- **人性量化**：RSI 背离检测直接捕捉市场贪婪与恐惧的临界点
- **数学严谨**：严格阈值（顶背离 80，底背离 20/30）过滤 90% 情绪化假信号
- **置信度量化**：每个信号都有明确的可靠性评分，避免盲目跟风

### 开发者友好的架构
- **模块化设计**：plotting 绘图、RSI 背离计算、SuperTrend 趋势计算，三大组件独立可复用
- **清晰接口**：每个函数都有明确的输入输出定义
- **易于扩展**：标准化的组件接口，方便添加新指标
- **详尽文档**：从安装到自定义开发的完整指南

### 适合这些朋友
- **投资新手**：想学习量化方法但被复杂工具劝退的朋友
- **技术爱好者**：希望了解 AI 与投资分析正确结合方式的开发者  
- **实战投资者**：需要可靠技术指标辅助投资决策的个人投资者
- **开源贡献者**：相信数据精确性，愿意推动行业正确发展的技术人

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/your-repo/TrendSight.git
cd TrendSight

# 安装依赖
pip install -r requirements.txt

# 运行交互式股票分析
python TrendInsigt.py

# 或运行 AI 分析（需要 AIHUBMIX_API_KEY 环境变量）
python analysis.py

# 查询已存储的技术指标
python indicators_query.py --list
python indicators_query.py 杭钢股份
python indicators_query.py 杭钢股份 --export
```

## 📖 项目结构

```
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
├── analyst_prompt.md           # AI 分析师 system prompt
├── 技术指标存储使用说明.md       # 数据存储系统文档
└── requirements.txt            # 项目依赖
```

## Todo
- [x] 组件化
- [x] 对接 LLM
  - [x] system prompt
  - [ ] 补充到缓存边界，高效利用 752 → 1024 Tokens
  - [x] 计算的部分使用代码解析器
  - [x] 图片读取
  - [x] 把 response 对象中的目标内容提取为 md 文档到 reports 目录
  - [x] 把传入的股票图表 encode_image，放到 report 文档，作为头图
- [x] 用于进一步分析的数据结构设计，增加输出模块，存储 csv
  - [x] indicators_query.py 数据查询工具
  - [x] CSV 导出功能（`python indicators_query.py 股票名称 --export`）
  - [x] 数据库统计和管理功能
- [x] 数据交互设计优化：股票名称 → 数据和图表 → LLM → 报告
  - [x] 终端交互优化，实时显示技术指标摘要
  - [x] 重要数据指标传入 user message
- [x] 分析时可以传入用户的其他上下文，如具体的问题或额外信息（已实现，需要多用例测试）
- [x] 修复非交易日获取数据时的处理异常
  - [x] 集成交易日历 API（akshare.tool_trade_date_hist_sina）
  - [x] 添加交易日历数据库表和缓存机制
  - [x] 优化数据更新逻辑，避免周末等非交易日的无效请求
  - [x] 提供友好的非交易日提示信息
- [x] 数据传递：补充交易量和量比的存储和传递

- [x] 对于除权除息日这种边缘情况，用XD前缀去匹配
- [ ] All-in-one 脚本
  
### Prompt 专项
- [x] 构建场域，影响 LLM 行为
- [x] prompt 层面大幅简化报告，提升可操作性和易读性
  - [x] 友好的讲解，避免充斥晦涩的术语
  - [x] 输出优化：原则清晰的前提下尽可能实现最大灵活度
- [x] 数据结构优化，实现数据持久化机制

## 🤝 贡献指南

欢迎所有形式的贡献！无论你是想报告 bug、提出功能建议、改进文档还是提交代码，我们都欢迎你的参与。

请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细的：
- 🐛 如何报告问题
- 💡 如何提出功能建议
- 🔧 代码提交规范
- 🧪 开发环境搭建
- 📝 文档改进指南

## ⚠️ 免责声明

**本项目仅供学习、研究和技术交流使用，不构成任何投资建议。**

### 🔍 学习用途
- 本工具旨在帮助用户学习量化分析方法和技术指标原理
- 提供开源代码供研究者和开发者学习算法实现
- 促进 AI 与量化投资技术的学术交流与讨论

### ⚖️ 法律声明
- **非投资建议**：本项目提供的所有分析结果、信号提示均不构成投资建议
- **风险自担**：用户基于本工具做出的任何投资决策，风险由用户自行承担
- **无收益保证**：过往表现不代表未来结果，任何投资策略都可能面临损失
- **合规使用**：用户应遵守所在地区的法律法规，本项目不承担用户违法使用的责任

### 🛡️ 技术免责
- **数据准确性**：虽然我们力求算法的准确性，但不保证数据源的完整性和实时性
- **系统稳定性**：本项目为开源软件，不保证在所有环境下的稳定运行
- **功能限制**：本工具仅为学习工具，不应用于实盘交易决策

### 📚 正确使用方式
- 将本项目作为学习量化分析的教育工具
- 用于研究技术指标的数学原理和实现方法
- 在模拟环境中测试和验证算法逻辑
- 与专业投资顾问咨询后再做实际投资决策

**使用本项目即表示您已阅读、理解并同意上述声明。如有疑问，请咨询专业的法律和投资顾问。**

## 📄 许可证

本项目采用 **GPL-3.0 许可证**，详见 [LICENSE](LICENSE) 文件。

### 🔓 开源承诺
- **完全开源**：所有代码公开透明，支持学习研究
- **自由使用**：个人学习、研究、非商业用途完全自由
- **社区保护**：任何基于本项目的衍生作品必须同样开源

### 💼 商业使用
- **开源要求**：商业使用必须遵循 GPL-3.0，保持代码开源
- **双重许可**：如需闭源商业使用，请联系项目维护者讨论商业许可
- **生态保护**：确保整个量化投资开源生态的健康发展

这种许可证选择体现了我们的核心价值：**推动行业正确发展，防止技术被滥用，建立开放透明的投资工具生态。**

## 🔗 关注作者

**Follow** [@eviljer](https://x.com/intent/follow?screen_name=eviljer) 获取更多 AI 量化投资的洞察和最新动态。