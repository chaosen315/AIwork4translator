from typing import NamedTuple
import os

class GlobalConfig(NamedTuple):
    preserve_structure: bool
    max_chunk_size: int

    @classmethod
    def create(cls) -> "GlobalConfig":
        defaults = {
            "preserve_structure": True,
            "max_chunk_size": 2000,
        }
        return cls(
            preserve_structure=os.getenv("PRESERVE_STRUCTURE", str(defaults["preserve_structure"]))
            .lower() == "true",
            max_chunk_size=int(os.getenv("MAX_CHUNK_SIZE", str(defaults["max_chunk_size"]))),
        )

def setup_runtime_config() -> GlobalConfig:
    current = global_config._asdict()
    new_values = {}
    try:
        new_values["preserve_structure"] = input("是否开启结构化模式？[y/n] (留空保持当前) ").lower() in ["y", ""]
        new_size = input("输入新的段落长度（留空保持当前）: ")
        if new_size:
            new_values["max_chunk_size"] = int(new_size)
    except Exception:
        pass
    return GlobalConfig(**{**current, **new_values})

global_config = GlobalConfig.create()
