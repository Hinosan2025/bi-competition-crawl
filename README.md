# 竞品分析工具 (针对边界BI/Boundary BI)

这是一个用于抓取和分析“边界BI”平台品类布局分析中竞品数据的自动化工具。它能够自动捕获鉴权凭证、批量请求接口、解密数据并导出为美化的 Excel 报表。

---

## 📖 目录

1. [🌟 功能亮点](#-功能亮点)
2. [🚀 快速开始](#-快速开始)
3. [🛠 详细配置指南](#-详细配置指南)
4. [💻 CLI 使用文档](#-cli-使用文档)
5. [🧠 核心实现逻辑](#-核心实现逻辑)
6. [🔍 技术原理与解密逆向](#-技术原理与解密逆向)
7. [❓ 常见问题排查](#-常见问题排查)
8. [⚖️ 免责声明](#-免责声明)

---

## 🌟 功能亮点

- **自动接管浏览器**：利用远程调试协议接管现有浏览器会话，无需手动输入账号密码。
- **动态凭证捕获**：自动拦截并提取接口请求中的 Token 和 Cookie。
- **高性能抓取**：采用纯接口请求模式，脱离 UI 限制，支持多店、多月并发/连续抓取。
- **自动化解密**：内置 AES-128-ECB 解密逻辑，支持通过环境变量灵活配置解密密钥。
- **专业报表导出**：一键生成带商品图片、格式美化、关键指标计算的 Excel 报表。

---

## 🚀 快速开始

### 1. 安装环境

本项目推荐使用 [uv](https://github.com/astral-sh/uv) 进行包管理：

```bash
git clone https://github.com/your-username/bi-competion-crawl.git
cd bi-competion-crawl
uv sync
```

### 2. 基础配置

1. 复制 `.env.example` 为 `.env`。
2. 填写相关参数（如 `TARGET_URL`、`BI_DECRYPT_KEY`）。

### 3. 运行爬虫

启动开启了远程调试端口的 Chrome（默认端口 `9222`）：

```bash
# Windows 示例
chrome.exe --remote-debugging-port=9222
```

执行全流程任务：

```bash
uv run python cli.py all -s 2025-01 -e 2025-01
```

---

## 🛠 详细配置指南

本项目需要手动配置目标店铺列表才能正常运行。由于平台限制，建议从浏览器获取原始数据。

### 1. 获取原始店铺数据 (shop.json)

本项目需要一份包含所有目标店铺及其看板 ID 的原始数据。请按以下步骤获取：

1.  **访问页面**：在浏览器中登录并进入“品类布局分析”数据页面（URL 见 `.env` 配置）。
2.  **定位接口**：按下 `F12` 打开开发者工具，切换到 **Network (网络)** 标签，搜索 `getBaseHistory`。
3.  **提取数据**：
    - 查看名为 `getBaseHistory` 的接口请求。
    - 查看该接口的 **Response (响应)** 内容。
    - 将返回的 JSON 字符串完整复制。
4.  **保存文件**：在项目根目录下创建 `shop.json` 文件，并粘贴上述内容。

### 2. 生成目标店铺列表 (target_shops.json)

获取到 `shop.json` 后，使用项目提供的提取工具进行清洗和格式化：

```bash
# 运行提取工具
uv run python tools/extract_shops.py
```

**工具说明**：

- 该脚本会读取 `shop.json`，提取每个店铺的 `shopName` 和 `shopId`。
- 执行成功后，根目录下会生成 `target_shops.json`。
- **自定义筛选**：您可以手动编辑 `target_shops.json`，仅保留您关心的店铺，以减少爬取时间。

### 3. 获取解密密钥 (BI_DECRYPT_KEY)

平台的数据采用 AES 加密。获取密钥的方法：

1. 在开发者工具中搜索关键词（如 `access-referer` ）。
2. 查看相关 JS 文件源码，寻找 16 位长度的密钥字符串 ( `let td, ad = "xxxxxxxxxxxxMDF";`.)。
3. **密钥参考**：请查看 `.env.example` 中的配置注释。

> [!IMPORTANT]
> `shop.json` 和 `target_shops.json` 包含业务敏感信息，已默认加入 `.gitignore`。

---

## 💻 CLI 使用文档

本项目提供统一的命令行工具 `cli.py`。

### 命令格式

```bash
uv run python cli.py [命令] [参数]
```

### 可用命令

#### 1. `crawl`：数据爬取

- `-s`, `--start` (必填)：开始月份 (YYYY-MM)。
- `-e`, `--end` (必填)：结束月份 (YYYY-MM)。
- `--force`：强制覆盖已存在的文件。
- `-id`：指定单个店铺 ID。

#### 2. `export`：数据导出

读取 `data/` 目录下的 JSON 文件生成 Excel。

- `-s`, `-e`: 月份范围。
- `-id`: 指定店铺。

#### 3. `all`：一键全流程

顺序执行爬取与导出。**强烈建议在测试时指定 `-id`。**

**指令示例**：

```bash
# 爬取并导出 2025年1月的所有店铺数据
uv run python cli.py all -s 2025-01 -e 2025-01
```

---

## 🧠 核心实现逻辑

1. **环境探针**：自动检测 `9222` 端口。连接成功后，脚本会在浏览器 Tab 标题前加上 `🟢` 标识。
2. **凭证捕获**：动态监听网络请求，拦截包含 `getGoodListByShopAnalysis` 的请求，提取 Headers（Token 等）和当前 Cookie。
3. **API 模拟**：使用 `requests.post` 带上凭证直接发送请求，脱离浏览器 UI 限制。
4. **自动化解密**：实时调用解密模块还原 `data` 字段。
5. **分层存储**：抓取的数据按店铺/月份分层存放，保留原始响应与解密 JSON。

---

## 🔍 技术原理与解密逆向

### 1. 现象描述

在抓取数据时，发现接口返回的核心业务数据位于 `data` 字段，表现为乱码 Base64 字符串：

```json
{
  "success": true,
  "code": 200,
  "data": "Cq+8xN...[Base64]...==",
  "trace": "..."
}
```

### 2. 逆向分析过程

1.  **流量观测**：确认 `getGoodListByShopAnalysis` 接口是核心数据来源。
2.  **JS 逆向**：通过全局搜索 `decrypt`、`AES` 定位到前端处理逻辑：
    - 发现使用了 `crypto-js` 库。
    - 确认模式为 `ECB`，填充方式为 `Pkcs7`。
    - 在源码中提取到了 16 字节的硬编码密钥（Key）。

### 3. 加解密参数表

| 参数           | 值        | 说明                   |
| :------------- | :-------- | :--------------------- |
| **算法**       | AES-128   | 高级加密标准           |
| **模式**       | ECB       | 电子密码本模式 (无 IV) |
| **填充**       | PKCS7     | 标准字节填充           |
| **密钥 (Key)** | 见 `.env` | 16 字节密钥            |
| **编码**       | Base64    | 密文以 Base64 传输     |

### 4. Python 实现参考

项目在 `core/decryptor.py` 中实现了完整逻辑：

```python
import os
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 从环境变量加载密钥
KEY = os.getenv("BI_DECRYPT_KEY", "").encode("utf-8")

def decrypt_data(encrypted_str):
    # 1. Base64 解码
    ciphertext = base64.b64decode(encrypted_str)
    # 2. 初始化 AES ECB 实例
    cipher = AES.new(KEY, AES.MODE_ECB)
    # 3. 执行解密并去除填充
    decrypted = cipher.decrypt(ciphertext)
    unpadded = unpad(decrypted, AES.block_size)
    # 4. 解析结果
    return json.loads(unpadded.decode("utf-8"))
```

---

## ❓ 常见问题排查

- **400 错误 (操作类型不能为空)**：通常是接口 Payload 参数不完整，请确保相关必要字段。
- **解密失败 (Padding Error)**：密钥配置错误或数据包截断。
- **Token 失效**：平台 Token 具有时效性。脚本会通过监听 `getBaseHistory` 动态捕获最新凭证。

---

## ⚖️ 免责声明

1. 本工具仅供**学习和研究**目的使用，请勿用于商业或非法用途。
2. 使用本工具产生的任何后果由使用者自行承担，作者不承担法律责任。
3. 请遵守目标平台的《服务协议》，尊重数据版权。

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源。
