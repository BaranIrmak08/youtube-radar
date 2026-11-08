"""JSON dosyalarını okur ve atomik olarak yazar."""
import json
import os
from pathlib import Path


def yukle(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def kaydet(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    gecici = path.with_suffix(path.suffix + ".tmp")
    gecici.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(gecici, path)
