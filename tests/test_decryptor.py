import unittest
import os
import json
from core.decryptor import decrypt_response, encrypt_data


class TestDecryptor(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.output_dir = os.path.join(self.base_dir, "output")

    def test_round_trip(self):
        """测试加密后解密是否能还原"""
        test_data = {"message": "Hello, World!", "status": 200}
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_response(encrypted)
        self.assertEqual(decrypted, test_data)

    def test_file_decryption(self):
        """测试从文件中读取加密数据并解密"""
        encrypted_file = os.path.join(self.data_dir, "test_encrypted.txt")
        if not os.path.exists(encrypted_file):
            self.skipTest("Test encrypted file not found.")

        with open(encrypted_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        decrypted = decrypt_response(content)

        # 验证解密后的数据
        self.assertIsInstance(decrypted, dict)
        self.assertEqual(decrypted.get("name"), "test_shop")

    def test_output_generation(self):
        """测试解密并输出到文件"""
        encrypted_file = os.path.join(self.data_dir, "test_encrypted.txt")
        if not os.path.exists(encrypted_file):
            self.skipTest("Test encrypted file not found.")

        with open(encrypted_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        decrypted = decrypt_response(content)

        # 写入输出目录
        output_file = os.path.join(self.output_dir, "run_decrypted.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(decrypted, f, ensure_ascii=False, indent=2)

        self.assertTrue(os.path.exists(output_file))

        # 清理
        os.remove(output_file)

    def test_real_data_decryption(self):
        """尝试解密真实的 HAR 文件数据（如果存在）"""
        har_path = r"c:\vibe-coding\bi-competion-crawl\tmp\filtered_entries.json"
        if not os.path.exists(har_path):
            self.skipTest("HAR file not found, skipping real data test.")

        try:
            with open(har_path, "r", encoding="utf-8") as f:
                har_data = json.load(f)

            encrypted_data = None
            if isinstance(har_data, list) and len(har_data) > 0:
                entry = har_data[0]
                response_text = (
                    entry.get("response", {}).get("content", {}).get("text", "")
                )
                if response_text:
                    resp_json = json.loads(response_text)
                    encrypted_data = resp_json.get("data")

            if not encrypted_data:
                self.skipTest("No encrypted data found in HAR entry.")

            decrypted = decrypt_response(encrypted_data)
            self.assertIsInstance(decrypted, dict)
            self.assertIn("shopInfoVoList", decrypted)

        except Exception as e:
            self.fail(f"Real data decryption failed: {e}")


if __name__ == "__main__":
    unittest.main()
