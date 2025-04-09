from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import jsonpickle
import statistics
import numpy as np

class Trader:
    def __init__(self):
        self.kelp_prices = []
        self.last_trade_time = -100
        self.entry_price = None

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        traderData = jsonpickle.encode({})

        # Constants
        WINDOW = 20
        Z_THRESHOLD = 0.9
        EXIT_THRESHOLD = 1.0
        POSITION_LIMIT = 50
        MAX_ORDER_SIZE = 6
        COOLDOWN = 30
        STOP_LOSS = -250

        # Timestamp
        timestamp = state.timestamp

        # Prepare order list for KELP
        orders: List[Order] = []

        # Extract order depth
        order_depth = state.order_depths.get("KELP")
        if not order_depth or not order_depth.buy_orders or not order_depth.sell_orders:
            return result, conversions, traderData

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid_price = (best_bid + best_ask) / 2

        self.kelp_prices.append(mid_price)
        if len(self.kelp_prices) > WINDOW:
            self.kelp_prices.pop(0)

        if len(self.kelp_prices) < WINDOW or (timestamp - self.last_trade_time <= COOLDOWN):
            return result, conversions, traderData

        avg = statistics.mean(self.kelp_prices)
        std = statistics.stdev(self.kelp_prices)
        if std == 0:
            return result, conversions, traderData

        z = (mid_price - avg) / std
        prev_mid = self.kelp_prices[-2] if len(self.kelp_prices) >= 2 else mid_price
        reverting_up = prev_mid < mid_price
        reverting_down = prev_mid > mid_price

        position = state.position.get("KELP", 0)
        trade_volume = max(1, min(MAX_ORDER_SIZE, int(abs(z))))

        # Stop-loss logic
        if position != 0 and self.entry_price is not None:
            unrealized = position * (mid_price - self.entry_price)
            if unrealized < STOP_LOSS:
                orders.append(Order("KELP", mid_price, -position))
                self.entry_price = None
                self.last_trade_time = timestamp
                result["KELP"] = orders
                return result, conversions, traderData

        # Entry logic
        if z < -Z_THRESHOLD and position < POSITION_LIMIT and reverting_up:
            qty = min(POSITION_LIMIT - position, trade_volume)
            orders.append(Order("KELP", best_ask + 1, qty))
            self.entry_price = best_ask + 1
            self.last_trade_time = timestamp

        elif z > Z_THRESHOLD and position > -POSITION_LIMIT and reverting_down:
            qty = min(POSITION_LIMIT + position, trade_volume)
            orders.append(Order("KELP", best_bid - 1, -qty))
            self.entry_price = best_bid - 1
            self.last_trade_time = timestamp

        # Exit logic
        elif abs(z) < EXIT_THRESHOLD and position != 0:
            if position > 0:
                qty = min(position, trade_volume)
                orders.append(Order("KELP", best_bid - 1, -qty))
            elif position < 0:
                qty = min(-position, trade_volume)
                orders.append(Order("KELP", best_ask + 1, qty))
            if position == qty or position == -qty:
                self.entry_price = None
            self.last_trade_time = timestamp

        if orders:
            result["KELP"] = orders

        return result, conversions, traderData