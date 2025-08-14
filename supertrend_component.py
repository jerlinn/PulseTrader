from stock_indicators import indicators, Quote
from typing import List
import pandas as pd

def calculate_supertrend(df: pd.DataFrame, lookback_periods: int = 14, multiplier: float = 2) -> pd.DataFrame:
    """
    计算超级趋势指标
    
    Parameters:
    df: 包含股票数据的DataFrame，需要包含'日期', '开盘', '最高', '最低', '收盘', '成交量'列
    lookback_periods: 回看周期，默认14
    multiplier: 乘数，默认2
    
    Returns:
    添加了SuperTrend相关列的DataFrame
    """
    # 创建 Quote 实例
    formatted_dates = df['日期'].tolist()
    quotes = [
        Quote(date, open, high, low, close, volume) 
        for date, open, high, low, close, volume 
        in zip(formatted_dates, df['开盘'], df['最高'], df['最低'], df['收盘'], df['成交量'])
    ]

    # 计算 SuperTrend 指标
    results = indicators.get_super_trend(quotes, lookback_periods=lookback_periods, multiplier=multiplier)

    # 创建新的DataFrame副本以避免修改原始数据
    df_result = df.copy()
    
    # 将结果添加到 DataFrame
    df_result['super_trend'] = [result.super_trend for result in results]
    df_result['upper_band'] = [result.upper_band for result in results]
    df_result['lower_band'] = [result.lower_band for result in results]

    # 确定趋势方向，处理 None 值
    df_result['trend'] = df_result.apply(
        lambda row: 1 if (row['收盘'] is not None and row['super_trend'] is not None and row['收盘'] > row['super_trend']) 
        else (-1 if (row['收盘'] is not None and row['super_trend'] is not None and row['收盘'] < row['super_trend']) 
        else 0), axis=1
    )
    
    return df_result

def get_trend_signals(df: pd.DataFrame) -> tuple:
    """
    获取趋势变化信号
    
    Parameters:
    df: 包含trend列的DataFrame
    
    Returns:
    tuple: (buy_positions, sell_positions) - 买入和卖出信号的索引位置
    """
    # 计算趋势变化点
    df['trend_shifted'] = df['trend'].shift(1)
    b_positions = df[(df['trend'] == 1) & (df['trend_shifted'] != 1)].index
    s_positions = df[(df['trend'] == -1) & (df['trend_shifted'] != -1)].index
    
    return b_positions, s_positions

def analyze_trend_performance(df: pd.DataFrame) -> dict:
    """
    分析趋势表现
    
    Parameters:
    df: 包含SuperTrend数据的DataFrame
    
    Returns:
    dict: 包含趋势分析结果的字典
    """
    if df.empty:
        return {}
    
    # 获取信号位置
    b_positions, s_positions = get_trend_signals(df)
    
    # 计算基本统计
    total_days = len(df)
    uptrend_days = len(df[df['trend'] == 1])
    downtrend_days = len(df[df['trend'] == -1])
    neutral_days = len(df[df['trend'] == 0])
    
    # 计算趋势持续时间
    trend_changes = df['trend'].diff().fillna(0)
    trend_periods = []
    current_trend_length = 1
    
    for i in range(1, len(df)):
        if trend_changes.iloc[i] == 0:  # 趋势未变化
            current_trend_length += 1
        else:  # 趋势变化
            trend_periods.append(current_trend_length)
            current_trend_length = 1
    trend_periods.append(current_trend_length)  # 添加最后一个周期
    
    # 计算收益率（如果有足够的信号）
    returns = []
    if len(b_positions) > 0 and len(s_positions) > 0:
        # 简化收益计算：只考虑完整的买卖周期
        min_signals = min(len(b_positions), len(s_positions))
        for i in range(min_signals):
            if i < len(b_positions) and i < len(s_positions):
                buy_price = df.loc[b_positions[i], '收盘']
                sell_price = df.loc[s_positions[i], '收盘']
                if buy_price and sell_price:
                    ret = (sell_price - buy_price) / buy_price * 100
                    returns.append(ret)
    
    analysis = {
        'total_days': total_days,
        'uptrend_days': uptrend_days,
        'downtrend_days': downtrend_days,
        'neutral_days': neutral_days,
        'uptrend_percentage': round(uptrend_days / total_days * 100, 2) if total_days > 0 else 0,
        'downtrend_percentage': round(downtrend_days / total_days * 100, 2) if total_days > 0 else 0,
        'buy_signals': len(b_positions),
        'sell_signals': len(s_positions),
        'avg_trend_duration': round(sum(trend_periods) / len(trend_periods), 1) if trend_periods else 0,
        'max_trend_duration': max(trend_periods) if trend_periods else 0,
        'min_trend_duration': min(trend_periods) if trend_periods else 0,
        'returns': returns,
        'avg_return': round(sum(returns) / len(returns), 2) if returns else 0,
        'total_return': round(sum(returns), 2) if returns else 0,
        'win_rate': round(len([r for r in returns if r > 0]) / len(returns) * 100, 2) if returns else 0
    }
    
    return analysis