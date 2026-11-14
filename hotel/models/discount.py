"""Chính sách giảm giá (chức năng mở rộng) – minh họa đa hình qua lớp trừu tượng.

* ``LongStayDiscount``: ở từ 3 đêm giảm 5%, từ 7 đêm giảm 10%.
* ``LoyaltyDiscount``: khách đã có ≥ 3 lượt trả phòng trước đó giảm thêm 5%.
* ``DiscountCalculator``: cộng dồn các chính sách, tối đa 15%, chỉ áp lên tiền phòng.
"""

from abc import ABC, abstractmethod


class DiscountPolicy(ABC):
    """Lớp trừu tượng cho một chính sách giảm giá."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên chính sách hiển thị trên hóa đơn."""

    @abstractmethod
    def rate(self, nights: int, completed_stays: int) -> float:
        """Tỷ lệ giảm (0–1) với số đêm và số lượt đã ở trước đó của khách."""

    def __str__(self) -> str:
        return self.name


class LongStayDiscount(DiscountPolicy):
    """Giảm giá theo số đêm lưu trú (bậc thang)."""

    def __init__(self, tiers: list[tuple[int, float]] | None = None) -> None:
        # Sắp xếp bậc giảm dần theo số đêm để lấy bậc cao nhất đạt được
        self.__tiers = sorted(tiers or [(7, 0.10), (3, 0.05)], reverse=True)

    @property
    def name(self) -> str:
        return "Ưu đãi lưu trú dài ngày"

    def rate(self, nights: int, completed_stays: int) -> float:
        for min_nights, tier_rate in self.__tiers:
            if nights >= min_nights:
                return tier_rate
        return 0.0


class LoyaltyDiscount(DiscountPolicy):
    """Giảm giá cho khách thân thiết."""

    def __init__(self, min_stays: int = 3, discount: float = 0.05) -> None:
        self.__min_stays = min_stays
        self.__discount = discount

    @property
    def name(self) -> str:
        return "Ưu đãi khách thân thiết"

    def rate(self, nights: int, completed_stays: int) -> float:
        return self.__discount if completed_stays >= self.__min_stays else 0.0


class DiscountCalculator:
    """Tổng hợp nhiều chính sách giảm giá (cộng dồn, có mức trần)."""

    def __init__(self, policies: list[DiscountPolicy] | None = None,
                 max_rate: float = 0.15) -> None:
        self.__policies = policies if policies is not None else [LongStayDiscount(),
                                                                 LoyaltyDiscount()]
        self.__max_rate = max_rate

    @property
    def max_rate(self) -> float:
        return self.__max_rate

    def details(self, nights: int, completed_stays: int) -> list[tuple[str, float]]:
        """Các chính sách được áp dụng (tên, tỷ lệ) – gọi đa hình ``rate()``."""
        result = []
        for policy in self.__policies:
            policy_rate = policy.rate(nights, completed_stays)
            if policy_rate > 0:
                result.append((policy.name, policy_rate))
        return result

    def calculate(self, nights: int, completed_stays: int) -> float:
        """Tổng tỷ lệ giảm, không vượt quá mức trần."""
        total = sum(r for _, r in self.details(nights, completed_stays))
        return round(min(total, self.__max_rate), 4)
