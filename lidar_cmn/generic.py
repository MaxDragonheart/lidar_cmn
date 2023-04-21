from pathlib import Path
from typing import Union


def check_path(path: Union[str, Path]) -> Path:
    if isinstance(path, str):
        print("STRING")
        
