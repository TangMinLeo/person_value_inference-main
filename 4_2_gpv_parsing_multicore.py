import json
from gpv import GPV
import os
from multiprocessing import Pool, cpu_count
from tqdm import tqdm


os.environ[
    'OPENAI_API_KEY'] = ""

# --- 配置 ---
# 将文件路径放在脚本顶部，方便修改
# 根据您的描述，这个脚本用于处理 'value_reason' 文件
INPUT_FILE = "./value_data/clean_data_with_value_reason.jsonl"
OUTPUT_FILE = "./parsing_data/clean_data_with_value_reason_parsing.jsonl"


# --- 工作函数 (每个进程将执行此函数) ---
def process_line(json_line):
    """
    处理来自JSONL文件的单行数据。
    此函数由每个工作进程独立执行。
    """
    try:
        # 1. 加载JSON数据
        data = json.loads(json_line.strip())

        # 2. 在工作进程中独立初始化GPV对象
        gpv = GPV()

        # 3. 提取需要处理的文本
        # 根据您的代码，这里我们使用 "value_reason" 字段
        text_to_parse = data["value_reason"]

        # 4. 执行核心的GPV解析任务
        results = gpv.parse_texts([text_to_parse])

        # 5. 将解析结果添加回数据字典
        data["perceptions"] = results[0]

        return data

    except Exception as e:
        # 打印错误信息以便调试，并返回None
        print(f"处理ID为 {data.get('id', '未知')} 的数据时出错: {e}")
        return None


# --- 主程序 ---
if __name__ == "__main__":
    # 1. 一次性将所有行读入内存
    print(f"正在从 {INPUT_FILE} 读取所有行...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            lines_to_process = f.readlines()
        print(f"已准备好处理 {len(lines_to_process)} 行数据。")
    except FileNotFoundError:
        print(f"错误：输入文件未找到，请检查路径 {INPUT_FILE}")
        exit()

    # 2. 自动检测可用的CPU核心数
    try:
        # 在Linux上，此方法会遵循taskset的CPU亲和性设置
        num_processes = len(os.sched_getaffinity(0))
    except AttributeError:
        # 为非Linux系统（如Windows, macOS）提供备用方案
        num_processes = cpu_count()

    print(f"启动并行处理，使用 {num_processes} 个核心... 🚀")

    # 3. 使用多进程池处理所有行
    # 首先以 'w' (写入)模式打开文件，清空之前可能存在的内容
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # 创建进程池
        with Pool(processes=num_processes) as pool:
            # imap_unordered 效率更高，tqdm 用于显示美观的进度条
            for result in tqdm(pool.imap_unordered(process_line, lines_to_process), total=len(lines_to_process)):
                # 只有在处理成功并返回有效结果时才写入文件
                if result:
                    # 使用 json.dump 写入，并手动添加换行符，以生成正确的JSONL格式
                    json.dump(result, outfile, ensure_ascii=False)
                    outfile.write('\n')

    print(f"\n✅ 所有任务已完成。结果已保存至 {OUTPUT_FILE}。")