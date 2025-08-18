#!/usr/bin/env python3
"""
成交量指标计算组件
实现极致缩量、放量、爆量的识别和计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class VolumeSignal:
    """成交量信号数据结构"""
    date: str
    volume: float
    signal_type: str  # 'low_vol', 'high_vol', 'sky_vol'
    vol_20d_avg: float
    vol_20d_max: float
    vol_50d_min: float
    price_condition_met: bool = False
    near_high_condition_met: bool = False


def calculate_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算极致缩量、放量、爆量指标
    
    Args:
        df: 包含股票数据的DataFrame，需要包含日期、收盘、最高、开盘、成交量列
        
    Returns:
        增强后的DataFrame，包含成交量指标
    """
    
    # 确保数据副本，避免修改原始数据
    data = df.copy()
    
    # 确保按日期排序
    data = data.sort_values('日期').reset_index(drop=True)
    
    # 计算基础成交量统计指标
    data['vol_20d_avg'] = data['成交量'].rolling(window=20, min_periods=1).mean()
    data['vol_20d_max'] = data['成交量'].rolling(window=20, min_periods=1).max()
    data['vol_50d_min'] = data['成交量'].rolling(window=50, min_periods=1).min()
    
    # 计算20日最高价（用于近期新高判断）
    data['high_20d_max'] = data['最高'].rolling(window=20, min_periods=1).max()
    
    # 计算前一日收盘价（用于涨幅计算）
    data['prev_close'] = data['收盘'].shift(1)
    
    # 条件1: 接近20日新高 (收盘价/20日最高价 > 0.9)
    data['near_20d_high'] = (data['收盘'] / data['high_20d_max']) > 0.9
    
    # 条件2: 当日成交量为20日最大
    data['is_vol_20d_max'] = data['成交量'] == data['vol_20d_max']
    
    # 条件3: 价格条件 (日涨幅>1.5% 且 盘中涨幅>2%)
    data['daily_gain_pct'] = ((data['收盘'] / data['prev_close']) - 1) * 100
    data['intraday_gain_pct'] = ((data['收盘'] / data['开盘']) - 1) * 100
    data['price_condition'] = (data['daily_gain_pct'] > 1.5) & (data['intraday_gain_pct'] > 2.0)
    
    # 放量条件
    data['is_high_vol_bar'] = (
        data['near_20d_high'] & 
        data['is_vol_20d_max'] & 
        data['price_condition']
    )
    
    # 爆量条件
    data['is_sky_vol_bar'] = (
        data['is_high_vol_bar'] & 
        (data['成交量'] > 3.5 * data['vol_20d_avg'])
    )
    
    # 极致缩量条件
    data['is_low_vol_bar'] = data['成交量'] == data['vol_50d_min']
    
    # 清理临时计算列
    columns_to_drop = ['high_20d_max', 'prev_close', 'daily_gain_pct', 'intraday_gain_pct']
    for col in columns_to_drop:
        if col in data.columns:
            data = data.drop(col, axis=1)
    
    return data


def extract_volume_signals(df: pd.DataFrame) -> List[VolumeSignal]:
    """
    提取成交量信号列表
    
    Args:
        df: 包含成交量指标的DataFrame
        
    Returns:
        成交量信号列表
    """
    signals = []
    
    for _, row in df.iterrows():
        date_str = row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期'])
        
        signal_types = []
        
        if row.get('is_low_vol_bar', False):
            signal_types.append('low_vol')
            
        if row.get('is_high_vol_bar', False):
            signal_types.append('high_vol')
            
        if row.get('is_sky_vol_bar', False):
            signal_types.append('sky_vol')
        
        # 为每种信号类型创建信号对象
        for signal_type in signal_types:
            signal = VolumeSignal(
                date=date_str,
                volume=float(row['成交量']),
                signal_type=signal_type,
                vol_20d_avg=float(row.get('vol_20d_avg', 0)),
                vol_20d_max=float(row.get('vol_20d_max', 0)),
                vol_50d_min=float(row.get('vol_50d_min', 0)),
                price_condition_met=bool(row.get('price_condition', False)),
                near_high_condition_met=bool(row.get('near_20d_high', False))
            )
            signals.append(signal)
    
    return signals


def get_volume_analysis_summary(df: pd.DataFrame) -> Dict[str, any]:
    """
    获取成交量分析摘要
    
    Args:
        df: 包含成交量指标的DataFrame
        
    Returns:
        成交量分析摘要字典
    """
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    # 统计各类成交量信号数量
    low_vol_count = df['is_low_vol_bar'].sum() if 'is_low_vol_bar' in df.columns else 0
    high_vol_count = df['is_high_vol_bar'].sum() if 'is_high_vol_bar' in df.columns else 0
    sky_vol_count = df['is_sky_vol_bar'].sum() if 'is_sky_vol_bar' in df.columns else 0
    
    # 最近的成交量信号
    recent_signals = []
    for _, row in df.tail(10).iterrows():
        date_str = row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期'])
        
        if row.get('is_low_vol_bar', False):
            recent_signals.append(f"{date_str}: 极致缩量")
        if row.get('is_high_vol_bar', False):
            recent_signals.append(f"{date_str}: 放量")
        if row.get('is_sky_vol_bar', False):
            recent_signals.append(f"{date_str}: 爆量")
    
    return {
        'latest_date': latest['日期'].strftime('%Y-%m-%d') if hasattr(latest['日期'], 'strftime') else str(latest['日期']),
        'current_volume': float(latest['成交量']),
        'vol_20d_avg': float(latest.get('vol_20d_avg', 0)),
        'vol_ratio_vs_20d_avg': float(latest['成交量'] / latest.get('vol_20d_avg', 1)) if latest.get('vol_20d_avg', 0) > 0 else 0,
        'is_current_low_vol': bool(latest.get('is_low_vol_bar', False)),
        'is_current_high_vol': bool(latest.get('is_high_vol_bar', False)),
        'is_current_sky_vol': bool(latest.get('is_sky_vol_bar', False)),
        'signal_counts': {
            'low_vol_bars': int(low_vol_count),
            'high_vol_bars': int(high_vol_count),
            'sky_vol_bars': int(sky_vol_count)
        },
        'recent_signals': recent_signals[-5:],  # 最近 5 个信号
        'volume_trend': 'increasing' if latest['成交量'] > latest.get('vol_20d_avg', 0) else 'decreasing'
    }


if __name__ == "__main__":
    # 测试函数
    print("📊 成交量指标计算组件测试")
    
    # 创建示例数据进行测试
    test_data = {
        '日期': pd.date_range('2024-01-01', periods=60, freq='D'),
        '开盘': np.random.uniform(10, 20, 60),
        '最高': np.random.uniform(15, 25, 60),
        '最低': np.random.uniform(8, 15, 60),
        '收盘': np.random.uniform(12, 22, 60),
        '成交量': np.random.uniform(1000000, 10000000, 60)
    }
    
    test_df = pd.DataFrame(test_data)
    
    # 计算成交量指标
    enhanced_df = calculate_volume_indicators(test_df)

    signals = extract_volume_signals(enhanced_df)
    
    summary = get_volume_analysis_summary(enhanced_df)
    
    print(f"✅ 计算完成，发现 {len(signals)} 个成交量信号")
    print(f"📈 摘要: {summary}")