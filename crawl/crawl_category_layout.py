import json
import os
import random
import logging
import sys
import socket

from datetime import datetime
from pathlib import Path
from time import sleep
import requests
from dotenv import load_dotenv

from core.decryptor import decrypt_response
from DrissionPage import WebPage, ChromiumOptions

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crawler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 全局变量配置（优先从环境变量读取）
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "")
BROWSER_PORT = int(os.getenv("BROWSER_PORT", 9222))
TARGET_URL = os.getenv(
    "TARGET_URL", "https://example-bi-platform.com/workTable/categoryLayout"
)
API_URL_BASE = os.getenv(
    "API_URL", "https://example-bi-platform.com/api/getGoodListByShopAnalysis"
)
API_PATTERN = os.getenv("API_PATTERN", "getGoodListByShopAnalysis")


class BICategoryCrawler:
    """BI 目录布局数据爬取器"""

    def __init__(
        self,
        browser_port: int = 9222,
        data_root: str = "data",
        user_data_path: str = None,
        api_url: str = None,
    ):
        self.browser_port = browser_port
        self.data_root = Path(data_root)
        self.user_data_path = user_data_path
        self.api_url = api_url or API_URL_BASE
        self.headers = {}

    def connect_browser(self) -> WebPage:
        """连接到已有浏览器"""
        logger.info(f"正在连接到端口 {self.browser_port} 的浏览器...")

        # 增加端口检查，防止 DrissionPage 在连不上时自动启动新的浏览器

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", self.browser_port)) != 0:
                logger.error(
                    f"未能在 127.0.0.1:{self.browser_port} 检测到已启动的浏览器！"
                )
                logger.info(
                    "请确保您已手动启动 Chrome，并带有参数：--remote-debugging-port=%d",
                    self.browser_port,
                )
                return None

        options = ChromiumOptions().set_local_port(self.browser_port)

        # 注意：连接已有浏览器时，不要设置 user_data_path。
        # 如果设置了，DrissionPage 可能会因为试图匹配或锁定该目录而导致连接失败。
        # 只要您的浏览器启动时已经带了正确的 userdata，这里直接通过端口连接即可。
        logger.info(
            f"提示：连接已有浏览器时忽略 UserData 路径设置，直接通过端口 {self.browser_port} 连接。"
        )

        try:
            page = WebPage(chromium_options=options)
            logger.info("成功连接到浏览器。")
            return page

        except Exception as e:
            logger.error(f"连接浏览器失败: {e}")
            logger.info(
                "请确保 Chrome 浏览器已启动，且启动参数包含 --remote-debugging-port=%d",
                self.browser_port,
            )
            return None

    def capture_credentials(
        self, page: WebPage, api_pattern: str, target_url: str
    ) -> bool:
        """监听并捕获凭证

        返回: 是否捕获成功
        """
        logger.info(f"当前页面 URL: {page.url}")
        logger.info(f"请确保您已手动跳转到: {target_url}")

        # 新增：接管状态提示（绿点）与用户控制
        try:
            original_title = page.title
            # 在标题前加绿点表示接管
            page.run_js("document.title = '🟢 [接管中] ' + document.title")

            # 控制台询问用户是否继续
            ans = input("脚本已成功接管浏览器！是否开始刷新并捕获凭据？(y/n): ")

            # 恢复原标题
            page.run_js(f"document.title = {json.dumps(original_title)}")

            if ans.lower() != "y":
                logger.warning("用户取消了运行。")
                sys.exit(0)
        except Exception as e:
            logger.error(f"在浏览器中设置状态失败（可能处于特殊页面）: {e}")
            # 降级为控制台询问
            ans = input("无法在浏览器弹窗。是否在控制台继续运行？(y/n): ")
            if ans.lower() != "y":
                sys.exit(0)

        logger.info(f"开始监听包含 '{api_pattern}' 的接口请求...")
        page.listen.start(api_pattern)

        logger.info("正在刷新页面以触发请求捕获...")
        page.refresh()

        logger.info("等待接口请求...")
        res = page.listen.wait(timeout=15)
        page.listen.stop()

        if not res:
            logger.error("超时：未捕获到目标接口请求。")
            return False

        logger.info("成功捕获到接口请求！")
        req = res.request

        # 提取并标准化 Headers
        raw_headers = dict(req.headers)
        self.headers = {}

        # 寻找 Token (不区分大小写)
        token_found = ""
        for k, v in raw_headers.items():
            if k.lower() == "bi-token":
                token_found = v
                self.headers["Bi-Token"] = v
            else:
                self.headers[k] = v

        # 手动处理 Cookie，确保 Session 鉴权有效
        cookies = page.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        self.headers["Cookie"] = cookie_str
        self.headers["Content-Type"] = "application/json;charset=UTF-8"

        # 打印调试信息
        logger.info(f"成功捕获到接口请求！真实 URL: {req.url}")
        if not token_found:
            logger.warning(
                f"警告：未在 Headers 中找到 'Bi-Token'。当前可用键名: {list(raw_headers.keys())}"
            )

        logger.info(f"已整理 Headers。Token 长度: {len(token_found)}")
        return True

    def fetch_single_month(self, shop_id: str, shop_name: str, month: str) -> dict:
        """获取单个店铺单月的数据 (纯接口请求，方便独立测试)"""
        payload = {
            "hasAuthCate": False,
            "shopIdList": [shop_id],
            "startDate": month,
            "endDate": month,
        }

        try:
            response = requests.post(
                self.api_url, headers=self.headers, json=payload, timeout=20
            )

            if response.status_code == 200:
                res_json = response.json()

                # 新增：直接解析/解密 data 数据
                decrypted_data = None
                if isinstance(res_json, dict) and "data" in res_json:
                    try:
                        # 动态导入解密模块

                        decrypted_data = decrypt_response(res_json["data"])
                        logger.info("    [解密] 成功解密响应中的 data 数据。")

                        # 数据校验：检查解密后的 shopId 是否匹配
                        if isinstance(decrypted_data, dict):
                            shop_info_list = decrypted_data.get("goodsToShopCate", [])
                            if not shop_info_list:
                                raise ValueError(
                                    "解密数据中未找到 goodsToShopCate 或列表为空"
                                )

                            returned_shop_id = str(
                                shop_info_list[0].get("shopId") or ""
                            )
                            if not returned_shop_id:
                                raise ValueError("解密数据中 shopId 为空")

                            if returned_shop_id != str(shop_id):
                                raise ValueError(
                                    f"数据不匹配！请求 ID: {shop_id}, 返回 ID: {returned_shop_id}"
                                )
                            else:
                                logger.info(
                                    f"    [校验] 数据校验通过，匹配店铺 ID: {shop_id}"
                                )
                    except Exception as e:
                        logger.error(f"    [解密/校验] 失败: {e}")
                        raise e

                # 组装完整结构进行存储
                combined_data = {
                    "request": {"url": self.api_url, "payload": payload},
                    "response": res_json,
                    "decrypted_data": decrypted_data,
                }
                return combined_data
            else:
                logger.error(
                    f"    请求失败，状态码: {response.status_code}, 内容: {response.text[:100]}"
                )
                return None
        except Exception as e:
            logger.exception(f"    请求发生异常: {e}")
            return None

    def get_data_file_path(self, shop_name: str, shop_id: str, month: str) -> Path:
        """获取数据文件的保存路径"""
        safe_shop_name = (
            shop_name.replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("*", "_")
            .replace("?", "_")
            .replace('"', "_")
            .replace("<", "_")
            .replace(">", "_")
            .replace("|", "_")
        )
        shop_dir = self.data_root / f"{safe_shop_name}_{shop_id}" / "responses"
        file_name = f"data_{shop_id}_{month}.json"
        return shop_dir / file_name

    def save_data(self, data: dict, shop_name: str, shop_id: str, month: str) -> Path:
        """保存数据到指定目录

        返回: 保存的文件路径
        """
        file_path = self.get_data_file_path(shop_name, shop_id, month)
        shop_dir = file_path.parent
        shop_dir.mkdir(parents=True, exist_ok=True)

        # 提取解密数据，避免包含在请求响应的主文件中
        data_to_save = data.copy()
        decrypted_data = data_to_save.pop("decrypted_data", None)

        # 保存主文件（包含请求内容和原始响应）
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)

        # 如果有解密数据，另外存储一份
        if decrypted_data is not None:
            # 修改为单独的 decrypted 目录
            decrypted_dir = shop_dir.parent / "decrypted"
            decrypted_dir.mkdir(parents=True, exist_ok=True)

            decrypted_file_name = f"decrypted_{shop_id}_{month}.json"
            decrypted_file_path = decrypted_dir / decrypted_file_name
            with open(decrypted_file_path, "w", encoding="utf-8") as f:
                json.dump(decrypted_data, f, ensure_ascii=False, indent=2)
            logger.info(
                f"    [解密] 数据已单独保存至: {decrypted_file_path.absolute()}"
            )

        return file_path


def generate_months(start_month: str, end_month: str):
    """生成月份列表，格式为 YYYY-MM"""
    start = datetime.strptime(start_month, "%Y-%m")
    end = datetime.strptime(end_month, "%Y-%m")

    current = start
    while current <= end:
        yield current.strftime("%Y-%m")
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


def main(
    date_start: str = None,
    date_end: str = None,
    skip_existing_files: bool = True,
    target_shop_id: str = None,
):
    # 校验日期参数
    if not date_start or not date_end:
        logger.error("错误：必须提供 date_start 和 date_end 参数，格式为 'YYYY-MM'。")
        return

    # 使用全局变量
    browser_port = BROWSER_PORT
    user_data_path = USER_DATA_PATH
    target_url = TARGET_URL
    api_pattern = API_PATTERN

    # 读取格式化后的店铺信息
    shops_file = Path(__file__).parent.parent / "target_shops.json"
    if not shops_file.exists():
        logger.error(
            f"错误：未找到 {shops_file.absolute()}，请确保项目根目录下存在该文件。"
        )
        return

    with open(shops_file, "r", encoding="utf-8") as f:
        shops = json.load(f)

    logger.info(f"成功加载了 {len(shops)} 个店铺。")

    # 初始化爬取器
    crawler = BICategoryCrawler(
        browser_port=browser_port, data_root="data", user_data_path=user_data_path
    )

    # 1. 连接浏览器
    page = crawler.connect_browser()
    if not page:
        raise RuntimeError(
            f"无法连接到浏览器，请确保浏览器已启动并开启了远程调试端口 {browser_port}。"
        )

    # 2. 捕获凭证
    success = crawler.capture_credentials(page, api_pattern, target_url)
    if not success:
        raise RuntimeError(
            f"未能捕获到接口凭证，请确保页面已正确加载且包含匹配 '{api_pattern}' 的请求。"
        )

    # 3. 循环请求
    months = list(generate_months(date_start, date_end))
    logger.info(f"计划爬取的月份: {months}")

    all_success = True  # 记录是否全量成功

    for shop in shops:
        shop_name = shop["shop_name"]
        shop_id = shop["shop_id"]

        # 如果指定了目标店铺，则进行过滤（用于测试或单店运行）
        if target_shop_id and shop_id != target_shop_id:
            continue

        logger.info(f"\n[店铺] 开始处理: {shop_name} ({shop_id})")

        for month in months:
            logger.info(f"  [月份] {month}")

            # 检查文件是否存在
            if skip_existing_files:
                file_path = crawler.get_data_file_path(shop_name, shop_id, month)
                if file_path.exists():
                    logger.info(f"    [跳过] 文件已存在: {file_path}")
                    continue

            # 调用解耦后的获取数据方法
            try:
                data = crawler.fetch_single_month(shop_id, shop_name, month)
                if data:
                    # 调用解耦后的保存数据方法
                    file_path = crawler.save_data(data, shop_name, shop_id, month)
                    logger.info(f"    成功保存: {file_path}")
                else:
                    logger.error(
                        f"    [失败] 未能获取到 {shop_name} {month} 的有效数据。"
                    )
                    all_success = False
            except Exception as e:
                logger.error(f"    [异常] 处理 {shop_name} {month} 时出错: {e}")
                all_success = False

            # 随机休眠 5-8 秒
            sleep_time = random.uniform(5.0, 8.0)
            logger.info(f"    随机休眠 {sleep_time:.2f} 秒...")
            sleep(sleep_time)

    if all_success:
        logger.info("\n所有店铺及月份数据爬取任务已成功完成！")
    else:
        logger.warning("\n爬取任务已结束，但部分数据抓取失败，请检查日志。")

    return all_success
