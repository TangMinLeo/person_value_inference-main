import os
import pandas as pd
from scipy.spatial.distance import cdist
import numpy as np
import csv
import json
from collections import defaultdict


# 1.将所有csv合成一个，并将<7min的轨迹删除
def process_poi_data_first(folder_path, output_file_name="integrated_poi_data.csv"):
    """
    Processes multiple CSV files containing POI data:
    1. Integrates all CSV files into a single DataFrame.
    2. Removes rows where 'end_time' - 'start_time' equals 420000ms.
    3. Sorts the data by 'uuid' (user) and then by 'start_time'.

    Args:
        folder_path (str): The path to the folder containing the CSV files.
        output_file_name (str): The name of the output integrated CSV file.
    """
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.csv')]

    if not all_files:
        print(f"No CSV files found in the specified folder: {folder_path}")
        return

    # List to hold DataFrames from each CSV file
    df_list = []

    print(f"Found {len(all_files)} CSV files. Processing...")

    for file in all_files:
        try:
            df = pd.read_csv(file)
            df_list.append(df)
            print(f"Successfully loaded: {os.path.basename(file)}")
        except Exception as e:
            print(f"Error loading {os.path.basename(file)}: {e}")

    if not df_list:
        print("No data was loaded from any CSV file. Exiting.")
        return

    # 1. Integrate all CSV files into one DataFrame
    print("Integrating all CSV files...")
    integrated_df = pd.concat(df_list, ignore_index=True)
    print(f"Total rows after integration: {len(integrated_df)}")

    # Ensure 'start_time' and 'end_time' are numeric for calculation
    integrated_df['start_time'] = pd.to_numeric(integrated_df['start_time'], errors='coerce')
    integrated_df['end_time'] = pd.to_numeric(integrated_df['end_time'], errors='coerce')

    # Drop rows where start_time or end_time could not be converted to numeric
    integrated_df.dropna(subset=['start_time', 'end_time'], inplace=True)

    # 2. Delete data where stay_duration (end_time - start_time) is 420000ms
    print("Filtering out data with stay duration of 420000ms...")
    initial_rows = len(integrated_df)
    integrated_df['stay_duration_ms'] = integrated_df['end_time'] - integrated_df['start_time']
    integrated_df = integrated_df[integrated_df['stay_duration_ms']> 420000]
    filtered_rows = len(integrated_df)
    print(f"Removed {initial_rows - filtered_rows} rows with > 420000ms stay duration.")

    # Drop the temporary 'stay_duration_ms' column
    integrated_df.drop(columns=['stay_duration_ms'], inplace=True)

    # 3. Sort data by 'uuid' and then by 'start_time'
    print("Sorting data by 'uuid' and 'start_time'...")
    integrated_df.sort_values(by=['uuid', 'start_time'], inplace=True)
    print("Data sorting complete.")

    # Save the processed data to a new CSV file
    # output_path = os.path.join(folder_path, output_file_name)
    # output_path = os.path.normpath(os.path.join(folder_path, output_file_name))
    integrated_df.to_csv(output_file_name, index=False)
    print(f"Processed data saved to: {output_file_name}")

# 可选是否要合并数据
import pandas as pd

def merge_consecutive_records(input_csv_path, output_csv_path,ms):
    """
    读取签到数据，合并物理上连续、ms毫秒内的相同地点记录，并保存结果。

    Args:
        input_csv_path (str): 原始CSV文件路径
        output_csv_path (str): 合并后结果的CSV输出路径
    """
    try:
        df = pd.read_csv(input_csv_path, sep=',')
    except FileNotFoundError:
        print(f"错误：找不到文件 '{input_csv_path}'。请确保路径正确。")
        return
    except Exception as e:
        print(f"读取CSV时发生错误: {e}")
        print("请检查CSV文件格式和分隔符是否正确。")
        return

    print("文件加载后的列名:")
    print(df.columns)

    required_columns = ['uuid', 'poi_id', 'start_time', 'end_time', 'end_hour']
    if not all(col in df.columns for col in required_columns):
        print(f"错误: CSV文件中缺少必要的列。需要 {required_columns}，但只找到了 {list(df.columns)}")
        return

    df['start_time'] = pd.to_numeric(df['start_time'])
    df['end_time'] = pd.to_numeric(df['end_time'])

    

    if df.empty:
        print("\n没有可处理的数据。")
        return

    merged_records = []

    current_merged_record = df.iloc[0].to_dict()

    for i in range(1, len(df)):
        previous_record = current_merged_record
        current_row = df.iloc[i]
        time_diff = current_row['start_time'] - previous_record['end_time']

        if (current_row['uuid'] == previous_record['uuid'] and
            current_row['poi_id'] == previous_record['poi_id'] and
            time_diff < ms):
            current_merged_record['end_time'] = current_row['end_time']
            current_merged_record['end_hour'] = current_row['end_hour']
        else:
            merged_records.append(current_merged_record)
            current_merged_record = current_row.to_dict()

    merged_records.append(current_merged_record)

    if merged_records:
        merged_df = pd.DataFrame(merged_records)
        merged_df['stay_minutes'] = (merged_df['end_time'] - merged_df['start_time']) / (1000 * 60)
        merged_df['stay_minutes'] = merged_df['stay_minutes'].astype(int)

        print("\n原始DataFrame的前5行:")
        print(df.head())
        print("\n仅合并连续记录后的DataFrame的前5行:")
        print(merged_df.head())

        merged_df.to_csv(output_csv_path, sep=',', index=False)
        print(f"\n处理完成，结果已保存到: {output_csv_path}")
    else:
        print("\n没有可处理的数据。")




# 2.给出poi类别信息
def process_poi_data(csv1_path, csv2_path, output_csv_path):
    """
    处理签到记录和POI信息，更新poi_id为0的记录，并添加POI类别信息。

    Args:
        csv1_path (str): 签到记录CSV文件的路径。
        csv2_path (str): POI经纬度坐标CSV文件的路径。
        output_csv_path (str): 输出CSV文件的路径。
    """
    try:
        df_checkins = pd.read_csv(csv1_path)
        df_pois = pd.read_csv(csv2_path)
    except FileNotFoundError:
        print("错误：文件未找到，请检查CSV文件路径是否正确。")
        return
    except Exception as e:
        print(f"读取CSV文件时发生错误：{e}")
        return

    # 确保经纬度列是数值类型
    df_checkins['lnt_wgs84'] = pd.to_numeric(df_checkins['lnt_wgs84'], errors='coerce')
    df_checkins['lat_wgs84'] = pd.to_numeric(df_checkins['lat_wgs84'], errors='coerce')
    df_pois['longitude'] = pd.to_numeric(df_pois['longitude'], errors='coerce')
    df_pois['latitude'] = pd.to_numeric(df_pois['latitude'], errors='coerce')

    # 移除包含NaN经纬度的行，这些行无法用于距离计算
    df_checkins.dropna(subset=['lnt_wgs84', 'lat_wgs84'], inplace=True)
    df_pois.dropna(subset=['longitude', 'latitude'], inplace=True)

    # 合并POI信息，为非poi_id=0的记录添加类别
    # 这一步是为了处理需求2：对于csv1中poi_id非0的地点，将对应的类别信息加到文件中
    # 我们使用 `df_pois` 的副本以确保原始 df_pois 不受影响，尽管这里不是必须的
    df_checkins = pd.merge(
        df_checkins,
        df_pois[['p_id', 'first_category_name', 'second_category_name', 'third_category_name']],
        left_on='poi_id',
        right_on='p_id',
        how='left',
        suffixes=('_checkin', '_poi_merged_initial')
    )
    # 移除合并过程中产生的辅助 p_id 列
    df_checkins.drop(columns=['p_id'], errors='ignore', inplace=True)


    # 处理poi_id为0的记录
    zero_poi_indices = df_checkins[df_checkins['poi_id'] == 0].index

    if not zero_poi_indices.empty:
        poi_coords = df_pois[['longitude', 'latitude']].values
        
        # 预先为类别列分配空间，避免在循环中重复添加
        if 'first_category_name' not in df_checkins.columns:
            df_checkins['first_category_name'] = np.nan
        if 'second_category_name' not in df_checkins.columns:
            df_checkins['second_category_name'] = np.nan
        if 'third_category_name' not in df_checkins.columns:
            df_checkins['third_category_name'] = np.nan

        print(f"开始处理 {len(zero_poi_indices)} 条 poi_id 为 0 的记录...")
        for i, idx in enumerate(zero_poi_indices):
            # 获取当前签到记录的经纬度
            checkin_lon = df_checkins.loc[idx, 'lnt_wgs84']
            checkin_lat = df_checkins.loc[idx, 'lat_wgs84']

            # 确保经纬度有效
            if pd.isna(checkin_lon) or pd.isna(checkin_lat):
                continue

            current_checkin_coord = np.array([[checkin_lon, checkin_lat]])

            # 计算当前签到记录与所有POI的距离
            # 注意：这里 cdist 的第一个参数必须是二维数组
            distances = cdist(current_checkin_coord, poi_coords, metric='euclidean')

            # 找到最近的POI的索引
            closest_poi_index_in_pois = np.argmin(distances)

            # 获取最近POI的信息
            closest_poi_info = df_pois.iloc[closest_poi_index_in_pois]

            # 更新当前签到记录的 poi_id 和类别信息
            df_checkins.loc[idx, 'poi_id'] = closest_poi_info['p_id']
            df_checkins.loc[idx, 'first_category_name'] = closest_poi_info['first_category_name']
            df_checkins.loc[idx, 'second_category_name'] = closest_poi_info['second_category_name']
            df_checkins.loc[idx, 'third_category_name'] = closest_poi_info['third_category_name']

            if (i + 1) % 100 == 0:
                print(f"已处理 {i + 1} 条记录。")
        print("所有 poi_id 为 0 的记录处理完毕。")


    # 保存为新的CSV文件
    try:
        df_checkins.to_csv(output_csv_path, index=False)
        print(f"数据处理完成，已保存到：{output_csv_path}")
    except Exception as e:
        print(f"保存CSV文件时发生错误：{e}")

# 3.过滤分类为空的记录
def clean_and_report_empty_third_category(input_csv_path, output_csv_path):
    """
    删除third_category_name为空的行，并打印这些行对应的poi_id

    Args:
        input_csv_path (str): 输入CSV文件路径
        output_csv_path (str): 输出清理后CSV文件路径
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_csv_path)

        # 判断哪些行 third_category_name 是空（包括空字符串和缺失值）
        empty_mask = df['third_category_name'].isna() | (df['third_category_name'].astype(str).str.strip() == '')
        empty_rows = df[empty_mask]

        # 打印对应的poi_id
        if not empty_rows.empty:
            print("以下记录的 third_category_name 为空，对应的 poi_id 如下：")
            print(set(empty_rows['poi_id'].to_list()))
        else:
            print("没有 third_category_name 为空的记录。")

        # 删除这些行
        cleaned_df = df[~empty_mask]

        # 保存结果
        cleaned_df.to_csv(output_csv_path, index=False)
        print(f"清理完成，剩余 {len(cleaned_df)} 条记录，已保存到：{output_csv_path}")

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_csv_path}")
    except KeyError:
        print("错误：CSV文件中没有 'third_category_name' 列")
    except Exception as e:
        print(f"发生意外错误：{e}")


# 4.统计结果为json
# 读取CSV文件并统计分类次数
def parse_csv(file_path):
    user_data = defaultdict(lambda: {
        "一级类别统计": defaultdict(int),
        "二级类别统计": defaultdict(int),
        "三级类别统计": defaultdict(int),
        "POI ID统计": defaultdict(int)
    })

    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            uuid = row['uuid']
            first_category = row['first_category_name']
            second_category = row['second_category_name']
            third_category = row['third_category_name']
            poi_id = row['poi_id']
            # 更新每个分类的次数
            user_data[uuid]["一级类别统计"][first_category] += 1
            user_data[uuid]["二级类别统计"][second_category] += 1
            user_data[uuid]["三级类别统计"][third_category] += 1
            user_data[uuid]["POI ID统计"][poi_id] += 1

    return user_data

# 将统计结果保存为JSON文件
def save_to_json(user_data, output_file):
    with open(output_file, mode='w', encoding='utf-8') as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

# 5.得到个人信息和基于三级分类的轨迹描述
def process_personal_data(
    personal_info_csv_path,
    input_json_path,
    output_json_path,
    level3_translation_path,
    job_translation_path
):
    """
    Processes personal information from a CSV, merges it into an existing JSON,
    performs translations, and generates a descriptive sentence.

    Args:
        personal_info_csv_path (str): Path to the personal information CSV file.
        input_json_path (str): Path to the existing JSON file (e.g., user records).
        output_json_path (str): Path to save the new JSON file.
        level3_translation_path (str): Path to the level 3 category translation JSON.
        job_translation_path (str): Path to the job translation JSON.
    """

    # --- 1. Load Translation Dictionaries ---
    job_translations = {}
    try:
        with open(job_translation_path, 'r', encoding='utf-8') as f:
            job_translations = json.load(f)
        print(f"Successfully loaded job translations from '{job_translation_path}'")
    except FileNotFoundError:
        print(f"Error: Job translation file '{job_translation_path}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{job_translation_path}': {e}")
        return

    level3_translations = {}
    try:
        with open(level3_translation_path, 'r', encoding='utf-8') as f:
            level3_translations = json.load(f)
        print(f"Successfully loaded level 3 translations from '{level3_translation_path}'")
    except FileNotFoundError:
        print(f"Error: Level 3 translation file '{level3_translation_path}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{level3_translation_path}': {e}")
        return

    # --- 2. Load Personal Information from CSV ---
    personal_info_data = {}
    required_csv_fields = [
        'uuid', 'job', 'is_deliveryman', 'is_driver', 'income_price',
        'consumption_price', 'marry', 'kids_stage', 'have_kids',
        'education_level', 'age_group', 'gender', 'have_house', 'have_pet',
        'food_avg_price'
    ]

    try:
        with open(personal_info_csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            # Check if all required fields are in the CSV header
            if not all(field in reader.fieldnames for field in required_csv_fields):
                missing_fields = [field for field in required_csv_fields if field not in reader.fieldnames]
                print(f"Error: Missing required fields in CSV: {', '.join(missing_fields)}")
                return

            for row in reader:
                uuid = row['uuid']
                
                # Helper function to get value or None if empty string/whitespace
                def get_value_or_none(key):
                    value = row.get(key)
                    return value.strip() if value and value.strip() else None

                personal_info_dict = {
                    "job": get_value_or_none('job'),
                    "is_deliveryman": bool(int(get_value_or_none('is_deliveryman'))) if get_value_or_none('is_deliveryman') is not None else None,
                    "is_driver": bool(int(get_value_or_none('is_driver'))) if get_value_or_none('is_driver') is not None else None,
                    "income_price": float(get_value_or_none('income_price')) if get_value_or_none('income_price') is not None else None,
                    "consumption_price": float(get_value_or_none('consumption_price')) if get_value_or_none('consumption_price') is not None else None,
                    "marry": get_value_or_none('marry'),
                    "kids_stage": get_value_or_none('kids_stage'),
                    "have_kids": bool(int(get_value_or_none('have_kids'))) if get_value_or_none('have_kids') is not None else None,
                    "education_level": get_value_or_none('education_level'),
                    "age_group": get_value_or_none('age_group'),
                    "gender": get_value_or_none('gender'),
                    "have_house": bool(int(get_value_or_none('have_house'))) if get_value_or_none('have_house') is not None else None,
                    "have_pet": bool(int(get_value_or_none('have_pet'))) if get_value_or_none('have_pet') is not None else None,
                    "food_avg_price": float(get_value_or_none('food_avg_price')) if get_value_or_none('food_avg_price') is not None else None,
                }
                personal_info_data[uuid] = personal_info_dict
        print(f"Successfully loaded personal information from '{personal_info_csv_path}'")
    except FileNotFoundError:
        print(f"Error: Personal information CSV file '{personal_info_csv_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # --- 3. Load and Process Existing JSON Data ---
    user_records = {}
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            user_records = json.load(f)
        print(f"Successfully loaded user records from '{input_json_path}'")
    except FileNotFoundError:
        print(f"Error: Input JSON file '{input_json_path}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{input_json_path}': {e}")
        return

    # --- 4. Merge, Translate, and Generate Sentence ---
    for uuid, record in user_records.items():
        if uuid in personal_info_data:
            personal_info = personal_info_data[uuid]

            # 1. Add personal_information field
            record['personal_information'] = personal_info

            # 2. Translate 'job' in personal_information
            original_job = personal_info.get('job') # Use .get() to return None if key not present or value is None
            translated_job = job_translations.get(original_job, original_job) if original_job else None
            personal_info['job_en'] = translated_job

            # 3. Translate '三级类别统计' in the main record
            if '三级类别统计' in record and isinstance(record['三级类别统计'], dict):
                translated_level3_stats = {}
                for category_cn, count in record['三级类别统计'].items():
                    # Only translate if category_cn is not an empty string or None
                    translated_category = level3_translations.get(category_cn, category_cn) if category_cn else None
                    if translated_category: # Only add to translated stats if there's a valid category
                        translated_level3_stats[translated_category] = count
                record['三级类别统计_en'] = translated_level3_stats

            # 4. Create personal_information_sentence
            sentence_parts = []
            
            # Gender
            gender_val = personal_info.get('gender')
            if gender_val is not None:
                gender_map = {
                    '0': 'male',
                    '1': 'female',
                }
                sentence_parts.append(f"This user is {gender_map.get(str(gender_val), 'of unknown gender')}.")

            # Age Group
            age_group = personal_info.get('age_group')
            if age_group: # Checks if not None or empty string
                # Replace "岁" with "years old"
                age_group = age_group.replace('岁', ' years old') 
                sentence_parts.append(f"The age group is {age_group}.")

            # Job
            if translated_job:
                sentence_parts.append(f"The occupation is {translated_job}.")
            elif original_job: # If not translated but original job exists
                 sentence_parts.append(f"The occupation is {original_job}.")


            # Income and Consumption
            income = personal_info.get('income_price')
            consumption = personal_info.get('consumption_price')
            if income is not None:
                sentence_parts.append(f"The monthly income is approximately {income:.0f} RMB.")
            if consumption is not None:
                sentence_parts.append(f"The monthly consumption is approximately {consumption:.0f} RMB.")

            # Marriage and Kids
            marry_val = personal_info.get('marry')
            if marry_val is not None:
                marry_map = {
                    '0': 'unmarried',
                    '1': 'married'
                }
                sentence_parts.append(f"The marital status is {marry_map.get(str(marry_val), 'unknown marital status')}.")

                have_kids_val = personal_info.get('have_kids')
                if have_kids_val is not None:
                    has_kids_text = "has children" if have_kids_val else "does not have children"
                    sentence_parts.append(has_kids_text)
                    kids_stage_val = personal_info.get('kids_stage')
                    if have_kids_val and kids_stage_val:
                        sentence_parts.append(f", with children in the {kids_stage_val} stage.")
                    else:
                        sentence_parts.append(".")
                else: # if have_kids is None, but marry_val exists
                    sentence_parts.append(".") # Close the previous sentence part

            # Education Level
            edu_level_val = personal_info.get('education_level')
            if edu_level_val is not None:
                edu_map = {
                    '1': 'high school or below',
                    '2': 'associate degree',
                    '3': "bachelor's degree or above",
                }
                sentence_parts.append(f"The education level is {edu_map.get(str(edu_level_val), 'unknown education level')}.")

            # Housing and Pet
            have_house_val = personal_info.get('have_house')
            have_pet_val = personal_info.get('have_pet')

            house_texts = []
            if have_house_val is not None:
                house_texts.append("owns property" if have_house_val else "does not own property")
            
            pet_texts = []
            if have_pet_val is not None:
                pet_texts.append("has pets" if have_pet_val else "does not have pets")
            
            if house_texts and pet_texts:
                sentence_parts.append(f"This user {house_texts[0]} and {pet_texts[0]}.")
            elif house_texts:
                sentence_parts.append(f"This user {house_texts[0]}.")
            elif pet_texts:
                sentence_parts.append(f"This user {pet_texts[0]}.")


            # Food Average Price
            food_avg_price = personal_info.get('food_avg_price')
            if food_avg_price is not None:
                sentence_parts.append(f"Their average food consumption is {food_avg_price:.2f} RMB.")

            record['personal_information_sentence'] = " ".join(sentence_parts)

                        # --- Modified: Generate sentence for translated level 3 categories with 80% threshold ---
            level3_category_sentence_parts = []
            translated_level3_stats = record.get('三级类别统计_en')

            if translated_level3_stats and sum(translated_level3_stats.values()) > 0:
                sorted_categories = sorted(translated_level3_stats.items(), key=lambda item: item[1], reverse=True)
                total_visits = sum(translated_level3_stats.values())

                main_interests = []
                other_visits = []
                cumulative_visits = 0

                for category, count in sorted_categories:
                    if total_visits > 0 and (cumulative_visits / total_visits) < 0.80:
                        main_interests.append(f"{category} ({count} times)")
                        cumulative_visits += count
                    else:
                        other_visits.append(f"{category} ({count} times)")
                
                if main_interests:
                    level3_category_sentence_parts.append("The user's main interests, based on category statistics, include: ")
                    level3_category_sentence_parts.append(", ".join(main_interests))
                    level3_category_sentence_parts.append(".")
                
                if other_visits:
                    if main_interests: # If there were main interests, append to the existing sentence
                        level3_category_sentence_parts.append(" Other frequent visits include: ")
                    else: # If no main interests (e.g., all visits below 80% threshold by themselves)
                        level3_category_sentence_parts.append("Their frequent visits include: ")
                    level3_category_sentence_parts.append(", ".join(other_visits))
                    level3_category_sentence_parts.append(".")

                if not main_interests and not other_visits:
                     level3_category_sentence_parts.append("No specific category interests were recorded.")

            else:
                level3_category_sentence_parts.append("No detailed category statistics available.")
            
            record['level3_category_sentence'] = "".join(level3_category_sentence_parts)

    # --- 5. Save the modified JSON data ---
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(user_records, f, ensure_ascii=False, indent=4)
        print(f"Processed JSON data saved to '{output_json_path}'")
    except IOError as e:
        print(f"Error saving JSON to file '{output_json_path}': {e}")


# 6.得到每一条记录的自然语言描述
def process_and_translate_behavior_data(csv_file_path, json_translation_path, output_csv_path):
    """
    处理签到数据：翻译分类、格式化时间并生成行为描述。

    Args:
        csv_file_path (str): 输入的CSV文件路径
        json_translation_path (str): 分类翻译的JSON文件路径
        output_csv_path (str): 输出的CSV文件路径
    """
    try:
        # --- 1. 加载数据 ---
        print("正在加载数据文件...")
        df = pd.read_csv(csv_file_path, sep=',')

        with open(json_translation_path, 'r', encoding='utf-8') as f:
            category_translation = json.load(f)
        print("数据加载成功！")

        # --- 2. 翻译分类名称 ---
        print("正在翻译分类名称...")
        df['first_category_name_en'] = df['first_category_name'].map(category_translation).fillna(df['first_category_name'])
        df['second_category_name_en'] = df['second_category_name'].map(category_translation).fillna(df['second_category_name'])
        df['third_category_name_en'] = df['third_category_name'].map(category_translation).fillna(df['third_category_name'])
        print("分类名称翻译完成。")

        # --- 3. 转换时间格式 ---
        print("正在转换时间格式...")
        df['start_time_formatted'] = pd.to_datetime(df['start_time'], unit='ms').dt.strftime('%A %H:%M')
        df['end_time_formatted'] = pd.to_datetime(df['end_time'], unit='ms').dt.strftime('%A %H:%M')
        print("时间格式转换完成。")

        # --- 4. 生成行为描述 ---
        print("正在生成行为描述...")

        def generate_behavior(row):
            stay_minutes_int = int(row['stay_minutes'])
            return (f"user stayed at {row['third_category_name_en']} "
                    f"from {row['start_time_formatted']} to {row['end_time_formatted']} "
                    f"for {stay_minutes_int} minutes.")

        df['behavior'] = df.apply(generate_behavior, axis=1)
        print("行为描述生成完成。")

        # --- 5. 保存结果 ---
        print(f"正在将处理结果保存到 {output_csv_path}...")
        output_columns = [
            'uuid', 'poi_id', 'start_time', 'end_time', 'stay_minutes',
            'start_time_formatted', 'end_time_formatted',
            'first_category_name', 'first_category_name_en',
            'second_category_name', 'second_category_name_en',
            'third_category_name', 'third_category_name_en',
            'behavior'
        ]
        final_df = df[output_columns]
        final_df.to_csv(output_csv_path, index=False, sep=',', encoding='utf-8-sig')

        print("\n处理完成！")
        print("\n处理后数据的前5行预览:")
        print(final_df.head())

    except FileNotFoundError:
        print(f"错误：找不到文件。请检查路径 '{csv_file_path}' 或 '{json_translation_path}' 是否正确。")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")


if __name__ == "__main__":
    # 自动创建所有用到的输出目录
    output_dirs = [
        "./clean_data_new",
        "./parsing_data_new",
        "./gpv_result_new",
        "./value_data_new",
        "./meta_data_new"
    ]
    for path in output_dirs:
        os.makedirs(path, exist_ok=True)

    # 1.合并+过滤7min以下数据
    folder_containing_csvs = r"D:\BaiduNetdiskDownload\trace20250616\ods_bd_person_trajectory"
    clean_data_output_file="./clean_data_new/clean_data.csv"
    process_poi_data_first(folder_containing_csvs, clean_data_output_file)

#     # 可选：合并数据
#     clean_merge_data_output_file="./clean_data/clean_data_merge.csv"
#     ms=60*60*1000
#     merge_consecutive_records(
#     clean_data_output_file,
#     clean_merge_data_output_file,
#     ms
# )

    # 2.给出poi类别信息
    poi_category_file = './meta_data/_ods_bd_poi__202506201108.csv'
    clean_data_with_category_output_file = './clean_data_new/clean_data_with_category.csv'
    process_poi_data(clean_data_output_file, poi_category_file, clean_data_with_category_output_file)
    # process_poi_data(clean_merge_data_output_file, poi_category_file, clean_data_with_category_output_file)

    # 3.过滤分类为空的记录
    clean_data_with_category_delete_none_output_path = './clean_data_new/clean_data_with_category_delete_none.csv'
    clean_and_report_empty_third_category(clean_data_with_category_output_file, clean_data_with_category_delete_none_output_path)

    # 4.统计结果为json
    output_json = './clean_data_new/clean_data_with_category_delete_none.json'  # 输出的JSON文件路径
    user_data = parse_csv(clean_data_with_category_delete_none_output_path)
    save_to_json(user_data, output_json)
    print(f"数据已成功保存到 {output_json}")

    # 5.得到个人信息和基于三级分类的轨迹描述
    personal_info_csv = "./ods_bd_user_profile/part-00000-22c5e68b-2c8f-40c8-9f41-8d336f490775-c000.csv"
    output_processed_json = "./clean_data_new/clean_data_with_person_information.json"
    level3_trans_json = "./meta_data/poi_dict.json"
    job_trans_json = "./meta_data/job_dict.json"


    # --- Run the processing function ---
    process_personal_data(
        personal_info_csv,
        output_json,
        output_processed_json,
        level3_trans_json,
        job_trans_json
    )

    # 6.得到每一条记录的自然语言描述
    process_and_translate_behavior_data(
    csv_file_path=clean_data_with_category_delete_none_output_path,
    json_translation_path='./meta_data/poi_dict.json',
    output_csv_path='./clean_data_new/clean_data_with_behavior.csv'
    )
