"""路径工具"""
from pathlib import Path

# telegram-service 根目录
SERVICE_ROOT = Path(__file__).parent.parent.parent  # utils -> src -> telegram-service
PROJECT_ROOT = SERVICE_ROOT.parent.parent           # services -> tradecat


def 获取数据服务CSV目录() -> Path:
    """返回 data-service CSV 目录"""
    return PROJECT_ROOT / "services" / "data-service" / "data" / "csv"


__all__ = ["获取数据服务CSV目录", "SERVICE_ROOT", "PROJECT_ROOT"]
