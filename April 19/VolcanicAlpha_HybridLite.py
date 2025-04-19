
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import math
import numpy as np
#3000 profit
class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data_out = {}
        pos = state.position
        rock_history = []

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                rock_history = prior_data.get("rock_history", [])
            except:
                pass

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Compute spot price from Volcanic Rock
            if "VOLCANIC_ROCK" in state.order_depths:
                rock_od = state.order_depths["VOLCANIC_ROCK"]
                if rock_od.buy_orders and rock_od.sell_orders:
                    spot_price = (max(rock_od.buy_orders) + min(rock_od.sell_orders)) / 2
                else:
                    spot_price = 9800
            else:
                spot_price = 9800

            if product == "VOLCANIC_ROCK":
                rock_history.append(spot_price)
                if len(rock_history) > 30:
                    rock_history.pop(0)

                # Rock trading band
                threshold = 150
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
                if not rock_history:
                    continue
                spot_price = rock_history[-1]
                time_now = state.timestamp
                TTE = max(0.1, 7 - time_now / 100_000)

                current_pos = pos.get(product, 0)
                max_pos = 200

                # Extract strike
                if "10250" in product or "10500" in product:
                    continue  # skip
                strike = int(product.split("_")[-1])

                # Compute m_t
                try:
                    m_t = math.log(strike / spot_price) / math.sqrt(TTE)
                except:
                    m_t = 0

                # Compute IV estimate as a proxy
                # Black-Scholes Approximation (implied vol heuristic)
                # Rearranged from V = S * N(d1) - K * exp(-rT) * N(d2), simplified
                # Here we just log normalized range scaled by sqrt(TTE)
                mid_price = None
                if order_depth.buy_orders and order_depth.sell_orders:
                    best_bid = max(order_depth.buy_orders)
                    best_ask = min(order_depth.sell_orders)
                    mid_price = (best_bid + best_ask) / 2
                elif order_depth.buy_orders:
                    mid_price = max(order_depth.buy_orders)
                elif order_depth.sell_orders:
                    mid_price = min(order_depth.sell_orders)
                else:
                    mid_price = 0

                if mid_price > 0 and TTE > 0:
                    v_t = abs(math.log(spot_price / strike)) / math.sqrt(TTE)
                else:
                    v_t = 0

                # Volatility scaling from rock
                vol_adj = np.std(rock_history) if len(rock_history) >= 5 else 0
                vol_factor = 1.0 + vol_adj / 100

                # Empirical anchors
                if product == "VOLCANIC_ROCK_VOUCHER_9500":
                    base_buy, base_sell = 800, 1200
                elif product == "VOLCANIC_ROCK_VOUCHER_9750":
                    base_buy, base_sell = 650, 1050
                elif product == "VOLCANIC_ROCK_VOUCHER_10000":
                    base_buy, base_sell = 500, 900
                else:
                    continue

                # Dynamic trade thresholds
                buy_below = base_buy * vol_factor
                sell_above = base_sell * vol_factor

                for ask, qty in sorted(order_depth.sell_orders.items()):
                    if ask < buy_below and current_pos + abs(qty) <= max_pos:
                        orders.append(Order(product, ask, abs(qty)))
                        current_pos += abs(qty)

                for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > sell_above and current_pos - abs(qty) >= -max_pos:
                        orders.append(Order(product, bid, -abs(qty)))
                        current_pos -= abs(qty)

            if orders:
                result[product] = orders

        trader_data_out["rock_history"] = rock_history
        traderData = jsonpickle.encode(trader_data_out)
        return result, conversions, traderData
