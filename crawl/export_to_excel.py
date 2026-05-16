import json
import time
import random
import os
import logging
from pathlib import Path
import requests
import pandas as pd
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.styles import Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter

# 配置日志
logger = logging.getLogger(__name__)


class BICategoryExporter:
    def __init__(self, data_root: str = "data"):
        self.data_root = Path(data_root)
        self.columns = [
            "月份",
            "商品图片",
            "商品id",
            "商品链接",
            "类目id",
            "类目名称",
            "全类目",
            "二级类目",
            "叶子类目",
            "店内排名",
            "店内同类目排名",
            "商品",
            "店铺",
            "销售额",
            "销售额同比",
            "销售额环比",
            "商品店铺销售额占比",
            "访客数",
            "访客数同比",
            "访客数环比",
            "UV价值",
            "搜索访客数",
            "客单价",
            "客单价同比",
            "客单价环比",
            "支付人数",
            "搜索访客数同比",
            "搜索访客数环比",
            "加购人数",
            "加购率",
            "收藏人数",
            "收藏率",
            "发货地",
            "商品店内同类目销售额占比",
            "访客数店铺占比",
            "支付转化率",
            "搜索访客数占比",
            "销售额类目占比",
            "访客数类目占比",
            "搜索访客数类目占比",
        ]

    def export_to_excel(self, shop_id: str, month: str):
        """解析指定店铺和月份的解密数据，并写入 Excel"""
        # 1. 寻找店铺目录和文件
        shop_dir = None
        for d in self.data_root.iterdir():
            if d.is_dir() and d.name.endswith(f"_{shop_id}"):
                shop_dir = d
                break

        if not shop_dir:
            logger.error(f"未找到店铺 ID 为 {shop_id} 的目录。")
            return

        json_file = shop_dir / "decrypted" / f"decrypted_{shop_id}_{month}.json"
        if not json_file.exists():
            logger.error(f"未找到文件 {json_file.absolute()}")
            return

        logger.info(f"正在解析: {json_file.name}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 2. 提取 extensibleTable
        extensible_table = data.get("extensibleTable", {})
        column_data = extensible_table.get("columnData", [])

        if not column_data:
            logger.warning("未在 extensibleTable 中找到 columnData 或数据为空。")
            return

        logger.info(f"找到 {len(column_data)} 条数据。")

        # 3. 提取店铺名称（用于文件名）
        shop_name = "未知店铺"
        if "goodsToShopCate" in data and len(data["goodsToShopCate"]) > 0:
            shop_name = data["goodsToShopCate"][0].get("shopName", shop_name)

        # 4. 组装数据行
        rows = []
        # 使用持久化的 images 目录，避免重复下载
        img_dir = shop_dir / "images"
        img_dir.mkdir(exist_ok=True)

        img_paths = []  # 记录图片路径，用于后续插入

        for idx, item in enumerate(column_data):
            if idx % 10 == 0:
                logger.info(f"正在处理第 {idx + 1}/{len(column_data)} 条数据...")
            # 基础映射
            row = {col: "" for col in self.columns}
            row["月份"] = month
            row["商品id"] = item.get("goodsId", "")
            row["商品链接"] = item.get("goodsLink", "")
            row["类目id"] = item.get("cateId", "")
            row["类目名称"] = item.get("cateName", "")
            row["全类目"] = item.get("catePathName", "")
            row["二级类目"] = item.get("secondCateName", "")
            row["叶子类目"] = item.get("cateName", "")
            row["店内排名"] = item.get("rank", "")
            row["店内同类目排名"] = item.get("cateRank", "")
            row["商品"] = item.get("goodsName", "")
            row["店铺"] = item.get("shopName", "")
            row["销售额"] = item.get("gmv", "")
            row["销售额同比"] = item.get("gmvYoYGrow", "")
            row["销售额环比"] = item.get("gmvGrow", "")
            row["商品店铺销售额占比"] = item.get("shopGmvRatio", "")
            row["访客数"] = item.get("visitor", "")
            row["访客数同比"] = item.get("visitorYoYGrow", "")
            row["访客数环比"] = item.get("visitorGrow", "")
            row["UV价值"] = item.get("uv", "")
            row["搜索访客数"] = item.get("searchVisitor", "")
            row["客单价"] = item.get("unitPrice", "")
            row["客单价同比"] = item.get("unitPriceYoYGrow", "")
            row["客单价环比"] = item.get("unitPriceGrow", "")
            row["支付人数"] = item.get("payCount", "")
            row["搜索访客数同比"] = item.get("searchVisitorYoYGrow", "")
            row["搜索访客数环比"] = item.get("searchVisitorGrow", "")
            row["加购人数"] = item.get("wqUv", "")
            row["加购率"] = item.get("wqConversionRatio", "")
            row["收藏人数"] = item.get("collectCount", "--")
            row["收藏率"] = item.get("collectRatio", "--")
            row["发货地"] = "--"  # 用户确认未找到
            row["商品店内同类目销售额占比"] = item.get("gmvRatio", "")
            row["访客数店铺占比"] = item.get("shopVisitorRatio", "")
            row["支付转化率"] = item.get("conversionRatio", "")
            row["搜索访客数占比"] = item.get("searchRatio", "")
            row["销售额类目占比"] = item.get("allShopGmvRatio", "")
            row["访客数类目占比"] = item.get("visitorCategoryRatio", "")
            row["搜索访客数类目占比"] = item.get("searchVisitorCategoryRatio", "")

            # 处理图片下载
            img_url = item.get("goodsUrl", "")
            img_path = ""
            if img_url and row["商品id"]:
                if img_url.startswith("//"):
                    img_url = "https:" + img_url

                img_path = img_dir / f"{row['商品id']}.jpg"

                # 避免重复下载
                if img_path.exists():
                    pass
                else:
                    try:
                        # 伪装 User-Agent，避免被 ban
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }
                        res = requests.get(img_url, headers=headers, timeout=5)
                        if res.status_code == 200:
                            with open(img_path, "wb") as f:
                                f.write(res.content)
                            # 增加随机延迟，防反爬
                            time.sleep(random.uniform(0.3, 1.0))
                        else:
                            logger.error(
                                f"下载图片失败 ({row['商品id']}), 状态码: {res.status_code}"
                            )
                            img_path = ""
                    except Exception as e:
                        logger.error(f"下载图片失败 ({row['商品id']}): {e}")
                        img_path = ""

            img_paths.append(img_path)
            rows.append(row)

        # 5. 写入 Excel
        excel_dir = shop_dir / "excels"
        excel_dir.mkdir(exist_ok=True)
        excel_file = excel_dir / f"{month}_{shop_name}_{shop_id}.xlsx"

        # 使用 pandas 创建基础表格
        df = pd.DataFrame(rows, columns=self.columns)

        # 直接写入（每个月一个独立文件）
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=month, index=False)

        # 6. 使用 openpyxl 插入图片和美化
        wb = openpyxl.load_workbook(excel_file)
        ws = wb[month]

        # 定义样式
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        header_font = Font(bold=True)

        # 冻结首行
        ws.freeze_panes = "A2"

        # 设置表头高度为 45
        ws.row_dimensions[1].height = 45

        # 设置数据行高为 60
        for i in range(2, len(rows) + 2):
            ws.row_dimensions[i].height = 60

        # 表头样式：水平垂直居中，加粗，加边框，且内容自动换行
        for cell in ws[1]:
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )

        # 自动列宽 + 特殊列宽
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)

            if col_letter == "B":  # 商品图片
                ws.column_dimensions[col_letter].width = 13
            else:
                # 除商品图片外，其他列宽设为 10
                ws.column_dimensions[col_letter].width = 10

        # 插入图片和美化数据行
        for idx, (row_dict, img_path) in enumerate(zip(rows, img_paths), start=2):
            # 插入图片
            if img_path and os.path.exists(img_path):
                try:
                    img = OpenpyxlImage(img_path)
                    img.width = 80
                    img.height = 80
                    ws.add_image(img, f"B{idx}")
                    ws[f"B{idx}"].value = ""  # 清空文本内容
                except Exception as e:
                    logger.error(f"插入图片失败: {e}")

            # 美化全列：加边框，仅垂直居中
            for cell in ws[idx]:
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

            # 唯独月份列、店内排名（J列）、店内同类目排名（K列）水平垂直居中
            ws[f"A{idx}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"J{idx}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"K{idx}"].alignment = Alignment(horizontal="center", vertical="center")

            # 商品列（J列）超出隐藏（不换行）
            ws[f"J{idx}"].alignment = Alignment(vertical="center", wrap_text=False)

        wb.save(excel_file)
        logger.info(f"数据已成功写入 Excel: {excel_file.absolute()}")


def export_shop_month(shop_id: str, month: str):
    exporter = BICategoryExporter()
    exporter.export_to_excel(shop_id, month)
