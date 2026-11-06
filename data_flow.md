以下是本项目流程的梳理：

---

## 一、项目目标

从用户的 **POI 轨迹数据**（去了哪里、待了多久）和 **个人画像**（性别、年龄、收入等）出发，利用大模型推断每个用户的**价值观向量**，最终输出可用于下游 POI 预测模型的数值特征。

---

## 二、数据流程全景图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  原始输入                                                                 │
│  ├── ods_bd_person_trajectory/*.csv    (用户轨迹: uuid, poi_id, 时间, 经纬度) │
│  ├── ods_bd_user_profile/*.csv         (用户画像: 性别/年龄/职业/收入/消费...) │
│  └── meta_data/_ods_bd_poi__*.csv      (POI元数据: 三级分类, 经纬度)         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  步骤 1: 1_data_process.py — 数据清洗与特征工程                             │
│  • 合并所有轨迹 CSV，过滤停留 ≤7 分钟的记录                                   │
│  • 通过 poi_id 或经纬度最近邻匹配 POI 分类（一级/二级/三级）                    │
│  • 按用户聚合分类统计，翻译为英文                                             │
│  • 生成自然语言描述句：personal_information_sentence + level3_category_sentence│
│  • 为每条记录生成 behavior 字段（英文行为描述）                                │
│  输出 → clean_data/ 下 6 个文件                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ 步骤 2: 2_get_user_value.py  │  │ 步骤 3: 3_get_record_value_   │
│ 用户级价值观语言生成           │  │   reason.py 记录级价值动因推断  │
│                              │  │                              │
│ 输入: 用户画像 + 分类统计句    │  │ 输入: 每条记录的 behavior +    │
│ LLM: gpt-4o-mini / qwen-turbo│  │       用户画像上下文           │
│ 输出: 用户行为习惯 + 价值观描述 │  │ LLM: gpt-4o-mini / qwen-turbo│
│ → value_data/                │  │ 输出: 每条记录的价值动因原因    │
│   clean_data_with_value_     │  │ → value_data/                │
│   language.jsonl             │  │   clean_data_with_value_     │
└──────────────────────────────┘  │   reason.jsonl               │
                    │             └──────────────────────────────┘
                    ▼                               │
┌─────────────────────────────────────────────────────────────────────────┐
│ 步骤 4: 4_gpv_parsing.py / 4_2_gpv_parsing.py — GPV 感知解析              │
│ • 调用 GPV 框架的 parse_texts() 将自然语言文本解析为结构化 "perceptions"     │
│ • 4: 用户级解析   4_2: 记录级解析                                         │
│ 输出 → parsing_data/ 下 2 个 jsonl 文件                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 步骤 5: 5_gpv_result.py / 5_2_gpv_result.py — ValueLlama 价值观测量       │
│ • 加载 Value4AI/ValueLlama-3-8B 模型（本地 GPU 推理）                      │
│ • 对每个 perception 与 91 个价值观词做关联度(valence) + 相关度(relevance)打分 │
│ • 输出每条 perception 对应的价值观得分                                      │
│ 输出 → gpv_result/ 下 2 个 jsonl 文件                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 步骤 6: 6_analyse_gpv_result.py — 按用户聚合                              │
│ • 将同一用户的多条 perception 得分合并，得到用户级价值观得分                   │
│ 输出 → gpv_result/person_value.jsonl                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 步骤 7: 7_result2pkl.py — 离散化生成向量                                  │
│ • 将连续得分离散化为 0/1/2 三档，生成 91 维价值向量                          │
│ 输出 → gpv_result/person_value_vector.pkl  (Dict[uuid, List[float]])     │
│      → gpv_result/person_value_vector.jsonl                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 步骤 8: 8_add_value_set.py — 回写记录级价值集合                             │
│ • 将记录级 value_set 合并回原始 CSV，每条记录关联其相关价值观                  │
│ 输出 → gpv_result/value_set.csv                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、关键组件说明

| 组件 | 路径 | 作用 |
|------|------|------|
| **翻译服务** | [ch_to_en_API/](file:///E:/project/simulate_project/person_value_inference/ch_to_en_API) | 基于 `Helsinki-NLP/opus-mt-zh-en` 的本地中译英 FastAPI 服务（端口 9970），步骤 1 中用于翻译 POI 分类和职业名 |
| **GPV 框架** | [gpv/](file:///E:/project/simulate_project/person_value_inference/gpv) | 第三方库，提供 `parse_texts()`（LLM 解析）和 `measure_perceptions()`（ValueLlama 模型测量） |
| **ValueLlama-3-8B** | 自动下载 | 基于 Llama-3-8B 微调的价值观评估模型，需 GPU 推理，对每个 perception+value 对判断支持/反对/中立 |

---

## 四、两种运行路径

本项目有 **用户级** 和 **记录级** 两条并行流水线：

| 维度 | 用户级 | 记录级 |
|------|--------|--------|
| 步骤 | 2 → 4 → 5 → 6 → 7 | 3 → 4_2 → 5_2 → 8 |
| 粒度 | 一个用户一个价值观向量 | 每条轨迹记录关联一组价值观 |
| 最终产出 | `person_value_vector.pkl` | `value_set.csv` |

---

## 五、并发变体

步骤 2、3、4 均有三种运行方式：

| 变体 | 后缀 | 适用场景 |
|------|------|----------|
| 同步版 | 无后缀（如 `2_get_user_value.py`） | 小数据量调试 |
| 异步版 | `_async_openai` / `_async_qwen` | 大量 API 调用，`asyncio.Semaphore` 限流 |
| 多核版 | `_multicore` | 多进程并行，充分利用 CPU 核数 |

---

## 六、关键数据文件一览

| 位置 | 文件 | 内容 |
|------|------|------|
| `meta_data/` | `all_value_list.json` | 91 个价值观词（community, creativity, responsibility...） |
| `meta_data/` | `poi_dict.json` | POI 三级分类中英文对照 |
| `meta_data/` | `job_dict.json` | 职业中英文对照 |
| `clean_data/` | `clean_data_with_person_information.json` | **核心中间文件**：用户级聚合数据 + 英文描述句 |
| `clean_data/` | `clean_data_with_behavior.csv` | 记录级行为描述 |
| `value_data/` | `clean_data_with_value_language.jsonl` | LLM 生成的用户价值观描述 |
| `value_data/` | `clean_data_with_value_reason.jsonl` | LLM 生成的记录级价值动因 |
| `gpv_result/` | `person_value_vector.pkl` | **最终产出**：用户价值向量 |

整体流程就是：**轨迹数据 → 清洗翻译 → LLM 生成价值观描述 → GPV 解析 → ValueLlama 测量 → 聚合输出向量**。



---

## 完整示例：从一段文本到最终的价值观向量（举例理解过程： GPV 解析 → ValueLlama 测量 → 聚合输出向量）

假设我们有一个用户 `user_001`，经过步骤 2 的 LLM 处理后，得到这样一段价值观描述：

> *"The user frequently visits gyms and parks, indicating a strong commitment to health and physical well-being. However, they rarely visit social venues, suggesting a preference for solitude. They also spend significant time at libraries, reflecting a pursuit of knowledge."*

这段文本就是 GPV 管线的起点。

---

### 阶段一：GPV Parsing（步骤 4）— 拆解为原子感知

[4_gpv_parsing.py](file:///E:/project/simulate_project/person_value_inference/4_gpv_parsing.py) 调用 `gpv.parse_texts([text])`，底层用 **gpt-4o-mini** 将长文本拆解为"perceptions"（原子化的价值感知单元）。

**Prompt 核心要求**（来自 [parser.py](file:///E:/project/simulate_project/person_value_inference/gpv/gpv/parser.py) 第 18-21 行）：
> - perception 必须是 value-laden（承载价值观）
> - perception 必须原子化（不可再拆分）
> - perception 必须自包含、有上下文
> - 所有 perception 合起来要覆盖原文全部价值相关内容

**输入文本** → **输出 3 个 perceptions**：

```json
{
  "perceptions": [
    "Frequently visiting gyms and parks, indicating a strong commitment to health and physical well-being",
    "Rarely visiting social venues, suggesting a preference for solitude",
    "Spending significant time at libraries, reflecting a pursuit of knowledge"
  ]
}
```

---

### 阶段二：ValueLlama 测量（步骤 5）— 每个 perception × 每个价值观打分

[5_gpv_result.py](file:///E:/project/simulate_project/person_value_inference/5_gpv_result.py) 调用 `gpv.measure_perceptions(perceptions, values)`，底层用 **ValueLlama-3-8B**（本地 GPU 模型）做两轮判断。

#### 第 1 轮：Relevance（相关性）— "这个 perception 和这个价值观有关吗？"

来自 [valuellama.py](file:///E:/project/simulate_project/person_value_inference/gpv/gpv/valuellama.py#L30-L33) 的模板：

```
[Task] Given a sentence and a value, determine whether the sentence is relevant to the value.
If the sentence is relevant to the value, output "yes", otherwise output "no".

Sentence: Frequently visiting gyms and parks, indicating a strong commitment to health...
Value: health
Output:
```

模型输出 `yes` 的概率 → 0.98（高相关）

```
Sentence: Frequently visiting gyms and parks, indicating a strong commitment to health...
Value: tradition
Output:
```

模型输出 `yes` 的概率 → 0.02（不相关）

只保留 `relevance > 0.5` 的价值观，进入下一轮：

| Perception | 通过 relevance 筛选的价值观 |
|------------|---------------------------|
| P1: 频繁去健身房和公园 | health(0.98), discipline(0.87), sustainability(0.61) |
| P2: 很少去社交场所 | community(0.72), collaboration(0.55) |
| P3: 花大量时间在图书馆 | knowledge(0.99), curiosity(0.91), discipline(0.68) |

#### 第 2 轮：Valence（态度）— "这个 perception 是支持还是反对该价值观？"

来自 [valuellama.py](file:///E:/project/simulate_project/person_value_inference/gpv/gpv/valuellama.py#L25-L28) 的模板：

```
[Task] Given a sentence and a value, determine whether the sentence supports or opposes the value.
If the sentence supports the value, output "support". If the sentence opposes the value, output "oppose".
If you need more context, output "either".

Sentence: Rarely visiting social venues, suggesting a preference for solitude
Value: community
Output:
```

模型输出 `support` 概率 0.12，`oppose` 概率 0.78，`either` 概率 0.10

→ 这意味着用户**反对** community 这个价值观（喜欢独处 = 对社区价值的负面态度）

#### 最终每个 perception 的完整结果：

```json
{
  "Frequently visiting gyms...": {
    "relevant_values": ["health", "discipline", "sustainability"],
    "relevances": [[0.98, 0.02], [0.87, 0.13], [0.61, 0.39]],
    "valences": [[0.95, 0.03, 0.02], [0.88, 0.05, 0.07], [0.72, 0.10, 0.18]]
  },
  "Rarely visiting social venues...": {
    "relevant_values": ["community", "collaboration"],
    "relevances": [[0.72, 0.28], [0.55, 0.45]],
    "valences": [[0.12, 0.78, 0.10], [0.15, 0.70, 0.15]]
  },
  "Spending significant time at libraries...": {
    "relevant_values": ["knowledge", "curiosity", "discipline"],
    "relevances": [[0.99, 0.01], [0.91, 0.09], [0.68, 0.32]],
    "valences": [[0.97, 0.01, 0.02], [0.93, 0.02, 0.05], [0.82, 0.08, 0.10]]
  }
}
```

---

### 阶段三：聚合（步骤 6）— 按用户汇总得分

[6_analyse_gpv_result.py](file:///E:/project/simulate_project/person_value_inference/6_analyse_gpv_result.py) 的核心逻辑（第 51-53 行）：

```python
# 对每个 perception 下的每个价值观，累加 valence 得分
result_value_dic[key][relevant_value] += valence[0] - valence[1]
# valence[0] = support概率, valence[1] = oppose概率
# 差值 > 0 表示支持, < 0 表示反对
result_num_dic[key][relevant_value] += 1  # 计数

# 最终求平均
result_dic[id][k] = result_value_dic[id][k] / result_num_dic[id][k]
```

以 `health` 为例，user_001 只有一个 perception 涉及它：

| Perception | support概率 | oppose概率 | 差值 |
|------------|------------|-----------|------|
| P1: 频繁去健身房 | 0.95 | 0.03 | +0.92 |
| **平均** | | | **+0.92** |

以 `discipline` 为例，有两个 perception 涉及：

| Perception | support | oppose | 差值 |
|------------|---------|--------|------|
| P1: 频繁去健身房 | 0.88 | 0.05 | +0.83 |
| P3: 花时间在图书馆 | 0.82 | 0.08 | +0.74 |
| **平均** | | | **+0.785** |

以 `community` 为例（负面）：

| Perception | support | oppose | 差值 |
|------------|---------|--------|------|
| P2: 很少社交 | 0.12 | 0.78 | **-0.66** |
| **平均** | | | **-0.66** |

---

### 阶段四：离散化（步骤 7）— 生成最终向量

[7_result2pkl.py](file:///E:/project/simulate_project/person_value_inference/7_result2pkl.py) 把连续得分映射为三档离散值：

```python
def transform_value(v):
    if v is None:    return 0      # 无数据 → 0
    elif v > 0:      return 1      # 正向 → 1
    elif v < 0:      return 0.33   # 负向 → 0.33
    else:            return 0.66   # 中性 → 0.66
```

**最终 user_001 的 91 维价值向量**（截取部分）：

```python
{
  "user_001": [
    # community:  -0.66 → 0.33  (负向，反对)
    # creativity:  None  → 0     (无数据)
    # health:     +0.92 → 1     (正向，支持)
    # knowledge:  +0.95 → 1     (正向，支持)
    # discipline: +0.785→ 1     (正向，支持)
    # tradition:  None  → 0     (无数据)
    # ...
    # 共 91 维
  ]
}
```

---

### 一图总结

```
输入文本                                     最终向量
"The user frequently visits gyms..."    ──→  [0.33, 0, 1, 1, 1, 0, ...]
                                                      ↑    ↑    ↑  ↑  ↑
    │                                            community  health knowledge
    │ ① GPV Parsing (gpt-4o-mini)                  (反对)  (支持)  (支持)
    ▼
["Frequently visiting gyms...",    ← 3 个 perceptions
 "Rarely visiting social venues...",
 "Spending time at libraries..."]
    │
    │ ② ValueLlama (本地GPU) 
    │   每个 perception × 91 个价值观
    │   → relevance 筛选 → valence 打分
    ▼
{ "Frequently visiting gyms...": {
    "health":      {relevance:0.98, valence:[0.95,0.03,0.02]},
    "discipline":  {relevance:0.87, valence:[0.88,0.05,0.07]}, ...
  },
  "Rarely visiting...": {
    "community":   {relevance:0.72, valence:[0.12,0.78,0.10]}, ...
  }, ...
}
    │
    │ ③ 聚合：按用户求平均 (support-oppose)
    ▼
{ "health": +0.92, "discipline": +0.785, "community": -0.66, ... }
    │
    │ ④ 离散化：>0→1, <0→0.33, =0→0.66, None→0
    ▼
[0.33, 0, 1, 1, 1, 0, ...]   ← 91维向量，存入 person_value_vector.pkl
```

核心思想：**一段自然语言 → 拆成原子观点 → 每个观点对照 91 个价值观逐条打分 → 汇总取平均 → 离散化输出**。这样就把"这个人有什么价值观"这个模糊问题，变成了一组可计算的数值向量。