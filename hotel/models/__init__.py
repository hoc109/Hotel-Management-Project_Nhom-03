"""Lớp thực thể (entity) của hệ thống, tách biệt khỏi lớp quản lý."""

from hotel.models.enums import BookingStatus, Permission, Role, RoomStatus
from hotel.models.room import DeluxeRoom, Room, RoomFactory, StandardRoom, SuiteRoom
from hotel.models.guest import Guest
from hotel.models.service import Service, ServiceUsage
from hotel.models.booking import Booking
from hotel.models.discount import (DiscountCalculator, DiscountPolicy,
                                   LongStayDiscount, LoyaltyDiscount)
from hotel.models.invoice import Invoice
from hotel.models.user import Admin, Receptionist, User, UserFactory

__all__ = [
    "BookingStatus", "Permission", "Role", "RoomStatus",
    "Room", "StandardRoom", "DeluxeRoom", "SuiteRoom", "RoomFactory",
    "Guest", "Service", "ServiceUsage", "Booking",
    "DiscountPolicy", "LongStayDiscount", "LoyaltyDiscount", "DiscountCalculator",
    "Invoice", "User", "Admin", "Receptionist", "UserFactory",
]
