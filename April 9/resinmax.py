from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict

class Trader:
    def run(self, state: TradingState):
        print("traderData:", state.traderData)
        print("Observations:", str(state.observations))

        result: Dict[str, List[Order]] = {}
        traderData = ""
        conversions = 0

        product = "RAINFOREST_RESIN"
        position_limit = 50
        fair_price = 10000
        trade_volume = 15  # Constant volume for every trade

        if product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            orders: List[Order] = []

            # BUY if best ask is below fair price and within position limits
            if order_depth.sell_orders:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = -order_depth.sell_orders[best_ask]
                if best_ask < fair_price and current_position < position_limit:
                    buy_qty = min(trade_volume, best_ask_volume, position_limit - current_position)
                    print(f"BUY {buy_qty} @ {best_ask}")
                    orders.append(Order(product, best_ask, buy_qty))

            # SELL if best bid is above fair price and within position limits
            if order_depth.buy_orders:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                if best_bid > fair_price and current_position > -position_limit:
                    sell_qty = min(trade_volume, best_bid_volume, current_position + position_limit)
                    print(f"SELL {sell_qty} @ {best_bid}")
                    orders.append(Order(product, best_bid, -sell_qty))

            result[product] = orders

        return result, conversions, traderData
