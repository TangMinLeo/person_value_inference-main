import json
from gpv.gpv import GPV
import os
from dotenv import load_dotenv # pip install python-dotenv
load_dotenv(override=True)

print(f"OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY', 'NOT SET')[:20]}...")
print(f"OPENAI_BASE_URL: {os.environ.get('OPENAI_BASE_URL', 'NOT SET')}")



# file_path = "./clean_data/clean_data_with_value_language.jsonl"
file_path = "./value_data_new/clean_data_with_value_language.jsonl"
output_file="./parsing_data_new/clean_data_with_value_language_parsing.jsonl"


with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line.strip())
        # if data["id"]<=1078:
        #     continue
        # 现在 data 是一个 dict，可以访问里面的字段
        print(data["id"])

        # gpv = GPV()
        # gpv = GPV(parsing_model_name="agnes-2.0-flash",use_flash=False)
        # gpv = GPV(parsing_model_name="deepseek-ai/DeepSeek-V4-Flash",use_flash=False)
        gpv = GPV(parsing_model_name="/root/kube-user/Qwen3.8-27B",use_flash=False)

        # print(answer)
        text= "The user's personal information is: \n"+data["origin_information"]["personal_information_sentence"]+"\n"+"The user's behavioral traits is: \n"+data["trajectory_description"]
        results = gpv.parse_texts([text])
        # print(results[0])
        data["perceptions"] = results[0]  # 存储GPV结果

        with open(output_file, 'a', encoding='utf-8') as outfile:
            json.dump(data, outfile, ensure_ascii=False)
            outfile.write('\n')  # 正确地写入换行