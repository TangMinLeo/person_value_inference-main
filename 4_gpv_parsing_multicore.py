import json
from gpv import GPV
import os
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# --- 配置 ---
# It's good practice to manage your API key via environment variables.
os.environ['OPENAI_API_KEY'] = "YOUR_API_KEY"

# --- 文件路径 ---
FILE_PATH = "./clean_data/clean_data_with_value_language.jsonl"
OUTPUT_FILE = "./parsing_data/clean_data_with_value_language_parsing.jsonl"


# --- 工作函数 (每个进程将执行此函数) ---
def process_line(json_line):
    """
    Processes a single line from the JSONL file.
    This function will be executed by each worker process.
    """
    try:
        # 1. 加载 JSON 数据
        data = json.loads(json_line.strip())

        # 2. 在工作进程中独立初始化 GPV 对象
        #    这可以确保没有跨进程共享对象的问题
        gpv = GPV()

        # 3. 构造输入文本
        text = (f"The user's personal information is: \n{data['origin_information']['personal_information_sentence']}\n"
                f"The user's behavioral traits is: \n{data['trajectory_description']}")

        # 4. 执行核心任务
        results = gpv.parse_texts([text])

        # 5. 将结果添加回数据字典
        data["perceptions"] = results[0]

        return data

    except Exception as e:
        # 打印错误信息，以便调试，并返回 None
        # data.get('id', 'unknown') 用于在出错时识别是哪条数据
        print(f"Error processing line for id {data.get('id', 'unknown')}: {e}")
        return None


# --- 主程序 ---
if __name__ == "__main__":
    # 1. 一次性读取所有行到内存中
    print(f"Reading all lines from {FILE_PATH}...")
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            lines_to_process = f.readlines()
        print(f"Found {len(lines_to_process)} lines to process.")
    except FileNotFoundError:
        print(f"Error: Input file not found at {FILE_PATH}")
        exit()

    # 2. 自动检测可用核心数
    try:
        # 在Linux上，此方法会遵循 taskset 的设置
        num_processes = len(os.sched_getaffinity(0))
    except AttributeError:
        # 为非Linux系统提供回退
        num_processes = cpu_count()

    print(f"Starting parallel processing with {num_processes} cores... 🚀")

    # 3. 使用多进程池处理所有行
    # 首先以 'w' 模式打开文件，以清空之前的内容
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # 创建进程池
        with Pool(processes=num_processes) as pool:
            # imap_unordered 效率更高，tqdm 用于显示进度条
            for result in tqdm(pool.imap_unordered(process_line, lines_to_process), total=len(lines_to_process)):
                # 只有在处理成功时才写入结果
                if result:
                    # 使用 json.dump 写入，并手动添加换行符
                    json.dump(result, outfile, ensure_ascii=False)
                    outfile.write('\n')

    print(f"\n✅ All tasks completed. Results saved to {OUTPUT_FILE}.")