from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np
import math

class Trader:
    def __init__(self):
        # Round 3 - Volcanic Rock Strategy State
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
        
        # Round 1-2 Kelp history
        self.kelp_history = []

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

    def average_price(self, depth: OrderDepth):
        if depth.buy_orders and depth.sell_orders:
            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            return (best_bid + best_ask) / 2
        return None

    def estimate_volatility(self, depth: OrderDepth):
        prices = list(depth.buy_orders.keys()) + list(depth.sell_orders.keys())
        return np.std(prices) if prices else 0

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_data_out = {}

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                self.kelp_history = prior_data.get("kelp_history", [])
            except:
                self.kelp_history = []

        for product in state.order_depths:
            orders: List[Order] = []
            order_depth: OrderDepth = state.order_depths[product]
            current_pos = state.position.get(product, 0)

            # === Volcanic Rock Trading ===
            if product == "VOLCANIC_ROCK":
                timestamp = state.timestamp
                best_ask = min(order_depth.sell_orders.keys(), default=None)
                best_bid = max(order_depth.buy_orders.keys(), default=None)

                if best_ask is None or best_bid is None or best_ask - best_bid > 2:
                    continue

                mid_price = (best_ask + best_bid) / 2
                rolling_vol = self.calculate_rolling_vol(mid_price)
                if rolling_vol > self.vol_cap:
                    continue

                fair_value = np.mean(self.vol_window) if self.vol_window else mid_price
                z_score = self.calculate_z_score(fair_value, mid_price)
                if abs(z_score) < 1.0:
                    continue

                rolling_mean = fair_value
                upper_band = rolling_mean + self.bollinger_alpha * rolling_vol
                lower_band = rolling_mean - self.bollinger_alpha * rolling_vol

                if self.entry_price is not None:
                    unrealized_pnl = (mid_price - self.entry_price) * current_pos
                    self.peak_pnl = max(self.peak_pnl, unrealized_pnl)
                    if unrealized_pnl < -self.max_loss or (self.peak_pnl > 0 and unrealized_pnl < self.peak_pnl * (1 - self.trailing_stop_pct)):
                        orders.append(Order(product, mid_price, -current_pos))
                        self.entry_price = None
                        self.peak_pnl = 0.0
                        self.loss_exit_time = timestamp
                        result[product] = orders
                        continue

                if timestamp - self.last_trade_time < self.cooldown_ticks:
                    continue

                price_diff = fair_value - mid_price
                trade_size = self.dynamic_trade_size(price_diff, rolling_vol)

                buy_confirmed = self.previous_mid_price is not None and self.previous_lower is not None and self.previous_mid_price < self.previous_lower and mid_price > lower_band
                sell_confirmed = self.previous_mid_price is not None and self.previous_upper is not None and self.previous_mid_price > self.previous_upper and mid_price < upper_band

                if best_ask < fair_value and current_pos < self.rock_limit and buy_confirmed:
                    qty = min(-order_depth.sell_orders[best_ask], trade_size, self.rock_limit - current_pos)
                    orders.append(Order(product, best_ask, qty))
                    self.entry_price = best_ask
                    self.peak_pnl = 0.0
                    self.last_trade_time = timestamp

                elif best_bid > fair_value and current_pos > -self.rock_limit and sell_confirmed:
                    qty = min(order_depth.buy_orders[best_bid], trade_size, self.rock_limit + current_pos)
                    orders.append(Order(product, best_bid, -qty))
                    self.entry_price = best_bid
                    self.peak_pnl = 0.0
                    self.last_trade_time = timestamp

                if orders:
                    result[product] = orders
                self.previous_mid_price = mid_price
                self.previous_upper = upper_band
                self.previous_lower = lower_band

            # === Round 1 & 2 Logic ===
            elif product == "KELP":
                position_limit = 50
                best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
                best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None

                if best_ask is not None and best_bid is not None:
                    mid_price = (best_ask + best_bid) / 2
                    self.kelp_history.append(mid_price)
                    if len(self.kelp_history) > 20:
                        self.kelp_history.pop(0)

                    mean_price = np.mean(self.kelp_history)
                    std_price = np.std(self.kelp_history) + 1e-6
                    z_ask = (mean_price - best_ask) / std_price
                    z_bid = (best_bid - mean_price) / std_price

                    def get_trade_size(z):
                        if z > 3: return 30
                        if z > 2: return 20
                        if z > 1: return 10
                        return 0

                    ask_size = get_trade_size(z_ask)
                    bid_size = get_trade_size(z_bid)

                    if ask_size > 0 and current_pos + ask_size <= position_limit:
                        vol = abs(order_depth.sell_orders[best_ask])
                        orders.append(Order(product, best_ask, min(vol, ask_size)))

                    if bid_size > 0 and current_pos - bid_size >= -position_limit:
                        vol = abs(order_depth.buy_orders[best_bid])
                        orders.append(Order(product, best_bid, -min(vol, bid_size)))

            elif product == "RAINFOREST_RESIN":
                fair_price = 10000
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price and current_pos + abs(qty) <= 50:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price and current_pos - abs(qty) >= -50:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "SQUID_INK":
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

        trader_data_out["kelp_history"] = self.kelp_history
        return result, 0, jsonpickle.encode(trader_data_out)