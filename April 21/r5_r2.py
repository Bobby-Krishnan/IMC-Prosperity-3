
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np
#5595 profit

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_data_out = {}

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

        basket1_volatility = 6 * croissant_vol + 3 * jam_vol + 1 * djembe_vol
        buffer1 = min(max(200, basket1_volatility * 2), 400)

        basket2_volatility = 4 * croissant_vol + 2 * jam_vol
        buffer2 = max(150, basket2_volatility * 2)

        for product in state.order_depths:
            orders: List[Order] = []
            order_depth: OrderDepth = state.order_depths[product]
            current_pos = state.position.get(product, 0)

            if product == "PICNIC_BASKET1":
                fair_price = 6 * croissant_fair + 3 * jam_fair + 1 * djembe_fair
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - buffer1 and current_pos + abs(qty) <= 60:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + buffer1 and current_pos - abs(qty) >= -60:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            elif product == "PICNIC_BASKET2":
                fair_price = 4 * croissant_fair + 2 * jam_fair
                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < fair_price - buffer2 and current_pos + abs(qty) <= 100:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)
                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fair_price + buffer2 and current_pos - abs(qty) >= -100:
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

        traderData = jsonpickle.encode(trader_data_out)
        return result, 0, traderData
