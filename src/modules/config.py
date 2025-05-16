# 全局变量
from typing import NamedTuple
import os
import json
from pathlib import Path

class GlobalConfig(NamedTuple):
    preserve_structure: bool
    max_chunk_size: int

    @classmethod
    def create(cls) -> "GlobalConfig":
        """创建配置实例（环境变量 > 配置文件 > 默认值）"""
        # 默认配置
        defaults = {
            "preserve_structure": True,
            "max_chunk_size": 2000
        }

        # # 从配置文件加载
        # config_path = Path("config.json")
        # if config_path.exists():
        #     with open(config_path) as f:
        #         defaults.update(json.load(f))

        # 环境变量覆盖
        return cls(
            preserve_structure=os.getenv(
                "PRESERVE_STRUCTURE", 
                str(defaults["preserve_structure"])
            ).lower() == "true",
            max_chunk_size=int(os.getenv(
                "MAX_CHUNK_SIZE",
                str(defaults["max_chunk_size"])
            ))
        )


def setup_runtime_config() -> GlobalConfig:
    """交互式配置设置（临时覆盖）"""
    current = global_config._asdict()
    
    print("当前配置：")
    for k, v in current.items():
        print(f"{k}: {v}")

    new_values = {}
    try:
        new_values["preserve_structure"] = input("是否开启结构化模式？[y/n] (留空保持当前) ").lower() in ["y", ""]
        new_size = input("输入新的段落长度（留空保持当前）: ")
        if new_size:
            new_values["max_chunk_size"] = int(new_size)
    except (ValueError, KeyboardInterrupt):
        print("配置保持原样")
    
    return GlobalConfig(**{**current, **new_values})

# 初始化全局配置
global_config = GlobalConfig.create()