import json
import jsonlines
from openai import AsyncOpenAI
import os
import pandas as pd
import asyncio
import aiofiles

# 设置 API key
os.environ[
    'OPENAI_API_KEY'] = ""


# 异步客户端
client = AsyncOpenAI()

# 构造 prompt
def create_prompt(trajectory_description, personal_information, behavior):
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

# 异步 GPT 请求
async def generate_value_reason(i, prompt):
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content

# 异步处理每一行数据
async def process_row(index, row, user_data, output_file, semaphore):


    uuid = row['uuid']
    behavior_sentence = row['behavior']
    individual_info = user_data.get(uuid)

    if not individual_info:
        print(f"Warning: UUID '{uuid}' not found in JSON.")
        return

    personal_info = individual_info.get("personal_information_sentence", "Personal information not available.")
    category_info = individual_info.get("level3_category_sentence", "Category statistics not available.")
    prompt = create_prompt(category_info, personal_info, behavior_sentence)

    async with semaphore:
        result = await generate_value_reason(index, prompt)

    individual_info_new = {
        "id": index,
        "uuid": uuid,
        "value_reason": result
    }

    # 同步写入 JSONL（轻量操作）
    with jsonlines.open(output_file, mode='a') as writer:
        writer.write(individual_info_new)

    print(index)
    print("-----------------------------------------------------------------")

# 主函数
async def main(csv_path, json_path, output_file):
    try:
        print(f"Loading CSV from: {csv_path}")
        df = pd.read_csv(csv_path, sep=',')

        print(f"Loading JSON from: {json_path}")
        async with aiofiles.open(json_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            user_data = json.loads(content)

        print("\n--- Starting Async Data Processing ---\n")

        semaphore = asyncio.Semaphore(5)  # 控制并发数量
        tasks = [
            process_row(index, row, user_data, output_file, semaphore)
            for index, row in df.iterrows()
        ]

        await asyncio.gather(*tasks)

    except FileNotFoundError as e:
        print(f"Error: File not found. {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# 启动执行
if __name__ == "__main__":
    csv_file_path = './clean_data/clean_data_with_behavior.csv'
    json_file_path = './clean_data/clean_data_with_person_information.json'
    output_file = './value_data/clean_data_with_value_reason.jsonl'

    asyncio.run(main(csv_file_path, json_file_path, output_file))
