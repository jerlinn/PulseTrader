from datetime import datetime
import pandas as pd
from stock_data_provider import create_data_provider
from plotting_component import create_stock_chart
from rsi_component import calculate_rsi, detect_rsi_divergence
from supertrend_component import calculate_supertrend
import os

# 以量价关系为主要量化依据
# 基础的超级趋势判断
# 合适的相对强度背离阈值，过滤大量假信号——顶背离80，底背离中长期20/短期30
# 接入 LLM 辅助分析
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

    # 计算 SuperTrend 指标
    df = calculate_supertrend(df, lookback_periods=14, multiplier=2)

    # 计算RSI指标
    rsi = calculate_rsi(df)
    df['rsi'] = rsi

    # 检测RSI背离
    divergences = detect_rsi_divergence(df, rsi)

    # 创建图表并显示
    fig = create_stock_chart(df, stock_name, divergences, today)
    fig.show()
    
    return fig

def main():
    """主函数 - 交互式股票分析"""
    print("=" * 50)
    print("         TrendSight @eviljer")
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
    default_stock = "中国中车"
    
    while True:
        try:
            # 获取用户输入
            user_input = input(f"\n请输入股票名称 (回车默认'{default_stock}', 按 'q' 退出): ").strip()
            
            if user_input.lower() in ['q', '0']:
                print("感谢使用 TrendSight")
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