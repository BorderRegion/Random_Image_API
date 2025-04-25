import socket
import os
import yaml
import uvicorn
from PIL import Image
import hashlib
import sqlite3
import random
from fastapi.responses import JSONResponse, FileResponse
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import time
from collections import defaultdict
import logging
"""
    @author: 朝汐 
    @contact: https://github.com/BorderRegion
    @license: MIT_license
    @version: 1.0
    @date : 2025-04-25

"""
# 默认配置模板
DEFAULT_CONFIG = {
    "database_Name": "test.db",
    "database_Cache": 256,
    "listen_Port": 20001,
    "imagePath_Origin": "Origin",
    "imagePath_Processed": "Processed",
    "compress_image_quality": 75,
    "strict_https": False,
    "rateLimit": 5,  # 允许的最大请求数
    "time_window": 60,  # 时间窗口（秒）
    "server_host": "0.0.0.0"  # 服务器的地址，默认为0.0.0.0
}

# YAML文件名
CONFIG_FILE = "config.yaml"


def create_default_yaml():
    """如果目录下没有YAML文件，则创建默认的YAML模板"""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            yaml.dump(DEFAULT_CONFIG, file, allow_unicode=True, sort_keys=False)
        print(f"已创建默认配置文件: {CONFIG_FILE}")
    else:
        print(f"配置文件已存在: {CONFIG_FILE}")


def load_config():
    """从YAML文件中读取配置"""
    if not os.path.exists(CONFIG_FILE):
        create_default_yaml()

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config_load = yaml.safe_load(file)

    # 确保所有默认配置项都存在，即使YAML文件中缺少某些项
    for key, value in DEFAULT_CONFIG.items():
        config_load.setdefault(key, value)

    return config_load


# 配置日志记录器
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),  # 将日志写入文件
        logging.StreamHandler()          # 同时将日志输出到控制台
    ]
)

logger = logging.getLogger(__name__)


# listen_Port API 监听端口
# ssl_LicensePath ssl证书地址
# imagePath_Origin 原图路径
# imagePath_Processed 处理后图像路径
# rateLimit 单 IP 下 API 速率限制，设置为 0 则无限制
# database_Name sqlite 数据库名称,字符串类型
# database_Cache sqlite 缓存数量，默认值为 256
# compress_image_quality
# strict_http 是否强制使用 https 协议
# server_host 服务器地址

compress_image_quality = 75


# 使用字典存储每个 IP 的请求记录
request_counts = defaultdict(list)


def initialize_api():
    """初始化 API"""
    logger.info("开始初始化 API...")
    if (initialize_sqlite()
            and is_port_disuse(listen_Port)
            and ensure_directory_exists(imagePath_Origin)
            and ensure_directory_exists(imagePath_Processed)):
        logger.info("初始化完成")
        return True
    else:
        logger.error("ERROR! 未完成初始化")
        return False


def initialize_sqlite():
    """初始化数据库"""
    try:
        sqlite3.connect(database_Name).close()
        logger.info("数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"ERROR!--数据库创建失败: {e}")
        return False


def is_port_disuse(port):
    """检测端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            s.close()
            logger.info("端口可用")
            return True
        except socket.error:
            logger.error("端口被占用")
            return False


def ensure_directory_exists(directory_path):
    """确保目录存在"""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path, exist_ok=True)
            logger.info(f"文件夹已创建: {directory_path}")
            return True
        except Exception as e:
            logger.error(f"ERROR! 创建文件夹失败: {e}")
            return False
    else:
        logger.info(f"文件夹已存在: {directory_path}")
        return True


def compress_image(input_path, output_path, quality=compress_image_quality, image_format="JPEG"):
    """
    压缩图片并保存为指定格式
    :param input_path: 原始图片路径
    :param output_path: 压缩后图片路径
    :param quality: 压缩质量 (0-100)
    :param image_format: 输出图片格式
    """
    try:
        with Image.open(input_path) as img:
            # 转换为 RGB 模式（避免某些格式不支持 RGBA）
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(output_path, format=image_format, quality=quality)
        logger.info(f"图片压缩成功: {input_path} -> {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error compressing image {input_path}: {e}")
        return False


def generate_alias(file_path):
    """
    使用文件路径生成加密别名
    :param file_path: 文件路径
    :return: 加密后的别名
    """
    hash_obj = hashlib.sha256()
    hash_obj.update(file_path.encode('utf-8'))
    alias = hash_obj.hexdigest()
    logger.info(f"生成加密别名: {alias}")
    return alias


def save_to_database(db_path, alias, file_path):
    """
    将图片信息存储到 SQLite 数据库
    :param db_path: 数据库路径
    :param alias: 加密别名
    :param file_path: 图片存储路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT UNIQUE,
            file_path TEXT
        )
    """)
    try:
        cursor.execute("INSERT INTO images (alias, file_path) VALUES (?, ?)", (alias, file_path))
        conn.commit()
        logger.info(f"图片信息保存到数据库: alias={alias}, file_path={file_path}")
    except sqlite3.IntegrityError:
        logger.warning(f"Alias {alias} already exists in the database.")
    finally:
        conn.close()


def process_images(input_folder, output_folder, db_path, quality=compress_image_quality, image_format="JPEG"):
    """
    处理文件夹中的所有图片
    :param input_folder: 输入文件夹路径
    :param output_folder: 输出文件夹路径
    :param db_path: SQLite 数据库路径
    :param quality: 压缩质量
    :param image_format: 输出图片格式
    """
    logger.info("开始处理图片...")
    os.makedirs(output_folder, exist_ok=True)

    for root, _, files in os.walk(input_folder):
        for file in files:
            input_path = os.path.join(root, file)
            try:
                with Image.open(input_path):
                    pass
            except Exception:
                logger.warning(f"跳过非图片文件: {input_path}")
                continue

            alias = generate_alias(input_path)
            output_filename = f"{alias}.{image_format.lower()}"
            output_path = os.path.join(output_folder, output_filename)

            if compress_image(input_path, output_path, quality, image_format):
                save_to_database(db_path, alias, output_path)
                os.remove(input_path)
                logger.info(f"已处理并移动: {input_path} -> {output_path}")
            else:
                logger.error(f"ERROR!处理失败=w=: {input_path}")


app = FastAPI()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()

    request_times = request_counts[client_ip]
    request_times = [t for t in request_times if current_time - t < time_window]

    if len(request_times) >= rateLimit:
        logger.warning(f"IP {client_ip} 请求速率太快，触发速率限制")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests！！!"}
        )

    request_times.append(current_time)
    request_counts[client_ip] = request_times

    response = await call_next(request)
    return response


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if strict_https:
        if request.url.scheme != "https":
            https_url = request.url.replace(scheme="https")
            logger.warning(f"HTTP 请求被重定向到 HTTPS: {request.url} -> {https_url}")
            return RedirectResponse(url=https_url)

    response = await call_next(request)
    return response


@app.get('/random_image')
async def get_random_image():
    """
    随机获取一张图片并返回图片本身
    """
    logger.info("收到 /random_image 请求")
    try:
        conn = sqlite3.connect(database_Name)
        cursor = conn.cursor()

        cursor.execute("SELECT alias, file_path FROM images")
        images = cursor.fetchall()

        if not images:
            logger.error("数据库中没有找到任何图片=x=")
            return JSONResponse(content={"error": "No images found in the database"}, status_code=404)

        selected_image = random.choice(images)
        alias, file_path = selected_image

        if not os.path.exists(file_path):
            logger.error(f"图片文件未找到: {file_path}")
            return JSONResponse(content={"error": f"Image file not found at {file_path}"}, status_code=404)

        logger.info(f"返回随机图片: {file_path}")
        return FileResponse(file_path, media_type='image/jpeg', status_code=200)

    except Exception as e:
        logger.error(f"获取随机图片时发生错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

    finally:
        conn.close()


@app.get('/image_get/{alias}')
async def get_image_by_alias(alias: str):
    """
    根据别名获取图片并返回图片本身
    :param alias: 图片的加密别名,同时也作为压缩后的图片名称
    """
    logger.info(f"收到 /image_by_alias/{alias} 请求")
    try:
        conn = sqlite3.connect(database_Name)
        cursor = conn.cursor()

        cursor.execute("SELECT file_path FROM images WHERE alias = ?", (alias,))
        result = cursor.fetchone()

        if not result:
            logger.error(f"未找到别名为 {alias} 的图片")
            return JSONResponse(content={"error": f"No image found with alias {alias}"}, status_code=404)

        file_path = result[0]

        if not os.path.exists(file_path):
            logger.error(f"图片文件未找到: {file_path}")
            return JSONResponse(content={"error": f"Image file not found at {file_path}"}, status_code=404)

        logger.info(f"返回别名图片: {file_path}")
        return FileResponse(file_path, media_type='image/jpeg', status_code=200)

    except Exception as e:
        logger.error(f"根据别名获取图片时发生错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

    finally:
        conn.close()


if __name__ == "__main__":

    # 检查并创建默认YAML文件
    create_default_yaml()
    config = load_config()

    database_Name = config["database_Name"]
    database_Cache = config["database_Cache"]
    listen_Port = config["listen_Port"]
    imagePath_Origin = config["imagePath_Origin"]
    imagePath_Processed = config["imagePath_Processed"]
    compress_image_quality = config["compress_image_quality"]
    strict_https = config["strict_https"]
    rateLimit = config["rateLimit"]
    time_window = config["time_window"]
    server_host = config["server_host"]

    print("加载的配置如下：")
    print(f"数据库名称database_Name: {database_Name}")
    print(f"数据库缓存大小database_Cache: {database_Cache}")
    print(f"监听端口listen_Port: {listen_Port}")
    print(f"原图文件夹地址imagePath_Origin: {imagePath_Origin}")
    print(f"压缩后图片地址imagePath_Processed: {imagePath_Processed}")
    print(f"图片压缩质量compress_image_quality: {compress_image_quality}")
    print(f"是否强制https strict_https: {strict_https}")
    print(f"单ip的速率限制 rateLimit: {rateLimit}")
    print(f"时间窗口 time_window: {time_window}")
    print(f"api服务器地址server_host: {server_host}")

    logger.info("---启动 API 服务---")
    if initialize_api():
        process_images(imagePath_Origin, imagePath_Processed, database_Name, compress_image_quality, "JPEG")
        uvicorn.run(app, host=server_host, port=listen_Port)

