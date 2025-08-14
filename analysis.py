from openai import OpenAI
import os
import base64
from PIL import Image
import io
import json
from datetime import datetime
import re

# ========== Configuration ==========

CHART_IMAGE_PATH = 'figures/杭钢股份_TrendSight_20250813.png'
SHOW_REASONING_IN_TERMINAL = True  # False 可隐藏推理过程
USE_COLORED_OUTPUT = True  # False 可禁用彩色输出
BUFFER_REASONING_CHUNKS = True  # 缓存推理片段

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
    """Save report as MD"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 生成文件名
    if stock_symbol:
        filename = f"{stock_symbol}_分析报告_{timestamp}.md"
    else:
        filename = f"股票分析报告_{timestamp}.md"
    
    filepath = os.path.join("reports", filename)
    
    # 格式化内容
    formatted_content = format_content(extracted_content['content'])
    # formatted_reasoning = format_content(extracted_content['reasoning'])
    
    # 图表部分（如果有图片路径）
    chart_section = ""
    if chart_image_path and os.path.exists(chart_image_path):
        # 使用相对路径，从 reports 目录指向 figures 目录
        relative_image_path = f"../{chart_image_path}"
        chart_section = f"""
## 股票走势图

![{stock_symbol or "股票"}走势图]({relative_image_path})

"""
    
    # 构建 MD 文档内容
    md_content = f"""# 股票分析报告 · {stock_symbol or "未指定"}

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  

{chart_section}
## 分析结果

{formatted_content}

---

*本报告由 TrendSight AI 自动生成*
"""
    
    # 保存文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"分析报告已保存至: {filepath}")
    return filepath

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
                { "type": "input_text", "text": "分析当前的股票走势，提供投资建议" },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{encode_image(CHART_IMAGE_PATH)}",
                    "detail": "low"
                }
            ]
        }
    ],
    reasoning={ "effort": "medium", "summary": "auto" }, # "low", "medium"(default), "high"
    text={"verbosity": "medium"}, # "low", "medium"(default), "high"
    stream=True
)

# ANSI 颜色代码
class Colors:
    BLUE = '\033[94m' if USE_COLORED_OUTPUT else ''
    GREEN = '\033[92m' if USE_COLORED_OUTPUT else ''
    YELLOW = '\033[93m' if USE_COLORED_OUTPUT else ''
    RED = '\033[91m' if USE_COLORED_OUTPUT else ''
    ENDC = '\033[0m' if USE_COLORED_OUTPUT else ''
    BOLD = '\033[1m' if USE_COLORED_OUTPUT else ''

# 推理内容缓冲区
reasoning_buffer = []
reasoning_display_buffer = ""
reasoning_started = False

# 收集所有响应事件并实时显示内容
response_events = []
print(f"{Colors.BOLD}🤖 AI 分析中...{Colors.ENDC}")
if SHOW_REASONING_IN_TERMINAL:
    print(f"{Colors.YELLOW}📝 (包含推理过程){Colors.ENDC}")
print("-" * 50)

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
            print(f"{Colors.BLUE}{'-' * 40}{Colors.ENDC}")
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

# 配置已在文件顶部定义

# 提取内容并保存报告
extracted_content = extract_content_from_response(response_events)

# 从图表路径自动提取股票名称
stock_symbol = extract_stock_symbol_from_path(CHART_IMAGE_PATH)
print(f"📈 检测到股票: {stock_symbol}")

report_path = save_analysis_report(
    extracted_content, 
    stock_symbol=stock_symbol, 
    chart_image_path=CHART_IMAGE_PATH
)

print(f"\n{Colors.GREEN}🎉 分析完成！报告已保存至: {Colors.BLUE}{report_path}{Colors.ENDC}")