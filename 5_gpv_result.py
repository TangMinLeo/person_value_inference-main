import os
import sys
import json
from gpv.gpv import GPV

# 指定使用 GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "0"


with open("./meta_data/all_value_list.json", "r", encoding="utf-8") as file:
    values = json.load(file)



gpv = GPV(parsing_model_name="/root/kube-user/Qwen3.8-27B", measurement_model_name="./models/ValueLlama-3-8B")
# gpv = GPV(measurement_model_name="models/Qwen_Qwen3.5_0.8B/snapshots/master") #



file_path="./parsing_data_new/clean_data_with_value_language_parsing.jsonl"
output_file="./gpv_result_new/value_language_result.jsonl"

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():  # 忽略空行
            user_data = json.loads(line)
            perceptions=user_data["perceptions"]
            if perceptions==[]:
                continue
            person_value = gpv.measure_perceptions(perceptions, values)
            user_data["value"]=person_value
            # 将处理后的数据写入输出文件
            with open(output_file, 'a', encoding='utf-8') as outfile:
                json.dump(user_data, outfile, ensure_ascii=False)  # 删除 indent=4
                outfile.write('\n')

            print(user_data["id"])