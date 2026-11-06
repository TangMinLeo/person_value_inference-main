FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# ========== 环境变量 ==========
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TORCH_CUDA_ARCH_LIST=Auto \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/app/cache/huggingface \
    TZ=Asia/Shanghai

# ========== 系统依赖（最小化安装，合并单层） ==========
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
        tzdata \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-distutils \
        python3.11-venv \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

# ========== pip（Python 3.11 专用，通过 ensurepip 引导安装） ==========
RUN python -m ensurepip --upgrade \
    && python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# ========== 工作目录 ==========
WORKDIR /app

# ========== 安装 Python 依赖（使用 gpv 子项目的完整依赖列表） ==========
COPY gpv/requirements.txt /app/gpv-requirements.txt
RUN pip install --no-cache-dir -r /app/gpv-requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 补充根目录 requirements.txt 中的额外依赖
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装翻译服务额外依赖
RUN pip install --no-cache-dir fastapi uvicorn aiofiles dashscope -i https://pypi.tuna.tsinghua.edu.cn/simple

# ========== 复制项目代码 ==========
COPY . /app/

# ========== 创建必要的输出目录 ==========
RUN mkdir -p /app/parsing_data /app/gpv_result /app/cache/huggingface

# ========== 暴露翻译 API 端口 ==========
EXPOSE 9970

# ========== 默认命令 ==========
CMD ["bash"]

# ============================================================
# 构建镜像命令：docker build -t person-value-inference:vlee1.0 .
#
# 运行方式：
#   有 GPU：docker run --gpus all -it --rm -p 9970:9970 person-value-inference:vlee1.0
#   无 GPU：docker run -it --rm -p 9970:9970 person-value-inference:vlee1.0
#
# 若需传入 API Key：
#   docker run --gpus all -it --rm -p 9970:9970 \
#       -e OPENAI_API_KEY=your_key \
#       -e DASHSCOPE_API_KEY=your_key \
#       person-value-inference:vlee1.0
#
# 设备检测逻辑（PyTorch 自动 fallback CPU）：
#   import torch
#   device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ============================================================