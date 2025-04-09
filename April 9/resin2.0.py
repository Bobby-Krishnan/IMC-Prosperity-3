from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict

class Trader:
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

        result: Dict[str, List[Order]] = {}
        traderData = ""
        conversions = 0

        product = "RAINFOREST_RESIN"
        position_limit = 50
        trade_volume = 15

        if product in state.order_depths:
            orders: List[Order] = []
            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)

            fair_price = 10000  # Conservative assumption

            if len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = order_depth.sell_orders[best_ask]
                if best_ask < fair_price and current_position + trade_volume <= position_limit:
                    buy_volume = min(-best_ask_volume, position_limit - current_position, trade_volume)
                    print(f"BUY {buy_volume} @ {best_ask}")
                    orders.append(Order(product, best_ask, buy_volume))

            if len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                if best_bid > fair_price and current_position - trade_volume >= -position_limit:
                    sell_volume = min(best_bid_volume, trade_volume, position_limit + current_position)
                    print(f"SELL {sell_volume} @ {best_bid}")
                    orders.append(Order(product, best_bid, -sell_volume))

            result[product] = orders

        return result, conversions, traderData
