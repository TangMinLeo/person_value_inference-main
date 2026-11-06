import json
import jsonlines
import asyncio
from openai import AsyncOpenAI
import os
import aiofiles

# 设置 API key
os.environ[
    'OPENAI_API_KEY'] = ""


# 异步客户端
client = AsyncOpenAI()

# 异步 GPT 请求
async def generate_trajectory_description(i, person_id, prompt, default_output):
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    result = completion.choices[0].message.content
    return result

# 构造提示词
def create_prompt(trajectory_description, personal_information):
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

# 异步处理单个用户数据
async def process_person(i, person_id, info, output_file):
    trajectory_description = info.get("level3_category_sentence", {})
    personal_information = info.get("personal_information_sentence", {})
    prompt = create_prompt(trajectory_description, personal_information)
    default_output = personal_information + "\n" + trajectory_description
    trajectory = await generate_trajectory_description(i, person_id, prompt, default_output)

    result = {
        'person_id': person_id,
        "id": i,
        "origin_information": info,
        "trajectory_description": trajectory
    }

    # 同步写入 JSONL
    with jsonlines.open(output_file, mode='a') as writer:
        writer.write(result)

    print(i, person_id)
    print("-----------------------------------------------------------------")

# 主函数
async def main():
    input_file = "./clean_data/clean_data_with_person_information.json"
    output_file = "./value_data/clean_data_with_value_language.jsonl"

    # 异步读取 JSON 文件
    async with aiofiles.open(input_file, 'r', encoding='utf-8') as f:
        content = await f.read()
        data = json.loads(content)

    # 创建任务并并发执行（限制并发数以控制 API 调用速率）
    tasks = []
    semaphore = asyncio.Semaphore(5)  # 限制并发数（例如最多5个同时）

    async def sem_task(i, person_id, info):
        async with semaphore:
            await process_person(i, person_id, info, output_file)

    for i, (person_id, info) in enumerate(data.items()):
        tasks.append(sem_task(i, person_id, info))

    await asyncio.gather(*tasks)

# 启动
if __name__ == "__main__":
    asyncio.run(main())
