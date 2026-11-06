import asyncio
import json
import pandas as pd
import aiofiles  # For async file operations
import dashscope
import aiohttp

# --- 1. Configure API ---
# It's safer to use environment variables for API keys
# os.environ['DASHSCOPE_API_KEY'] = "YOUR_QWEN_API_KEY"
dashscope.api_key = ''

LOCAL_LLM_URL = "http://172.16.41.254:30245/v1/chat/completions"  # 本地模型接口地址

# --- 2. Define Helper Functions ---

def create_prompt(trajectory_description, personal_information, behavior):
    """Creates the prompt for the language model."""
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


# async def generate_value_reason_async(index, prompt):
#     """
#     Asynchronously generates a value reason using the Qwen model.

#     The dashscope.Generation.call is a blocking I/O function. We use
#     asyncio.to_thread() to run it in a separate thread, which prevents it
#     from blocking the main asyncio event loop.
#     """
#     try:
#         response = await asyncio.to_thread(
#             dashscope.Generation.call,
#             model="qwen-turbo",  # Or any other suitable Qwen model
#             prompt=prompt
#         )
#         if response.status_code == 200:
#             return response.output.text
#         else:
#             print(f"[API Error] Index {index}: {response.message}")
#             return None
#     except Exception as e:
#         print(f"[Error] Index {index} failed: {e}")
#         return None


async def generate_value_reason_async(index, prompt):
    """
    Asynchronously generates a value reason using the Qwen model.

    The dashscope.Generation.call is a blocking I/O function. We use
    asyncio.to_thread() to run it in a separate thread, which prevents it
    from blocking the main asyncio event loop.
    """
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
        print(f"[Error] Index {index} failed: {e}")
        return None




async def process_row_async(semaphore, index, row, user_data, output_file):
    """
    Processes a single row of data: creates a prompt, calls the API, and writes the result.
    The semaphore limits how many of these functions can run at the same time.
    """
    async with semaphore:
        uuid = row['uuid']
        behavior_sentence = row['behavior']
        individual_info = user_data.get(uuid)

        if not individual_info:
            print(f"Warning: UUID '{uuid}' (Index {index}) not found in JSON data.")
            return

        personal_info = individual_info.get("personal_information_sentence", "Personal information not available.")
        category_info = individual_info.get("level3_category_sentence", "Category statistics not available.")

        prompt = create_prompt(category_info, personal_info, behavior_sentence)
        value_reason = await generate_value_reason_async(index, prompt)

        if value_reason:
            result_data = {
                "id": index,
                "uuid": uuid,
                "value_reason": value_reason.strip()
            }
            # Use aiofiles for asynchronous file writing
            async with aiofiles.open(output_file, mode='a', encoding='utf-8') as f:
                await f.write(json.dumps(result_data, ensure_ascii=False) + '\n')

            print(f"Successfully processed Index: {index}")
            print("-----------------------------------------------------------------")


async def main():
    """Main function to orchestrate the data loading and concurrent processing."""
    csv_file_path = r'./clean_data/clean_data_with_behavior.csv'
    json_file_path = r'./clean_data/clean_data_with_person_information.json'
    output_file = r'./value_data_new/clean_data_with_value_reason_async.jsonl'

    # --- Load data synchronously (it's a one-time operation) ---
    print("Loading data files...")
    df = pd.read_csv(csv_file_path, sep=',')
    with open(json_file_path, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
    print("Data loading complete. Starting processing...")

    # --- Set up concurrent processing ---
    # Semaphore limits concurrent API calls to 10 to avoid rate limiting
    CONCURRENT_LIMIT = 10
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

    tasks = []
    for index, row in df.iterrows():
        # Create a task for each row
        task = process_row_async(semaphore, index, row, user_data, output_file)
        tasks.append(task)

    # Run all tasks concurrently
    await asyncio.gather(*tasks)
    print("\n--- All processing complete. ---")


# --- Main execution block ---
if __name__ == "__main__":
    asyncio.run(main())