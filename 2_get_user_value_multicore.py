import json
import jsonlines
from openai import OpenAI
import os
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# --- 配置 ---
# 建议使用环境变量来设置API密钥，而不是硬编码
# os.environ['OPENAI_API_KEY'] = "YOUR_API_KEY"

# 如果没有设置环境变量，请在此处填写
if 'OPENAI_API_KEY' not in os.environ:
    os.environ[
        'OPENAI_API_KEY'] = "sk-REPLACED"

INPUT_FILE = "./clean_data/clean_data_with_person_information.json"
OUTPUT_FILE = "./value_data/clean_data_with_value_language.jsonl"


# --- 辅助函数 ---

def create_prompt(trajectory_description, personal_information):
    """根据轨迹和个人信息创建提示"""
    prompt = f'''You are a psychologist. You will be given a trajectory description of a user over the course of a month, along with the user’s personal information. 
##TASK
Based on this information, please summarize:
1. The user's behavioral habits.
2. If the user deviates from the general population's behavior, please point it out. If there are no deviations, you may omit this section.
## input
Here is the user's trajectory description:
{trajectory_description}
Here is the user's personal information:
{personal_information}
'''
    return prompt


# --- 工作函数（每个进程将执行此函数） ---

def process_entry(args):
    """
    处理单个数据条目的函数。
    接收一个元组作为参数，包含索引、ID和信息。
    """
    index, person_id, info = args

    # 在每个工作进程中独立初始化客户端
    client = OpenAI()

    try:
        trajectory_description = info.get("level3_category_sentence", {})
        personal_information = info.get("personal_information_sentence", {})
        prompt = create_prompt(trajectory_description, personal_information)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        trajectory = completion.choices[0].message.content

        # 准备要返回的结果字典
        result = {
            'person_id': person_id,
            "id": index,
            "origin_information": info,
            "trajectory_description": trajectory
        }
        return result

    except Exception as e:
        # 异常处理：打印错误并返回 None，或一个包含错误信息的字典
        print(f"Error processing person_id {person_id}: {e}")
        return None


# --- 主程序 ---

if __name__ == "__main__":
    # 1. 读取原始 JSON 文件
    print(f"Reading data from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. 准备要并行处理的任务列表
    tasks = [(i, person_id, info) for i, (person_id, info) in enumerate(data.items())]
    print(f"Prepared {len(tasks)} tasks to process.")

    # 3. 使用多进程池处理任务
    # ✨ 优化点: 自动检测被taskset或cgroups限制后可用的CPU核心数
    try:
        # 在Linux上，这会遵循taskset设置的CPU亲和性
        num_processes = len(os.sched_getaffinity(0))
    except AttributeError:
        # 为非Linux系统（如Windows, macOS）提供回退方案
        num_processes = cpu_count()

    print(f"Starting parallel processing. Available cores for this process: {num_processes} 🚀")

    # 清空或创建输出文件
    with open(OUTPUT_FILE, 'w') as f:
        pass

    # 创建一个进程池
    with Pool(processes=num_processes) as pool:
        with jsonlines.open(OUTPUT_FILE, mode='a') as writer:
            for result in tqdm(pool.imap_unordered(process_entry, tasks), total=len(tasks)):
                if result:
                    writer.write(result)

    print(f"\n✅ All tasks completed. Results saved to {OUTPUT_FILE}.")