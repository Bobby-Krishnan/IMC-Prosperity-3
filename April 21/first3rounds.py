from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np
import math

class Trader:
    def __init__(self):
        # Volcanic Rock strategy params
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

    def trade_volcanic_rock(self, state: TradingState, result: Dict[str, List[Order]]):
        pos = state.position.get("VOLCANIC_ROCK", 0)
        if "VOLCANIC_ROCK" not in state.order_depths:
            return
        order_depth = state.order_depths["VOLCANIC_ROCK"]
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        best_bid = max(order_depth.buy_orders.keys(), default=None)

        if best_ask is None or best_bid is None or best_ask - best_bid > 2:
            return

        mid_price = (best_ask + best_bid) / 2
        rolling_vol = self.calculate_rolling_vol(mid_price)
        if rolling_vol > self.vol_cap:
            return

        fair_value = np.mean(self.vol_window) if self.vol_window else mid_price
        z_score = self.calculate_z_score(fair_value, mid_price)
        if abs(z_score) < 1.0:
            return

        upper = fair_value + self.bollinger_alpha * rolling_vol
        lower = fair_value - self.bollinger_alpha * rolling_vol
        orders = []

        # Exit logic
        if self.entry_price is not None:
            unrealized_pnl = (mid_price - self.entry_price) * pos
            self.peak_pnl = max(self.peak_pnl, unrealized_pnl)
            if unrealized_pnl < -self.max_loss or (self.peak_pnl > 0 and unrealized_pnl < self.peak_pnl * (1 - self.trailing_stop_pct)):
                orders.append(Order("VOLCANIC_ROCK", mid_price, -pos))
                self.entry_price = None
                self.peak_pnl = 0.0
                self.loss_exit_time = state.timestamp
                result["VOLCANIC_ROCK"] = orders
                return

        if state.timestamp - self.last_trade_time < self.cooldown_ticks:
            return

        price_diff = fair_value - mid_price
        trade_size = self.dynamic_trade_size(price_diff, rolling_vol)

        buy_confirmed = self.previous_mid_price is not None and self.previous_lower is not None and self.previous_mid_price < self.previous_lower and mid_price > lower
        sell_confirmed = self.previous_mid_price is not None and self.previous_upper is not None and self.previous_mid_price > self.previous_upper and mid_price < upper

        if best_ask < fair_value and pos < self.rock_limit and buy_confirmed:
            qty = min(-order_depth.sell_orders[best_ask], trade_size, self.rock_limit - pos)
            orders.append(Order("VOLCANIC_ROCK", best_ask, qty))
            self.entry_price = best_ask
            self.peak_pnl = 0.0
            self.last_trade_time = state.timestamp

        elif best_bid > fair_value and pos > -self.rock_limit and sell_confirmed:
            qty = min(order_depth.buy_orders[best_bid], trade_size, self.rock_limit + pos)
            orders.append(Order("VOLCANIC_ROCK", best_bid, -qty))
            self.entry_price = best_bid
            self.peak_pnl = 0.0
            self.last_trade_time = state.timestamp

        if orders:
            result["VOLCANIC_ROCK"] = orders

        self.previous_mid_price = mid_price
        self.previous_upper = upper
        self.previous_lower = lower

    def trade_r1_r2(self, state: TradingState, result: Dict[str, List[Order]], kelp_history: List[float]):
        def average_price(depth: OrderDepth):
            if depth.buy_orders and depth.sell_orders:
                best_bid = max(depth.buy_orders)
                best_ask = min(depth.sell_orders)
                return (best_bid + best_ask) / 2
            return None

        def estimate_volatility(depth: OrderDepth):
            prices = list(depth.buy_orders.keys()) + list(depth.sell_orders.keys())
            return np.std(prices) if prices else 0

        croissant_depth = state.order_depths.get("CROISSANTS", OrderDepth())
        jam_depth = state.order_depths.get("JAMS", OrderDepth())
        djembe_depth = state.order_depths.get("DJEMBES", OrderDepth())

        croissant_fair = average_price(croissant_depth) or 300
        jam_fair = average_price(jam_depth) or 400
        djembe_fair = average_price(djembe_depth) or 800

        croissant_vol = estimate_volatility(croissant_depth)
        jam_vol = estimate_volatility(jam_depth)
        djembe_vol = estimate_volatility(djembe_depth)

        buffer1 = min(max(200, (6 * croissant_vol + 3 * jam_vol + djembe_vol) * 2), 400)
        buffer2 = max(150, (4 * croissant_vol + 2 * jam_vol) * 2)

        for product, depth in state.order_depths.items():
            orders: List[Order] = []
            current_pos = state.position.get(product, 0)

            if product == "KELP":
                position_limit = 50
                best_ask = min(depth.sell_orders) if depth.sell_orders else None
                best_bid = max(depth.buy_orders) if depth.buy_orders else None

                if best_ask and best_bid:
                    mid = (best_ask + best_bid) / 2
                    kelp_history.append(mid)
                    if len(kelp_history) > 20:
                        kelp_history.pop(0)

                    mean = np.mean(kelp_history)
                    std = np.std(kelp_history) + 1e-6
                    z_ask = (mean - best_ask) / std
                    z_bid = (best_bid - mean) / std

                    def size(z): return 30 if z > 3 else 20 if z > 2 else 10 if z > 1 else 0

                    ask_size, bid_size = size(z_ask), size(z_bid)
                    if ask_size and current_pos + ask_size <= position_limit:
                        orders.append(Order(product, best_ask, min(abs(depth.sell_orders[best_ask]), ask_size)))
                    if bid_size and current_pos - bid_size >= -position_limit:
                        orders.append(Order(product, best_bid, -min(abs(depth.buy_orders[best_bid]), bid_size)))

            elif product == "RAINFOREST_RESIN":
                for ask, qty in sorted(depth.sell_orders.items()):
                    if ask < 10000 and current_pos + abs(qty) <= 50:
                        orders.append(Order(product, ask, abs(qty)))
                for bid, qty in sorted(depth.buy_orders.items(), reverse=True):
                    if bid > 10000 and current_pos - abs(qty) >= -50:
                        orders.append(Order(product, bid, -abs(qty)))

            elif product == "SQUID_INK":
                for ask, qty in sorted(depth.sell_orders.items()):
                    if ask < 6700 and current_pos + abs(qty) <= 50:
                        orders.append(Order(product, ask, abs(qty)))
                for bid, qty in sorted(depth.buy_orders.items(), reverse=True):
                    if bid > 7300 and current_pos - abs(qty) >= -50:
                        orders.append(Order(product, bid, -abs(qty)))

            elif product == "PICNIC_BASKET1":
                fair = 6 * croissant_fair + 3 * jam_fair + djembe_fair
                for ask, qty in sorted(depth.sell_orders.items()):
                    if ask < fair - buffer1 and current_pos + abs(qty) <= 60:
                        orders.append(Order(product, ask, abs(qty)))
                for bid, qty in sorted(depth.buy_orders.items(), reverse=True):
                    if bid > fair + buffer1 and current_pos - abs(qty) >= -60:
                        orders.append(Order(product, bid, -abs(qty)))

            elif product == "PICNIC_BASKET2":
                fair = 4 * croissant_fair + 2 * jam_fair
                for ask, qty in sorted(depth.sell_orders.items()):
                    if ask < fair - buffer2 and current_pos + abs(qty) <= 100:
                        orders.append(Order(product, ask, abs(qty)))
                for bid, qty in sorted(depth.buy_orders.items(), reverse=True):
                    if bid > fair + buffer2 and current_pos - abs(qty) >= -100:
                        orders.append(Order(product, bid, -abs(qty)))

            elif product in ["CROISSANTS", "JAMS", "DJEMBES"]:
                base = {"CROISSANTS": 300, "JAMS": 400, "DJEMBES": 800}[product]
                limit = {"CROISSANTS": 250, "JAMS": 350, "DJEMBES": 60}[product]
                for ask, qty in sorted(depth.sell_orders.items()):
                    if ask < base - 20 and current_pos + abs(qty) <= limit:
                        orders.append(Order(product, ask, abs(qty)))
                for bid, qty in sorted(depth.buy_orders.items(), reverse=True):
                    if bid > base + 20 and current_pos - abs(qty) >= -limit:
                        orders.append(Order(product, bid, -abs(qty)))

            if orders:
                result[product] = orders

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        kelp_history = []

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                kelp_history = prior_data.get("kelp_history", [])
            except:
                kelp_history = []

        self.trade_volcanic_rock(state, result)
        self.trade_r1_r2(state, result, kelp_history)

        traderData = jsonpickle.encode({"kelp_history": kelp_history})
        return result, conversions, traderData