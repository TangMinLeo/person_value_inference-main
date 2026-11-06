
import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# 设置HuggingFace镜像站点（解决网络连接问题）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 导入transformers
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# 加载模型（首次运行会从镜像站下载，约500MB）
print("正在加载模型...")
try:
    tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-zh-en")
    model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-zh-en")
    print("✅ 模型加载完成")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    print("请检查网络连接或尝试以下命令：")
    print("export HF_ENDPOINT=https://hf-mirror.com")
    exit(1)

app = FastAPI()


class InputData(BaseModel):
    text: str


@app.get('/')
async def index():
    return {
        "message": "中译英翻译API",
        "status": "运行中",
        "model": "Helsinki-NLP/opus-mt-zh-en",
        "mirror": "hf-mirror.com"
    }


@app.post('/translate')
async def translate(data: InputData):
    try:
        # 编码
        encoded = tokenizer([data.text], return_tensors="pt")
        # 翻译
        translation = model.generate(**encoded)
        # 解码
        result = tokenizer.batch_decode(translation, skip_special_tokens=True)[0]

        print(f"翻译: '{data.text}' -> '{result}'")
        return {"original": data.text, "translation": result}

    except Exception as e:
        print(f"翻译错误: {e}")
        return {"error": str(e)}


if __name__ == '__main__':
    print("启动翻译服务...")
    print("使用镜像站点: https://hf-mirror.com")
    uvicorn.run(app=app, host='0.0.0.0', port=9970)