import requests
import os
from dotenv import load_dotenv
import time




def server_llm_invoke(prompt: str = "Hello, respond with one word.") -> dict:
    """
    通过 HTTP request 直接测试 Agnes-2.0-flash 模型
    """
    api_key = os.environ.get("OPENAI_API_KEY", "sk-REPLACED")
    url = "https://apihub.agnes-ai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": "agnes-2.0-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        # "max_tokens": 256,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        # 提取核心返回内容
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        print(f" 模型回复: {content}")
        print(f" Token用量: prompt={usage.get('prompt_tokens')}, "
              f"completion={usage.get('completion_tokens')}, "
              f"total={usage.get('total_tokens')}")

        time.sleep(1)

        return content

    except requests.exceptions.HTTPError as e:
        print(f" API请求失败 [{e.response.status_code}]: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        print(f" 网络请求异常: {e}")
        raise

def server_llm_invoke2(prompt: str = "Hello, respond with one word.") -> dict:
    """
    通过 HTTP request 直接测试 DeepSeek-V4-Flash 模型
    """
    api_key = os.environ.get("OPENAI_API_KEY2", "sk-REPLACED")
    url = "https://api-inference.modelscope.cn/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": "deepseek-ai/DeepSeek-V4-Flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        # "max_tokens": 256,
        "stream": False
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        # print("debug: ", result)
        # 提取核心返回内容
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        print(f" 模型回复: {content}")
        print(f" Token用量: prompt={usage.get('prompt_tokens')}, "
              f"completion={usage.get('completion_tokens')}, "
              f"total={usage.get('total_tokens')}")

        time.sleep(1)

        return content

    except requests.exceptions.HTTPError as e:
        print(f" API请求失败 [{e.response.status_code}]: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        print(f" 网络请求异常: {e}")
        raise

def test():
    from openai import OpenAI

    client = OpenAI(
        base_url='https://api-inference.modelscope.cn/v1',
        api_key='',  # ModelScope Token
    )

    response = client.chat.completions.create(
        model='deepseek-ai/DeepSeek-V4-Flash',  # ModelScope Model-Id, required
        messages=[
            {
                'role': 'user',
                'content': '你好'
            }
        ],
        stream=False
    )

    print(response.choices[0].message.reasoning_content)
    print('\n\n === Final Answer ===\n')
    print(response.choices[0].message.content)


load_dotenv(override=True)
if __name__ == "__main__":
    # 从 .env 文件加载环境变量（OPENAI_API_KEY 放在 .env 中）
    load_dotenv(override=True)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")


    # server_llm_invoke("用一句话介绍你自己")
    server_llm_invoke2("用一句话介绍你自己")
    # test()
