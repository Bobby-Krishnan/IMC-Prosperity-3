from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
#THIS IS ONLY SQUID INK FROM ROUND 3 THAT IS MAKING 1.5K

class Trader:
    def __init__(self):
        self.fair_price = 7000
        self.threshold = 300
        self.position_limit = 50

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        orders_squid: List[Order] = []

        order_depth: OrderDepth = state.order_depths.get("SQUID_INK", OrderDepth())
        current_pos = state.position.get("SQUID_INK", 0)

        # BUY below fair price - threshold
        for ask, qty in sorted(order_depth.sell_orders.items()):
            if ask < self.fair_price - self.threshold and current_pos + abs(qty) <= self.position_limit:
                orders_squid.append(Order("SQUID_INK", ask, abs(qty)))
                current_pos += abs(qty)

        # SELL above fair price + threshold
        for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid > self.fair_price + self.threshold and current_pos - abs(qty) >= -self.position_limit:
                orders_squid.append(Order("SQUID_INK", bid, -abs(qty)))
                current_pos -= abs(qty)

        result["SQUID_INK"] = orders_squid
        return result, conversions, ""
