"""Lớp quản lý (nghiệp vụ), tách biệt khỏi lớp thực thể."""

from hotel.managers.base_manager import BaseManager
from hotel.managers.room_manager import RoomManager
from hotel.managers.guest_manager import GuestManager
from hotel.managers.service_manager import ServiceManager
from hotel.managers.booking_manager import BookingManager
from hotel.managers.report_manager import ReportManager
from hotel.managers.auth_manager import AuthManager
from hotel.managers.hotel_manager import HotelManager

__all__ = ["BaseManager", "RoomManager", "GuestManager", "ServiceManager",
           "BookingManager", "ReportManager", "AuthManager", "HotelManager"]
