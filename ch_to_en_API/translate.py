"""
精简版JSON文件翻译脚本
文件名: translate.py
"""
import json
import requests
import time


def contains_chinese(text):
    """检查是否包含中文"""
    return any('\u4e00' <= char <= '\u9fff' for char in str(text))


def translate_text(text, api_url="http://localhost:9970/translate"):
    """调用API翻译文本"""
    try:
        response = requests.post(api_url, json={"text": text}, timeout=10)
        if response.status_code == 200:
            return response.json()["translation"]
        else:
            print(f"翻译失败: {text}")
            return text
    except Exception as e:
        print(f"API调用失败: {e}")
        return text


def translate_json_file(input_file, output_file=None):
    """翻译JSON文件"""

    # 读取文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"开始翻译文件: {input_file}")

    # 收集所有中文文本
    chinese_texts = set()

    def collect_chinese(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if contains_chinese(key):
                    chinese_texts.add(key)
                collect_chinese(value)
        elif isinstance(obj, list):
            for item in obj:
                collect_chinese(item)
        elif isinstance(obj, str) and contains_chinese(obj):
            chinese_texts.add(obj)

    collect_chinese(data)

    if not chinese_texts:
        print("未找到中文文本")
        return

    print(f"找到 {len(chinese_texts)} 个中文文本，开始翻译...")

    # 翻译所有中文文本
    translations = {}
    for i, text in enumerate(chinese_texts, 1):
        print(f"翻译进度 {i}/{len(chinese_texts)}: {text}")
        translations[text] = translate_text(text)
        time.sleep(0.1)  # 避免请求过快

    # 替换原数据中的中文
    def replace_chinese(obj):
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                new_key = translations.get(key, key)
                new_dict[new_key] = replace_chinese(value)
            return new_dict
        elif isinstance(obj, list):
            return [replace_chinese(item) for item in obj]
        elif isinstance(obj, str):
            return translations.get(obj, obj)
        else:
            return obj

    translated_data = replace_chinese(data)

    # 保存结果
    if output_file is None:
        output_file = input_file.replace('.json', '_translated.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=2)

    print(f"翻译完成！保存到: {output_file}")

    # 保存翻译对照表
    mapping_file = output_file.replace('.json', '_mapping.json')
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"翻译对照表: {mapping_file}")


if __name__ == "__main__":
    # 检查API服务是否运行
    try:
        response = requests.get("http://localhost:9970/")
        if response.status_code != 200:
            print("API服务未运行，请先启动 server.py")
            exit(1)
    except:
        print("API服务未运行，请先启动 server.py")
        exit(1)

    # 翻译指定文件 - 修改这里的路径为你的文件路径
    input_file = "/root/autodl-tmp/users/xyh/beiwuyuan_poi_month_data/meta_data/job_dict_chinese_terms.json"
    translate_json_file(input_file)