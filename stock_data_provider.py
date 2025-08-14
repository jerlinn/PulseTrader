#!/usr/bin/env python3
"""
股票数据提供器组件
整合缓存管理和API数据获取，提供统一的数据接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from stock_cache import StockDataCache


class StockDataProvider:
    """股票数据提供器，整合缓存和API获取"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        初始化数据提供器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_manager = StockDataCache(cache_dir)
        self._stock_info_cache = None  # 股票信息缓存
        
        # 周期映射
        self.period_mapping = {
            '1年': 365,
            '半年': 180,
            '1季度': 90,
            '1月': 30
        }
    
    def get_stock_data(self, stock_symbol: str, stock_name: str, period: str = '1年') -> pd.DataFrame:
        """
        获取指定周期的股票数据，使用缓存策略
        
        Args:
            stock_symbol: 股票代码
            stock_name: 股票名称
            period: 时间周期 ('1年', '半年', '1季度', '1月')
            
        Returns:
            包含股票数据的DataFrame
        """
        days = self.period_mapping.get(period, 365)
        start_date = (datetime.today() - timedelta(days=days)).strftime('%Y%m%d')
        today = datetime.today().strftime('%Y%m%d')
        
        print(f"📊 获取股票数据: {stock_name} ({period})")
        
        # 检查是否需要更新数据
        need_update, last_cached_date = self.cache_manager.needs_update(stock_symbol)
        
        # 先尝试从缓存获取数据
        cached_df = self.cache_manager.get_cached_data(stock_symbol, stock_name, start_date, today)
        
        if not cached_df.empty and not need_update:
            print(f"🎯 使用缓存数据，无需更新")
            return cached_df
        
        # 需要从API获取数据
        try:
            if need_update and last_cached_date:
                # 增量更新：只获取最后缓存日期之后的数据
                df = self._incremental_update(stock_symbol, stock_name, last_cached_date, today, cached_df, start_date)
            else:
                # 全量获取数据
                df = self._full_update(stock_symbol, stock_name, start_date, today)
            
            return df
            
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            if not cached_df.empty:
                print("🔄 回退使用缓存数据")
                return cached_df
            else:
                return pd.DataFrame()
    
    def _incremental_update(self, stock_symbol: str, stock_name: str, last_cached_date: str, 
                          today: str, cached_df: pd.DataFrame, start_date: str) -> pd.DataFrame:
        """执行增量更新"""
        update_start_date = (datetime.strptime(last_cached_date, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
        print(f"🔄 增量更新数据，从 {update_start_date} 开始")
        
        new_df = ak.stock_zh_a_hist(
            symbol=stock_symbol, 
            period="daily", 
            start_date=update_start_date, 
            end_date=today, 
            adjust="qfq"
        )
        
        if not new_df.empty:
            new_df['日期'] = pd.to_datetime(new_df['日期'])
            self.cache_manager.save_to_cache(stock_symbol, stock_name, new_df)
            
            # 合并缓存数据和新数据
            if not cached_df.empty:
                df = pd.concat([cached_df, new_df], ignore_index=True)
                df = df.drop_duplicates(subset=['日期']).sort_values('日期').reset_index(drop=True)
            else:
                df = new_df
        else:
            print("⚠️ 没有新数据需要更新")
            df = cached_df
        
        # 过滤到指定周期的数据
        if not df.empty:
            df = df[df['日期'] >= pd.to_datetime(start_date)].reset_index(drop=True)
        
        return df
    
    def _full_update(self, stock_symbol: str, stock_name: str, start_date: str, today: str) -> pd.DataFrame:
        """执行全量更新"""
        print(f"📥 全量获取数据")
        df = ak.stock_zh_a_hist(
            symbol=stock_symbol, 
            period="daily", 
            start_date=start_date, 
            end_date=today, 
            adjust="qfq"
        )
        
        if not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            self.cache_manager.save_to_cache(stock_symbol, stock_name, df)
        
        return df
    
    def get_stock_info(self) -> pd.DataFrame:
        """获取股票信息列表，使用缓存"""
        if self._stock_info_cache is None:
            # 首先检查数据库缓存
            if self.cache_manager.is_stock_info_cache_valid():
                print("📋 从缓存加载股票信息列表...")
                self._stock_info_cache = self.cache_manager.get_cached_stock_info()
            else:
                print("📋 从网络获取股票信息列表...")
                self._stock_info_cache = ak.stock_info_a_code_name()
                # 保存到缓存
                self.cache_manager.save_stock_info_to_cache(self._stock_info_cache)
                
        return self._stock_info_cache
    
    def get_stock_symbol(self, stock_info: pd.DataFrame, stock_name: str) -> str:
        """
        根据股票名称获取股票代码
        
        Args:
            stock_info: 股票信息DataFrame
            stock_name: 股票名称
            
        Returns:
            股票代码
            
        Raises:
            ValueError: 如果未找到股票
        """
        matching_stocks = stock_info[stock_info['name'] == stock_name]
        if matching_stocks.empty:
            raise ValueError(f"未找到股票: {stock_name}")
        return matching_stocks['code'].iloc[0]
    
    def show_cache_status(self):
        """显示缓存状态"""
        self.cache_manager.show_cache_status()
    
    def get_cached_stocks(self) -> pd.DataFrame:
        """获取已缓存的股票列表"""
        return self.cache_manager.get_cached_stocks()
    
    def clear_cache(self, symbol: str = None):
        """清除缓存数据"""
        self.cache_manager.clear_cache(symbol)
    
    def optimize_cache(self):
        """优化缓存数据库"""
        self.cache_manager.optimize_database()


# 便捷函数
def create_data_provider(cache_dir: str = "cache") -> StockDataProvider:
    """
    创建股票数据提供器的便捷函数
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        StockDataProvider实例
    """
    return StockDataProvider(cache_dir)


if __name__ == "__main__":
    # 测试数据提供器
    provider = create_data_provider()
    provider.show_cache_status()
    
    # 测试获取股票数据
    try:
        stock_info = provider.get_stock_info()
        symbol = provider.get_stock_symbol(stock_info, "中国中车")
        
        print(f"\n🔍 测试获取中国中车数据 (代码: {symbol})")
        df = provider.get_stock_data(symbol, "中国中车", "1月")
        
        if not df.empty:
            print(f"✅ 获取到 {len(df)} 条数据")
            print(f"日期范围: {df['日期'].min()} 到 {df['日期'].max()}")
        else:
            print("❌ 未获取到数据")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")