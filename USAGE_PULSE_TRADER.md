# PulseTrader All-in-One 使用指南

## 概述

`pulse_trader.py` 是一个集成了技术分析和 AI 智能分析的 all-in-one 脚本，整合了 `TrendInsigt` 和 `analysis` 两个独立组件。

## 特性

- ✅ 保持原有组件独立性
- ✅ 优化变量传递，避免冗余定义
- ✅ 灵活的用户交互流程
- ✅ 支持交互式和命令行模式

## 使用方法

### 1. 交互式模式（推荐）

```bash
python pulse_trader.py
```

或者强制使用交互式模式：

```bash
python pulse_trader.py --interactive
```

**流程：**
1. 输入股票名称（回车默认"杭钢股份"）
2. 系统进行技术分析并生成图表
3. 询问是否需要 AI 分析
4. 如选择是，则进行 AI 分析并生成报告

### 2. 命令行模式

#### 完整分析（技术分析 + AI 分析）
```bash
python pulse_trader.py --stock "股票名称"
```

#### 仅技术分析
```bash
python pulse_trader.py --stock "股票名称" --no-ai
```

## 命令行参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--stock STOCK` | `-s` | 指定要分析的股票名称 |
| `--no-ai` | - | 仅进行技术分析，跳过 AI 分析 |
| `--interactive` | `-i` | 强制使用交互模式 |
| `--help` | `-h` | 显示帮助信息 |

## 输出文件

### 技术分析
- **图表文件**: `figures/{股票名称}_PulseTrader_{日期}.png`
- **技术指标**: 存储在 SQLite 数据库中

### AI 分析
- **分析报告**: `reports/{股票名称}_分析报告_{时间戳}.md`

## 示例

### 分析杭钢股份（完整流程）
```bash
python pulse_trader.py --stock "杭钢股份"
```

### 快速技术分析东方电气
```bash
python pulse_trader.py --stock "东方电气" --no-ai
```

### 交互式分析多个股票
```bash
python pulse_trader.py --interactive
```

## 架构说明

### 组件独立性
- `TrendInsigt.py`: 技术分析组件，负责数据获取、指标计算、图表生成
- `analysis.py`: AI 分析组件，负责智能分析和报告生成
- `pulse_trader.py`: 集成管理器，协调两个组件的工作流程

### 变量传递优化
- 移除了 `analysis.py` 中的硬编码图表路径
- 通过函数参数动态传递股票名称和图表路径
- 避免了组件间的直接依赖和数据冗余

### 工作流程
```
1. 用户输入股票名称
   ↓
2. 技术分析（TrendInsigt）
   ↓ 
3. 生成图表和技术指标
   ↓
4. 用户确认是否需要 AI 分析
   ↓ (如果是)
5. AI 分析（analysis）
   ↓
6. 生成智能分析报告
```

## 注意事项

1. **环境要求**: 确保设置了 `AIHUBMIX_API_KEY` 环境变量用于 AI 分析
2. **网络连接**: AI 分析需要稳定的网络连接
3. **数据缓存**: 系统会自动管理股票数据缓存，提高后续分析速度
4. **目录结构**: 脚本会自动创建 `figures/` 和 `reports/` 目录

## 故障排除

### 技术分析失败
- 检查股票名称是否正确
- 确认数据源连接正常

### AI 分析失败
- 检查 `AIHUBMIX_API_KEY` 环境变量
- 确认网络连接稳定
- 检查图表文件是否存在

### 系统初始化失败
- 检查数据源配置
- 确认相关依赖包已安装