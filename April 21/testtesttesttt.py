from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def __init__(self):
        self.cooldown_ticks = 1000  # You can tweak this value

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        product = "SQUID_INK"
        orders: List[Order] = []

        # Decode traderData to get last_trade_time
        trader_data_out = {}
        last_trade_time = -10000
        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                last_trade_time = prior_data.get("last_trade_time", -10000)
            except:
                pass

        current_time = state.timestamp
        cooldown = self.cooldown_ticks

        # Only trade if cooldown passed
        if current_time - last_trade_time >= cooldown:
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

            # Only update last_trade_time if we placed orders
            if orders:
                trader_data_out["last_trade_time"] = current_time
        else:
            # Keep the old timestamp if no trade happens
            trader_data_out["last_trade_time"] = last_trade_time

        result[product] = orders
        traderData = jsonpickle.encode(trader_data_out)
        return result, 0, traderData