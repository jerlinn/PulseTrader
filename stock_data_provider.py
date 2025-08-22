#!/usr/bin/env python3
"""
股票数据提供器组件
整合缓存管理和 API 数据获取，提供统一的数据接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
from stock_cache import StockDataCache


class StockDataProvider:
    """股票数据提供器，整合缓存和 API 获取，支持 A 股和港股"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        初始化数据提供器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_manager = StockDataCache(cache_dir)
        self._stock_info_cache = None  # A股信息缓存
        self._hk_stock_info_cache = None  # 港股信息缓存
        self._trading_calendar_cache = None  # 交易日历缓存
        
        self.period_mapping = {
            '1年': 365,
            '半年': 180,
            '1季度': 90,
            '1月': 30
        }
        
        self._init_trading_calendar()
    
    def detect_market_type(self, symbol: str) -> str:
        """
        根据股票代码自动检测市场类型
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场类型: 'a' (A股) 或 'hk' (港股)
            
        Raises:
            ValueError: 无法识别的股票代码格式
        """
        symbol = symbol.strip()
        
        # 港股代码：5位数字，通常以0开头
        if len(symbol) == 5 and symbol.isdigit() and symbol.startswith('0'):
            return 'hk'
        # A股代码：6位数字
        elif len(symbol) == 6 and symbol.isdigit():
            return 'a'
        else:
            raise ValueError(f"无法识别市场类型，股票代码格式不正确: {symbol}")
    
    def get_stock_data(self, stock_symbol: str, stock_name: str, period: str = '1年') -> pd.DataFrame:
        """
        获取指定周期的股票数据，使用缓存策略
        
        Args:
            stock_symbol: 股票代码
            stock_name: 股票名称
            period: 时间周期 ('1年', '半年', '1季度', '1月')
            
        Returns:
            包含股票数据的 DataFrame
        """
        days = self.period_mapping.get(period, 365)
        start_date = (datetime.today() - timedelta(days=days)).strftime('%Y%m%d')
        
        # 检测市场类型
        market_type = self.detect_market_type(stock_symbol)
        market_name = '港股' if market_type == 'hk' else 'A股'
        
        # 获取最近的交易日作为结束日期，而不是今天
        today_str = datetime.today().strftime('%Y-%m-%d')
        last_trading_day = self.get_last_trading_day(today_str)
        
        if last_trading_day:
            end_date = last_trading_day.replace('-', '')  # 转换为YYYYMMDD格式
            print(f"📊 获取{market_name}数据: {stock_name} ({period}) 至 {last_trading_day}")
        else:
            # 如果无法获取交易日历，回退到使用今天
            end_date = datetime.today().strftime('%Y%m%d')
            print(f"📊 获取{market_name}数据: {stock_name} ({period}) - 无交易日历，使用今日")
        
        # 检查是否需要更新数据（基于交易日历）
        need_update, last_cached_date = self._needs_update_with_trading_calendar(stock_symbol)
        
        # 先尝试从缓存获取数据
        cached_df = self.cache_manager.get_cached_data(stock_symbol, stock_name, start_date, end_date, market_type)
        
        if not cached_df.empty and not need_update:
            # 检查今天是否为交易日，如果不是，提供更友好的提示
            if not self.is_trading_day(today_str):
                print(f"📅 今日非交易日，使用最新交易日数据 ({last_trading_day})")
            else:
                print(f"🎯 使用缓存数据，无需更新")
            return cached_df
        
        # 需要从 API 获取数据
        try:
            if need_update and last_cached_date:
                # 增量更新：只获取最后缓存日期之后的数据
                df = self._incremental_update(stock_symbol, stock_name, last_cached_date, end_date, cached_df, start_date, market_type)
            else:
                # 全量获取数据
                df = self._full_update(stock_symbol, stock_name, start_date, end_date, market_type)
            
            return df
            
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            if not cached_df.empty:
                print("🔄 回退使用缓存数据")
                return cached_df
            else:
                return pd.DataFrame()
    
    def _get_stock_data_by_market(self, symbol: str, start_date: str, end_date: str, market_type: str) -> pd.DataFrame:
        """
        根据市场类型获取股票数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            market_type: 市场类型 ('a' 或 'hk')
            
        Returns:
            股票数据 DataFrame
        """
        if market_type == 'hk':
            df = ak.stock_hk_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            # 为港股数据添加股票代码字段以保持一致性
            if not df.empty:
                df['股票代码'] = symbol
        else:  # A股
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
        
        return df
    
    def _incremental_update(self, stock_symbol: str, stock_name: str, last_cached_date: str, 
                          end_date: str, cached_df: pd.DataFrame, start_date: str, market_type: str) -> pd.DataFrame:
        """执行增量更新"""
        update_start_date = (datetime.strptime(last_cached_date, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
        print(f"🔄 增量更新数据，从 {update_start_date} 到 {end_date}")
        
        new_df = self._get_stock_data_by_market(stock_symbol, update_start_date, end_date, market_type)
        
        if not new_df.empty:
            new_df['日期'] = pd.to_datetime(new_df['日期'])
            self.cache_manager.save_to_cache(stock_symbol, stock_name, new_df, market_type)
            
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
    
    def _full_update(self, stock_symbol: str, stock_name: str, start_date: str, end_date: str, market_type: str) -> pd.DataFrame:
        """执行全量更新"""
        print(f"📥 全量获取数据，从 {start_date} 到 {end_date}")
        df = self._get_stock_data_by_market(stock_symbol, start_date, end_date, market_type)
        
        if not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            self.cache_manager.save_to_cache(stock_symbol, stock_name, df, market_type)
        
        return df
    
    def get_stock_info(self, market_type: str = 'a') -> pd.DataFrame:
        """
        获取股票信息列表，使用缓存
        
        Args:
            market_type: 市场类型 ('a' 或 'hk')
            
        Returns:
            股票信息 DataFrame
        """
        if market_type == 'hk':
            if self._hk_stock_info_cache is None:
                # 首先检查数据库缓存
                if self.cache_manager.is_stock_info_cache_valid('hk'):
                    print("从缓存加载港股信息列表...")
                    self._hk_stock_info_cache = self.cache_manager.get_cached_stock_info('hk')
                else:
                    print("📋 从网络获取港股信息列表...")
                    self._hk_stock_info_cache = ak.stock_hk_spot_em()
                    # 重命名列以保持一致性
                    if not self._hk_stock_info_cache.empty:
                        # 根据实际返回的列名进行映射
                        column_mapping = {'代码': 'code', '名称': 'name'}
                        available_columns = self._hk_stock_info_cache.columns
                        
                        # 找到包含代码和名称的列
                        code_col = None
                        name_col = None
                        for col in available_columns:
                            if '代码' in col or 'code' in col.lower():
                                code_col = col
                            elif '名称' in col or 'name' in col.lower():
                                name_col = col
                        
                        if code_col and name_col:
                            self._hk_stock_info_cache = self._hk_stock_info_cache[[code_col, name_col]]
                            self._hk_stock_info_cache.columns = ['code', 'name']
                        else:
                            print("⚠️ 港股数据列格式不符合预期，使用原始格式")
                    
                    # 保存到缓存
                    self.cache_manager.save_stock_info_to_cache(self._hk_stock_info_cache, 'hk')
                    
            return self._hk_stock_info_cache
        else:
            if self._stock_info_cache is None:
                # 首先检查数据库缓存
                if self.cache_manager.is_stock_info_cache_valid('a'):
                    print("从缓存加载 A 股信息列表...")
                    self._stock_info_cache = self.cache_manager.get_cached_stock_info('a')
                else:
                    print("从网络获取 A 股信息列表...")
                    self._stock_info_cache = ak.stock_info_a_code_name()
                    # 保存到缓存
                    self.cache_manager.save_stock_info_to_cache(self._stock_info_cache, 'a')
                    
            return self._stock_info_cache
    
    def get_stock_symbol(self, stock_name: str, market_type: str = None) -> tuple[str, str]:
        """
        根据股票名称获取股票代码，支持多市场搜索
        
        Args:
            stock_name: 股票名称
            market_type: 指定市场类型 ('a', 'hk' 或 None 表示自动搜索)
            
        Returns:
            (股票代码, 市场类型) 元组
            
        Raises:
            ValueError: 如果未找到股票
        """
        # 如果指定了市场类型，只在该市场搜索
        if market_type:
            stock_info = self.get_stock_info(market_type)
            result = self._search_in_market(stock_info, stock_name, market_type)
            if result:
                return result, market_type
        else:
            # 自动搜索，优先A股，再港股
            for mt in ['a', 'hk']:
                try:
                    stock_info = self.get_stock_info(mt)
                    result = self._search_in_market(stock_info, stock_name, mt)
                    if result:
                        market_name = 'A股' if mt == 'a' else '港股'
                        print(f"在 {market_name} 找到: {stock_name} ({result})")
                        return result, mt
                except Exception as e:
                    print(f"⚠️ 搜索{mt}市场时出错: {e}")
                    continue
        
        raise ValueError(f"未找到股票: {stock_name}")
    
    def _search_in_market(self, stock_info: pd.DataFrame, stock_name: str, market_type: str) -> Optional[str]:
        """
        在指定市场中搜索股票
        
        Args:
            stock_info: 股票信息 DataFrame
            stock_name: 股票名称
            market_type: 市场类型
            
        Returns:
            股票代码或None
        """
        if stock_info.empty:
            return None
            
        # 首先尝试精确匹配
        matching_stocks = stock_info[stock_info['name'] == stock_name]
        if not matching_stocks.empty:
            return matching_stocks['code'].iloc[0]
        
        # 对于A股，处理 XD 前缀情况
        if market_type == 'a' and len(stock_name) >= 3:
            xd_name = 'XD' + stock_name[:3]
            xd_matches = stock_info[stock_info['name'] == xd_name]
            if not xd_matches.empty:
                print(f"XD 前缀匹配: {stock_name} → {xd_name} ({xd_matches.iloc[0]['code']})")
                return xd_matches.iloc[0]['code']
        
        # 尝试部分匹配
        partial_matches = stock_info[stock_info['name'].str.contains(stock_name, na=False, regex=False)]
        if not partial_matches.empty:
            print(f"部分匹配找到 {len(partial_matches)} 个结果，使用第一个: {partial_matches.iloc[0]['name']}")
            return partial_matches.iloc[0]['code']
        
        return None
    
    def show_cache_status(self):
        """显示缓存状态"""
        self.cache_manager.show_cache_status()
    
    def get_cached_stocks(self) -> pd.DataFrame:
        """获取已缓存的股票列表"""
        return self.cache_manager.get_cached_stocks()
    
    def clear_cache(self, symbol: str = None):
        """清除缓存数据"""
        self.cache_manager.clear_cache(symbol)
    
    def _init_trading_calendar(self):
        """初始化交易日历"""
        try:
            # 检查交易日历缓存是否有效
            if not self.cache_manager.is_trading_calendar_cache_valid():
                print("🗓️ 更新交易日历数据...")
                trading_dates = ak.tool_trade_date_hist_sina()
                self.cache_manager.save_trading_calendar(trading_dates)
                print("✅ 交易日历数据更新完成")
            else:
                print("📅 交易日历缓存有效，无需更新")
        except Exception as e:
            print(f"⚠️ 交易日历初始化失败: {e}")
    
    def is_trading_day(self, date_str: str) -> bool:
        """检查指定日期是否为交易日"""
        return self.cache_manager.is_trading_day(date_str)
    
    def get_last_trading_day(self, before_date: str = None) -> Optional[str]:
        """获取最近的交易日"""
        return self.cache_manager.get_last_trading_day(before_date)
    
    def _needs_update_with_trading_calendar(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        检查是否需要更新数据（基于交易日历）
        
        Args:
            symbol: 股票代码
            
        Returns:
            (是否需要更新, 最后缓存日期)
        """
        last_date = self.cache_manager.get_last_cached_date(symbol)
        if not last_date:
            return True, None
        
        # 获取最近的交易日
        today_str = datetime.today().strftime('%Y-%m-%d')
        last_trading_day = self.get_last_trading_day(today_str)
        
        if not last_trading_day:
            # 如果无法获取交易日历，回退到原逻辑
            today_obj = datetime.today()
            if today_obj.weekday() < 5:  # 工作日
                last_date_obj = datetime.strptime(last_date, '%Y%m%d')
                return last_date_obj.date() < today_obj.date(), last_date
            return False, last_date
        
        # 转换最近交易日格式
        last_trading_day_formatted = last_trading_day.replace('-', '')
        
        # 如果缓存的最后日期早于最近交易日，则需要更新
        return last_date < last_trading_day_formatted, last_date
    
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
        symbol, market_type = provider.get_stock_symbol("中国中车")
        market_name = 'A股' if market_type == 'a' else '港股'
        
        print(f"\n测试获取中国中车数据 ({market_name}代码: {symbol})")
        df = provider.get_stock_data(symbol, "中国中车", "1月")
        
        if not df.empty:
            print(f"✅ 获取到 {len(df)} 条数据")
            print(f"日期范围: {df['日期'].min()} 到 {df['日期'].max()}")
        else:
            print("❌ 未获取到数据")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")