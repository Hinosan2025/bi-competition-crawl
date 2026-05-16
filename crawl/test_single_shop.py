import json
import os
from pathlib import Path

# 从主脚本中导入解耦后的类
from crawl.crawl_category_layout import BICategoryCrawler, USER_DATA_PATH


def main():
    # =============== 配置区域 ===============
    browser_port = 9222  # 浏览器调试端口
    user_data_path = USER_DATA_PATH  # 使用主脚本中统一设置的全局变量

    target_url = "https://example-bi-platform.com/workTable/categoryLayout"
    api_pattern = "getGoodListByShopAnalysis"
    test_month = "2025-01"  # 测试单月份
    # ========================================

    # 读取格式化后的店铺信息
    shops_file = Path(__file__).parent.parent / "target_shops.json"
    if not shops_file.exists():
        print(f"错误：未找到 {shops_file.absolute()}，请确保项目根目录下存在该文件。")
        return

    with open(shops_file, "r", encoding="utf-8") as f:
        shops = json.load(f)

    if not shops:
        print("错误：店铺列表为空。")
        return

    # 只取第一个店铺进行测试
    shop_name = "test_shop"
    shop_id = "123"

    print(f"=== 开始单店单月测试 (复用解耦类) ===")
    print(f"测试店铺: {shop_name} ({shop_id})")
    print(f"测试月份: {test_month}")

    # 初始化爬取器，数据保存到 test_data 目录以示区分
    crawler = BICategoryCrawler(
        browser_port=browser_port, data_root="test_data", user_data_path=user_data_path
    )

    # 1. 连接浏览器
    page = crawler.connect_browser()
    if not page:
        print("测试终止：无法连接浏览器。")
        return

    # 2. 捕获凭证
    success = crawler.capture_credentials(page, api_pattern, target_url)
    if not success:
        print("测试终止：未能捕获到有效凭证。")
        return

    # 3. 测试核心获取方法
    print(f"\n正在调用 fetch_single_month 测试核心请求逻辑...")
    data = crawler.fetch_single_month(shop_id, shop_name, test_month)

    if data:
        print("  请求成功！响应状态码: 200")

        # 4. 测试保存方法
        file_path = crawler.save_data(data, shop_name, shop_id, test_month)
        print(f"  测试数据已成功保存至: {file_path.absolute()}")

        # 打印部分数据预览
        # 检查解密数据或原始响应中的 data
        if data.get("decrypted_data"):
            print(
                f"  成功获取解密数据，预览 (前 200 字符): {str(data['decrypted_data'])[:200]}"
            )
        elif (
            "response" in data
            and isinstance(data["response"], dict)
            and data["response"].get("data")
        ):
            print(
                f"  成功获取原始数据 (加密)，预览 (前 200 字符): {str(data['response']['data'])[:200]}"
            )
        else:
            print("  警告：响应中未包含 'data' 字段或数据为空。")
    else:
        print("  请求失败：未获取到数据。")

    print("\n=== 测试结束 ===")


if __name__ == "__main__":
    main()
