
from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
#made 2.5k
class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data_out = {}
        pos = state.position

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product == "VOLCANIC_ROCK":
                # Same rock strategy: buy low, sell high
                if order_depth.buy_orders and order_depth.sell_orders:
                    spot_price = (max(order_depth.buy_orders) + min(order_depth.sell_orders)) / 2
                else:
                    spot_price = 9800

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
                current_pos = pos.get(product, 0)
                max_pos = 200

                # Hard-coded buy/sell bands from Round 4 analysis
                if product == "VOLCANIC_ROCK_VOUCHER_9500":
                    buy_below, sell_above = 800, 1200
                elif product == "VOLCANIC_ROCK_VOUCHER_9750":
                    buy_below, sell_above = 650, 1050
                elif product == "VOLCANIC_ROCK_VOUCHER_10000":
                    buy_below, sell_above = 500, 900
                elif product == "VOLCANIC_ROCK_VOUCHER_10250":
                    buy_below, sell_above = 350, 750
                elif product == "VOLCANIC_ROCK_VOUCHER_10500":
                    buy_below, sell_above = 250, 550
                else:
                    continue

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

        traderData = jsonpickle.encode(trader_data_out)
        return result, conversions, traderData
