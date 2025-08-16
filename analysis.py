from openai import OpenAI
import os
import base64
from PIL import Image
import io
import json
from datetime import datetime
import re
import sys
import argparse
from indicators_storage import IndicatorsStorage

# ========== Configuration ==========

CHART_IMAGE_PATH = 'figures/杭钢股份_TrendSight_20250816.png'
SHOW_REASONING_IN_TERMINAL = True  # False 可隐藏推理过程
USE_COLORED_OUTPUT = True  # False 可禁用彩色输出
BUFFER_REASONING_CHUNKS = True  # 缓存推理片段

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
    """解析单个事件的内容，区分文本输出、推理输出和工具输出"""
    try:
        event_str = str(event)
        
        # 跳过工具调用相关的输出（代码执行）
        if 'ResponseToolCallDeltaEvent' in event_str:
            return {'type': 'tool_call', 'content': None}
        
        # 跳过代码输出相关的事件
        if 'tool_call' in event_str.lower() or 'code_interpreter' in event_str.lower():
            return {'type': 'tool_call', 'content': None}
        
        # 处理推理过程输出
        if 'ResponseReasoningDeltaEvent' in event_str or 'ResponseReasoningSummaryTextDeltaEvent' in event_str:
            if 'delta=' in event_str:
                delta_start = event_str.find("delta='") + 7
                delta_end = event_str.find("'", delta_start)
                if delta_start > 6 and delta_end > delta_start:
                    delta_content = event_str[delta_start:delta_end]
                    return {'type': 'reasoning', 'content': delta_content}
        
        # 处理纯文本响应事件
        if 'ResponseTextDeltaEvent' in event_str:
            # 提取 delta 内容
            if 'delta=' in event_str:
                delta_start = event_str.find("delta='") + 7
                delta_end = event_str.find("'", delta_start)
                if delta_start > 6 and delta_end > delta_start:
                    delta_content = event_str[delta_start:delta_end]
                    # 更精确的代码过滤：只过滤明显的 Python 代码行
                    if (delta_content.startswith(('from ', 'import ', 'img.', 'Image.', 'display(')) or
                        '/mnt/data/' in delta_content or
                        delta_content.strip().endswith(('.png', '.jpg', '.jpeg'))):
                        return {'type': 'code', 'content': None}
                    return {'type': 'text', 'content': delta_content}
        
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
    
    # 生成文件名
    if stock_symbol:
        filename = f"{stock_symbol}_分析报告_{timestamp}.md"
    else:
        filename = f"股票分析报告_{timestamp}.md"
    
    filepath = os.path.join("reports", filename)
    
    # 格式化内容
    formatted_content = format_content(extracted_content['content'])
    
    # 获取技术指标数据
    indicators_section = ""
    if stock_symbol:
        storage = IndicatorsStorage()
        indicators_summary = storage.get_latest_indicators(stock_symbol)
        
        if indicators_summary:
            current = indicators_summary['current_indicators']
            indicators_section = f"""
## 技术指标数据

**最新数据日期**: {current['date']}

### 核心指标
- **RSI14**: {current['rsi14']}
- **MA10**: {current['ma10']}
- **日涨幅**: {f"{current['daily_change_pct']:.2f}%" if current.get('daily_change_pct') is not None else "无数据"}
- **成交量**: {f"{current['volume']:.0f}" if current.get('volume') is not None else "无数据"}
- **量比**: {f"{current['vol_ratio']:.2f}" if current.get('vol_ratio') is not None else "无数据"}
- **趋势上轨**: {current['upper_band']}
- **趋势下轨**: {current['lower_band']}
- **趋势状态**: {"上升" if current['trend'] == 1 else "下降" if current['trend'] == -1 else "中性"}

### 背离信号
"""
            
            if indicators_summary['recent_divergences']:
                for div in indicators_summary['recent_divergences'][:3]:
                    div_type = "顶背离" if div['type'] == 'bearish' else "底背离"
                    timeframe = {"short": "短期", "medium": "中期", "long": "长期"}.get(div['timeframe'], div['timeframe'])
                    indicators_section += f"- **{div['date']}**: {div_type}({timeframe}) - 置信度: {div['confidence']}%\n"
            else:
                indicators_section += "- 暂无显著背离信号\n"
            
            indicators_section += "\n### 趋势信号\n"
            
            if indicators_summary['recent_trend_signals']:
                for signal in indicators_summary['recent_trend_signals'][:3]:  # 取前3个最新信号
                    signal_text = "B" if signal['signal_type'] == 'buy' else "S"
                    indicators_section += f"- **{signal['date']}**: {signal_text} @ {signal['price']}\n"
            else:
                indicators_section += "- 暂无趋势变化信号\n"
    
    # 图表部分（如果有图片路径）
    chart_section = ""
    if chart_image_path and os.path.exists(chart_image_path):
        # 使用相对路径，从 reports 目录指向 figures 目录
        relative_image_path = f"../{chart_image_path}"
        chart_section = f"""
## 走势脉络图

![{stock_symbol or "股票"}走势图]({relative_image_path})

"""
    
    # 构建 MD 文档内容
    md_content = f"""# 📊 交易诊断书 · {stock_symbol or "未指定"}

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  

{chart_section}{indicators_section}
## 策略研判

{formatted_content}

---

TrendSight：计算你的计划。

"""
    
    # 保存文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"分析报告已保存至: {filepath}")
    return filepath

def get_technical_indicators_context(chart_image_path):
    """从图片路径推断股票并获取技术指标上下文，在后续的 all-in-one 合入中，不再计算技术指标，直接从上一节点传递"""
    if not chart_image_path or not os.path.exists(chart_image_path):
        return ""
    
    # 从文件名推断股票名称
    filename = os.path.basename(chart_image_path)
    stock_name = filename.split('_')[0] if '_' in filename else None
    
    if not stock_name:
        return ""
    
    # 获取股票代码
    try:
        from stock_data_provider import create_data_provider
        data_provider = create_data_provider()
        stock_info = data_provider.get_stock_info()
        stock_symbol = data_provider.get_stock_symbol(stock_info, stock_name)
        
        # 获取技术指标数据
        storage = IndicatorsStorage()
        indicators_summary = storage.get_latest_indicators(stock_symbol)
        
        if indicators_summary:
            current = indicators_summary['current_indicators']
            
            # 格式化趋势状态
            trend_status = "上升" if current['trend'] == 1 else "下降" if current['trend'] == -1 else "中性"
            
            # 格式化趋势上下轨
            upper_band = current['upper_band'] if current['upper_band'] is not None else "None"
            lower_band = current['lower_band'] if current['lower_band'] is not None else "None"
            
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
            
            context = f"""技术指标背景数据：

📊 {stock_name} · {current['date']} 技术指标：
RSI14: {current['rsi14']}
MA10: {current['ma10']}
日涨幅: {daily_change_text}
成交量: {volume_text}
量比: {vol_ratio_text}
{'SuperTrend 阻力位' if trend_status == '下降趋势' else 'SuperTrend 支撑位'}: {upper_band if trend_status == '下降趋势' else lower_band}
趋势状态: {trend_status}
今日趋势信号：{today_signal_text}"""
            
            if latest_signal_text:
                context += f"\n最新信号：{latest_signal_text}"
            
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
        return "你是专业的股票分析师，请分析股票走势并提供投资建议。"

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
    print(f"{Colors.BOLD}🤖 AI 分析中...{Colors.ENDC}")
    if SHOW_REASONING_IN_TERMINAL:
        print(f"{Colors.YELLOW}📝 (包含推理过程){Colors.ENDC}")
    
    def process_reasoning_content(content):
        """处理推理内容，按句子单位显示"""
        global reasoning_display_buffer, reasoning_started
        
        reasoning_display_buffer += content
        
        # 检查是否有完整的句子
        sentences = []
        remaining_text = reasoning_display_buffer
        
        # 按句子分割（支持中英文标点）
        sentence_endings = ['. ', '。', '! ', '！', '? ', '？', '\n']
        
        for ending in sentence_endings:
            if ending in remaining_text:
                parts = remaining_text.split(ending)
                # 除了最后一部分，其他都是完整句子
                for part in parts[:-1]:
                    sentence = part + ending.strip()
                    if sentence.strip():
                        sentences.append(sentence.strip())
                
                # 更新剩余文本
                remaining_text = parts[-1]
                break
        
        # 显示完整句子
        for sentence in sentences:
            if not reasoning_started:
                print(f"\n\n{Colors.BLUE}🧠 [推理过程]:{Colors.ENDC}")
                reasoning_started = True
            
            print(f"{Colors.BLUE}{sentence}{Colors.ENDC}")
        
        # 更新缓冲区为剩余文本
        reasoning_display_buffer = remaining_text
    
    def finish_reasoning_display():
        """完成推理显示，输出剩余内容"""
        global reasoning_display_buffer, reasoning_started
        
        if reasoning_display_buffer.strip():
            if not reasoning_started:
                print(f"\n\n{Colors.BLUE}🧠 [推理过程]:{Colors.ENDC}")
                print(f"{Colors.BLUE}{'-' * 30}{Colors.ENDC}")
            
            print(f"{Colors.BLUE}{reasoning_display_buffer.strip()}{Colors.ENDC}")
        
        if reasoning_started:
            print(f"{Colors.BLUE}{'-' * 30}{Colors.ENDC}")
        
        reasoning_display_buffer = ""
        reasoning_started = False
    
    for event in response:
        response_events.append(event)
        
        # 解析并显示可读内容
        parsed = parse_event_content(event)
        if parsed and parsed.get('content') and parsed['content'].strip():
            if parsed['type'] == 'text':
                print(f"{Colors.GREEN}{parsed['content']}{Colors.ENDC}", end='', flush=True)
            elif parsed['type'] == 'reasoning' and SHOW_REASONING_IN_TERMINAL:
                process_reasoning_content(parsed['content'])
    
    # 完成推理显示
    if SHOW_REASONING_IN_TERMINAL:
        finish_reasoning_display()
    
    print(f"\n{Colors.BOLD}" + "-" * 30 + f"{Colors.ENDC}")
    
    return response_events

def process_reasoning_content(content):
    """处理推理内容，按句子单位显示"""
    global reasoning_display_buffer, reasoning_started
    
    reasoning_display_buffer += content
    
    # 检查是否有完整的句子
    sentences = []
    remaining_text = reasoning_display_buffer
    
    # 按句子分割（支持中英文标点）
    sentence_endings = ['. ', '。', '! ', '！', '? ', '？', '\n']
    
    for ending in sentence_endings:
        if ending in remaining_text:
            parts = remaining_text.split(ending)
            # 除了最后一部分，其他都是完整句子
            for part in parts[:-1]:
                sentence = part + ending.strip()
                if sentence.strip():
                    sentences.append(sentence.strip())
            
            # 更新剩余文本
            remaining_text = parts[-1]
            break
    
    # 显示完整句子
    for sentence in sentences:
        if not reasoning_started:
            print(f"\n\n{Colors.BLUE}🧠 [推理过程]:{Colors.ENDC}")
            reasoning_started = True
        
        print(f"{Colors.BLUE}{sentence}{Colors.ENDC}")
    
    # 更新缓冲区为剩余文本
    reasoning_display_buffer = remaining_text

def finish_reasoning_display():
    """完成推理显示，输出剩余内容"""
    global reasoning_display_buffer, reasoning_started
    
    if reasoning_display_buffer.strip():
        if not reasoning_started:
            print(f"\n\n{Colors.BLUE}🧠 [推理过程]:{Colors.ENDC}")
            print(f"{Colors.BLUE}{'-' * 30}{Colors.ENDC}")
        
        print(f"{Colors.BLUE}{reasoning_display_buffer.strip()}{Colors.ENDC}")
    
    if reasoning_started:
        print(f"{Colors.BLUE}{'-' * 30}{Colors.ENDC}")
    
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
    
    # 事件处理 - 添加网络错误处理
    response_events = []
    print(f"{Colors.BOLD}🤖 AI 分析中...{Colors.ENDC}")
    if SHOW_REASONING_IN_TERMINAL:
        print(f"{Colors.YELLOW}📝 (包含推理过程){Colors.ENDC}")

    try:
        for event in response:
            response_events.append(event)
            
            # 恢复事件解析，但添加错误处理避免卡住
            try:
                parsed = parse_event_content(event)
                if parsed and parsed.get('content') and parsed['content'].strip():
                    if parsed['type'] == 'text':
                        print(f"{Colors.GREEN}{parsed['content']}{Colors.ENDC}", end='', flush=True)
                    elif parsed['type'] == 'reasoning' and SHOW_REASONING_IN_TERMINAL:
                        process_reasoning_content(parsed['content'])
                else:
                    print(".", end='', flush=True)  # 未解析到内容时显示进度点
            except Exception:
                # 如果解析出错，显示进度点并继续
                print(".", end='', flush=True)
    
    except Exception as e:
        # 处理网络连接错误
        error_msg = str(e)
        if 'RemoteProtocolError' in error_msg or 'incomplete chunked read' in error_msg:
            print(f"\n{Colors.YELLOW}⚠️  网络连接中断，但已接收到部分响应{Colors.ENDC}")
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
            pass  # 如果推理显示出错，忽略并继续

    print(f"\n{Colors.BOLD}" + "-" * 30 + f"{Colors.ENDC}")
    
    # 提取内容并保存报告
    extracted_content = extract_content_from_response(response_events)
    
    # 从图表路径自动提取股票名称
    stock_symbol = extract_stock_symbol_from_path(chart_image_path)
    print(f"📈 检测到股票: {stock_symbol}")
    
    report_path = save_analysis_report(
        extracted_content, 
        stock_symbol=stock_symbol, 
        chart_image_path=chart_image_path
    )
    
    print(f"\n{Colors.GREEN}🎉 分析完成！报告已保存至: {Colors.BLUE}{report_path}{Colors.ENDC}")
    
    return response, chart_image_path

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='TrendSight 股票分析工具')
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
            print(f"{Colors.GREEN}📝 用户上下文已记录: {user_context}{Colors.ENDC}")
    
    # 运行分析
    response, used_chart_path = run_analysis(
        chart_image_path=args.chart, 
        user_context=user_context
    )
    
    return response, used_chart_path

if __name__ == "__main__":
    # 如果作为脚本直接运行，使用主函数
    response, used_chart_path = main()
else:
    # 如果作为模块导入，使用原有的默认行为
    response, used_chart_path = run_analysis(user_context=None)