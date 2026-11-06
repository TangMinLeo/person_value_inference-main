# AGENTS.md — ValueAssessment 项目指南

> 本文件面向 AI Coding Agent。阅读者默认对该项目一无所知。
> 原 `AGENTS.md` 不存在，本文档根据项目实际文件内容整理而成。

---

## 1. 项目概述

`ValueAssessment` 是一个基于用户轨迹数据推断个体/行为层面“价值观”的 Python 数据处理与 LLM 实验项目。

核心目标：

1. 读取用户的 POI 轨迹记录（`ods_bd_person_trajectory`）和个人画像（`ods_bd_user_profile`）。
2. 对轨迹进行清洗、POI 匹配、分类统计，并生成自然语言行为描述。
3. 调用大语言模型（GPT-4o-mini / Qwen）对用户行为进行“价值观语言”建模，以及对单条行为记录推断其内在价值动因。
4. 通过 [GPV (Goal-Perception-Value)](https://github.com/ValueByte-AI/gpv) 框架对 LLM 输出进行 parsing 与 measurement。
5. 输出可用于下游 POI 预测模型的价值向量（`person_value_vector.pkl`）以及记录级价值集合（`value_set.csv`）。

项目采用**纯脚本化、手动流水线**方式运行，没有正式的包管理、构建步骤、测试套件或 CI/CD。

---

## 2. 技术栈与依赖

### 2.1 编程语言

- Python 3（代码中使用 f-string、async/await、`multiprocessing` 等特性）

### 2.2 核心依赖（`requirements.txt`）

```text
pandas
scipy
numpy
jsonlines
```

### 2.3 其他实际使用的第三方库

| 库 | 用途 |
|---|---|
| `openai` | 调用 GPT-4o-mini |
| `dashscope` | 调用阿里通义千问 `qwen-turbo` |
| `aiofiles` | 异步文件写入 |
| `tqdm` | 多核版本进度条 |
| `transformers` | `ch_to_en_API` 本地中译英模型 |
| `fastapi` / `uvicorn` | 翻译微服务 |
| `requests` | 翻译客户端调用 |

### 2.4 外部模型与服务

- **OpenAI** `gpt-4o-mini`：用户级行为总结、单条记录价值动因推断、GPV parsing。
- **DashScope / Qwen** `qwen-turbo`：上述任务的替代异步后端。
- **Helsinki-NLP/opus-mt-zh-en**：本地中译英服务（约 500MB，首次自动下载）。
- **GPV + Value4AI/ValueLlama-3-8B**：对 parsing 得到的 `perceptions` 进行价值观测量，需要 GPU。

### 2.5 关键配置说明

- 没有 `pyproject.toml`、`setup.py`、`package.json`、`Makefile`、`Dockerfile`、`.gitignore` 或测试配置文件。
- 依赖直接写在 `requirements.txt` 中，GPV 相关依赖需参考其独立仓库的 `requirements.txt`。
- 多个脚本硬编码了 `OPENAI_API_KEY` 或 `dashscope.api_key`；Qwen 相关脚本当前 Key 为空字符串占位。

---

## 3. 目录结构与模块划分

```
/home/pku/python_project/ValueAssessment/
├── requirements.txt                 # 项目依赖
├── readme.txt                       # 中文项目说明（主要文档）
├── AGENTS.md                        # 本文件
│
├── 1_data_process.py                # 数据清洗与特征工程
├── 2_get_user_value*.py             # LLM：用户级价值观语言生成
├── 3_get_record_value_reason*.py    # LLM：记录级价值动因推断
├── 4_gpv_parsing*.py                # GPV parsing（用户级）
├── 4_2_gpv_parsing*.py              # GPV parsing（记录级）
├── 5_gpv_result*.py                 # GPV measurement（用户级）
├── 5_2_gpv_result.py                # GPV measurement + value_set（记录级）
├── 6_analyse_gpv_result.py          # 聚合用户级价值得分
├── 7_result2pkl.py                  # 生成 pkl/jsonl 向量
├── 8_add_value_set.py               # 把价值集合合并回原 CSV
│
├── ch_to_en_API/                    # 中译英翻译服务
│   ├── sever.py                     # FastAPI 服务（端口 9970）
│   ├── translate.py                 # 翻译客户端
│   └── readme.md                    # 翻译工具说明
│
├── clean_data/                      # 中间清洗数据
├── meta_data/                       # 字典、价值体系、POI 元数据
└── value_data/                      # LLM 生成的价值观语言/动因输出
```

**注意**：项目不是 Python 包，根目录和子目录中均没有 `__init__.py`。

---

## 4. 数据处理流水线

建议按编号顺序执行。部分步骤有同步、异步、多核三种变体，任选其一即可。

| 步骤 | 脚本（示例） | 主要输入 | 主要输出 | 说明 |
|---|---|---|---|---|
| 1 | `1_data_process.py` | `ods_bd_person_trajectory/*.csv`、`ods_bd_user_profile/*.csv`、`meta_data/_ods_bd_poi__*.csv` | `clean_data/` 下多个 CSV/JSON | 合并、过滤停留 ≤7min、POI 匹配、分类统计、生成自然语言描述 |
| 2 | `2_get_user_value.py` | `clean_data/clean_data_with_person_information.json` | `value_data/clean_data_with_value_language.jsonl` | 调用 LLM 总结用户行为习惯与偏离群体行为 |
| 3 | `3_get_record_value_reason.py` | `clean_data/clean_data_with_behavior.csv` + 同上 JSON | `value_data/clean_data_with_value_reason.jsonl` | 对每条记录推断内在价值动因 |
| 4 | `4_gpv_parsing.py` | `value_data/clean_data_with_value_language.jsonl` | `parsing_data/clean_data_with_value_language_parsing.jsonl` | 解析出 GPV `perceptions` |
| 4' | `4_2_gpv_parsing.py` | `value_data/clean_data_with_value_reason.jsonl` | `parsing_data/clean_data_with_value_reason_parsing.jsonl` | 记录级 perceptions |
| 5 | `5_gpv_result.py` | 用户级 parsing 结果 + `meta_data/all_value_list.json` | `gpv_result/value_language_result.jsonl` | ValueLlama 测量用户级价值 |
| 5' | `5_2_gpv_result.py` | 记录级 parsing 结果 | `gpv_result/value_reason_result.jsonl` | 记录级测量 |
| 6 | `6_analyse_gpv_result.py` | `gpv_result/value_language_result.jsonl` | `gpv_result/person_value.jsonl` | 按用户聚合价值得分（valence[0]-valence[1] 平均） |
| 7 | `7_result2pkl.py` | `gpv_result/person_value.jsonl` | `gpv_result/person_value_vector.pkl` + `.jsonl` | 离散化为 `{>0:1, <0:0.33, =0:0.66, None:0}` 向量 |
| 8 | `8_add_value_set.py` | `gpv_result/value_reason_result.jsonl` + `clean_data/clean_data_with_category_delete_none.csv` | `gpv_result/value_set.csv` + `.jsonl` | 把相关价值观集合拼回原表 |

### 4.1 输出目录约定

脚本默认输出到以下相对路径：

- `./clean_data/`
- `./value_data/`
- `./parsing_data/`
- `./gpv_result/`

这些目录由脚本在运行时通过 `os.makedirs` 自动创建（如果脚本中包含该逻辑）。

### 4.2 并发变体

- `_async_openai.py` / `_async_qwen.py`：使用 `asyncio.Semaphore(5)` 限制并发，适合 API 调用。
- `_multicore.py`：使用 `multiprocessing.Pool`，依据 `os.sched_getaffinity(0)` 获取 CPU 核数。
- 无后缀版本：顺序执行，直接 `append` 到 JSONL。

### 4.3 GPV 运行注意事项

- `4_gpv_parsing.py`、`4_2_gpv_parsing.py`、`5_gpv_result.py`、`5_2_gpv_result.py` 需要**在克隆后的 `gpv-master/gpv/` 目录下**新建 `.py` 文件运行（即脚本要放在 GPV 仓库内部，并 `from gpv import GPV`）。
- GPV 默认配置在 `gpv/gpv-master/gpv/measure.py` 中：
  - `parsing_model_name="gpt-4o-mini"`
  - `measurement_model_name="Value4AI/ValueLlama-3-8B"`
- `5_*.py` 脚本中设置了 `os.environ["CUDA_VISIBLE_DEVICES"] = "1"`，需要对应 GPU。

---

## 5. 各脚本详细说明

### 数据预处理

- **`1_data_process.py`**：
  - 合并 `ods_bd_person_trajectory` 下所有 CSV。
  - 删除 `end_time - start_time <= 420000ms`（即 ≤7 分钟）的记录。
  - 对 `poi_id=0`（约 80% 数据缺失）的记录，用欧氏距离匹配最近的 POI。
  - 删除无分类记录，聚合用户各级别分类统计、POI ID 统计。
  - 合并个人画像信息，生成英文描述句（`personal_information_sentence`、`level3_category_sentence`）。
  - 为每条记录生成自然语言 `behavior` 字段。

### LLM 调用

- **`2_get_user_value.py`**：顺序调用 OpenAI，生成用户级行为总结。
- **`2_get_user_value_openai.py`**：异步 OpenAI 版本。
- **`2_get_user_value_async_qwen.py`**：异步 Qwen 版本。
- **`2_get_user_value_multicore.py`**：多进程 OpenAI 版本。
- **`3_get_record_value_reason.py`**：顺序调用 OpenAI，逐条生成价值动因。
- **`3_get_record_value_reason_async_openai.py`** / `_async_qwen.py` / `_multicore.py`：对应变体。

### GPV

- **`4_gpv_parsing.py`** / **`4_2_gpv_parsing.py`**：用户级/记录级 perceptions 解析。
- **`4_gpv_parsing_multicore.py`** / **`4_2_gpv_parsing_multicore.py`**：多核版本。
- **`5_gpv_result.py`**：用户级价值观测量。
- **`5_2_gpv_result.py`**：记录级测量，并提取 `value_set`。

### 后处理

- **`6_analyse_gpv_result.py`**：按用户聚合每个 value 的得分。
- **`7_result2pkl.py`**：把聚合结果转为 pkl/jsonl 向量。
- **`8_add_value_set.py`**：把记录级相关价值观集合写回原 CSV 的 `value_set` 列。

### 翻译服务

- **`ch_to_en_API/sever.py`**：FastAPI 服务，监听 `0.0.0.0:9970`，端点 `/translate`。
- **`ch_to_en_API/translate.py`**：递归翻译 JSON 中中文文本，生成翻译后文件与中英文对照表。

---

## 6. 运行方式

### 6.1 环境安装

```bash
# 基础依赖
pip install -r requirements.txt

# OpenAI / Qwen / 异步支持
pip install openai dashscope aiofiles

# 多核版本需要的进度条
pip install tqdm

# 翻译服务额外依赖
pip install transformers fastapi uvicorn requests
```

GPV 依赖请单独安装：

```bash
git clone https://github.com/ValueByte-AI/gpv.git
cd gpv
pip install -r requirements.txt
```

### 6.2 运行翻译服务（可选）

仅当需要重新生成 `poi_dict.json` / `job_dict.json` 时才运行：

```bash
cd ch_to_en_API
python sever.py        # 启动服务，默认 http://0.0.0.0:9970
# 另开终端
python translate.py    # 翻译客户端
```

### 6.3 执行主流水线

```bash
python 1_data_process.py

# 步骤 2：任选其一
python 2_get_user_value.py
# 或 python 2_get_user_value_openai.py
# 或 python 2_get_user_value_async_qwen.py
# 或 python 2_get_user_value_multicore.py

# 步骤 3：任选其一
python 3_get_record_value_reason.py
# 或对应 async / multicore 版本

# 步骤 4-5：需要在 gpv-master/gpv/ 目录下执行
# 将 4_gpv_parsing.py、4_2_gpv_parsing.py、5_gpv_result.py、5_2_gpv_result.py
# 复制到 gpv-master/gpv/ 后运行

python 6_analyse_gpv_result.py
python 7_result2pkl.py
python 8_add_value_set.py
```

### 6.4 构建与测试

- **没有构建步骤**。项目是脚本集合，直接运行。
- **没有自动化测试**。验证方式：检查输出文件是否存在、行数是否匹配、字段是否符合预期。

---

## 7. 代码风格与开发约定

- **语言混合**：注释和变量名中英文混杂，以中文注释为主。
- **过程式脚本**：没有类封装（除 GPV 外部类外），函数较长，直接操作文件路径。
- **硬编码路径**：输入/输出路径多为硬编码的相对路径，修改脚本时需注意。
- **追加写入**：大量脚本使用 JSONL 追加模式（`mode='a'`），**不会自动去重**。重复运行会导致输出文件中出现重复记录，建议手动清理旧输出。
- **并发控制**：
  - 异步版本使用 `asyncio.Semaphore(5)` 限制并发。
  - 多核版本使用 `multiprocessing.Pool`。
- **命名不一致**：例如 `ch_to_en_API/sever.py` 文件名疑似 `server.py` 的拼写错误；`readme.txt` 中部分输出路径与脚本实际输出路径不完全一致（如 `readme.txt` 写为 `./clean_data/...`，实际脚本输出到 `./value_data/...`）。

---

## 8. 测试策略

- **当前没有单元测试、集成测试、pytest 配置或任何断言验证。**
- 建议的最小验证方式：
  1. 检查中间产物行数是否与输入一致。
  2. 抽样查看 `value_language.jsonl`、`value_reason.jsonl` 中的 `trajectory_description` / `value_reason` 字段是否非空。
  3. 检查 `person_value_vector.pkl` 是否为 `Dict[str, List[float]]` 且长度与 `all_value_list.json` 一致。
  4. 检查 `value_set.csv` 的 `value_set` 列是否按 `id` 正确对齐。

---

## 9. 安全注意事项

> ⚠️ **重要**：该项目目前存在明显的密钥泄露风险。

- 多个脚本（如 `2_get_user_value.py`、`2_get_user_value_multicore.py`、`3_get_record_value_reason_multicore.py`）中**硬编码了真实的 OpenAI API Key**。
- Qwen 相关脚本中 `dashscope.api_key = ''` 为空字符串占位，但同样未使用环境变量管理。
- **建议**：
  1. 立即在 OpenAI/DashScope 后台撤销相关 API Key。
  2. 将 Key 改为从环境变量读取，例如：
     ```python
     import os
     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
     ```
  3. 避免在版本控制中提交包含密钥的文件。
  4. 项目当前没有 `.gitignore`，建议添加：
     ```gitignore
     .env
     __pycache__/
     *.pyc
     .DS_Store
     ```
- 运行 GPV 测量脚本时设置了 `CUDA_VISIBLE_DEVICES="1"`，请确保该 GPU 可用或按需修改。

---

## 10. 已知问题与注意事项

1. **数据缺失**：`readme.txt` 说明约 80% 记录的 `poi_id=0`，脚本通过欧氏距离匹配最近 POI 进行补全。
2. **路径依赖**：多个脚本默认从项目根目录运行，直接 `cd` 到子目录运行可能因相对路径出错。
3. **GPV 外部依赖**：步骤 4-5 需要把脚本放入 GPV 仓库内部执行，不能直接在项目根目录 `from gpv import GPV`。
4. **重复运行风险**：JSONL 追加模式会导致重复数据，重新运行前建议删除旧输出文件。
5. **没有 CI/CD 与容器化**：当前为纯手动本地运行，未配置 GitHub Actions、Docker、Makefile 等。
6. **最终产物**：
   - `gpv_result/person_value_vector.pkl`
   - `gpv_result/value_set.csv`
   这两个文件会用于下游 POI 预测模型。

---

## 11. 常用命令速查

```bash
# 安装基础依赖
pip install -r requirements.txt

# 运行数据预处理
python 1_data_process.py

# 生成用户级价值观语言（示例）
python 2_get_user_value_openai.py

# 生成记录级价值动因（示例）
python 3_get_record_value_reason_async_openai.py

# 启动翻译服务
python ch_to_en_API/sever.py

# 后处理
python 6_analyse_gpv_result.py
python 7_result2pkl.py
python 8_add_value_set.py
```
