import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from rsi_component import calculate_rsi, detect_rsi_divergence
from supertrend_component import calculate_supertrend, get_trend_signals
from stock_cache import StockDataCache


@dataclass
class TechnicalIndicators:
    """技术指标数据结构"""
    date: str
    rsi14: Optional[float] = None
    ma10: Optional[float] = None
    daily_change_pct: Optional[float] = None  # 日涨幅百分比
    # 统一的 SuperTrend 参数
    upper_band: Optional[float] = None  # SuperTrend 上轨
    lower_band: Optional[float] = None  # SuperTrend 下轨
    trend: Optional[int] = None  # 趋势方向：1=上涨, -1=下跌, 0=中性
    supertrend_value: Optional[float] = None  # 当前 SuperTrend 值


@dataclass
class RSIDivergence:
    """RSI背离信号数据结构"""
    date: str
    prev_date: str
    type: str  # 'bullish' or 'bearish'
    timeframe: str  # 'short', 'medium', 'long'
    rsi_change: float
    price_change: float
    confidence: float
    current_rsi: float
    prev_rsi: float
    current_price: float
    prev_price: float


@dataclass
class TrendSignal:
    """趋势信号数据结构"""
    date: str
    signal_type: str  # 'buy' or 'sell'
    price: float
    trend_value: float


class IndicatorsStorage:
    """技术指标存储管理器 - 基于SQLite数据库"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache = StockDataCache(cache_dir)
    
    def calculate_and_store_indicators(self, df: pd.DataFrame, stock_name: str, symbol: str = None) -> Dict[str, Any]:
        """计算并存储所有技术指标"""
        
        # 如果没有提供symbol，使用stock_name作为symbol
        if symbol is None:
            symbol = stock_name
        
        # 确保数据副本，避免修改原始数据
        data = df.copy()
        
        # 计算技术指标
        indicators_data = self._calculate_all_indicators(data)
        
        # 使用增强后的DataFrame（包含所有技术指标）
        enhanced_df = indicators_data['dataframe']
        
        # 计算RSI背离信号
        rsi_divergences = self._calculate_rsi_divergences(enhanced_df, indicators_data['rsi'])
        
        # 计算趋势信号（使用包含trend列的DataFrame）
        trend_signals = self._calculate_trend_signals(enhanced_df)
        
        # 存储到数据库
        self.cache.save_technical_indicators(symbol, stock_name, indicators_data['indicators'])
        self.cache.save_rsi_divergences(symbol, stock_name, rsi_divergences)
        self.cache.save_trend_signals(symbol, stock_name, trend_signals)
        
        # 存储数据
        storage_result = {
            'indicators': indicators_data,
            'rsi_divergences': rsi_divergences,
            'trend_signals': trend_signals,
            'enhanced_dataframe': enhanced_df,  # 直接包含增强后的DataFrame
            'stock_name': stock_name,
            'symbol': symbol,
            'calculation_time': datetime.now().isoformat()
        }
        
        return storage_result
    
    def _calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, List[TechnicalIndicators]]:
        """计算所有技术指标"""
        
        # 计算 SuperTrend 指标（已包含 super_trend, upper_band, lower_band, trend）
        df = calculate_supertrend(df, lookback_periods=14, multiplier=2)
        
        # 计算 RSI14 指标
        df['rsi14'] = calculate_rsi(df, period=14)
        df['rsi'] = df['rsi14']  # 添加 rsi 别名以保持向后兼容
        
        # 计算 MA10
        df['ma10'] = df['收盘'].rolling(window=10).mean()
        
        # 处理日涨幅数据：优先使用 akshare 的涨跌幅，否则计算
        if '涨跌幅' in df.columns:
            df['日涨幅'] = df['涨跌幅']  # 直接使用 akshare 的涨跌幅字段
        elif '日涨幅' not in df.columns:
            df = df.sort_values('日期').reset_index(drop=True)
            df['日涨幅'] = df['收盘'].pct_change() * 100
        
        indicators_list = []
        rsi_values = []
        
        for i, row in df.iterrows():
            date_str = row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期'])
            
            # 安全地获取列值，如果列不存在则使用默认值
            def safe_get(column, default=None):
                return row.get(column, default) if column in df.columns else default
            
            # 安全地转换数值类型（处理 Decimal 类型）
            def safe_float(value, decimal_places=2):
                if pd.isnull(value) or value is None:
                    return None
                try:
                    return round(float(value), decimal_places)
                except (ValueError, TypeError):
                    return None
            
            def safe_int(value, default=0):
                if pd.isnull(value) or value is None:
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default
            
            indicator = TechnicalIndicators(
                date=date_str,
                rsi14=safe_float(safe_get('rsi14')),
                ma10=safe_float(safe_get('ma10')),
                daily_change_pct=safe_float(safe_get('日涨幅'), 4),
                upper_band=safe_float(safe_get('upper_band')),
                lower_band=safe_float(safe_get('lower_band')),
                trend=safe_int(safe_get('trend', 0)),
                supertrend_value=safe_float(safe_get('super_trend'))
            )
            
            indicators_list.append(indicator)
            rsi_values.append(safe_get('rsi14'))
        
        return {
            'indicators': indicators_list,
            'rsi': df['rsi'],  # 使用 rsi 列（与 rsi14 相同）用于背离计算
            'dataframe': df  # 保留完整DataFrame
        }
    
    def _calculate_rsi_divergences(self, df: pd.DataFrame, rsi: pd.Series) -> List[RSIDivergence]:
        """计算RSI背离信号"""
        divergences_df = detect_rsi_divergence(df, rsi)
        
        divergences_list = []
        if not divergences_df.empty:
            for _, row in divergences_df.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                prev_date_str = row['prev_date'].strftime('%Y-%m-%d') if hasattr(row['prev_date'], 'strftime') else str(row['prev_date'])
                
                divergence = RSIDivergence(
                    date=date_str,
                    prev_date=prev_date_str,
                    type=row['type'],
                    timeframe=row['timeframe'],
                    rsi_change=round(float(row['rsi_change']), 2),
                    price_change=round(float(row['price_change']), 2),
                    confidence=round(float(row['confidence']), 2),
                    current_rsi=round(float(row['current_rsi']), 2),
                    prev_rsi=round(float(row['prev_rsi']), 2),
                    current_price=round(float(row['current_price']), 2),
                    prev_price=round(float(row['prev_price']), 2)
                )
                divergences_list.append(divergence)
        
        return divergences_list
    
    def _calculate_trend_signals(self, df: pd.DataFrame) -> List[TrendSignal]:
        """计算趋势变化信号"""
        buy_positions, sell_positions = get_trend_signals(df)
        
        signals_list = []
        
        # 添加买入信号
        for pos in buy_positions:
            if pos < len(df):
                row = df.iloc[pos]
                date_str = row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期'])
                
                signal = TrendSignal(
                    date=date_str,
                    signal_type='buy',
                    price=round(float(row['收盘']), 2),
                    trend_value=round(float(row['super_trend']), 2) if pd.notnull(row['super_trend']) else 0.0
                )
                signals_list.append(signal)
        
        # 添加卖出信号
        for pos in sell_positions:
            if pos < len(df):
                row = df.iloc[pos]
                date_str = row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期'])
                
                signal = TrendSignal(
                    date=date_str,
                    signal_type='sell',
                    price=round(float(row['收盘']), 2),
                    trend_value=round(float(row['super_trend']), 2) if pd.notnull(row['super_trend']) else 0.0
                )
                signals_list.append(signal)
        
        # 按日期排序
        signals_list.sort(key=lambda x: x.date)
        
        return signals_list
    
    def get_latest_indicators(self, stock_name: str) -> Optional[Dict[str, Any]]:
        """获取最新的技术指标摘要"""
        return self.cache.get_latest_indicators(stock_name)
    
    def export_to_dataframe(self, stock_name: str) -> Optional[pd.DataFrame]:
        """将指标数据导出为DataFrame"""
        return self.cache.get_indicators_dataframe(stock_name)


def enhance_analysis_with_indicators(df: pd.DataFrame, stock_name: str, symbol: str = None) -> Dict[str, Any]:
    """为analysis.py提供的便捷函数：计算并返回增强的指标数据"""
    storage = IndicatorsStorage()
    result = storage.calculate_and_store_indicators(df, stock_name, symbol)
    
    # 直接使用存储结果中的增强DataFrame
    enhanced_df = result['enhanced_dataframe'].copy()
    
    return {
        'enhanced_dataframe': enhanced_df,
        'indicators_summary': storage.get_latest_indicators(symbol or stock_name),
        'storage_result': result
    }