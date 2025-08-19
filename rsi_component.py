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
    高效的滑动窗口峰谷检测算法
    
    算法原理：
    1. 使用滑动窗口扫描整个序列，每个窗口内直接找最大值/最小值
    2. 只在窗口中心区域（25%-75%位置）识别峰谷，确保真实性
    3. 通过步长优化减少重复计算，提高效率
    4. 验证邻近点关系，过滤平台型假峰值
    
    参数说明：
    - series: 价格序列（收盘价）
    - window: 观察窗口大小（短期 20，中期 60，长期 90）
    - min_distance: 峰谷间最小间隔（防止频繁震荡）
    
    返回: (peaks_indices, troughs_indices) 峰值和谷值的索引列表
    
    优势：
    - 时间复杂度: O(n×window/step) vs 传统方法 O(n×window)
    - 避免均值计算的复杂判断，直接基于极值
    - 自动去重排序，确保结果唯一性
    """
    peaks = []
    troughs = []
    n = len(series)
    
    # 步长优化：根据最小距离确定窗口移动步长
    # step = min_distance // 3 确保信号覆盖完整，避免遗漏
    step = max(1, min_distance // 3)
    
    for start in range(0, n - window + 1, step):
        end = start + window
        window_data = series.iloc[start:end]
        
        # 步骤1: 在当前窗口内找到绝对最大值和最小值
        local_max_idx = window_data.idxmax()
        local_min_idx = window_data.idxmin()
        
        # 步骤2: 转换为原始序列的全局索引位置
        global_max_idx = series.index.get_loc(local_max_idx)
        global_min_idx = series.index.get_loc(local_min_idx)
        
        # 步骤3: 定义窗口中心区域（25%-75%），避免边缘效应
        center_start = start + window // 4
        center_end = start + 3 * window // 4
        
        # 步骤4: 峰值验证与添加
        if (center_start <= global_max_idx <= center_end and  # 在中心区域
            (not peaks or global_max_idx - peaks[-1] >= min_distance)):  # 满足最小距离
            # 邻近点验证：确保是真实峰值而非平台
            if (global_max_idx > 0 and global_max_idx < n-1 and
                series.iloc[global_max_idx] >= series.iloc[global_max_idx-1] and
                series.iloc[global_max_idx] >= series.iloc[global_max_idx+1]):
                peaks.append(global_max_idx)
        
        # 步骤5: 谷值验证与添加
        if (center_start <= global_min_idx <= center_end and  # 在中心区域
            (not troughs or global_min_idx - troughs[-1] >= min_distance)):  # 满足最小距离
            # 邻近点验证：确保是真实谷值而非平台
            if (global_min_idx > 0 and global_min_idx < n-1 and
                series.iloc[global_min_idx] <= series.iloc[global_min_idx-1] and
                series.iloc[global_min_idx] <= series.iloc[global_min_idx+1]):
                troughs.append(global_min_idx)
    
    # 步骤6: 后处理 - 去重并排序，确保结果唯一性和时间顺序
    peaks = sorted(list(set(peaks)))
    troughs = sorted(list(set(troughs)))
    
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
        rsi_condition = current_rsi < prev_rsi * 0.995       # RSI 下降超过 0.5%，更灵敏
        rsi_range = 55 <= max(current_rsi, prev_rsi) <= 90   # 要求至少有一个峰值的 RSI 在 55-90 区间内，允许极端超买
        
        # 关键约束：根据时间框架调整超买阈值
        # 短期更宽松，中长期更严格
        if timeframe == 'short':
            rsi_overbought_crossed = interval_rsi.max() >= 60  # 短期宽松阈值
        else:
            rsi_overbought_crossed = interval_rsi.max() >= 65  # 中长期严格阈值
        
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
        rsi_range = 15 <= min(current_rsi, prev_rsi) <= 45   # 要求至少有一个峰值的 RSI 在 15-45 区间内，允许极端超卖
        
        # 底背离严格阈值：确保充分调整
        # 中长期要求深度超卖，短期相对宽松
        if timeframe == 'medium' or timeframe == 'long':
            rsi_oversold_crossed = interval_rsi.min() <= 30   # RSI14 标准超卖线
        else:  # short term
            rsi_oversold_crossed = interval_rsi.min() <= 35   # 短期相对宽松阈值
        
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
    优化的背离检测算法，置信度 35 (%)
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
                
                if confidence >= 35:
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
                
                if confidence >= 35:
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