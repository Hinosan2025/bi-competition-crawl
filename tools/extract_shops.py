import json
from pathlib import Path

# 读取 shop.json
# 由于脚本在 crawl 目录中运行，需要向上查找
shop_file = Path("../shop.json")
if not shop_file.exists():
    shop_file = Path("shop.json")  # 备用路径

try:
    with open(shop_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"错误：未找到 {shop_file.absolute()}")
    exit(1)

formatted_shops = []
seen_ids = set()

# 遍历提取
for item in data.get("data", {}).get("list", []):
    for shop in item.get("dplist", []):
        shop_id = shop.get("shopid")
        shop_name = shop.get("shopName")
        if shop_id and shop_id not in seen_ids:
            seen_ids.add(shop_id)
            formatted_shops.append(
                {
                    "shop_name": shop_name,
                    "shop_id": shop_id,
                }
            )

# 保存到项目根目录
output_file = Path(__file__).parent.parent / "target_shops.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(formatted_shops, f, ensure_ascii=False, indent=2)

print(f"成功提取 {len(formatted_shops)} 个店铺，已保存至 {output_file.absolute()}")
