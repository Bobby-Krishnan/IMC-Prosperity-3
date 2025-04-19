from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np
#37k
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
        self.last_trade_time = {}
        self.cooldown_ticks = 2000
        self.entry_price = {}
        self.max_loss = 3300

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
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data_out = {}

        kelp_history = []
        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                kelp_history = prior_data.get("kelp_history", [])
            except:
                pass

        available = set(state.order_depths.keys())
        pos = state.position

        timestamp = state.timestamp

        rock_price = None
        if "VOLCANIC_ROCK" in state.order_depths:
            rock_order_depth = state.order_depths["VOLCANIC_ROCK"]
            rock_best_ask = min(rock_order_depth.sell_orders.keys(), default=None)
            rock_best_bid = max(rock_order_depth.buy_orders.keys(), default=None)
            if rock_best_ask is not None and rock_best_bid is not None:
                rock_price = (rock_best_ask + rock_best_bid) / 2

        rolling_vol = self.calculate_rolling_vol(rock_price) if rock_price else 1.0

        if rock_price and rolling_vol <= 35:
            for product, strike in self.voucher_strikes.items():
                if product not in state.order_depths:
                    continue

                last_time = self.last_trade_time.get(product, -float('inf'))
                if timestamp - last_time < self.cooldown_ticks:
                    continue

                order_depth = state.order_depths[product]
                best_ask = min(order_depth.sell_orders.keys(), default=None)
                best_bid = max(order_depth.buy_orders.keys(), default=None)

                orders: List[Order] = []
                TTE = max(1, 7 - state.timestamp // 100000)
                intrinsic = max(0, rock_price - strike)
                fair_vt = intrinsic + rock_price * 0.5 * rolling_vol * np.sqrt(TTE)

                position = pos.get(product, 0)
                rock_pos = pos.get("VOLCANIC_ROCK", 0)

                sell_threshold = fair_vt + self.bollinger_alpha * rolling_vol
                buy_threshold = fair_vt - self.bollinger_alpha * rolling_vol

                entry = self.entry_price.get(product)
                if entry and position != 0:
                    mid_price = None
                    if position > 0 and best_bid is not None:
                        mid_price = best_bid
                    elif position < 0 and best_ask is not None:
                        mid_price = best_ask
                    if mid_price:
                        unrealized_pnl = (mid_price - entry) * position
                        if unrealized_pnl < -self.max_loss:
                            result[product] = [Order(product, mid_price, -position)]
                            self.entry_price[product] = None
                            continue

                if best_bid is not None and best_bid > sell_threshold and position > -self.voucher_limit:
                    price_diff = best_bid - fair_vt
                    trade_size = self.dynamic_trade_size(price_diff, rolling_vol)
                    qty = min(order_depth.buy_orders[best_bid], trade_size, self.voucher_limit + position)
                    result[product] = [Order(product, best_bid, -qty)]
                    self.last_trade_time[product] = timestamp
                    self.entry_price[product] = best_bid
                    if rock_pos > -self.rock_limit:
                        hedge_qty = min(qty, self.rock_limit + rock_pos)
                        result.setdefault("VOLCANIC_ROCK", []).append(Order("VOLCANIC_ROCK", rock_best_bid, -hedge_qty))

                elif best_ask is not None and best_ask < buy_threshold and position < self.voucher_limit:
                    price_diff = fair_vt - best_ask
                    trade_size = self.dynamic_trade_size(price_diff, rolling_vol)
                    qty = min(-order_depth.sell_orders[best_ask], trade_size, self.voucher_limit - position)
                    result[product] = [Order(product, best_ask, qty)]
                    self.last_trade_time[product] = timestamp
                    self.entry_price[product] = best_ask
                    if rock_pos < self.rock_limit:
                        hedge_qty = min(qty, self.rock_limit - rock_pos)
                        result.setdefault("VOLCANIC_ROCK", []).append(Order("VOLCANIC_ROCK", rock_best_ask, hedge_qty))

        for product in state.order_depths:
            if product in self.voucher_strikes or product == "VOLCANIC_ROCK":
                continue  # already handled above

            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            current_pos = pos.get(product, 0)

            if product == "RAINFOREST_RESIN":
                fair_price = 10000
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price and current_pos + abs(qty) <= 50:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price and current_pos - abs(qty) >= -50:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "KELP":
                window = 6
                best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
                best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None
                if best_ask and best_bid:
                    mid_price = (best_ask + best_bid) / 2
                    kelp_history.append(mid_price)
                    if len(kelp_history) > window:
                        kelp_history.pop(0)
                    fair_price = np.mean(kelp_history)
                    if best_ask < fair_price and current_pos + order_depth.sell_orders[best_ask] <= 50:
                        orders.append(Order(product, best_ask, abs(order_depth.sell_orders[best_ask])))
                    if best_bid > fair_price and current_pos - order_depth.buy_orders[best_bid] >= -50:
                        orders.append(Order(product, best_bid, -abs(order_depth.buy_orders[best_bid])))

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

            elif product == "PICNIC_BASKET1":
                fair_price = 6 * 300 + 3 * 400 + 1 * 800
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - 200 and current_pos + abs(qty) <= 60:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + 200 and current_pos - abs(qty) >= -60:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "PICNIC_BASKET2":
                fair_price = 4 * 300 + 2 * 400
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - 150 and current_pos + abs(qty) <= 100:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + 150 and current_pos - abs(qty) >= -100:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product in ["CROISSANTS", "JAMS", "DJEMBES"]:
                base_price = {"CROISSANTS": 300, "JAMS": 400, "DJEMBES": 800}[product]
                limit = {"CROISSANTS": 250, "JAMS": 350, "DJEMBES": 60}[product]
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < base_price - 20 and current_pos + abs(qty) <= limit:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > base_price + 20 and current_pos - abs(qty) >= -limit:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            result[product] = orders

        trader_data_out["kelp_history"] = kelp_history
        traderData = jsonpickle.encode(trader_data_out)
        return result, conversions, traderData
