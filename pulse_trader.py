#!/usr/bin/env python3
"""
PulseTrader All-in-One 集成脚本
整合 TrendInsigt 和 analysis 组件，提供统一的用户交互界面
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

# 导入项目组件
from TrendInsigt import analyze_stock as trend_analyze_stock, initialize_system
from analysis import run_analysis as ai_analysis


class PulseTraderIntegrated:
    """PulseTrader 集成管理器"""
    
    def __init__(self):
        self.stock_name = None
        self.chart_path = None
        self.analysis_result = None
        
        # 确保必要的目录存在
        os.makedirs("figures", exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        
    def welcome_message(self):
        """显示欢迎信息"""
        print("=" * 60)
        print("         PulseTrader All-in-One @eviljer")
        print("=" * 60)
        print("📈 集成技术分析 + AI 智能研判")
        print()
    
    def get_stock_input(self) -> str:
        """获取用户输入的股票名称"""
        default_stock = "杭钢股份"
        
        try:
            user_input = input(f"请输入股票名称 (回车默认'{default_stock}', 按 'q' 退出): ").strip()
            
            if user_input.lower() in ['q', '0']:
                print("See you next time.")
                sys.exit(0)
            
            stock_name = user_input if user_input else default_stock
            if not user_input:
                print(f"使用默认股票: {stock_name}")
            
            return stock_name
            
        except KeyboardInterrupt:
            print("\n\n用户中断程序")
            sys.exit(0)
    
    def run_technical_analysis(self, stock_name: str) -> Optional[Dict[str, Any]]:
        """运行技术分析，生成图表"""
        print(f"\n🔍 Step 1: 技术分析 - {stock_name}")
        print("-" * 40)
        
        try:
            # 调用 TrendInsigt 的核心分析功能
            result = trend_analyze_stock(stock_name)
            
            if result is not None:
                # 构建图表路径（基于 TrendInsigt 的命名规则）
                today = datetime.today().strftime('%Y%m%d')
                chart_filename = f"{stock_name}_PulseTrader_{today}.png"
                chart_path = os.path.join("figures", chart_filename)
                
                if os.path.exists(chart_path):
                    print(f"✅ 技术分析完成")
                    print(f"📊 图表已保存: {chart_path}")
                    return {
                        'stock_name': stock_name,
                        'chart_path': chart_path,
                        'figure': result,
                        'success': True
                    }
                else:
                    print(f"⚠️  图表文件未找到: {chart_path}")
                    print("   可能的原因：绘图过程中出错或文件名格式不匹配")
                    return None
            else:
                print("❌ 技术分析失败")
                return None
                
        except Exception as e:
            print(f"❌ 技术分析过程中发生错误: {e}")
            return None
    
    def confirm_ai_analysis(self) -> tuple[bool, str]:
        """询问用户是否需要 AI 分析，并获取额外的分析上下文"""
        print(f"\n🤖 是否进入智能分析？")
        print("   AI 将基于技术图表提供投资建议和策略研判")
        
        try:
            choice = input("请选择 (y/n): ").strip().lower()
            if choice in ['y', 'yes', '是', 'Y']:
                # 获取额外的分析上下文
                print(f"\n💡 提供额外的信息")
                context = input("请输入（可选，直接回车跳过）: ").strip()
                return True, context if context else None
            else:
                return False, None
        except KeyboardInterrupt:
            print("\n跳过 AI 分析")
            return False, None
    
    def run_ai_analysis(self, stock_name: str, chart_path: str, user_context: str = None) -> Optional[str]:
        """运行 AI 分析"""
        print(f"\n🧠 Step 2: 智能分析 - {stock_name}")
        print("-" * 40)
        
        try:
            # 调用 analysis 的核心分析功能
            result, used_chart_path = ai_analysis(
                chart_image_path=chart_path,
                user_context=user_context
            )
            
            # 检查分析是否成功
            if result is None:
                print(f"⚠️  AI 分析未完成，可能由于网络问题")
                return None
            else:
                print(f"✅ AI 分析完成")
                return used_chart_path
            
        except Exception as e:
            print(f"❌ AI 分析过程中发生错误: {e}")
            return None
    
    def run_interactive_mode(self):
        """运行交互式模式"""
        self.welcome_message()
        
        print("🔄 正在初始化系统...")
        if not initialize_system():
            print("❌ 系统初始化失败，请检查数据源配置")
            return
        
        while True:
            try:
                # Step 1: 获取股票名称并进行技术分析
                stock_name = self.get_stock_input()
                
                technical_result = self.run_technical_analysis(stock_name)
                if not technical_result:
                    print("技术分析失败，请重试")
                    continue
                
                self.stock_name = technical_result['stock_name']
                self.chart_path = technical_result['chart_path']
                
                # Step 2: 询问是否需要 AI 分析
                need_ai, user_context = self.confirm_ai_analysis()
                if need_ai:
                    if user_context:
                        print(f"📝 分析重点: {user_context}")
                    ai_result = self.run_ai_analysis(self.stock_name, self.chart_path, user_context)
                    if ai_result:
                        print(f"\n🎉 完整分析流程完成！")
                        print(f"📊 技术图表: {self.chart_path}")
                        print(f"📝 分析报告: 已保存至 reports/ 目录")
                    else:
                        print("AI 分析失败，但技术分析已完成")
                else:
                    print(f"\n✅ 技术分析完成！")
                    print(f"📊 图表路径: {self.chart_path}")
                
                # 询问是否继续分析其他股票
                print()
                continue_choice = input("是否分析其他股票? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes', '是']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n用户中断程序")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")
                continue
        
        print("\nSee you next time.")
    
    def run_single_analysis(self, stock_name: str, enable_ai: bool = True):
        """运行单次分析（非交互模式）"""
        print(f"🔄 开始分析 {stock_name}...")
        
        # 初始化系统（静默模式）
        if not initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        # 技术分析
        technical_result = self.run_technical_analysis(stock_name)
        if not technical_result:
            print("❌ 技术分析失败")
            return False
        
        self.stock_name = technical_result['stock_name']
        self.chart_path = technical_result['chart_path']
        
        # AI 分析
        if enable_ai:
            ai_result = self.run_ai_analysis(self.stock_name, self.chart_path)
            if ai_result:
                print(f"\n🎉 完整分析流程完成！")
                return True
            else:
                print("⚠️  AI 分析失败，但技术分析已完成")
                return False
        else:
            print(f"\n✅ 技术分析完成！")
            return True


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='PulseTrader All-in-One 股票分析工具')
    parser.add_argument('--stock', '-s', type=str, 
                       help='指定要分析的股票名称')
    parser.add_argument('--no-ai', action='store_true',
                       help='仅进行技术分析，跳过 AI 分析')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='强制使用交互模式（即使提供了股票名称）')
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 创建集成管理器实例
    pulse_trader = PulseTraderIntegrated()
    
    # 判断运行模式
    if args.interactive or not args.stock:
        # 交互模式
        pulse_trader.run_interactive_mode()
    else:
        # 单次分析模式
        enable_ai = not args.no_ai
        success = pulse_trader.run_single_analysis(args.stock, enable_ai)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()