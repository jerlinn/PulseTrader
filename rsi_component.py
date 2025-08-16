import pandas as pd
import numpy as np
from typing import Tuple, List

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    使用 Wilder 平滑法计算 RSI
    """
    # 计算价格变化
    delta = data['收盘'].diff()
    
    # 分离上涨和下跌
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # 初始化平均值数组
    avg_gains = np.zeros(len(gains))
    avg_losses = np.zeros(len(losses))
    
    # 计算第一个平均值
    avg_gains[period] = gains.iloc[:period+1].mean()
    avg_losses[period] = losses.iloc[:period+1].mean()
    
    # 使用 Wilder 平滑计算后续值
    for i in range(period + 1, len(gains)):
        avg_gains[i] = ((period - 1) * avg_gains[i-1] + gains.iloc[i]) / period
        avg_losses[i] = ((period - 1) * avg_losses[i-1] + losses.iloc[i]) / period
    
    # 转换为 Series
    avg_gains = pd.Series(avg_gains, index=data.index)
    avg_losses = pd.Series(avg_losses, index=data.index)
    
    # 计算 RS 和 RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.round(1)

def find_peaks_troughs(series: pd.Series, window: int, min_distance: int) -> Tuple[List[int], List[int]]:
    """
    改进的峰谷检测算法，更适合中期背离
    """
    peaks = []
    troughs = []
    
    # 使用更灵活的窗口计算
    look_back = window // 2  # 缩小回看窗口
    look_forward = window // 3  # 前瞻窗口更小，提高实时性
    
    for i in range(look_back, len(series) - look_forward):
        # 检查最小距离
        if peaks and i - peaks[-1] < min_distance:
            continue
        if troughs and i - troughs[-1] < min_distance:
            continue
        
        # 获取局部窗口数据
        window_left = series.iloc[i-look_back:i]
        window_right = series.iloc[i+1:i+look_forward+1]
        current = series.iloc[i]
        
        # 峰值条件：比两侧的移动平均都高
        if (current > window_left.mean() * 1.001 and  # 比左侧均值高 0.1%
            current > window_right.mean() * 1.001 and  # 比右侧均值高 0.1%
            current >= series.iloc[i-1] and  # 比前一点高
            current >= series.iloc[i+1]):    # 比后一点高
            peaks.append(i)
            
        # 谷值条件：比两侧的移动平均都低
        elif (current < window_left.mean() * 0.999 and  # 比左侧均值低 0.1%
              current < window_right.mean() * 0.999 and  # 比右侧均值低 0.1%
              current <= series.iloc[i-1] and  # 比前一点低
              current <= series.iloc[i+1]):    # 比后一点低
            troughs.append(i)
    
    return peaks, troughs

def is_valid_divergence(
    price_data: pd.Series,
    rsi_data: pd.Series,
    current_idx: int,
    prev_idx: int,
    divergence_type: str,
    timeframe: str
) -> bool:
    """
    判断是否为有效背离
    增加超买/超卖区域穿越检查，确保调整充分
    """
    # 获取区间数据
    interval_price = price_data.iloc[prev_idx:current_idx+1]
    interval_rsi = rsi_data.iloc[prev_idx:current_idx+1]
    
    current_price = price_data.iloc[current_idx]
    prev_price = price_data.iloc[prev_idx]
    current_rsi = rsi_data.iloc[current_idx]
    prev_rsi = rsi_data.iloc[prev_idx]
    
    if divergence_type == 'bearish':
        # 顶背离条件
        price_condition = current_price > prev_price * 1.001  # 价格上涨超过 0.1%
        rsi_condition = current_rsi < prev_rsi * 0.99        # RSI 下降超过 1%
        rsi_range = 50 <= max(current_rsi, prev_rsi) <= 90   # RSI 区间
        
        # 关键约束：统一使用严格标准，RSI 必须进入深度超买区域（80以上）
        # 这样可以有效屏蔽短期假信号，确保调整充分
        rsi_overbought_crossed = interval_rsi.max() >= 80  # 统一要求触及深度超买线
        
        # 中期背离特殊处理
        if timeframe == 'medium':
            # 允许价格不是最高点，但必须接近最高点
            price_peak = interval_price.max()
            price_proximity = current_price >= price_peak * 0.98
            return (price_condition and rsi_condition and rsi_range and 
                   rsi_overbought_crossed and price_proximity)
        
        return (price_condition and rsi_condition and rsi_range and 
               rsi_overbought_crossed)
    
    else:  # bullish
        # 底背离条件
        price_condition = current_price < prev_price * 0.999  # 价格下跌超过 0.1%
        rsi_condition = current_rsi > prev_rsi * 1.01        # RSI 上升超过 1%
        rsi_range = 10 <= min(current_rsi, prev_rsi) <= 50   # RSI 区间
        
        # 底背离严格阈值：确保充分调整
        # 中长期要求深度超卖，短期相对宽松
        if timeframe == 'medium' or timeframe == 'long':
            rsi_oversold_crossed = interval_rsi.min() <= 20   # 中长期要求深度超卖
        else:  # short term
            rsi_oversold_crossed = interval_rsi.min() <= 30   # 短期适中阈值
        
        # 中期背离特殊处理
        if timeframe == 'medium':
            # 允许价格不是最低点，但必须接近最低点
            price_bottom = interval_price.min()
            price_proximity = current_price <= price_bottom * 1.02
            return (price_condition and rsi_condition and rsi_range and 
                   rsi_oversold_crossed and price_proximity)
        
        return (price_condition and rsi_condition and rsi_range and 
               rsi_oversold_crossed)

def calculate_rsi_divergence_confidence(
    strength: float,
    time_diff: int,
    max_time_diff: int,
    rsi_current: float,
    rsi_previous: float,
    divergence_type: str,
    timeframe: str
) -> float:
    """
    改进的置信度计算
    """
    # 调整时间权重
    time_weights = {
        'short': 0.25,    # 短期权重
        'medium': 0.3,    # 中期权重
        'long': 0.35      # 长期权重
    }
    
    # 计算时间因子（使用非线性衰减）
    time_factor = np.exp(-time_diff / max_time_diff)
    
    # RSI 区间评估
    if divergence_type == 'bearish':
        rsi_max = max(rsi_current, rsi_previous)
        rsi_factor = max(0, min((rsi_max - 55) / 30, 1))  # 55-85 区间
    else:
        rsi_min = min(rsi_current, rsi_previous)
        rsi_factor = max(0, min((45 - rsi_min) / 30, 1))  # 15-45 区间
    
    # 添加趋势强度因子
    trend_factor = min(abs(rsi_current - rsi_previous) / 30, 1)
    
    # 计算最终置信度
    confidence = (
        time_factor * time_weights[timeframe] +
        rsi_factor * 0.35 +
        trend_factor * 0.35
    ) * 100
    
    return round(confidence, 1)

def detect_rsi_divergence(price_data: pd.DataFrame, rsi: pd.Series) -> pd.DataFrame:
    """
    优化的背离检测算法
    """
    divergences = []
    
    windows = {
        'short': {'window': 20, 'min_distance': 5},
        'medium': {'window': 60, 'min_distance': 30},
        'long': {'window': 90, 'min_distance': 50}
    }
    
    for timeframe, params in windows.items():
        price_peaks, price_troughs = find_peaks_troughs(
            price_data['收盘'], 
            window=params['window'],
            min_distance=params['min_distance']
        )
        
        # 检测顶背离
        for i in range(1, len(price_peaks)):
            current_idx = price_peaks[i]
            prev_idx = price_peaks[i-1]
            
            if is_valid_divergence(
                price_data['收盘'],
                rsi,
                current_idx,
                prev_idx,
                'bearish',
                timeframe
            ):
                current_price = price_data['收盘'].iloc[current_idx]
                prev_price = price_data['收盘'].iloc[prev_idx]
                
                current_rsi = rsi.iloc[current_idx]
                prev_rsi = rsi.iloc[prev_idx]
                
                days_between = current_idx - prev_idx
                
                rsi_change = current_rsi - prev_rsi
                price_change = ((current_price - prev_price) / prev_price * 100).round(1)
                
                confidence = calculate_rsi_divergence_confidence(
                    strength=abs(rsi_change),
                    time_diff=days_between,
                    max_time_diff=params['window'] * 2,
                    rsi_current=current_rsi,
                    rsi_previous=prev_rsi,
                    divergence_type='bearish',
                    timeframe=timeframe
                )
                
                if confidence >= 30:
                    divergences.append({
                        'date': price_data['日期'].iloc[current_idx],
                        'prev_date': price_data['日期'].iloc[prev_idx],
                        'type': 'bearish',
                        'timeframe': timeframe,
                        'rsi_change': rsi_change,
                        'price_change': price_change,
                        'confidence': confidence,
                        'days_between_peaks': days_between,
                        'current_price': current_price,
                        'prev_price': prev_price,
                        'current_rsi': current_rsi,
                        'prev_rsi': prev_rsi
                    })
        
        # 检测底背离
        for i in range(1, len(price_troughs)):
            current_idx = price_troughs[i]
            prev_idx = price_troughs[i-1]
            
            if is_valid_divergence(
                price_data['收盘'],
                rsi,
                current_idx,
                prev_idx,
                'bullish',
                timeframe
            ):
                current_price = price_data['收盘'].iloc[current_idx]
                prev_price = price_data['收盘'].iloc[prev_idx]
                
                current_rsi = rsi.iloc[current_idx]
                prev_rsi = rsi.iloc[prev_idx]
                
                days_between = current_idx - prev_idx
                
                rsi_change = current_rsi - prev_rsi
                price_change = ((current_price - prev_price) / prev_price * 100).round(1)
                
                confidence = calculate_rsi_divergence_confidence(
                    strength=abs(rsi_change),
                    time_diff=days_between,
                    max_time_diff=params['window'] * 2,
                    rsi_current=current_rsi,
                    rsi_previous=prev_rsi,
                    divergence_type='bullish',
                    timeframe=timeframe
                )
                
                if confidence >= 30:
                    divergences.append({
                        'date': price_data['日期'].iloc[current_idx],
                        'prev_date': price_data['日期'].iloc[prev_idx],
                        'type': 'bullish',
                        'timeframe': timeframe,
                        'rsi_change': rsi_change,
                        'price_change': price_change,
                        'confidence': confidence,
                        'days_between_peaks': days_between,
                        'current_price': current_price,
                        'prev_price': prev_price,
                        'current_rsi': current_rsi,
                        'prev_rsi': prev_rsi
                    })
    
    if not divergences:
        return pd.DataFrame()
    
    return pd.DataFrame(divergences).sort_values('confidence', ascending=False)