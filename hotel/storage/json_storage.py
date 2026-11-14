"""Đọc/ghi dữ liệu dạng JSON, mỗi tập dữ liệu là một file trong thư mục ``data/``."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from hotel.utils.exceptions import StorageError


class JsonStorage:
    """Lưu và nạp danh sách dict ra file JSON.

    * Ghi an toàn: ghi vào file tạm rồi ``os.replace`` để không làm hỏng file
      cũ nếu chương trình bị tắt giữa chừng.
    * Đọc: nếu file hỏng (sai cú pháp JSON) thì đổi tên thành ``.bak`` và ghi
      cảnh báo vào ``warnings`` để giao diện thông báo cho người dùng.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.__data_dir = Path(data_dir)
        self.__warnings: list[str] = []

    @property
    def data_dir(self) -> Path:
        return self.__data_dir

    @property
    def warnings(self) -> list[str]:
        return list(self.__warnings)

    def clear_warnings(self) -> None:
        self.__warnings.clear()

    def _path(self, name: str) -> Path:
        return self.__data_dir / f"{name}.json"

    def exists(self, name: str) -> bool:
        return self._path(name).is_file()

    def load(self, name: str) -> list[dict] | None:
        """Đọc file ``<name>.json``. Trả về ``None`` nếu chưa có hoặc file hỏng."""
        path = self._path(name)
        if not path.is_file():
            return None
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                raise ValueError("dữ liệu gốc phải là một danh sách")
            return data
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
            backup = path.with_suffix(f".{datetime.now():%Y%m%d%H%M%S}.bak")
            os.replace(path, backup)
            self.__warnings.append(
                f"File {path.name} bị lỗi ({exc}); đã sao lưu thành {backup.name}.")
            return None
        except OSError as exc:
            raise StorageError(f"Không đọc được file {path}: {exc}") from exc

    def save(self, name: str, records: list[dict]) -> None:
        """Ghi danh sách dict ra ``<name>.json`` (UTF-8, thụt lề cho dễ đọc)."""
        try:
            self.__data_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=self.__data_dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(records, file, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path(name))
        except OSError as exc:
            raise StorageError(f"Không ghi được dữ liệu {name}: {exc}") from exc
