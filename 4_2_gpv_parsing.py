import json
from gpv.gpv import GPV
import os

os.environ[
    'OPENAI_API_KEY'] = ""


# "./value_data/clean_data_with_value_language.jsonl"，'./value_data/clean_data_with_value_reason.jsonl'
# file_path = "./value_data/clean_data_with_value_language.jsonl"
# output_file="./parsing_data/clean_data_with_value_language_parsing.jsonl"
file_path = "./value_data_new/clean_data_with_value_reason_async.jsonl"
output_file="./parsing_data_new/clean_data_with_value_reason_parsing_async.jsonl"

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
            
        try:
            data = json.loads(line.strip())
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            continue
        
        # 现在 data 是一个 dict，可以访问里面的字段
        print(data["id"])
        
        id_ = int(data["id"])
        if id_ < 356 and id_ != 349:
            continue

        gpv = GPV(parsing_model_name="/root/kube-user/Qwen3.8-27B",use_flash=False)
        # print(answer)
        text= data["value_reason"]
        results = gpv.parse_texts([text])
        # print(results[0])
        data["perceptions"] = results[0]  # 存储GPV结果

        with open(output_file, 'a', encoding='utf-8') as outfile:
            json.dump(data, outfile, ensure_ascii=False)
            outfile.write('\n')  # 正确地写入换行