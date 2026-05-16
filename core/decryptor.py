import base64
import json
import sys
import os
from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad

# 加载环境变量
load_dotenv()

# 默认解密密钥 (从环境变量读取)
BI_DECRYPT_KEY = os.getenv("BI_DECRYPT_KEY", "").encode("utf-8")


def decrypt_response(encrypted_data, key=BI_DECRYPT_KEY):
    """
    解密接口返回的加密数据。

    :param encrypted_data: Base64 编码的加密字符串
    :param key: AES 密钥 (bytes), 默认从环境变量 BI_DECRYPT_KEY 读取
    :return: 解密后的 JSON 字典或原始字符串
    """
    if not encrypted_data:
        return None

    try:
        # Base64 解码
        ciphertext = base64.b64decode(encrypted_data)

        # AES-ECB 解密
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted_data = cipher.decrypt(ciphertext)

        # 去除 Pkcs7 填充
        unpadded_data = unpad(decrypted_data, AES.block_size)

        # 尝试解析为 JSON
        result_str = unpadded_data.decode("utf-8")
        try:
            return json.loads(result_str)
        except json.JSONDecodeError:
            return result_str

    except Exception as e:
        raise ValueError(f"解密失败: {e}")


def encrypt_data(data, key=BI_DECRYPT_KEY):
    """
    加密数据（用于测试）。

    :param data: 字符串或字典
    :param key: AES 密钥 (bytes)
    :return: Base64 编码的加密字符串
    """
    if isinstance(data, (dict, list)):
        data = json.dumps(data, ensure_ascii=False)

    # 填充
    padded_data = pad(data.encode("utf-8"), AES.block_size)

    # AES-ECB 加密
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(padded_data)

    # Base64 编码
    return base64.b64encode(ciphertext).decode("utf-8")


if __name__ == "__main__":
    # 提供 CLI 简单调用方式
    if len(sys.argv) < 2:
        print("使用方法: python decryptor.py <encrypted_string_or_file_path>")
        sys.exit(1)

    arg = sys.argv[1]

    # 检查是否是文件路径
    try:
        with open(arg, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # 如果是 JSON 文件，尝试提取 'data' 字段
            try:
                js = json.loads(content)
                if isinstance(js, dict) and "data" in js:
                    content = js["data"]
            except json.JSONDecodeError:
                pass
    except FileNotFoundError:
        content = arg

    try:
        result = decrypt_response(content)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
