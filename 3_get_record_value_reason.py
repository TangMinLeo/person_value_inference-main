import json
import jsonlines
from openai import OpenAI
import os
import pandas as pd


os.environ[
    'OPENAI_API_KEY'] = ""


client = OpenAI()


# 模拟 GPT 生成轨迹描述的函数（你应替换为真实的 GPT 调用）
def generate_value_reason(i,prompt):
    completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
    result = completion.choices[0].message.content

    return result



def create_prompt(trajectory_description,personal_information,behavior):
    prompt=f'''You are a psychologist. You will be given a trajectory description of a user over the course of a month, the user's personal information, and a specific behavior of the user.  
##TASK
Based on the trajectory description and personal information, please summarize the most relevant intrinsic value reasons behind the user's action in one sentence.
## input
Here is the user's trajectory description:
{trajectory_description}
Here is the user's personal information:
{personal_information}
Here is the user's behavior:
{behavior}
'''
    return prompt


def process_data(csv_path, json_path,output_file):
    """
    Reads data from a CSV and a JSON file, combines sentences, and prints the result.

    Args:
        csv_path (str): The file path for the input CSV file.
        json_path (str): The file path for the input JSON file.
    """
    try:
        # --- 1. Load the data files ---
        print(f"Loading CSV file from: {csv_path}")
        # Use sep='\t' because the sample data is tab-separated.
        df = pd.read_csv(csv_path, sep=',')

        print(f"Loading JSON file from: {json_path}")
        # Open the JSON file with utf-8 encoding to handle Chinese characters.
        with open(json_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        print("\n--- Starting Data Processing ---\n")

        # --- 2. Iterate through each row of the CSV DataFrame ---
        for index, row in df.iterrows():
            uuid = row['uuid']
            behavior_sentence = row['behavior']

            # --- 3. Look up the uuid in the JSON data ---
            # Use .get() to safely access the dictionary, preventing errors if a uuid is not found.
            individual_info = user_data.get(uuid)

            if individual_info:
                # Safely get the sentences from the user's data.
                # Provide a default message if a key is missing.
                individual_info_new = {"id": index, "uuid": uuid}
                personal_info = individual_info.get("personal_information_sentence",
                                                    "Personal information not available.")
                category_info = individual_info.get("level3_category_sentence", "Category statistics not available.")

                # --- 4. Concatenate the three sentences ---
                prompt=create_prompt(category_info,personal_info,behavior_sentence)
                result=generate_value_reason(index, prompt)
                individual_info_new["value_reason"] = result
                with jsonlines.open(output_file, mode='a') as writer:
                    writer.write(individual_info_new)
                print(index)
                print("-----------------------------------------------------------------")


            else:
                # Handle cases where the uuid from the CSV is not found in the JSON file.
                print(f"--- Record for UUID: {uuid} ---")
                print(f"Warning: UUID '{uuid}' not found in the JSON data.")
                print("\n")

    except FileNotFoundError as e:
        print(f"Error: File not found. Please check your file paths.")
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Main execution block ---
if __name__ == "__main__":
    # Please replace these with the actual paths to your files.
    csv_file_path = r'./clean_data/clean_data_with_behavior.csv'  # 替换为你的CSV文件路径
    json_file_path = r'./clean_data/clean_data_with_person_information.json'  # 替换为你的JSON文件路径
    output_file=r'./value_data/clean_data_with_value_reason.jsonl'
    process_data(csv_file_path, json_file_path,output_file)
