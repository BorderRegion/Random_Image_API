**Image Processing API** 是一个基于 FastAPI 的图片处理服务，支持图片压缩、加密别名生成、随机图片获取等功能，并通过 SQLite 数据库存储图片信息。该项目旨在提供一个高效、可扩展的图片处理解决方案。
## 特性

- **图片压缩**: 支持将图片压缩为指定质量（默认 75），并转换为 JPEG 格式。
- **加密别名生成**: 使用 SHA-256 哈希算法生成图片的加密别名，确保文件名唯一且安全。
- **随机图片获取**: 提供 `/random_image` 接口，用户可随机获取一张已处理的图片。
- **别名图片获取**: 提供 `/image_get/{alias}` 接口，用户可通过别名获取指定图片。
- **速率限制**: 支持单 IP 请求速率限制，防止恶意请求。
- **HTTPS 强制**: 可配置强制使用 HTTPS 协议。
- **动态配置**: 使用 YAML 文件进行配置管理，灵活调整参数。

---

## 配置说明

项目使用 `config.yaml` 文件进行配置。如果未找到配置文件，系统会自动生成默认配置。

### 默认配置模板

```yaml
database_Name: "test.db"           # SQLite 数据库名称
database_Cache: 256                # SQLite 缓存大小
listen_Port: 20001                 # API 监听端口
imagePath_Origin: "Origin"         # 原图路径
imagePath_Processed: "Processed"  # 处理后图片路径
compress_image_quality: 75        # 图片压缩质量 (0-100)
strict_https: false               # 是否强制使用 HTTPS
rateLimit: 5                      # 单 IP 最大请求数
time_window: 60                   # 时间窗口（秒）
server_host: "0.0.0.0"            # 服务器地址
```

### 配置加载逻辑

- 如果 `config.yaml` 文件不存在，系统会自动生成默认配置。
- 如果 `config.yaml` 存在但缺少某些配置项，系统会自动补全缺失项。

---

## 安装与运行

### 环境依赖

- Python >= 3.8
- 必要的 Python 包：`fastapi`, `uvicorn`, `Pillow`, `PyYAML`, `sqlite3`

安装依赖：

```bash
pip install fastapi uvicorn pyyaml pillow
```

### 启动服务

克隆仓库并启动服务：

```bash
git clone https://github.com/BorderRegion/Image-Processing-API.git
cd Image-Processing-API
python main.py
```

服务启动后，默认监听 `0.0.0.0:20001`，您可以通过浏览器或 API 工具访问接口。

---

## API 接口

### 1. 获取随机图片

- **URL**: `/random_image`
- **Method**: `GET`
- **Response**:
  - 成功: 返回随机图片（JPEG 格式）。
  - 失败: 返回 JSON 错误信息。

示例请求：

```bash
curl http://localhost:20001/random_image
```

### 2. 根据别名获取图片

- **URL**: `/image_get/{alias}`
- **Method**: `GET`
- **Response**:
  - 成功: 返回指定别名的图片（JPEG 格式）。
  - 失败: 返回 JSON 错误信息。

示例请求：

```bash
curl http://localhost:20001/image_get/<alias>
```

### 3. 速率限制与 HTTPS 强制

- 如果单 IP 在指定时间窗口内超过最大请求数（`rateLimit`），将返回 `429 Too Many Requests`。
- 如果启用了 `strict_https`，所有 HTTP 请求将被重定向到 HTTPS。

---

## 日志记录

日志信息会同时输出到控制台和文件 `api.log` 中，方便调试和监控。

示例日志格式：

```
2023-10-01 12:00:00 - INFO - 开始初始化 API...
2023-10-01 12:00:01 - INFO - 数据库连接成功
2023-10-01 12:00:02 - INFO - 端口可用
2023-10-01 12:00:03 - INFO - 文件夹已创建: Processed
```

---

## 注意事项

1. **图片格式**: 当前仅支持 JPEG 格式的图片压缩。如果需要支持其他格式，请修改 `compress_image` 函数。
2. **安全性**: 请确保 `config.yaml` 文件的安全性，避免泄露敏感信息。
3. **HTTPS**: 如果启用 `strict_https`，请确保服务器已正确配置 SSL 证书。

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！如果您发现任何问题或有改进建议，请随时联系我。

---

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

---

## 联系方式

- **作者**: 朝汐
- **GitHub**: [https://github.com/BorderRegion](https://github.com/BorderRegion)

---
