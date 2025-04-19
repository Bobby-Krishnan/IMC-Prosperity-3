from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy as np
#18.8k from volcanic

class Trader:
    def __init__(self):
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }
        self.voucher_limit = 200
        self.rock_limit = 400
        self.vol_window = []
        self.vol_window_size = 20
        self.bollinger_alpha = 2.5
        self.last_trade_time = {}  # cooldown control
        self.cooldown_ticks = 2000  # 2000 ticks between trades per product

    def calculate_rolling_vol(self, new_price):
        self.vol_window.append(new_price)
        if len(self.vol_window) > self.vol_window_size:
            self.vol_window.pop(0)
        if len(self.vol_window) >= 2:
            return np.std(self.vol_window)
        return 1.0

    def dynamic_trade_size(self, price_diff, rolling_vol):
        signal_strength = abs(price_diff) / (rolling_vol + 1e-5)
        if signal_strength > 3:
            return 100
        elif signal_strength > 2:
            return 75
        elif signal_strength > 1:
            return 50
        else:
            return 20

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        traderData = state.traderData
        timestamp = state.timestamp

        rock_price = None
        if "VOLCANIC_ROCK" in state.order_depths:
            rock_order_depth = state.order_depths["VOLCANIC_ROCK"]
            rock_best_ask = min(rock_order_depth.sell_orders.keys(), default=None)
            rock_best_bid = max(rock_order_depth.buy_orders.keys(), default=None)
            if rock_best_ask is not None and rock_best_bid is not None:
                rock_price = (rock_best_ask + rock_best_bid) / 2

        if rock_price is None:
            return result, conversions, traderData

        rolling_vol = self.calculate_rolling_vol(rock_price)

        for product, strike in self.voucher_strikes.items():
            if product not in state.order_depths:
                continue

            # Cooldown logic: enforce time gap between trades
            last_time = self.last_trade_time.get(product, -float('inf'))
            if timestamp - last_time < self.cooldown_ticks:
                continue  # skip trading this product until cooldown passed

            order_depth = state.order_depths[product]
            best_ask = min(order_depth.sell_orders.keys(), default=None)
            best_bid = max(order_depth.buy_orders.keys(), default=None)

            orders: List[Order] = []
            TTE = max(1, 7 - state.timestamp // 100000)
            intrinsic = max(0, rock_price - strike)
            fair_vt = intrinsic + rock_price * 0.5 * rolling_vol * np.sqrt(TTE)

            position = state.position.get(product, 0)
            rock_pos = state.position.get("VOLCANIC_ROCK", 0)

            sell_threshold = fair_vt + self.bollinger_alpha * rolling_vol
            buy_threshold = fair_vt - self.bollinger_alpha * rolling_vol

            if best_bid is not None and best_bid > sell_threshold and position > -self.voucher_limit:
                price_diff = best_bid - fair_vt
                trade_size = self.dynamic_trade_size(price_diff, rolling_vol)
                qty = min(order_depth.buy_orders[best_bid], trade_size, self.voucher_limit + position)
                orders.append(Order(product, best_bid, -qty))
                self.last_trade_time[product] = timestamp
                if rock_pos > -self.rock_limit:
                    hedge_qty = min(qty, self.rock_limit + rock_pos)
                    result.setdefault("VOLCANIC_ROCK", []).append(Order("VOLCANIC_ROCK", rock_best_bid, -hedge_qty))

            if best_ask is not None and best_ask < buy_threshold and position < self.voucher_limit:
                price_diff = fair_vt - best_ask
                trade_size = self.dynamic_trade_size(price_diff, rolling_vol)
                qty = min(-order_depth.sell_orders[best_ask], trade_size, self.voucher_limit - position)
                orders.append(Order(product, best_ask, qty))
                self.last_trade_time[product] = timestamp
                if rock_pos < self.rock_limit:
                    hedge_qty = min(qty, self.rock_limit - rock_pos)
                    result.setdefault("VOLCANIC_ROCK", []).append(Order("VOLCANIC_ROCK", rock_best_ask, hedge_qty))

            result[product] = orders

        return result, conversions, traderData
