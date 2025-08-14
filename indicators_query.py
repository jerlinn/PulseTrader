#!/usr/bin/env python3
"""
技术指标数据查询工具
使用方法: python indicators_query.py [股票名称]
"""

import sys
from indicators_storage import IndicatorsStorage
from datetime import datetime


def format_indicators_display(indicators_summary):
    """格式化显示技术指标数据"""
    if not indicators_summary:
        print("❌ 未找到该股票的技术指标数据")
        return
    
    print("\n" + "="*60)
    print(f"📊 {indicators_summary['stock_name']} - 技术指标数据")
    print("="*60)
    
    current = indicators_summary['current_indicators']
    print(f"📅 数据日期: {current['date']}")
    print(f"🕐 计算时间: {indicators_summary['calculation_time']}")
    
    print("\n📈 核心技术指标:")
    print(f"  • RSI14: {current['rsi14']} {'🔴 超买' if current['rsi14'] and current['rsi14'] > 70 else '🟢 超卖' if current['rsi14'] and current['rsi14'] < 30 else '⚪ 中性'}")
    print(f"  • MA10: {current['ma10']}")
    print(f"  • 趋势上轨: {current['trend_upper']}")
    print(f"  • 趋势下轨: {current['trend_lower']}")
    print(f"  • SuperTrend: {current['supertrend_value']}")
    
    trend_emoji = "🚀" if current['trend_status'] == 1 else "📉" if current['trend_status'] == -1 else "➡️"
    trend_text = "上升趋势" if current['trend_status'] == 1 else "下降趋势" if current['trend_status'] == -1 else "横盘整理"
    print(f"  • 趋势状态: {trend_emoji} {trend_text}")
    
    # 显示背离信号
    print(f"\n🚨 RSI背离信号 (近期高置信度):")
    if indicators_summary['recent_divergences']:
        for div in indicators_summary['recent_divergences']:
            div_type = "🔴 顶背离" if div['type'] == 'bearish' else "🟢 底背离"
            timeframe = {"short": "短期", "medium": "中期", "long": "长期"}.get(div['timeframe'], div['timeframe'])
            confidence_color = "🔥" if div['confidence'] >= 80 else "⚡" if div['confidence'] >= 60 else "💫"
            print(f"  • {div['date']}: {div_type} ({timeframe}) {confidence_color} {div['confidence']}%")
            print(f"    RSI变化: {div['prev_rsi']:.1f} → {div['current_rsi']:.1f}")
            print(f"    价格变化: {div['price_change']:+.1f}%")
    else:
        print("  暂无显著背离信号")
    
    # 显示趋势信号
    print(f"\n📡 趋势变化信号 (最近5个):")
    if indicators_summary['recent_trend_signals']:
        for signal in indicators_summary['recent_trend_signals']:
            signal_emoji = "🟢 BUY" if signal['signal_type'] == 'buy' else "🔴 SELL"
            print(f"  • {signal['date']}: {signal_emoji} @ ¥{signal['price']}")
    else:
        print("  暂无趋势变化信号")
    
    print("="*60)


def export_indicators_csv(stock_name):
    """导出技术指标数据为CSV"""
    storage = IndicatorsStorage()
    df = storage.export_to_dataframe(stock_name)
    
    if df is not None:
        filename = f"{stock_name}_indicators_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"📁 数据已导出至: {filename}")
        return filename
    else:
        print("❌ 无数据可导出")
        return None


def list_available_stocks():
    """列出所有有数据的股票"""
    storage = IndicatorsStorage()
    
    # 从数据库获取有技术指标数据的股票
    try:
        import sqlite3
        conn = sqlite3.connect(storage.cache.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT symbol, stock_name, 
                   MAX(date) as latest_date,
                   COUNT(*) as record_count
            FROM technical_indicators 
            GROUP BY symbol, stock_name
            ORDER BY stock_name
        ''')
        
        stocks_data = cursor.fetchall()
        conn.close()
        
        if not stocks_data:
            print("❌ 暂无股票指标数据")
            return []
        
        stocks = []
        print("\n📋 可用股票数据:")
        print("-" * 40)
        
        for symbol, stock_name, latest_date, record_count in stocks_data:
            print(f"  📊 {stock_name} ({symbol})")
            print(f"     └── 最新数据: {latest_date}")
            print(f"     └── 记录数量: {record_count}")
            stocks.append(stock_name)
        
        print("-" * 40)
        return stocks
        
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return []


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("📊 TrendSight 技术指标查询工具")
        print("\n用法:")
        print("  python indicators_query.py <股票名称>     # 查看指定股票指标")
        print("  python indicators_query.py --list        # 列出所有可用股票")
        print("  python indicators_query.py <股票名称> --export  # 导出CSV数据")
        print("\n示例:")
        print("  python indicators_query.py 杭钢股份")
        print("  python indicators_query.py 杭钢股份 --export")
        return
    
    if sys.argv[1] == '--list':
        list_available_stocks()
        return
    
    stock_name = sys.argv[1]
    storage = IndicatorsStorage()
    
    # 检查是否需要导出
    export_flag = '--export' in sys.argv
    
    # 获取指标摘要
    indicators_summary = storage.get_latest_indicators(stock_name)
    
    if indicators_summary:
        format_indicators_display(indicators_summary)
        
        if export_flag:
            print(f"\n🔄 正在导出 {stock_name} 的详细数据...")
            export_indicators_csv(stock_name)
    else:
        print(f"❌ 未找到 '{stock_name}' 的技术指标数据")
        print("\n💡 提示:")
        print(f"1. 确保股票名称正确 (如: 中国中车、杭钢股份)")
        print(f"2. 运行 TrendInsigt.py 生成该股票的技术指标数据")
        print(f"3. 使用 'python indicators_query.py --list' 查看可用股票")


if __name__ == "__main__":
    main()