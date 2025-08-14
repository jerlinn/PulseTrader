#!/usr/bin/env python3
"""
股票数据缓存管理组件
提供SQLite数据库存储、智能缓存策略和增量更新功能
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional


class StockDataCache:
    """股票数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", db_name: str = "stock_data.db"):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
            db_name: 数据库文件名
        """
        self.cache_directory = cache_dir
        self.db_name = db_name
        
        # 创建缓存目录
        os.makedirs(self.cache_directory, exist_ok=True)
        
        # 数据库文件路径
        self.db_path = os.path.join(self.cache_directory, self.db_name)
        
        # 初始化数据库
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建股票数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                date TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 创建股票信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_data(symbol, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_data(stock_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_updated_at ON stock_data(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_info(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_info_name ON stock_info(name)')
        
        conn.commit()
        conn.close()
    
    def get_cached_data(self, symbol: str, stock_name: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从缓存中获取股票数据
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            包含股票数据的DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT date, open_price as 开盘, high_price as 最高, 
                   low_price as 最低, close_price as 收盘, volume as 成交量
            FROM stock_data 
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
        conn.close()
        
        if not df.empty:
            df['日期'] = pd.to_datetime(df['date'])
            df = df.drop('date', axis=1)
            print(f"✅ 从缓存加载 {len(df)} 条数据")
        
        return df
    
    def save_to_cache(self, symbol: str, stock_name: str, df: pd.DataFrame):
        """
        保存股票数据到缓存
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            df: 要保存的股票数据DataFrame
        """
        if df.empty:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 准备数据
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                symbol,
                stock_name,
                row['日期'].strftime('%Y%m%d'),
                float(row['开盘']),
                float(row['最高']),
                float(row['最低']),
                float(row['收盘']),
                int(row['成交量']),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # 使用REPLACE INTO来处理重复数据
        cursor.executemany('''
            REPLACE INTO stock_data 
            (symbol, stock_name, date, open_price, high_price, low_price, close_price, volume, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        conn.commit()
        conn.close()
        print(f"✅ 已缓存 {len(data_to_insert)} 条数据到数据库")
    
    def get_last_cached_date(self, symbol: str) -> Optional[str]:
        """
        获取缓存中最后一个交易日期
        
        Args:
            symbol: 股票代码
            
        Returns:
            最后缓存的日期字符串 (YYYYMMDD) 或 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(date) FROM stock_data WHERE symbol = ?
        ''', (symbol,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else None
    
    def needs_update(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        检查是否需要更新数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            (是否需要更新, 最后缓存日期)
        """
        last_date = self.get_last_cached_date(symbol)
        if not last_date:
            return True, None
        
        # 检查最后缓存日期是否为今天或最近的交易日
        last_date_obj = datetime.strptime(last_date, '%Y%m%d')
        today_obj = datetime.today()
        today_str = today_obj.strftime('%Y%m%d')
        
        # 如果缓存数据不是今天的，且今天是工作日，则需要更新
        if last_date != today_str or (today_obj.weekday() < 5 and last_date_obj.date() < today_obj.date()):
            return True, last_date
        
        return False, last_date
    
    def show_cache_status(self):
        """显示缓存数据库状态"""
        if not os.path.exists(self.db_path):
            print("📊 缓存数据库未创建")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取总记录数
            cursor.execute('SELECT COUNT(*) FROM stock_data')
            total_records = cursor.fetchone()[0]
            
            # 获取股票数量
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_data')
            stock_count = cursor.fetchone()[0]
            
            # 获取最新更新时间
            cursor.execute('SELECT MAX(updated_at) FROM stock_data')
            last_update = cursor.fetchone()[0]
            
            # 获取数据库大小
            db_size = os.path.getsize(self.db_path) / 1024 / 1024
            
            print(f"📊 缓存数据库状态:")
            print(f"   • 总记录数: {total_records:,}")
            print(f"   • 股票数量: {stock_count}")
            print(f"   • 最后更新: {last_update}")
            print(f"   • 数据库大小: {db_size:.2f} MB")
            
        except Exception as e:
            print(f"❌ 获取缓存状态失败: {e}")
        finally:
            conn.close()
    
    def get_cached_stocks(self) -> pd.DataFrame:
        """
        获取所有已缓存的股票列表
        
        Returns:
            包含股票信息的DataFrame
        """
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
            
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT symbol, stock_name, 
                   MIN(date) as earliest_date,
                   MAX(date) as latest_date,
                   COUNT(*) as record_count
            FROM stock_data 
            GROUP BY symbol, stock_name
            ORDER BY stock_name
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def clear_cache(self, symbol: str = None):
        """
        清除缓存数据
        
        Args:
            symbol: 股票代码，如果为None则清除所有数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('DELETE FROM stock_data WHERE symbol = ?', (symbol,))
            print(f"✅ 已清除股票 {symbol} 的缓存数据")
        else:
            cursor.execute('DELETE FROM stock_data')
            print("✅ 已清除所有缓存数据")
        
        conn.commit()
        conn.close()
    
    def get_cached_stock_info(self) -> pd.DataFrame:
        """
        从缓存中获取股票信息列表
        
        Returns:
            包含股票信息的DataFrame (code, name列)
        """
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
            
        conn = sqlite3.connect(self.db_path)
        query = 'SELECT code, name FROM stock_info ORDER BY code'
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def save_stock_info_to_cache(self, stock_info_df: pd.DataFrame):
        """
        保存股票信息列表到缓存
        
        Args:
            stock_info_df: 股票信息DataFrame (需包含code和name列)
        """
        if stock_info_df.empty:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 清除旧数据
        cursor.execute('DELETE FROM stock_info')
        
        # 准备数据
        data_to_insert = [
            (row['code'], row['name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            for _, row in stock_info_df.iterrows()
        ]
        
        # 批量插入
        cursor.executemany('''
            INSERT INTO stock_info (code, name, updated_at)
            VALUES (?, ?, ?)
        ''', data_to_insert)
        
        conn.commit()
        conn.close()
        print(f"✅ 已缓存 {len(data_to_insert)} 只股票信息")
    
    def is_stock_info_cache_valid(self) -> bool:
        """
        检查股票信息缓存是否有效（1天内更新的）
        
        Returns:
            True if cache is valid, False otherwise
        """
        if not os.path.exists(self.db_path):
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT MAX(updated_at) FROM stock_info')
            result = cursor.fetchone()
            
            if not result or not result[0]:
                return False
            
            # 检查是否在1天内更新
            last_update = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            return (datetime.now() - last_update).days < 1
            
        except Exception:
            return False
        finally:
            conn.close()

    def optimize_database(self):
        """优化数据库性能"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 执行VACUUM操作来压缩数据库
        cursor.execute('VACUUM')
        
        # 分析表以优化查询计划
        cursor.execute('ANALYZE')
        
        conn.commit()
        conn.close()
        print("✅ 数据库优化完成")


# 便捷函数
def create_cache_manager(cache_dir: str = "cache") -> StockDataCache:
    """
    创建股票数据缓存管理器的便捷函数
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        StockDataCache实例
    """
    return StockDataCache(cache_dir)


if __name__ == "__main__":
    # 测试缓存管理器
    cache = create_cache_manager()
    cache.show_cache_status()
    
    # 显示已缓存的股票
    cached_stocks = cache.get_cached_stocks()
    if not cached_stocks.empty:
        print("\n📈 已缓存的股票:")
        for _, stock in cached_stocks.iterrows():
            print(f"   • {stock['stock_name']} ({stock['symbol']}) - {stock['record_count']} 条记录")