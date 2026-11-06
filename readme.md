# ValueAssessment 项目说明

> 基于用户 POI 轨迹数据，利用大语言模型（LLM）与 GPV（Goal-Perception-Value）框架推断个体层面与记录层面的价值观，并生成可用于下游 POI 预测模型的价值向量。

---

## 1. 项目概述

本项目从用户轨迹记录（`ods_bd_person_trajectory`）和个人画像（`ods_bd_user_profile`）出发，通过数据清洗、POI 匹配、分类统计、自然语言行为描述生成，再调用 OpenAI/Qwen 等大模型对用户行为进行价值观建模，最后借助 GPV 框架完成 perception parsing 与 value measurement，输出：

- `gpv_result/person_value_vector.pkl`：每个用户的价值向量，供 POI 预测模型使用。
- `gpv_result/value_set.csv`：每条轨迹记录对应的相关价值观集合。

---

## 2. 数据文件说明

### 2.1 原始输入数据

| 数据 | 路径/文件 | 说明 |
|------|-----------|------|
| 轨迹记录 | `ods_bd_person_trajectory/*.csv` | 用户的 POI 签到/轨迹记录，包含 `uuid`、`poi_id`、`start_time`、`end_time`、`lnt_wgs84`、`lat_wgs84` 等字段。 |
| 个人画像 | `ods_bd_user_profile/*.csv` | 用户的画像信息，包含 `uuid`、`job`、`gender`、`age_group`、`marry`、`have_kids`、`income_price`、`consumption_price` 等字段。 |

### 2.2 元数据（`meta_data/`）

| 文件 | 说明 |
|------|------|
| `_ods_bd_poi__202506201108.csv` | POI 表，包含 `p_id`、`longitude`、`latitude`、`first_category_name`、`second_category_name`、`third_category_name`。 |
| `all_value_list.json` | 价值体系中的价值词列表（共 91 个），如 `community`、`creativity`、`responsibility` 等，是 GPV measurement 的目标价值集合。 |
| `job_dict.json` | 职业中英文对照表。 |
| `poi_dict.json` | POI 三级分类中英文对照表。 |
| `missing_ids.json` | 轨迹记录中存在但 POI 表中缺失的 `poi_id` 列表。 |

### 2.3 中间数据（`clean_data/`）

| 文件 | 说明 |
|------|------|
| `clean_data.csv` | 合并所有轨迹 CSV 并过滤停留 ≤7 分钟后的数据。 |
| `clean_data_with_category.csv` | 为记录补充 POI 一级/二级/三级分类后的数据。 |
| `clean_data_with_category_delete_none.csv` | 删除三级分类为空的记录后的数据。 |
| `clean_data_with_category_delete_none.json` | 按用户聚合的各级别分类统计与 POI ID 统计。 |
| `clean_data_with_person_information.json` | 合并个人画像并生成英文描述句后的用户级 JSON。 |
| `clean_data_with_behavior.csv` | 为每条记录生成自然语言 `behavior` 描述后的数据。 |

### 2.4 LLM 生成数据（`value_data/`）

| 文件 | 说明 |
|------|------|
| `clean_data_with_value_language.jsonl` | 用户级行为总结与价值观语言描述。 |
| `clean_data_with_value_reason.jsonl` | 记录级价值动因推断结果。 |

### 2.5 GPV 处理数据

| 文件 | 说明 |
|------|------|
| `parsing_data/clean_data_with_value_language_parsing.jsonl` | 用户级 perceptions 解析结果。 |
| `parsing_data/clean_data_with_value_reason_parsing.jsonl` | 记录级 perceptions 解析结果。 |
| `gpv_result/value_language_result.jsonl` | 用户级价值测量结果。 |
| `gpv_result/value_reason_result.jsonl` | 记录级价值测量结果。 |
| `gpv_result/person_value.jsonl` | 按用户聚合后的价值得分。 |
| `gpv_result/person_value_vector.pkl` | 最终用户价值向量（`Dict[str, List[float]]`）。 |
| `gpv_result/person_value_vector.jsonl` | 用户价值向量的 JSONL 形式。 |
| `gpv_result/value_set.csv` | 记录级相关价值观集合与原表合并结果。 |
| `gpv_result/value_set.jsonl` | 记录级 `value_set` 中间文件。 |

---

## 3. 流水线总览

建议按编号顺序执行，步骤 2、3、4、5 均有同步、异步、多核三种变体，任选其一即可。

| 步骤 | 脚本（示例） | 主要输入 | 主要输出 | 核心任务 |
|------|-------------|----------|----------|----------|
| 1 | `1_data_process.py` | 轨迹 CSV、画像 CSV、POI 表 | `clean_data/` 下多个文件 | 数据清洗、POI 匹配、分类统计、自然语言描述生成 |
| 2 | `2_get_user_value.py` | `clean_data_with_person_information.json` | `value_data/clean_data_with_value_language.jsonl` | LLM 生成用户级行为习惯与价值观描述 |
| 3 | `3_get_record_value_reason.py` | `clean_data_with_behavior.csv` + 用户 JSON | `value_data/clean_data_with_value_reason.jsonl` | LLM 推断每条记录的价值动因 |
| 4 | `4_gpv_parsing.py` | `value_data/clean_data_with_value_language.jsonl` | `parsing_data/clean_data_with_value_language_parsing.jsonl` | GPV parsing：用户级 perceptions |
| 4' | `4_2_gpv_parsing.py` | `value_data/clean_data_with_value_reason.jsonl` | `parsing_data/clean_data_with_value_reason_parsing.jsonl` | GPV parsing：记录级 perceptions |
| 5 | `5_gpv_result.py` | 用户级 parsing 结果 + `all_value_list.json` | `gpv_result/value_language_result.jsonl` | ValueLlama 测量用户级价值 |
| 5' | `5_2_gpv_result.py` | 记录级 parsing 结果 | `gpv_result/value_reason_result.jsonl` | ValueLlama 测量记录级价值 |
| 6 | `6_analyse_gpv_result.py` | `gpv_result/value_language_result.jsonl` | `gpv_result/person_value.jsonl` | 按用户聚合价值得分 |
| 7 | `7_result2pkl.py` | `gpv_result/person_value.jsonl` | `gpv_result/person_value_vector.pkl` + `.jsonl` | 离散化并生成价值向量 |
| 8 | `8_add_value_set.py` | `gpv_result/value_reason_result.jsonl` + 原 CSV | `gpv_result/value_set.csv` | 把记录级 value_set 合并回原表 |

---

## 4. 各脚本详细说明

### 4.1 数据预处理：`1_data_process.py`

**输入**

- `ods_bd_person_trajectory/*.csv`：轨迹记录文件夹。
- `ods_bd_user_profile/part-00000-22c5e68b-2c8f-40c8-9f41-8d336f490775-c000.csv`：用户画像文件（路径可修改）。
- `meta_data/_ods_bd_poi__202506201108.csv`：POI 元数据。
- `meta_data/poi_dict.json`：POI 分类中英文对照。
- `meta_data/job_dict.json`：职业中英文对照。

**输出**

- `clean_data/clean_data.csv`
- `clean_data/clean_data_with_category.csv`
- `clean_data/clean_data_with_category_delete_none.csv`
- `clean_data/clean_data_with_category_delete_none.json`
- `clean_data/clean_data_with_person_information.json`
- `clean_data/clean_data_with_behavior.csv`

**算法逻辑**

脚本内部包含 6 个处理函数，按顺序执行：

1. **`process_poi_data(folder_path, output_file_name)`**  
   合并轨迹文件夹下所有 CSV，将 `end_time - start_time <= 420000ms`（即 ≤7 分钟）的记录删除，再按 `uuid`、`start_time` 排序。约 80% 原始记录的 `poi_id=0`，但此阶段不做处理。

2. **`merge_consecutive_records(input_csv_path, output_csv_path, ms)`（可选）**  
   合并同一用户、同一 POI、且相邻记录间隔小于 `ms` 毫秒的连续记录，合并后重新计算停留时长 `stay_minutes`。该函数默认未启用。

3. **`process_poi_data(csv1_path, csv2_path, output_csv_path)`**  
   - 通过 `poi_id` 左连接 POI 表，为 `poi_id != 0` 的记录补充一级/二级/三级分类。
   - 对 `poi_id=0` 的记录，使用记录经纬度与 POI 表中欧氏距离最近的 POI，回填 `poi_id` 与三个分类字段。

4. **`clean_and_report_empty_third_category(input_csv_path, output_csv_path)`**  
   删除 `third_category_name` 为空或空字符串的记录。

5. **`parse_csv(file_path)` + `save_to_json(user_data, output_file)`**  
   按用户聚合：一级类别统计、二级类别统计、三级类别统计、POI ID 统计，保存为 JSON。

6. **`process_personal_data(...)`**  
   - 读取用户画像 CSV，提取性别、年龄、职业、收入、消费、婚姻、子女、教育、房产、宠物、平均餐饮消费等字段。
   - 将职业与三级类别统计翻译为英文。
   - 生成 `personal_information_sentence`：一段描述用户画像的英文句子。
   - 生成 `level3_category_sentence`：基于三级类别访问次数排序，按 80% 累计阈值划分“主要兴趣”与“其他频繁访问”的英文句子。

7. **`process_and_translate_behavior_data(...)`**  
   - 读取 `clean_data_with_category_delete_none.csv`。
   - 将一/二/三级分类翻译为英文。
   - 将 `start_time`、`end_time` 从毫秒时间戳转为 `Weekday HH:MM` 格式。
   - 生成每条记录的 `behavior` 字段：`user stayed at {third_category_name_en} from {start_time_formatted} to {end_time_formatted} for {stay_minutes} minutes.`

---

### 4.2 用户级价值观语言生成：`2_get_user_value.py`

**输入**

- `clean_data/clean_data_with_person_information.json`

**输出**

- `value_data/clean_data_with_value_language.jsonl`

**算法逻辑**

1. 读取上一步生成的用户级 JSON。
2. 对每个用户构造 prompt：
   - 角色：心理学家。
   - 任务：根据用户的轨迹描述（`level3_category_sentence`）和个人信息（`personal_information_sentence`），总结：
     1. 用户的行为习惯；
     2. 用户与群体行为的偏离之处（若无则省略）。
3. 调用 `gpt-4o-mini`（可替换为其他 LLM）生成 `trajectory_description`。
4. 将结果写入 JSONL，每条记录包含：
   - `person_id`
   - `id`
   - `origin_information`：原始用户 JSON
   - `trajectory_description`：LLM 生成的行为习惯与价值观描述

**并发变体**

- `2_get_user_value_openai.py`：异步 OpenAI 版本，使用 `asyncio.Semaphore(5)` 限制并发。
- `2_get_user_value_async_qwen.py`：异步 Qwen（`qwen-turbo`）版本。
- `2_get_user_value_multicore.py`：多进程 OpenAI 版本，依据 `os.sched_getaffinity(0)` 获取 CPU 核数。

---

### 4.3 记录级价值动因推断：`3_get_record_value_reason.py`

**输入**

- `clean_data/clean_data_with_behavior.csv`
- `clean_data/clean_data_with_person_information.json`

**输出**

- `value_data/clean_data_with_value_reason.jsonl`

**算法逻辑**

1. 读取 `clean_data_with_behavior.csv`，逐行遍历每条轨迹记录。
2. 根据 `uuid` 在用户 JSON 中查找对应的 `personal_information_sentence` 与 `level3_category_sentence`。
3. 为每条记录构造 prompt：
   - 角色：心理学家。
   - 任务：基于用户轨迹描述和个人信息，总结驱使该行为的最相关内在价值动因，用一句话概括。
   - 输入：轨迹描述、个人信息、当前行为 `behavior`。
4. 调用 `gpt-4o-mini` 生成 `value_reason`。
5. 写入 JSONL，每条记录包含：
   - `id`：记录在原 CSV 中的行号
   - `uuid`
   - `value_reason`：LLM 生成的价值动因

**并发变体**

- `3_get_record_value_reason_async_openai.py`：异步 OpenAI 版本，`asyncio.Semaphore(5)` 限制并发。
- `3_get_record_value_reason_async_qwen.py`：异步 Qwen 版本。
- `3_get_record_value_reason_multicore.py`：多进程 OpenAI 版本。

---

### 4.4 用户级 GPV Parsing：`4_gpv_parsing.py`

**输入**

- `value_data/clean_data_with_value_language.jsonl`

**输出**

- `parsing_data/clean_data_with_value_language_parsing.jsonl`

**算法逻辑**

1. 逐行读取用户级 `value_language.jsonl`。
2. 构造待 parse 的文本：
   ```
   The user's personal information is:
   {personal_information_sentence}
   The user's behavioral traits is:
   {trajectory_description}
   ```
3. 调用 `GPV().parse_texts([text])`，将文本分解为 `perceptions` 列表。
4. 将 `perceptions` 字段追加到原记录中，写入输出 JSONL。

---

### 4.5 记录级 GPV Parsing：`4_2_gpv_parsing.py`

**输入**

- `value_data/clean_data_with_value_reason.jsonl`

**输出**

- `parsing_data/clean_data_with_value_reason_parsing.jsonl`

**算法逻辑**

与用户级 parsing 相同，只是待 parse 的文本为每条记录的 `value_reason` 字段。

---

### 4.6 用户级 GPV Measurement：`5_gpv_result.py`

**输入**

- `parsing_data/clean_data_with_value_language_parsing.jsonl`
- `meta_data/all_value_list.json`

**输出**

- `gpv_result/value_language_result.jsonl`

**算法逻辑**

1. 读取价值词列表 `all_value_list.json`。
2. 初始化 `GPV()`，默认使用 CUDA 设备 1（`CUDA_VISIBLE_DEVICES="1"`）。
3. 逐行读取用户级 parsing 结果：
   - 若 `perceptions` 为空，跳过。
   - 调用 `gpv.measure_perceptions(perceptions, values)`，得到每个 perception 对应的相关价值、相关度、情感极性。
4. 将测量结果 `value` 追加到原记录中，写入输出 JSONL。

---

### 4.7 记录级 GPV Measurement：`5_2_gpv_result.py`

**输入**

- `parsing_data/clean_data_with_value_reason_parsing.jsonl`
- `meta_data/all_value_list.json`

**输出**

- `gpv_result/value_reason_result.jsonl`

**算法逻辑**

与用户级 measurement 相同，对记录级 parsing 结果中的 `perceptions` 逐一测量。

> **注意**：当前仓库中的 `5_2_gpv_result.py` 文件同时包含了两段逻辑（前段重复了用户级测量，后段处理记录级结果），实际使用前建议检查并清理。

---

### 4.8 聚合用户级价值得分：`6_analyse_gpv_result.py`

**输入**

- `gpv_result/value_language_result.jsonl`
- `meta_data/all_value_list.json`

**输出**

- `gpv_result/person_value.jsonl`

**算法逻辑**

1. 读取所有 `person_id`，为每个用户初始化每个价值的累计值 `result_value_dic` 与计数 `result_num_dic`。
2. 遍历 `value_language_result.jsonl` 中的每个用户测量结果：
   - 对每个 perception，取出其 `relevant_values`、`relevances`、`valences`。
   - 对第 `i` 个相关价值，计算 `valence[0] - valence[1]` 并累加到该用户该价值的 `result_value_dic` 中；同时 `result_num_dic` 计数 +1。
3. 对每个用户的每个价值，计算平均分：
   - 若计数为 0，得分为 `None`。
   - 否则为 `result_value_dic / result_num_dic`。
4. 保存为 `person_value.jsonl`。

---

### 4.9 生成价值向量：`7_result2pkl.py`

**输入**

- `gpv_result/person_value.jsonl`

**输出**

- `gpv_result/person_value_vector.pkl`
- `gpv_result/person_value_vector.jsonl`

**算法逻辑**

1. 读取 `person_value.jsonl`。
2. 对每个用户的每个价值得分 `v` 做离散化：
   - `v > 0` → `1`
   - `v < 0` → `0.33`
   - `v == 0` → `0.66`
   - `v is None` → `0`
3. 生成 `Dict[str, List[float]]`，其中 key 为 `uuid`，list 长度与 `all_value_list.json` 一致。
4. 同时保存为 `.pkl`（pickle）和 `.jsonl` 两种格式。

---

### 4.10 合并记录级价值集合：`8_add_value_set.py`

**输入**

- `gpv_result/value_reason_result.jsonl`
- `clean_data/clean_data_with_category_delete_none.csv`

**输出**

- `gpv_result/value_set.csv`
- `gpv_result/value_set.jsonl`

**算法逻辑**

1. 读取 `clean_data_with_category_delete_none.csv`，新增空列 `value_set`。
2. 读取记录级测量结果 `value_reason_result.jsonl`：
   - 对每个记录，收集其所有 perception 的 `relevant_values`，去重后得到 `value_set`。
   - 写入 `value_set.jsonl`。
3. 根据 `id`（即原 CSV 行号）将 `value_set` 以逗号分隔的字符串写回 DataFrame。
4. 保存为 `value_set.csv`。

---

### 4.11 翻译服务：`ch_to_en_API/`

| 文件 | 作用 |
|------|------|
| `sever.py` | 基于 `Helsinki-NLP/opus-mt-zh-en` 的 FastAPI 翻译服务，监听 `0.0.0.0:9970`，端点 `/translate`。 |
| `translate.py` | 翻译客户端，递归翻译 JSON 文件中的中文文本，输出翻译后文件与中英文对照表。 |

主要用于生成 `meta_data/job_dict.json` 与 `meta_data/poi_dict.json`。

---

## 5. GPV（Goal-Perception-Value）框架详解

本项目使用 GPV 框架将自然语言文本转换为一组可测量的 **perceptions**，再对每个 perception 测量其背后反映的人类价值。GPV 包含三个核心步骤：**Chunking → Parsing → Measurement**。

### 5.1 核心概念

| 概念 | 含义 |
|------|------|
| **Text** | 原始输入文本，例如 LLM 生成的用户行为习惯描述或单条记录的价值动因。 |
| **Perception** | 文本中的原子化价值感知单元。每个 perception 应该是：价值负载的、不可再分的、上下文自包含的、且覆盖原文相关内容的。 |
| **Value** | 待测量的价值词，来自 `all_value_list.json`，如 `community`、`creativity`、`responsibility`。 |
| **Relevance** | 某个 perception 与某个 value 是否相关。 |
| **Valence** | 某个 perception 对某个 value 是支持（support）、反对（oppose）还是无法判断（either）。 |

### 5.2 Chunking

- 使用 `semchunk` 库按 token 数（默认 `chunk_size=300`）将长文本切分为若干 chunk。
- 切分后的 chunk 进入 Parser 进行 perception 抽取。

### 5.3 Parsing

- 使用 `gpt-4o-mini` 作为 parsing 模型（可配置）。
- 系统 prompt 要求模型扮演人类价值专家，将文本转换为 JSON 格式：
  ```json
  {"perceptions": ["perception 1", "perception 2", ...]}
  ```
- 对 FlashParser，使用异步批处理调用 OpenAI API；对普通 Parser，使用同步批处理。

### 5.4 Measurement

Measurement 由 `ValueLlama` 模型完成，默认模型为 `Value4AI/ValueLlama-3-8B`。

#### 5.4.1 Relevance 判定

对每个 `(perception, value)` 对，构造 prompt：

```
[Task] Given a sentence and a value, determine whether the sentence is relevant to the value.
If the sentence is relevant to the value, output "yes", otherwise output "no".
Sentence: {sentence}
Value: {value}
Output:
```

模型只输出一个 token，在 `yes` 和 `no` 上的概率分布作为 relevance 分数（`relevances[i][0]` 为 yes 概率，`relevances[i][1]` 为 no 概率）。

#### 5.4.2 Valence 判定

对 relevant 的 `(perception, value)` 对，构造 prompt：

```
[Task] Given a sentence and a value, determine whether the sentence supports or opposes the value.
If the sentence supports the value, output "support".
If the sentence opposes the value, output "oppose".
If you need more context to make a decision, output "either".
Sentence: {sentence}
Value: {value}
Output:
```

模型在 `support`、`oppose`、`either` 三个 token 上的概率分布作为 valence 向量：

- `valence[0]`：支持概率
- `valence[1]`：反对概率
- `valence[2]`：无法判断概率

#### 5.4.3 筛选与输出

对一组 perceptions 和 values，`measure_perceptions` 的输出格式为：

```python
{
  "perception 1": {
    "relevant_values": ["value_a", "value_b"],
    "relevances": [[yes_prob, no_prob], [yes_prob, no_prob]],
    "valences": [[support_prob, oppose_prob, either_prob], ...]
  },
  ...
}
```

筛选规则：

- 仅保留 relevance 中 `yes` 概率 > 0.5 的价值。
- 对每个保留的价值，记录其 relevance 向量与 valence 向量。

#### 5.4.4 聚合与离散化

用户级结果聚合（`6_analyse_gpv_result.py`）：

- 对每个 `(user, value)`，累加所有相关 perception 的 `valence[0] - valence[1]`。
- 除以相关 perception 数量，得到平均得分。
- 得分 > 0 表示总体上支持该价值；得分 < 0 表示反对；得分 = 0 表示中立；无相关 perception 则为 `None`。

最终向量离散化（`7_result2pkl.py`）：

| 原始得分 | 向量值 | 含义 |
|----------|--------|------|
| `v > 0` | `1` | 支持 |
| `v < 0` | `0.33` | 反对 |
| `v == 0` | `0.66` | 中立 |
| `v is None` | `0` | 无证据 |

---

## 6. 运行方式

### 6.1 环境安装

```bash
# 基础依赖
pip install -r requirements.txt

# OpenAI / Qwen / 异步支持
pip install openai dashscope aiofiles

# 多核版本进度条
pip install tqdm

# 翻译服务
pip install transformers fastapi uvicorn requests
```

GPV 依赖需单独安装：

```bash
git clone https://github.com/ValueByte-AI/gpv.git
cd gpv
pip install -r requirements.txt
```

### 6.2 运行翻译服务（可选）

仅当需要重新生成 `poi_dict.json` / `job_dict.json` 时运行：

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
# python 2_get_user_value_openai.py
# python 2_get_user_value_async_qwen.py
# python 2_get_user_value_multicore.py

# 步骤 3：任选其一
python 3_get_record_value_reason.py
# python 3_get_record_value_reason_async_openai.py
# python 3_get_record_value_reason_async_qwen.py
# python 3_get_record_value_reason_multicore.py

# 步骤 4-5：需要在 gpv 仓库的 gpv/ 目录下执行
# 将 4_gpv_parsing.py、4_2_gpv_parsing.py、5_gpv_result.py、5_2_gpv_result.py
# 复制到 gpv-master/gpv/ 后运行

python 6_analyse_gpv_result.py
python 7_result2pkl.py
python 8_add_value_set.py
```

---

## 7. 重要注意事项

1. **API Key 管理**  
   多个脚本中硬编码或留空了 `OPENAI_API_KEY` / `dashscope.api_key`。生产环境建议改为从环境变量读取。

2. **GPV 外部依赖**  
   步骤 4-5 需要把脚本放入 GPV 仓库内部执行，因为脚本通过 `from gpv import GPV` 导入。

3. **GPU 设置**  
   `5_gpv_result.py` 与 `5_2_gpv_result.py` 中设置了 `CUDA_VISIBLE_DEVICES="1"`，请确保该 GPU 可用或按需修改。

4. **重复运行风险**  
   多个脚本使用 JSONL 追加模式（`mode='a'`），重复运行会导致输出文件中出现重复记录，建议重新运行前删除旧输出。

5. **路径依赖**  
   脚本默认从项目根目录运行，直接 `cd` 到子目录运行可能因相对路径出错。

6. **最终产物**  
   - `gpv_result/person_value_vector.pkl`
   - `gpv_result/value_set.csv`  
   这两个文件会用于下游 POI 预测模型。

---

## 8. 文件清单

```
.
├── 1_data_process.py
├── 2_get_user_value.py
├── 2_get_user_value_async_qwen.py
├── 2_get_user_value_multicore.py
├── 2_get_user_value_openai.py
├── 3_get_record_value_reason.py
├── 3_get_record_value_reason_async_openai.py
├── 3_get_record_value_reason_async_qwen.py
├── 3_get_record_value_reason_multicore.py
├── 4_2_gpv_parsing.py
├── 4_2_gpv_parsing_multicore.py
├── 4_gpv_parsing.py
├── 4_gpv_parsing_multicore.py
├── 5_2_gpv_result.py
├── 5_gpv_result.py
├── 6_analyse_gpv_result.py
├── 7_result2pkl.py
├── 8_add_value_set.py
├── ch_to_en_API/
│   ├── readme.md
│   ├── sever.py
│   └── translate.py
├── clean_data/
├── meta_data/
├── value_data/
├── readme.txt
├── readme.md
└── requirements.txt
```
