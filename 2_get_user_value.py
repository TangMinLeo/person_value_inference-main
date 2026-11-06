import json
import jsonlines
from openai import OpenAI
import os

os.environ[
    'OPENAI_API_KEY'] = ""
# 设置 API key
os.environ[
    'OPENAI_API_KEY'] = "sk-REPLACED"



client = OpenAI()





# 模拟 GPT 生成轨迹描述的函数（你应替换为真实的 GPT 调用）
def generate_trajectory_description(i,id,prompt,default_output):
    completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
    result = completion.choices[0].message.content

    return result




def create_prompt(trajectory_description,personal_information):
    prompt=f'''You are a psychologist. You will be given a trajectory description of a user over the course of a month, along with the user’s personal information. 
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







# 读取原始 JSON 文件
input_file = "./clean_data/clean_data_with_person_information.json"
output_file = "./value_data/clean_data_with_value_language.jsonl"

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 写入 JSONL 输出
i=0

for person_id, info in data.items():
    trajectory_description = info.get("level3_category_sentence", {})
    personal_information = info.get("personal_information_sentence", {})
    prompt=create_prompt(trajectory_description,personal_information)
    default_output=personal_information+"\n"+trajectory_description
    trajectory = generate_trajectory_description(i,person_id,prompt,default_output)
    result={}
    result['person_id'] = person_id
    result["id"] = i
    result["origin_information"]=info
    result["trajectory_description"] = trajectory

    with jsonlines.open(output_file, mode='a') as writer:
        writer.write(result)
    print(i,person_id)
    print("-----------------------------------------------------------------")

