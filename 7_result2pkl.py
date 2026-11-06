import json
import pickle

def transform_value(v):
    if v is None:
        return 0.0
    else:
        return float(v)
    # elif v > 0:
    #     return 1
    # elif v < 0:
    #     return 0.33
    # else:  # v == 0
    #     return 0.66

# 1. 读取 JSON 文件
input_file="./gpv_result_new/person_value.jsonl"
with open(input_file, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 2. 转换为 Dict[str, list] 并应用转换规则
uuid_to_vector = {
    uuid: [transform_value(v) for v in values.values()]
    for uuid, values in raw_data.items()
}

output_pkl_file="./gpv_result_new/person_value_vector.pkl"
# 3. 保存为 .pkl 文件
with open(output_pkl_file, 'wb') as f:
    pickle.dump(uuid_to_vector, f)

output_jsonl_file="./gpv_result_new/person_value_vector.jsonl"
# 4. 保存为 .jsonl 文件（每行为一个 dict）
with open(output_jsonl_file, 'w', encoding='utf-8') as f:
    for uuid, vector in uuid_to_vector.items():
        json_line = json.dumps({uuid: vector}, ensure_ascii=False)
        f.write(json_line + '\n')

print(f"✅ 数据已保存为 {output_pkl_file} 和 {output_jsonl_file}")
