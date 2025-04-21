from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np
import math
#4878 profit

class Trader:
    def __init__(self):
        self.rock_limit = 400
        self.vol_window = []
        self.vol_window_size = 20
        self.bollinger_alpha = 2.0
        self.last_trade_time = 0
        self.cooldown_ticks = 1000
        self.entry_price = None
        self.peak_pnl = 0.0
        self.trailing_stop_pct = 0.15
        self.max_loss = 2500 
        self.loss_exit_time = -float("inf")
        self.vol_cap = 40
        self.price_history = []
        self.z_window = 20
        self.previous_mid_price = None
        self.previous_upper = None
        self.previous_lower = None

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

    def calculate_z_score(self, fair_value, market_price):
        error = market_price - fair_value
        self.price_history.append(error)
        if len(self.price_history) > self.z_window:
            self.price_history.pop(0)
        if len(self.price_history) < self.z_window:
            return 0
        mean = np.mean(self.price_history)
        std = np.std(self.price_history) + 1e-5
        return (error - mean) / std

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data_out = {}

        timestamp = state.timestamp
        pos = state.position.get("VOLCANIC_ROCK", 0)

        if "VOLCANIC_ROCK" not in state.order_depths:
            return result, conversions, jsonpickle.encode(trader_data_out)

        order_depth = state.order_depths["VOLCANIC_ROCK"]
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        best_bid = max(order_depth.buy_orders.keys(), default=None)

        if best_ask is None or best_bid is None or best_ask - best_bid > 2:
            return result, conversions, jsonpickle.encode(trader_data_out)

        mid_price = (best_ask + best_bid) / 2
        rolling_vol = self.calculate_rolling_vol(mid_price)

        if rolling_vol > self.vol_cap:
            return result, conversions, jsonpickle.encode(trader_data_out)

        fair_value = np.mean(self.vol_window) if self.vol_window else mid_price
        z_score = self.calculate_z_score(fair_value, mid_price)
        if abs(z_score) < 1.0:
            return result, conversions, jsonpickle.encode(trader_data_out)

        # Compute Bollinger Bands
        rolling_mean = fair_value
        upper_band = rolling_mean + self.bollinger_alpha * rolling_vol
        lower_band = rolling_mean - self.bollinger_alpha * rolling_vol

        position = pos
        orders = []

        # Exit logic
        if self.entry_price is not None:
            unrealized_pnl = (mid_price - self.entry_price) * position
            self.peak_pnl = max(self.peak_pnl, unrealized_pnl)
            if unrealized_pnl < -self.max_loss or (
                self.peak_pnl > 0 and unrealized_pnl < self.peak_pnl * (1 - self.trailing_stop_pct)):
                orders.append(Order("VOLCANIC_ROCK", mid_price, -position))
                self.entry_price = None
                self.peak_pnl = 0.0
                self.loss_exit_time = timestamp
                result["VOLCANIC_ROCK"] = orders
                return result, conversions, jsonpickle.encode(trader_data_out)

        if timestamp - self.last_trade_time < self.cooldown_ticks:
            return result, conversions, jsonpickle.encode(trader_data_out)

        price_diff = fair_value - mid_price
        trade_size = self.dynamic_trade_size(price_diff, rolling_vol)

        # Entry confirmation logic
        buy_confirmed = (
            self.previous_mid_price is not None and
            self.previous_lower is not None and
            self.previous_mid_price < self.previous_lower and mid_price > lower_band
        )
        sell_confirmed = (
            self.previous_mid_price is not None and
            self.previous_upper is not None and
            self.previous_mid_price > self.previous_upper and mid_price < upper_band
        )

        if best_ask < fair_value and position < self.rock_limit and buy_confirmed:
            qty = min(-order_depth.sell_orders[best_ask], trade_size, self.rock_limit - position)
            orders.append(Order("VOLCANIC_ROCK", best_ask, qty))
            self.entry_price = best_ask
            self.peak_pnl = 0.0
            self.last_trade_time = timestamp

        elif best_bid > fair_value and position > -self.rock_limit and sell_confirmed:
            qty = min(order_depth.buy_orders[best_bid], trade_size, self.rock_limit + position)
            orders.append(Order("VOLCANIC_ROCK", best_bid, -qty))
            self.entry_price = best_bid
            self.peak_pnl = 0.0
            self.last_trade_time = timestamp

        if orders:
            result["VOLCANIC_ROCK"] = orders

        # Update previous values for confirmation logic
        self.previous_mid_price = mid_price
        self.previous_upper = upper_band
        self.previous_lower = lower_band

        return result, conversions, jsonpickle.encode(trader_data_out)