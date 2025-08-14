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
        
        # 创建技术指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                date TEXT NOT NULL,
                rsi14 REAL,
                ma10 REAL,
                trend INTEGER DEFAULT 0,
                upper_band REAL,
                lower_band REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 创建RSI背离信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rsi_divergences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                date TEXT NOT NULL,
                prev_date TEXT NOT NULL,
                type TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                rsi_change REAL NOT NULL,
                price_change REAL NOT NULL,
                confidence REAL NOT NULL,
                current_rsi REAL NOT NULL,
                prev_rsi REAL NOT NULL,
                current_price REAL NOT NULL,
                prev_price REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建趋势信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trend_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                date TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                trend_value REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_data(symbol, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_data(stock_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_updated_at ON stock_data(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_info(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_info_name ON stock_info(name)')
        
        # 技术指标表索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_symbol_date ON technical_indicators(symbol, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_stock_name ON technical_indicators(stock_name)')
        
        # RSI背离表索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergences_symbol ON rsi_divergences(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergences_date ON rsi_divergences(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergences_confidence ON rsi_divergences(confidence)')
        
        # 趋势信号表索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol_date ON trend_signals(symbol, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_type ON trend_signals(signal_type)')
        
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

    def save_technical_indicators(self, symbol: str, stock_name: str, indicators_data: list):
        """
        保存技术指标数据到数据库
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            indicators_data: 技术指标数据列表
        """
        if not indicators_data:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 准备数据
        data_to_insert = []
        for indicator in indicators_data:
            data_to_insert.append((
                symbol,
                stock_name,
                indicator.date,
                indicator.rsi14,
                indicator.ma10,
                indicator.trend,
                indicator.upper_band,
                indicator.lower_band,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # 使用REPLACE INTO处理重复数据
        cursor.executemany('''
            REPLACE INTO technical_indicators 
            (symbol, stock_name, date, rsi14, ma10, trend, upper_band, lower_band, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        conn.commit()
        conn.close()
        print(f"✅ 已保存 {len(data_to_insert)} 条技术指标数据")
    
    def save_rsi_divergences(self, symbol: str, stock_name: str, divergences_data: list):
        """
        保存RSI背离信号到数据库
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称  
            divergences_data: RSI背离数据列表
        """
        if not divergences_data:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先删除该股票的旧背离数据（避免重复）
        cursor.execute('DELETE FROM rsi_divergences WHERE symbol = ?', (symbol,))
        
        # 准备数据
        data_to_insert = []
        for div in divergences_data:
            data_to_insert.append((
                symbol, stock_name, div.date, div.prev_date, div.type, div.timeframe,
                div.rsi_change, div.price_change, div.confidence, div.current_rsi, div.prev_rsi,
                div.current_price, div.prev_price, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        cursor.executemany('''
            INSERT INTO rsi_divergences 
            (symbol, stock_name, date, prev_date, type, timeframe, rsi_change, price_change, 
             confidence, current_rsi, prev_rsi, current_price, prev_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        conn.commit()
        conn.close()
        print(f"✅ 已保存 {len(data_to_insert)} 条RSI背离信号")
    
    def save_trend_signals(self, symbol: str, stock_name: str, signals_data: list):
        """
        保存趋势信号到数据库
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            signals_data: 趋势信号数据列表
        """
        if not signals_data:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先删除该股票的旧信号数据
        cursor.execute('DELETE FROM trend_signals WHERE symbol = ?', (symbol,))
        
        # 准备数据
        data_to_insert = []
        for signal in signals_data:
            data_to_insert.append((
                symbol, stock_name, signal.date, signal.signal_type, 
                signal.price, signal.trend_value, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        cursor.executemany('''
            INSERT INTO trend_signals 
            (symbol, stock_name, date, signal_type, price, trend_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        conn.commit()
        conn.close()
        print(f"✅ 已保存 {len(data_to_insert)} 条趋势信号")
    
    def get_latest_indicators(self, symbol: str) -> dict:
        """
        获取最新的技术指标摘要
        
        Args:
            symbol: 股票代码
            
        Returns:
            技术指标摘要字典
        """
        conn = sqlite3.connect(self.db_path)
        
        # 获取最新指标数据
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM technical_indicators 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT 1
        ''', (symbol,))
        
        latest_indicator = cursor.fetchone()
        # 在查询后立即获取列描述
        indicator_cols = [desc[0] for desc in cursor.description] if cursor.description else []
        
        if not latest_indicator:
            conn.close()
            return None
        
        # 获取高置信度背离信号
        cursor.execute('''
            SELECT * FROM rsi_divergences 
            WHERE symbol = ? AND confidence >= 50 
            ORDER BY date DESC, confidence DESC 
            LIMIT 3
        ''', (symbol,))
        
        divergences = cursor.fetchall()
        
        # 获取最近的趋势信号
        cursor.execute('''
            SELECT * FROM trend_signals 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT 5
        ''', (symbol,))
        
        trend_signals = cursor.fetchall()
        
        conn.close()
        
        # 构建返回数据 - 使用正确的列描述
        latest_data = dict(zip(indicator_cols, latest_indicator)) if latest_indicator else None
        
        return {
            'stock_name': latest_data['stock_name'] if latest_data else None,
            'latest_date': latest_data['date'] if latest_data else None,
            'calculation_time': latest_data['updated_at'] if latest_data else None,
            'current_indicators': latest_data,
            'recent_divergences': [dict(zip([
                'symbol', 'stock_name', 'date', 'prev_date', 'type', 'timeframe',
                'rsi_change', 'price_change', 'confidence', 'current_rsi', 'prev_rsi',
                'current_price', 'prev_price', 'created_at'
            ], div)) for div in divergences],
            'recent_trend_signals': [dict(zip([
                'id', 'symbol', 'stock_name', 'date', 'signal_type', 'price', 'trend_value', 'created_at'
            ], signal)) for signal in trend_signals]
        }
    
    def get_indicators_dataframe(self, symbol: str) -> pd.DataFrame:
        """
        获取技术指标数据的DataFrame
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含技术指标的DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT date, rsi14, ma10, upper_band, lower_band, trend
            FROM technical_indicators 
            WHERE symbol = ? 
            ORDER BY date ASC
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
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