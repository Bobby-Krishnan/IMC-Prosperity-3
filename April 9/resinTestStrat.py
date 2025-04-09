from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        traderData = ""
        conversions = 0

        product = "RAINFOREST_RESIN"
        position_limit = 50
        static_fair_price = 10000

        if product in state.order_depths:
            orders: List[Order] = []
            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)

            buy_orders = order_depth.buy_orders
            sell_orders = order_depth.sell_orders

            if len(buy_orders) > 0 and len(sell_orders) > 0:
                best_bid = max(buy_orders.keys())
                best_bid_volume = buy_orders[best_bid]
                best_ask = min(sell_orders.keys())
                best_ask_volume = sell_orders[best_ask]

                spread = best_ask - best_bid
                midpoint = (best_bid + best_ask) // 2

                # Use static fair price, but optionally check how close to midpoint
                fair_price = static_fair_price
                spread_threshold = 2  # Only trade if spread > 2

                # Dynamic volume: larger volume on bigger spreads
                if abs(current_position) > 40:
                    base_volume = 5
                elif abs(current_position) > 30:
                    base_volume = 10
                else:
                    base_volume = 15

                if spread >= spread_threshold:
                    # BUY condition
                    if best_ask < fair_price and current_position + base_volume <= position_limit:
                        buy_volume = min(-best_ask_volume, position_limit - current_position, base_volume)
                        orders.append(Order(product, best_ask, buy_volume))
                        print(f"BUY {buy_volume} @ {best_ask}")

                    # SELL condition
                    if best_bid > fair_price and current_position - base_volume >= -position_limit:
                        sell_volume = min(best_bid_volume, base_volume, position_limit + current_position)
                        orders.append(Order(product, best_bid, -sell_volume))
                        print(f"SELL {sell_volume} @ {best_bid}")

            result[product] = orders

        return result, conversions, traderData
