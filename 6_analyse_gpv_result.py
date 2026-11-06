import json
# JSON 文件路径
input_json_path = "./meta_data/all_value_list.json"

# 从 JSON 文件中读取列表
with open(input_json_path, 'r', encoding='utf-8') as jsonfile:
    our_values = json.load(jsonfile)

import json

# 替换成你的 .jsonl 文件路径
user_jsonl_path = "./gpv_result_new/value_language_result.jsonl"


# 用于存储所有 id 的列表
id_list = []

# 逐行读取并解析 jsonl
with open(user_jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():  # 跳过空行
            data = json.loads(line)
            id_list.append(data["person_id"])



result_value_dic={}
result_num_dic={}
result_dic={}
for id in id_list:
    result_value_dic[id]={value: 0 for value in our_values}
    result_num_dic[id]={value: 0 for value in our_values}
    result_dic[id]={value: 0 for value in our_values}

with open(user_jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():  # 跳过空行
            data = json.loads(line)
            key=data["person_id"]
            value=data["value"]
            for perception,res in value.items():
                relevant_values_list=res["relevant_values"]
                relevances_list = res["relevances"]
                valences_list = res["valences"]
                list_len=len(relevant_values_list)
                for i in range(0,list_len):
                    relevant_value=relevant_values_list[i]
                    relevance=relevances_list[i]
                    valence=valences_list[i]
                    result_value_dic[key][relevant_value]+=valence[0]-valence[1]
                    result_num_dic[key][relevant_value] += 1


for id in id_list:
    for k,v in result_dic[id].items():
        if(result_num_dic[id][k]!=0):
            result_dic[id][k]=result_value_dic[id][k]/result_num_dic[id][k]
        else:
            # 为空的情况
            result_dic[id][k]= None




# 将数据保存到JSON文件中
with open("./gpv_result_new/person_value.jsonl", 'w', encoding='utf-8') as json_file:
    json.dump(result_dic, json_file, ensure_ascii=False, indent=4)