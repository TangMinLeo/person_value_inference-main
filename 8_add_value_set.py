import pandas as pd
import json

# 读取CSV文件
csv_path = './clean_data/clean_data_with_category_delete_none.csv'
df = pd.read_csv(csv_path)

# 初始化空列
df["value_set"] = ""

jsonl_path="./gpv_result/value_reason_result.jsonl"
jsonl_path_value_set = './gpv_result/value_set.jsonl'

with open(jsonl_path, 'r', encoding='utf-8') as infile, \
     open(jsonl_path_value_set, 'w', encoding='utf-8') as outfile:
    
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


# 读取JSONL并更新DataFrame
with open(jsonl_path_value_set, 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        row_index = obj["id"]
        if row_index < len(df):
            df.at[row_index, "value_set"] = ", ".join(obj["value_set"])
        else:
            print(f"警告：id={obj['id']} 的目标行号 {row_index} 超出CSV范围")

output_file="./gpv_result/value_set.csv"
# 输出新CSV
df.to_csv(output_file, index=False)

# 打印前100行
print(df.head(100).to_string(index=False))
