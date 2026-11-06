import asyncio
import json
import jsonlines
import aiofiles
import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Message
import aiohttp

# 设置 API Key
# 建议使用环境变量等更安全的方式管理 API Key
dashscope.api_key = ''

LOCAL_LLM_URL = "http://172.16.41.254:30245/v1/chat/completions"  # 本地模型接口地址

# 创建提示词
def create_prompt(trajectory_description, personal_information):
    return f'''You are a psychologist. You will be given a trajectory description of a user over the course of a month, along with the user’s personal information. 
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


async def generate_trajectory_description(i, person_id, prompt, default_output):
    payload = {
        "model": "/root/kube-user/Qwen3.8-27B",
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(LOCAL_LLM_URL, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Error] index={i}, person_id={person_id}: {e}")
        return default_output



# # 异步生成 Qwen 内容
# async def generate_trajectory_description(i, person_id, prompt, default_output):
#     try:
#         # dashscope.Generation.call 是一个同步阻塞调用。
#         # 使用 asyncio.to_thread 将其放入一个单独的线程中运行，以避免阻塞事件循环。
#         response = await asyncio.to_thread(
#             Generation.call,
#             model="qwen-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             result_format="message",
#         )
#         return response["output"]["choices"][0]["message"]["content"]
#     except Exception as e:
#         print(f"[Error] index={i}, person_id={person_id}: {e}")
#         return default_output


# 异步处理每条数据
async def process_person(i, person_id, info, output_file):
    trajectory_description = info.get("level3_category_sentence", "")
    personal_information = info.get("personal_information_sentence", "")
    prompt = create_prompt(trajectory_description, personal_information)
    default_output = personal_information + "\n" + trajectory_description
    trajectory = await generate_trajectory_description(i, person_id, prompt, default_output)

    result = {
        'person_id': person_id,
        "id": i,
        "origin_information": info,
        "trajectory_description": trajectory
    }

    # 异步写入文件
    async with aiofiles.open(output_file, mode='a', encoding='utf-8') as writer:
        await writer.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(i, person_id)
    print("-----------------------------------------------------------------")


# 主程序
async def main():
    input_file = "./clean_data_new/clean_data_with_person_information.json"
    output_file = "./value_data_new/clean_data_with_value_language.jsonl"
    
    f1 = open('./clean_data_new/calculated_ids.json', "r", encoding="utf-8")
    uuid_list = json.load(f1)
    f1.close()

    # 异步读取文件
    async with aiofiles.open(input_file, 'r', encoding='utf-8') as f:
        content = await f.read()
        data = json.loads(content)

    # 使用 Semaphore 限制并发数量为 5
    semaphore = asyncio.Semaphore(5)
    tasks = []

    async def sem_task(i, person_id, info):
        async with semaphore:
            await process_person(i, person_id, info, output_file)

    for i, (person_id, info) in enumerate(data.items()):
        if person_id not in uuid_list:
            tasks.append(sem_task(i, person_id, info))

    # 并发执行所有任务
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    # 确保在 Windows 上也能正确运行
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())