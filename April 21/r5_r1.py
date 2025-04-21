
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_data_out = {}
        kelp_history = []

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                kelp_history = prior_data.get("kelp_history", [])
            except:
                kelp_history = []

        for product in state.order_depths:
            orders: List[Order] = []
            order_depth: OrderDepth = state.order_depths[product]
            current_pos = state.position.get(product, 0)

            if product == "KELP":
                position_limit = 50
                best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
                best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None

                if best_ask is not None and best_bid is not None:
                    mid_price = (best_ask + best_bid) / 2
                    kelp_history.append(mid_price)
                    if len(kelp_history) > 20:
                        kelp_history.pop(0)

                    mean_price = np.mean(kelp_history)
                    std_price = np.std(kelp_history) + 1e-6
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
                        current_pos += min(vol, ask_size)

                    if bid_size > 0 and current_pos - bid_size >= -position_limit:
                        vol = abs(order_depth.buy_orders[best_bid])
                        orders.append(Order(product, best_bid, -min(vol, bid_size)))
                        current_pos -= min(vol, bid_size)

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

        trader_data_out["kelp_history"] = kelp_history
        traderData = jsonpickle.encode(trader_data_out)
        return result, 0, traderData
