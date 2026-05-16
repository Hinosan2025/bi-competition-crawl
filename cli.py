import argparse
import json
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from crawl.crawl_category_layout import main as run_crawl
from crawl.export_to_excel import export_shop_month

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cli.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="BI 竞品数据抓取与导出工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ---- Crawl 子命令 ----
    crawl_parser = subparsers.add_parser("crawl", help="爬取店铺目录数据")
    crawl_parser.add_argument("-s", "--start", required=True, help="开始月份 (YYYY-MM)")
    crawl_parser.add_argument("-e", "--end", required=True, help="结束月份 (YYYY-MM)")
    crawl_parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的文件（默认跳过）",
    )
    crawl_parser.add_argument(
        "-id",
        "--shop-id",
        help="可选：指定店铺 ID（用于测试或单店运行）",
    )

    # ---- Export 子命令 ----
    export_parser = subparsers.add_parser("export", help="导出数据到 Excel")
    export_parser.add_argument(
        "-s", "--start", required=True, help="开始月份 (YYYY-MM)"
    )
    export_parser.add_argument("-e", "--end", required=True, help="结束月份 (YYYY-MM)")
    export_parser.add_argument(
        "-id", "--shop-id", help="可选：指定店铺 ID（默认处理所有店铺）"
    )

    # ---- All 子命令 ----
    all_parser = subparsers.add_parser(
        "all", help="一键完成“爬取 + 解析 + 导出”的全流程"
    )
    all_parser.add_argument("-s", "--start", required=True, help="开始月份 (YYYY-MM)")
    all_parser.add_argument("-e", "--end", required=True, help="结束月份 (YYYY-MM)")
    all_parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的文件（默认跳过）",
    )
    all_parser.add_argument(
        "-id",
        "--shop-id",
        help="可选：指定店铺 ID（用于测试或单店运行）",
    )

    args = parser.parse_args()

    if args.command == "crawl":
        success = run_crawl(
            date_start=args.start,
            date_end=args.end,
            skip_existing_files=not args.force,
            target_shop_id=args.shop_id,
        )
        if not success:
            logger.error("爬取任务未完全成功，请检查日志。")
            sys.exit(1)

    elif args.command == "export":
        # 获取月份列表
        from crawl.crawl_category_layout import generate_months

        months = list(generate_months(args.start, args.end))

        # 读取店铺信息
        shops_file = Path(__file__).parent / "target_shops.json"
        if not shops_file.exists():
            logger.error(f"未找到 {shops_file.absolute()}")
            return

        with open(shops_file, "r", encoding="utf-8") as f:
            shops = json.load(f)

        for shop in shops:
            shop_name = shop["shop_name"]
            shop_id = shop["shop_id"]

            # 如果指定了 shop_id，则过滤
            if args.shop_id and shop_id != args.shop_id:
                continue

            logger.info(f"\n[导出店铺] {shop_name} ({shop_id})")
            for month in months:
                logger.info(f"  [月份] {month}")
                try:
                    export_shop_month(shop_id=shop_id, month=month)
                except Exception as e:
                    logger.error(f"    导出失败: {e}")

    elif args.command == "all":
        # 1. 爬取
        logger.info(">>> 步骤 1: 开始爬取数据...")
        success = run_crawl(
            date_start=args.start,
            date_end=args.end,
            skip_existing_files=not args.force,
            target_shop_id=args.shop_id,
        )

        if not success:
            logger.error(">>> 步骤 1 爬取期间存在失败项，停止后续导出步骤。")
            sys.exit(1)

        # 2. 导出
        logger.info("\n>>> 步骤 2: 开始导出 Excel...")
        # 读取店铺信息
        shops_file = Path(__file__).parent / "target_shops.json"
        if not shops_file.exists():
            logger.error(f"未找到 {shops_file.absolute()}")
            return

        with open(shops_file, "r", encoding="utf-8") as f:
            shops = json.load(f)

        # 生成月份列表
        from crawl.crawl_category_layout import generate_months

        months = list(generate_months(args.start, args.end))

        for shop in shops:
            shop_name = shop["shop_name"]
            shop_id = shop["shop_id"]

            # 如果指定了 shop_id，则过滤
            if args.shop_id and shop_id != args.shop_id:
                continue

            logger.info(f"\n[处理店铺] {shop_name} ({shop_id})")
            for month in months:
                logger.info(f"  [导出月份] {month}")
                try:
                    export_shop_month(shop_id=shop_id, month=month)
                except Exception as e:
                    logger.error(f"    导出失败: {e}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
