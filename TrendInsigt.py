from datetime import datetime
import pandas as pd
from stock_data_provider import create_data_provider
from plotting_component import create_stock_chart
from indicators_storage import enhance_analysis_with_indicators
import os

# 以量价关系为主要量化依据
# 基础的超级趋势判断
# 合适的相对强度背离阈值，过滤大量假信号——顶背离80，底背离中长期20/短期30
# 对数坐标系，良好的可读性

today = datetime.today().strftime('%Y%m%d')
output_directory = "figures"

# 创建输出目录（如果不存在）
os.makedirs(output_directory, exist_ok=True)

# 创建数据提供器实例
data_provider = create_data_provider()


def analyze_stock(stock_name, period='1年'):
    """分析指定股票"""
    print(f"正在分析股票: {stock_name} ({period})")
    
    # 获取股票代码（只在首次调用时获取股票信息）
    try:
        stock_info = data_provider.get_stock_info()
        stock_symbol = data_provider.get_stock_symbol(stock_info, stock_name)
        symbol = stock_symbol
    except ValueError as e:
        print(f"错误: {e}")
        print("请检查股票名称是否正确")
        return None 
    except Exception as e:
        print(f"获取股票信息失败: {e}")
        return None

    # 获取股票数据
    df = data_provider.get_stock_data(symbol, stock_name, period)
    
    if df.empty:
        print("❌ 无法获取股票数据")
        return None

    # 计算并存储技术指标
    enhanced_result = enhance_analysis_with_indicators(df, stock_name, symbol)
    
    # 使用增强后的数据框
    enhanced_df = enhanced_result['enhanced_dataframe']
    indicators_summary = enhanced_result['indicators_summary']
    
    # 从存储结果中获取背离数据
    divergences_list = enhanced_result['storage_result']['rsi_divergences']
    
    # 转换背离数据为DataFrame格式以兼容绘图函数
    if divergences_list:
        divergences_data = []
        for div in divergences_list:
            divergences_data.append({
                'date': pd.to_datetime(div.date),
                'prev_date': pd.to_datetime(div.prev_date),
                'type': div.type,
                'timeframe': div.timeframe,
                'rsi_change': div.rsi_change,
                'price_change': div.price_change,
                'confidence': div.confidence,
                'current_price': div.current_price,
                'prev_price': div.prev_price,
                'current_rsi': div.current_rsi,
                'prev_rsi': div.prev_rsi
            })
        divergences = pd.DataFrame(divergences_data).sort_values('confidence', ascending=False)
    else:
        divergences = pd.DataFrame()

    # 创建图表并显示
    fig = create_stock_chart(enhanced_df, stock_name, divergences, today)
    fig.show()
    
    # 打印技术指标摘要
    if indicators_summary:
        current = indicators_summary['current_indicators']
        
        # 格式化趋势状态
        trend_status = "上升" if current['trend'] == 1 else "下降" if current['trend'] == -1 else "中性"
        
        # 格式化趋势上下轨
        upper_band = current['upper_band'] if current['upper_band'] is not None else "None"
        lower_band = current['lower_band'] if current['lower_band'] is not None else "None"
        
        print(f"\n📊 {stock_name} · {current['date']} 技术指标：")
        print(f"RSI14: {current['rsi14']}")
        print(f"MA10: {current['ma10']}")
        print(f"趋势上轨: {upper_band}")
        print(f"趋势下轨: {lower_band}")
        print(f"趋势状态: {trend_status}")
        
        # 显示今日和最新趋势信号
        today_date = datetime.today().strftime('%Y-%m-%d')
        today_signal_text = "None"
        latest_signal_text = ""
        
        if indicators_summary['recent_trend_signals']:
            # 检查是否有今日信号
            for signal in indicators_summary['recent_trend_signals']:
                if signal['date'] == today_date:
                    signal_type = "B" if signal['signal_type'] == 'buy' else "S"
                    today_signal_text = f"{signal_type} @ {signal['price']}"
                    break
            
            # 获取最新信号
            recent_signal = indicators_summary['recent_trend_signals'][0]
            signal_text = "B" if recent_signal['signal_type'] == 'buy' else "S"
            latest_signal_text = f"{recent_signal['date']} {signal_text} {recent_signal['price']}"
        
        print(f"今日趋势信号：{today_signal_text}")
        if latest_signal_text:
            print(f"最新信号：{latest_signal_text}")
    
    return fig

def main():
    """主函数 - 交互式股票分析"""
    print("=" * 50)
    print("         PulseTrader @eviljer")
    print("=" * 50)
    
    # 显示缓存状态
    data_provider.show_cache_status()
    
    # 预加载股票信息（避免每次分析时重复获取）
    try:
        print("🔄 预加载股票信息...")
        data_provider.get_stock_info()
        print("✅ 股票信息加载完成")
    except Exception as e:
        print(f"⚠️  预加载股票信息失败: {e}")
    
    # 默认股票
    default_stock = "杭钢股份"
    
    while True:
        try:
            # 获取用户输入
            user_input = input(f"\n请输入股票名称 (回车默认'{default_stock}', 按 'q' 退出): ").strip()
            
            if user_input.lower() in ['q', '0']:
                print("See you next time.")
                break
            
            # 确定要分析的股票
            stock_name = user_input if user_input else default_stock
            if not user_input:
                print(f"使用默认股票: {stock_name}")
            
            # 分析股票
            print(f"\n开始分析 {stock_name}...")
            result = analyze_stock(stock_name)
            
            if result is not None:
                print(f"✅ {stock_name} 分析完成!")
                
                # 询问是否继续
                continue_choice = input("\n是否分析其他股票? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes', '是']:
                    break
            else:
                print("❌ 分析失败，请检查股票名称")
                
        except KeyboardInterrupt:
            print("\n\n用户中断程序")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            continue

if __name__ == "__main__":
    main()