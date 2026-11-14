"""Điểm khởi chạy chương trình Quản lý Khách sạn.

Cách chạy:
    python main.py
"""

import os
import sys
from pathlib import Path

from hotel.managers.hotel_manager import HotelManager
from hotel.ui.app import HotelApp

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    # Hiển thị đúng tiếng Việt trên console Windows
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    os.chdir(BASE_DIR)
    hotel = HotelManager(data_dir=BASE_DIR / "data", invoice_dir=BASE_DIR / "invoices",
                         export_dir=BASE_DIR / "exports")
    HotelApp(hotel).run()


if __name__ == "__main__":
    main()
