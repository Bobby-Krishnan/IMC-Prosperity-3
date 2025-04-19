
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import math
import numpy as np
#+4k profit

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data_out = {}
        pos = state.position
        rock_history = []
        running_pnl = 0

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                rock_history = prior_data.get("rock_history", [])
                running_pnl = prior_data.get("running_pnl", 0)
            except:
                pass

        # --- Volcanic Rock Price ---
        for product in state.order_depths:
            if product == "VOLCANIC_ROCK":
                order_depth: OrderDepth = state.order_depths[product]
                if order_depth.buy_orders and order_depth.sell_orders:
                    spot_price = (max(order_depth.buy_orders) + min(order_depth.sell_orders)) / 2
                else:
                    spot_price = 9800
                rock_history.append(spot_price)
                if len(rock_history) > 30:
                    rock_history.pop(0)

                # Rock base band trading
                orders: List[Order] = []
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
                if orders:
                    result[product] = orders

        if not rock_history or len(rock_history) < 10:
            trader_data_out["rock_history"] = rock_history
            trader_data_out["running_pnl"] = running_pnl
            return result, conversions, jsonpickle.encode(trader_data_out)

        spot_price = rock_history[-1]
        time_now = state.timestamp
        TTE = max(0.1, 7 - time_now / 100_000)
        rock_vol = np.std(rock_history[-10:])
        rock_momentum = np.mean(np.diff(rock_history[-5:]))  # Simple trend

        # === Volatility Cutoff ===
        if rock_vol > 250:
            trader_data_out["rock_history"] = rock_history
            trader_data_out["running_pnl"] = running_pnl
            return result, conversions, jsonpickle.encode(trader_data_out)

        # === Voucher Info ===
        voucher_info = {
            "VOLCANIC_ROCK_VOUCHER_9500": {"strike": 9500, "buy": 800, "sell": 1200},
            "VOLCANIC_ROCK_VOUCHER_9750": {"strike": 9750, "buy": 650, "sell": 1050},
            "VOLCANIC_ROCK_VOUCHER_10000": {"strike": 10000, "buy": 500, "sell": 900}
        }

        for product, info in voucher_info.items():
            if product not in state.order_depths:
                continue

            order_depth: OrderDepth = state.order_depths[product]
            strike = info["strike"]
            base_buy = info["buy"]
            base_sell = info["sell"]

            try:
                m_t = abs(math.log(strike / spot_price) / math.sqrt(TTE))
            except:
                m_t = 0.5

            size_scale = max(0.25, min(1.0, 1.0 - m_t))
            max_base = 200 * size_scale

            # === Early Round Exposure Cap ===
            if time_now < 30000:
                max_base *= 0.6

            # === Profit-based slight boost ===
            if running_pnl > 2000:
                max_base *= 1.2

            # === Momentum Biasing ===
            bias = 1.0
            if rock_momentum > 0 and strike < spot_price:
                bias = 1.3  # favor long
            elif rock_momentum < 0 and strike > spot_price:
                bias = 1.3  # favor short

            max_size = int(max_base * bias)

            buy_below = base_buy * (1 + rock_vol / 200)
            sell_above = base_sell * (1 + rock_vol / 200)
            current_pos = pos.get(product, 0)
            orders: List[Order] = []

            for ask, qty in sorted(order_depth.sell_orders.items()):
                if ask < buy_below and current_pos + abs(qty) <= max_size:
                    trade_qty = min(abs(qty), max_size - current_pos)
                    if trade_qty > 0:
                        orders.append(Order(product, ask, trade_qty))
                        current_pos += trade_qty
                        running_pnl -= ask * trade_qty

            for bid, qty in sorted(order_depth.buy_orders.items(), reverse=True):
                if bid > sell_above and current_pos - abs(qty) >= -max_size:
                    trade_qty = min(abs(qty), current_pos + max_size)
                    if trade_qty > 0:
                        orders.append(Order(product, bid, -trade_qty))
                        current_pos -= trade_qty
                        running_pnl += bid * trade_qty

            if orders:
                result[product] = orders

        trader_data_out["rock_history"] = rock_history
        trader_data_out["running_pnl"] = running_pnl
        return result, conversions, jsonpickle.encode(trader_data_out)
