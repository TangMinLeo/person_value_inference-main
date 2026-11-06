# JSON文件中译英翻译工具

基于Helsinki-NLP/opus-mt-zh-en模型的JSON文件中文内容翻译工具


## 🔧 环境要求

```bash
pip install transformers fastapi uvicorn requests
```

## 🚀 使用方法

### 1. 启动翻译服务
```bash
python server.py
```
等待模型加载完成，看到 `Uvicorn running on http://0.0.0.0:9970` 表示启动成功

### 2. 运行翻译脚本
**打开新终端**，运行：
```bash
python translate.py
```

## 📁 输出文件

翻译完成后会生成两个文件：

- `job_dict_chinese_terms_translated.json` - 翻译后的JSON文件
- `job_dict_chinese_terms_translated_mapping.json` - 中英文对照表

### 示例

**原始文件：**
```json
[
  "写字楼白领",
  "大学生",
  "工厂蓝领工"
]
```

**翻译结果：**
```json
[
  "Office white-collar workers",
  "College students",
  "Factory blue-collar workers"
]
```

**对照表：**
```json
{
  "写字楼白领": "Office white-collar workers",
  "大学生": "College students",
  "工厂蓝领工": "Factory blue-collar workers"
}
```

## ⚠️ 注意事项

1. **首次运行**：会自动下载模型（约500MB），需要等待几分钟
2. **运行顺序**：必须先启动 `server.py`，再运行 `translate.py`
3. **保持服务运行**：翻译过程中不要关闭 `server.py` 窗口
4. **文件路径**：需要翻译其他文件时，修改 `translate.py` 中的 `input_file` 路径

## 🛠️ 自定义配置

修改 `translate.py` 中的文件路径：
```python
input_file = "你的JSON文件路径"
```

## 📞 问题排查

- **网络问题**：使用国内镜像站 `hf-mirror.com`
- **端口占用**：确保9970端口未被占用
- **内存不足**：建议8GB+内存