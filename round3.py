
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
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

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product == "RAINFOREST_RESIN":
                fair_price = 10000
                position_limit = 50
                current_pos = pos.get(product, 0)
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price and current_pos + abs(qty) <= position_limit:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price and current_pos - abs(qty) >= -position_limit:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "KELP":
                position_limit = 50
                window = 6
                current_pos = pos.get(product, 0)
                best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
                best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None
                if best_ask and best_bid:
                    mid_price = (best_ask + best_bid) / 2
                    kelp_history.append(mid_price)
                    if len(kelp_history) > window:
                        kelp_history.pop(0)
                    fair_price = np.mean(kelp_history)
                    if best_ask < fair_price and current_pos + order_depth.sell_orders[best_ask] <= position_limit:
                        orders.append(Order(product, best_ask, abs(order_depth.sell_orders[best_ask])))
                    if best_bid > fair_price and current_pos - order_depth.buy_orders[best_bid] >= -position_limit:
                        orders.append(Order(product, best_bid, -abs(order_depth.buy_orders[best_bid])))

            elif product == "SQUID_INK":
                fair_price = 7000
                position_limit = 50
                current_pos = pos.get(product, 0)
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - 300 and current_pos + abs(qty) <= position_limit:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + 300 and current_pos - abs(qty) >= -position_limit:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "PICNIC_BASKET1":
                fair_price = 6 * 300 + 3 * 400 + 1 * 800
                current_pos = pos.get(product, 0)
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
                current_pos = pos.get(product, 0)
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
                current_pos = pos.get(product, 0)
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < base_price - 20 and current_pos + abs(qty) <= limit:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > base_price + 20 and current_pos - abs(qty) >= -limit:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif "VOUCHER" in product:
                parts = product.split("_")
                strike = int(parts[-1])
                premium = 1000 + (strike - 9500) // 250 * 200
                TTE = 7 - state.timestamp // 100_000
                fair_price = max(0, strike - 10000) * (TTE / 7)
                current_pos = pos.get(product, 0)
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - 100 and current_pos + abs(qty) <= 200:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + 100 and current_pos - abs(qty) >= -200:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "VOLCANIC_ROCK":
                fair_price = 10000
                current_pos = pos.get(product, 0)
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - 100 and current_pos + abs(qty) <= 400:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + 100 and current_pos - abs(qty) >= -400:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            result[product] = orders

        trader_data_out["kelp_history"] = kelp_history
        traderData = jsonpickle.encode(trader_data_out)
        return result, conversions, traderData
