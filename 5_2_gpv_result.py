import os
import sys
import json
from gpv.gpv import GPV

# 指定使用 GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "0"


with open("./meta_data/all_value_list.json", "r", encoding="utf-8") as file:
    values = json.load(file)



# # gpv = GPV()
# gpv = GPV(parsing_model_name="/root/kube-user/Qwen3.8-27B", measurement_model_name="./models/ValueLlama-3-8B")

# file_path="./parsing_data_new/clean_data_with_value_language_parsing.jsonl"
# output_file="./gpv_result_new/value_language_result.jsonl"

# with open(file_path, "r", encoding="utf-8") as f:
#     for line in f:
#         if line.strip():  # 忽略空行
#             user_data = json.loads(line)
#             perceptions=user_data["perceptions"]
#             if perceptions==[]:
#                 continue
#             person_value = gpv.measure_perceptions(perceptions, values)
#             user_data["value"]=person_value

#             # 将处理后的数据写入输出文件
#             with open(output_file, 'a', encoding='utf-8') as outfile:
#                 json.dump(user_data, outfile, ensure_ascii=False)  # 删除 indent=4
#                 outfile.write('\n')

#             print(user_data["id"])

            
import json

# input_path = './clean_data/clean_data_with_value_reason_parsing.jsonl'
input_path = './gpv_result_new/value_language_result.jsonl'
output_path = './gpv_result_new/value_reason_result.jsonl'

with open(input_path, 'r', encoding='utf-8') as infile, \
     open(output_path, 'w', encoding='utf-8') as outfile:
    
    for line in infile:
        item = json.loads(line)
        value_dict = item.get("value", {})

        # 收集所有 relevant_values
        value_set = set()
        for v in value_dict.values():
            relevant = v.get("relevant_values", [])
            value_set.update(relevant)
        
        # 构造新的输出 dict
        new_item = {
            "id": item["id"],
            "value_set": list(value_set)
        }

        # 写入新文件
        outfile.write(json.dumps(new_item, ensure_ascii=False) + "\n")
