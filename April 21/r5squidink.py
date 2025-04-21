
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_data_out = {}

        product = "SQUID_INK"
        orders: List[Order] = []
        order_depth: OrderDepth = state.order_depths.get(product, OrderDepth())
        current_pos = state.position.get(product, 0)

        fair_price = 7000
        for ask, qty in sorted(order_depth.sell_orders.items()):
            if ask < fair_price - 300 and current_pos + abs(qty) <= 50:
                orders.append(Order(product, ask, abs(qty)))
                current_pos += abs(qty)

        for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid > fair_price + 300 and current_pos - abs(qty) >= -50:
                orders.append(Order(product, bid, -abs(qty)))
                current_pos -= abs(qty)

        result[product] = orders
        traderData = jsonpickle.encode(trader_data_out)
        return result, 0, traderData
