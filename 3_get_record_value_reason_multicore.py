import json
import jsonlines
from openai import OpenAI
import os
import pandas as pd
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# --- 配置 ---
# 如果没有设置环境变量，请在此处填写
if 'OPENAI_API_KEY' not in os.environ:
    os.environ[
        'OPENAI_API_KEY'] = "sk-REPLACED"

# --- 文件路径 ---
CSV_FILE_PATH = r'./clean_data/clean_data_with_behavior.csv'
JSON_FILE_PATH = r'./clean_data/clean_data_with_person_information.json'
OUTPUT_FILE = r'./value_data/clean_data_with_value_reason.jsonl'


# --- 辅助函数 ---
def create_prompt(trajectory_description, personal_information, behavior):
    """根据输入信息创建提示"""
    prompt = f'''You are a psychologist. You will be given a trajectory description of a user over the course of a month, the user's personal information, and a specific behavior of the user.  
##TASK
Based on the trajectory description and personal information, please summarize the most relevant intrinsic value reasons behind the user's action in one sentence.
## input
Here is the user's trajectory description:
{trajectory_description}
Here is the user's personal information:
{personal_information}
Here is the user's behavior:
{behavior}
'''
    return prompt


# --- 工作函数（每个进程将执行此函数） ---
def process_row(args):
    """
    处理CSV文件中的单行数据。
    """
    index, row_data, user_info = args

    # 在每个工作进程中独立初始化客户端
    client = OpenAI()

    if not user_info:
        # 如果找不到对应的用户信息，则跳过
        print(f"Warning: UUID '{row_data['uuid']}' not found in JSON data. Skipping row {index}.")
        return None

    try:
        behavior_sentence = row_data['behavior']
        personal_info = user_info.get("personal_information_sentence", "Personal information not available.")
        category_info = user_info.get("level3_category_sentence", "Category statistics not available.")

        # 创建提示并调用API
        prompt = create_prompt(category_info, personal_info, behavior_sentence)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        value_reason = completion.choices[0].message.content

        # 准备结果
        result = {
            "id": index,
            "uuid": row_data['uuid'],
            "value_reason": value_reason
        }
        return result

    except Exception as e:
        print(f"Error processing row {index} (UUID: {row_data['uuid']}): {e}")
        return None


# --- 主程序 ---
if __name__ == "__main__":
    try:
        # 1. 在主进程中一次性加载所有数据
        print(f"Loading CSV file from: {CSV_FILE_PATH}")
        df = pd.read_csv(CSV_FILE_PATH, sep=',')

        print(f"Loading JSON file from: {JSON_FILE_PATH}")
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 2. 准备任务列表
        # to_dict('records') 将DataFrame转换为字典列表，更易于处理
        tasks = [
            (index, row, user_data.get(row['uuid']))
            for index, row in enumerate(df.to_dict('records'))
        ]
        print(f"Prepared {len(tasks)} tasks to process.")

        # 3. 自动检测可用核心数
        try:
            num_processes = len(os.sched_getaffinity(0))
        except AttributeError:
            num_processes = cpu_count()

        print(f"Starting parallel processing with {num_processes} cores... 🚀")

        # 清空或创建输出文件
        with open(OUTPUT_FILE, 'w') as f:
            pass

        # 4. 使用多进程池处理任务并写入结果
        with Pool(processes=num_processes) as pool:
            with jsonlines.open(OUTPUT_FILE, mode='a') as writer:
                # 使用tqdm显示进度条
                for result in tqdm(pool.imap_unordered(process_row, tasks), total=len(tasks)):
                    if result:
                        writer.write(result)

        print(f"\n✅ All tasks completed. Results saved to {OUTPUT_FILE}.")

    except FileNotFoundError as e:
        print(f"Error: File not found. Please check your file paths.")
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")