
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np
    #-1.3k
class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data_out = {}

        rock_history = []

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                rock_history = prior_data.get("rock_history", [])
            except:
                pass

        pos = state.position

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product == "VOLCANIC_ROCK":
                if order_depth.buy_orders and order_depth.sell_orders:
                    spot_price = (max(order_depth.buy_orders) + min(order_depth.sell_orders)) / 2
                else:
                    spot_price = 10000
                rock_history.append(spot_price)
                if len(rock_history) > 10:
                    rock_history.pop(0)

                std_dev = np.std(rock_history) if len(rock_history) > 2 else 100
                threshold = 0.5 * std_dev
                current_pos = pos.get(product, 0)
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < spot_price - threshold and current_pos + abs(qty) <= 400:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > spot_price + threshold and current_pos - abs(qty) >= -400:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif "VOUCHER" in product:
                parts = product.split("_")
                strike = int(parts[-1])
                premium = 1000 + (strike - 9500) // 250 * 200
                TTE = 7 - state.timestamp // 100_000

                if "VOLCANIC_ROCK" in state.order_depths:
                    rock_od = state.order_depths["VOLCANIC_ROCK"]
                    if rock_od.buy_orders and rock_od.sell_orders:
                        spot_price = (max(rock_od.buy_orders) + min(rock_od.sell_orders)) / 2
                    else:
                        spot_price = 10000
                else:
                    spot_price = 10000

                fair_price = max(0, spot_price - strike) * (TTE / 7) - premium
                std_dev = np.std(rock_history) if len(rock_history) > 2 else 100
                threshold = 0.5 * std_dev
                current_pos = pos.get(product, 0)

                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - threshold and current_pos + abs(qty) <= 200:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + threshold and current_pos - abs(qty) >= -200:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            if orders:
                result[product] = orders

        trader_data_out["rock_history"] = rock_history
        traderData = jsonpickle.encode(trader_data_out)
        return result, conversions, traderData
