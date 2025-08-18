from openai import OpenAI
import os
import base64
from PIL import Image
import io
from datetime import datetime
import re
import argparse
from indicators_storage import IndicatorsStorage

"""
@eviljer

* 无特别信号时简洁分析
* 独立运作时，需要先用 TrendInsigt.py 处理数据
* code_interpreter 工具不支持 reasoning.effort 最低档位 'minimal'
* 如需更深度的推理，使用 reasoning={ "effort": "high", "summary": "auto" },
"""

# ========== Configuration ==========
CHART_IMAGE_PATH = 'figures/腾讯控股_PulseTrader_20250818.png'
SHOW_REASONING_IN_TERMINAL = True  # False 可隐藏推理过程
USE_COLORED_OUTPUT = True  # False 可禁用彩色输出
SIMPLE_DISPLAY_MODE = True  # True 启用简化显示模式

# 全局变量用于推理过程显示
reasoning_buffer = []
reasoning_display_buffer = ""
reasoning_started = False

def resize_image(image_path, max_size=512):
    """预处理最大边到指定尺寸"""
    with Image.open(image_path) as img:
        max_dimension = max(img.width, img.height)
        if max_dimension > max_size:
            scale_ratio = max_size / max_dimension
            new_width = int(img.width * scale_ratio)
            new_height = int(img.height * scale_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', optimize=True)
        return img_buffer.getvalue()

def encode_image(image_path, max_size=512):
    image_bytes = resize_image(image_path, max_size)
    return base64.b64encode(image_bytes).decode('utf-8')

def parse_event_content(event):
    """解析单个事件的内容，基于 OpenAI 官方文档优化处理"""
    try:
        event_str = str(event)
        event_type = type(event).__name__
        
        # 检测流完成事件
        if event_type == 'ResponseCompletedEvent':
            return {'type': 'completed', 'content': None}
        
        # 处理 code interpreter 相关事件
        if any(ci_marker in event_str for ci_marker in [
            'ResponseCodeInterpreterToolCall',
            'ResponseToolCallDeltaEvent', 
            'code_interpreter_call',
            'container_id'
        ]):
            return {'type': 'code_interpreter', 'content': None}
        
        # 处理推理过程输出（流式） - 增强检测
        if 'Reasoning' in event_type and 'Delta' in event_type:
            if 'delta=' in event_str:
                delta_start = event_str.find("delta='") + 7
                delta_end = event_str.find("'", delta_start)
                if delta_start > 6 and delta_end > delta_start:
                    delta_content = event_str[delta_start:delta_end]
                    return {'type': 'reasoning', 'content': delta_content}
        
        # 处理推理过程汇总
        if event_type == 'ResponseReasoningSummaryTextDeltaEvent':
            if 'delta=' in event_str:
                delta_start = event_str.find("delta='") + 7
                delta_end = event_str.find("'", delta_start)
                if delta_start > 6 and delta_end > delta_start:
                    delta_content = event_str[delta_start:delta_end]
                    return {'type': 'reasoning_summary', 'content': delta_content}
        
        # 处理最终文本输出（非推理、非代码）
        if event_type == 'ResponseTextDeltaEvent':
            if 'delta=' in event_str:
                delta_start = event_str.find("delta='") + 7
                delta_end = event_str.find("'", delta_start)
                if delta_start > 6 and delta_end > delta_start:
                    delta_content = event_str[delta_start:delta_end]
                    return {'type': 'text', 'content': delta_content}
        
        # 处理输出消息（完整消息）
        if event_type == 'ResponseOutputMessage':
            return {'type': 'output_message', 'content': None}
            
    except Exception:
        pass
    return None

def extract_content_from_response(response_events):
    content_parts = []
    reasoning_parts = []
    
    text_event_count = 0
    reasoning_event_count = 0
    
    for event in response_events:
        parsed = parse_event_content(event)
        if parsed and parsed.get('content'):
            if parsed['type'] == 'text':
                content_parts.append(parsed['content'])
                text_event_count += 1
            elif parsed['type'] == 'reasoning':
                reasoning_parts.append(parsed['content'])
                reasoning_event_count += 1
    
    return {
        'content': ''.join(content_parts),
        'reasoning': ''.join(reasoning_parts)
    }

def extract_stock_symbol_from_path(image_path):
    if not image_path:
        return None
    
    filename = os.path.splitext(os.path.basename(image_path))[0]
    parts = filename.split('_')
    
    if len(parts) >= 2:
        # 第一部分设计为股票名称
        stock_name = parts[0]
        return stock_name
    
    # 如果分割失败，返回整个文件名
    return filename

def format_content(content):
    if not content:
        return ""
    
    # 处理 \n 换行符
    content = content.replace('\\n', '\n')
    
    # 处理双换行（段落分隔）
    content = re.sub(r'\n\n+', '\n\n', content)
    
    # 处理列表项格式
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        
        # 跳过空行
        if not line:
            formatted_lines.append('')
            continue
            
        # 检测并格式化列表项
        if line.startswith('- ') or line.startswith('* '):
            formatted_lines.append(line)
        elif re.match(r'^\d+\.\s', line):  # 数字列表
            formatted_lines.append(line)
        elif line.startswith('\\n-'):  # 处理转义的列表项
            formatted_lines.append(line.replace('\\n-', '- '))
        elif '- ' in line and not line.startswith('#'):
            # 可能是被合并的列表项
            parts = line.split('- ')
            if len(parts) > 1:
                formatted_lines.append(parts[0].strip())
                for part in parts[1:]:
                    if part.strip():
                        formatted_lines.append(f"- {part.strip()}")
            else:
                formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def save_analysis_report(extracted_content, stock_symbol=None, chart_image_path=None):
    """Save report as MD with technical indicators data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if stock_symbol:
        filename = f"{stock_symbol}_分析报告_{timestamp}.md"
    else:
        filename = f"股票分析报告_{timestamp}.md"
    
    filepath = os.path.join("reports", filename)
    
    formatted_content = format_content(extracted_content['content'])
    
    # 图表部分（如果有图片路径）
    chart_section = ""
    if chart_image_path and os.path.exists(chart_image_path):
        # 使用相对路径，从 reports 目录指向 figures 目录
        relative_image_path = f"../{chart_image_path}"
        chart_section = f"""
## 走势脉络图

![{stock_symbol or "股票"}走势图]({relative_image_path})

"""
    
    md_content = f"""# 📊 交易诊断书 · {stock_symbol or "未指定"}

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  

{chart_section}
## 策略研判

{formatted_content}

---

PulseTrader：计算你的计划。

"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return filepath

def get_technical_indicators_context(chart_image_path):
    """从图片路径推断股票并获取技术指标上下文"""
    if not chart_image_path or not os.path.exists(chart_image_path):
        return ""
    
    # 从文件名推断股票名称
    filename = os.path.basename(chart_image_path)
    stock_name = filename.split('_')[0] if '_' in filename else None
    
    if not stock_name:
        return ""
    
    # 获取股票代码（支持多市场搜索）
    try:
        from stock_data_provider import create_data_provider
        data_provider = create_data_provider()
        stock_symbol, _ = data_provider.get_stock_symbol(stock_name)
        
        # 获取技术指标数据
        storage = IndicatorsStorage()
        indicators_summary = storage.get_latest_indicators(stock_symbol)
        
        if indicators_summary:
            current = indicators_summary['current_indicators']
            
            # 格式化趋势状态
            trend_status = "上升" if current['trend'] == 1 else "下降" if current['trend'] == -1 else "中性"
            
            # 格式化今日和最新趋势信号
            today_date = datetime.now().strftime('%Y-%m-%d')
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
                signal_type = "B" if recent_signal['signal_type'] == 'buy' else "S"
                latest_signal_text = f"{recent_signal['date']} {signal_type} {recent_signal['price']}"
            
            # 格式化日涨幅
            daily_change = current.get('daily_change_pct', None)
            daily_change_text = f"{daily_change:.2f}%" if daily_change is not None else "None"
            
            # 格式化成交量和量比
            volume = current.get('volume', None)
            volume_text = f"{volume:.0f}" if volume is not None else "None"
            vol_ratio = current.get('vol_ratio', None)
            vol_ratio_text = f"{vol_ratio:.2f}" if vol_ratio is not None else "None"
            
            # 检查成交量指标并构建上下文
            volume_signal_context = ""
            
            # 检查是否为高量柱（20日最高量）
            if current.get('is_high_vol_bar'):
                vol_20d_max = current.get('vol_20d_max', None)
                vol_20d_avg = current.get('vol_20d_avg', None)
                if vol_20d_max and vol_20d_avg:
                    volume_signal_context += f"\n当日成交量 {volume_text} 为 20 日最高量，20 日平均量 {vol_20d_avg:.0f}"
            
            # 检查是否为天量柱（20日最高量且显著爆量）
            if current.get('is_sky_vol_bar'):
                vol_20d_max = current.get('vol_20d_max', None)
                vol_20d_avg = current.get('vol_20d_avg', None)
                if vol_20d_max and vol_20d_avg and volume:
                    vol_multiple = volume / vol_20d_avg
                    volume_signal_context += f"\n当日成交量 {volume_text} 为 20 日最高量且达到 20 日均量的 {vol_multiple:.1f} 倍"
            
            # 检查是否为地量柱（50日最低量）
            if current.get('is_low_vol_bar'):
                vol_50d_min = current.get('vol_50d_min', None)
                if vol_50d_min:
                    volume_signal_context += f"\n当日成交量 {volume_text} 为 50 日最低量"
            
            # 格式化收盘价
            close_price = current.get('close_price', None)
            close_price_text = f"{close_price:.2f}" if close_price is not None else "None"
            
            context = f"""技术指标背景数据：

📊 {stock_name} · {current['date']} 技术指标：
收盘价: {close_price_text}
日涨幅: {daily_change_text}
MA10: {current['ma10']}
成交量: {volume_text}
量比: {vol_ratio_text}
RSI14: {current['rsi14']}
趋势状态: {trend_status}
今日趋势信号：{today_signal_text}"""
            
            if latest_signal_text:
                context += f"\n最新信号：{latest_signal_text}"
                
            # 添加成交量信号信息（如果有的话）
            if volume_signal_context:
                context += volume_signal_context
            
            return context + "\n\n"
    
    except Exception as e:
        print(f"获取技术指标上下文时出错: {e}")
        return ""
    
    return ""

def build_user_message(chart_image_path, user_context=None):
    technical_context = get_technical_indicators_context(chart_image_path)

    base_message = "分析当前的股票走势，提供投资建议"
    
    # 如果有用户提供的上下文，则整合到消息中
    if user_context and user_context.strip():
        user_message = f"{technical_context}用户补充信息：{user_context.strip()}\n\n{base_message}"
    else:
        user_message = f"{technical_context}{base_message}"
    
    return user_message

client = OpenAI(
    api_key=os.getenv("AIHUBMIX_API_KEY"),
    base_url="https://aihubmix.com/v1"
)

def load_system_prompt():
    try:
        with open('analyst_prompt.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("警告：找不到 analyst_prompt.md 文件，使用默认提示")
        return """You are Agent Z — the user's direct trading delegate with real capital at risk ("skin in the game"). You embody contrarian wisdom with a strong left-side bias: prefer entering during weakness rather than chasing strength, and favor certainty over speculation. You think and act like an accountable owner: every recommendation must be executable, risk-aware, and defensible. Base your reasoning on price–volume structure, quantitative patterns, human behavior, and simple mathematics; your job is to turn analysis into action while keeping users away from FOMO-driven mistakes."""

# ANSI 颜色代码
class Colors:
    BLUE = '\033[94m' if USE_COLORED_OUTPUT else ''
    GREEN = '\033[92m' if USE_COLORED_OUTPUT else ''
    YELLOW = '\033[93m' if USE_COLORED_OUTPUT else ''
    RED = '\033[91m' if USE_COLORED_OUTPUT else ''
    ENDC = '\033[0m' if USE_COLORED_OUTPUT else ''
    BOLD = '\033[1m' if USE_COLORED_OUTPUT else ''

def process_response_stream(response):
    """处理响应流并显示内容"""
    # 推理内容缓冲区 - 使用全局变量
    global reasoning_display_buffer, reasoning_started
    reasoning_display_buffer = ""
    reasoning_started = False
    
    # 收集所有响应事件并实时显示内容
    response_events = []
    if SHOW_REASONING_IN_TERMINAL:
        print(f"{Colors.BOLD}🤖 AI 分析中... {Colors.YELLOW}(包含推理过程){Colors.ENDC}")
    else:
        print(f"{Colors.BOLD}🤖 AI 分析中...{Colors.ENDC}")
    
    
    # 优雅的流处理，基于 OpenAI 官方文档最佳实践
    event_count = 0
    max_events = 1000  # 增加事件限制以支持复杂分析
    reasoning_event_count = 0
    max_reasoning_events = 200  # 增加推理事件限制
    text_output_started = False  # 标记文本输出是否开始
    
    try:
        for event in response:
            event_count += 1
            response_events.append(event)
            
            # 防止无限循环 - 静默处理
            if event_count > max_events:
                break
            
            # 解析并显示可读内容，添加错误保护
            try:
                parsed = parse_event_content(event)
                
                
                if parsed:
                    if parsed['type'] == 'text' and parsed.get('content'):
                        if not text_output_started:
                            text_output_started = True
                            print(f"\n\n{Colors.BOLD}📋 [Analysis]{Colors.ENDC}")
                        print(f"{Colors.GREEN}{parsed['content']}{Colors.ENDC}", end='', flush=True)
                    elif parsed['type'] in ['reasoning', 'reasoning_summary'] and SHOW_REASONING_IN_TERMINAL:
                        reasoning_event_count += 1
                        # 调试：显示推理事件统计
                        if reasoning_event_count == 1:
                            print(f"\n{Colors.BLUE}🧠 [Thinking]{Colors.ENDC}")
                            reasoning_started = True
                        
                        if parsed.get('content'):
                            if reasoning_event_count <= max_reasoning_events:
                                print(f"{Colors.BLUE}{parsed['content']}{Colors.ENDC}", end='', flush=True)
                            elif reasoning_event_count == max_reasoning_events + 1:
                                print(f"\n{Colors.YELLOW}推理内容较多，切换为摘要显示{Colors.ENDC}")
                    elif parsed['type'] == 'code_interpreter':
                        # 代码执行事件 - 静默处理，符合预期
                        pass
                    elif parsed['type'] == 'output_message':
                        # 输出消息完成标志
                        pass
                    elif parsed['type'] == 'completed':
                        # 流完成事件 - 优雅退出
                        print(f"\n{Colors.GREEN}[Done]{Colors.ENDC}")
                        break
                else:
                    # 每50个事件显示一个进度点
                    if event_count % 50 == 0:
                        print(".", end='', flush=True)
            except Exception:
                # 单个事件解析错误不影响整体流程
                if event_count % 100 == 0:  # 减少进度点显示频率
                    print(".", end='', flush=True)
    
    except Exception as e:
        # 处理各种网络和连接错误
        error_msg = str(e)
        if any(keyword in error_msg.lower() for keyword in 
               ['remoteprotocolerror', 'incomplete chunked read', 'connection', 'timeout']):
            print(f"\n{Colors.YELLOW}⚠️ 网络连接中断，但已接收到部分响应{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}❌ 流处理错误: {error_msg}{Colors.ENDC}")
        
        # 如果已经收集到一些事件，继续处理
        if response_events:
            print(f"{Colors.YELLOW}📄 处理已接收的部分内容...{Colors.ENDC}")
    
    # 完成推理显示
    if SHOW_REASONING_IN_TERMINAL:
        try:
            finish_reasoning_display()
        except Exception:
            pass  # 推理显示错误不影响主流程
    
    return response_events


def finish_reasoning_display():
    """简化的推理显示结束"""
    global reasoning_display_buffer, reasoning_started
    
    reasoning_display_buffer = ""
    reasoning_started = False

def get_user_context_input():
    """获取用户输入的分析上下文"""
    print(f"\n{Colors.YELLOW}💡 可选：提供额外的分析上下文{Colors.ENDC}")
    print("   例如：「我关注短期波动风险」、「重点分析基本面」、「评估长期投资价值」等")
    print("   如不需要额外信息，直接按 Enter 跳过")
    
    try:
        user_input = input(f"\n{Colors.BLUE}🔍 请输入分析重点或问题（可选）: {Colors.ENDC}").strip()
        return user_input if user_input else None
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Colors.YELLOW}已跳过用户输入{Colors.ENDC}")
        return None

def run_analysis(chart_image_path=None, user_context=None):
    """运行股票分析，支持可选的用户上下文输入"""
    if chart_image_path is None:
        chart_image_path = CHART_IMAGE_PATH
    
    # 技术指标上下文获取
    technical_context = get_technical_indicators_context(chart_image_path)
    
    # 构建用户消息
    if user_context and user_context.strip():
        user_message = f"{technical_context}用户补充信息：{user_context.strip()}\n\n分析当前的股票走势，提供投资建议"
    else:
        user_message = f"{technical_context}分析当前的股票走势，提供投资建议"
    
    response = client.responses.create(
        model="gpt-5", # gpt-5, gpt-5-chat-latest, gpt-5-mini, gpt-5-nano
        tools=[
            {
                "type": "code_interpreter",
                "container": {"type": "auto"}
            }
        ],
        input=[
            {
                "role": "system",
                "content": [
                    { "type": "input_text", "text": load_system_prompt() }
                ]
            },
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": user_message },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{encode_image(chart_image_path)}",
                        "detail": "low"
                    }
                ]
            }
        ],
        reasoning={ "effort": "medium", "summary": "auto" }, # "low", "medium"(default), "high"
        text={"verbosity": "low"}, # "low", "medium"(default), "high"，维持用 low 测试
        stream=True
    )
    
    # 使用强化错误处理的流处理函数
    try:
        response_events = process_response_stream(response)
        
        extracted_content = extract_content_from_response(response_events)
        
        # 检查是否有有效内容
        if not extracted_content.get('content') and not response_events:
            print(f"{Colors.YELLOW}⚠️ 未能获取有效的分析内容，可能由于网络中断{Colors.ENDC}")
            return None, chart_image_path
        
        # 从图表路径提取股票名称并保存报告
        stock_symbol = extract_stock_symbol_from_path(chart_image_path)
        report_path = save_analysis_report(
            extracted_content, 
            stock_symbol=stock_symbol, 
            chart_image_path=chart_image_path
        )
        
        print(f"\n{Colors.GREEN}🎉 {stock_symbol} 分析完成，报告已保存: {Colors.BLUE}{os.path.basename(report_path)}{Colors.ENDC}")
        
        return response, chart_image_path
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ 分析过程中发生严重错误: {e}{Colors.ENDC}")
        print(f"{Colors.YELLOW}💡 建议检查网络连接后重试{Colors.ENDC}")
        return None, chart_image_path

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='PulseTrader 股票分析工具')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='启用交互式模式，允许用户输入分析上下文')
    parser.add_argument('--context', '-c', type=str, 
                       help='直接提供分析上下文，跳过交互输入')
    parser.add_argument('--chart', type=str, default=CHART_IMAGE_PATH,
                       help='指定图表文件路径')
    return parser.parse_args()

def main():
    """主函数，处理命令行参数和用户交互"""
    args = parse_arguments()
    
    user_context = None
    
    # 处理用户上下文输入
    if args.context:
        # 直接使用命令行提供的上下文
        user_context = args.context
        print(f"{Colors.GREEN}📝 使用提供的分析上下文: {user_context}{Colors.ENDC}")
    elif args.interactive:
        # 交互式输入
        user_context = get_user_context_input()
        if user_context:
            print(f"{Colors.GREEN}📝 用户上下文已补充: {user_context}{Colors.ENDC}")
    
    response, used_chart_path = run_analysis(
        chart_image_path=args.chart, 
        user_context=user_context
    )
    
    return response, used_chart_path

if __name__ == "__main__":
    # 如果作为脚本直接运行，使用主函数
    main()