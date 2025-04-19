from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import jsonpickle
#16k from macaroons

class Trader:
    def __init__(self):
        self.position_limit = 75
        self.critical_sunlight_index = 50
        self.macaron_symbol = "MAGNIFICENT_MACARONS"

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        traderData = state.traderData

        if self.macaron_symbol not in state.order_depths:
            return result, conversions, traderData

        order_depth = state.order_depths[self.macaron_symbol]
        orders: List[Order] = []
        position = state.position.get(self.macaron_symbol, 0)

        # Extract sunlight index from observation
        sunlight = 100.0  # default fallback
        if self.macaron_symbol in state.observations.conversionObservations:
            sunlight = state.observations.conversionObservations[self.macaron_symbol].sunlightIndex

        # Calculate fair price
        bids = sorted(order_depth.buy_orders.items(), reverse=True)
        asks = sorted(order_depth.sell_orders.items())
        if bids and asks:
            fair_price = (bids[0][0] + asks[0][0]) / 2
        elif bids:
            fair_price = bids[0][0]
        elif asks:
            fair_price = asks[0][0]
        else:
            fair_price = 700  # fallback fair price

        print("Acceptable price :", fair_price)
        print("Buy Order depth :", len(order_depth.buy_orders), ", Sell order depth :", len(order_depth.sell_orders))

        if sunlight < self.critical_sunlight_index:
            # PANIC STRATEGY: Buy low, Sell high
            for ask_price, ask_volume in asks:
                if ask_price < fair_price:
                    qty = min(-ask_volume, self.position_limit - position)
                    if qty > 0:
                        print("BUY", qty, "x", ask_price)
                        orders.append(Order(self.macaron_symbol, ask_price, qty))
                        position += qty

            for bid_price, bid_volume in bids:
                if bid_price > fair_price + 5:
                    qty = min(bid_volume, position + self.position_limit)
                    if qty > 0:
                        print("SELL", qty, "x", bid_price)
                        orders.append(Order(self.macaron_symbol, bid_price, -qty))
                        position -= qty
        else:
            # STABLE STRATEGY: Market-make around fair value
            spread = 3
            buy_price = int(fair_price - spread)
            sell_price = int(fair_price + spread)

            buy_qty = min(10, self.position_limit - position)
            sell_qty = min(10, position + self.position_limit)

            if buy_qty > 0:
                print("BUY", buy_qty, "x", buy_price)
                orders.append(Order(self.macaron_symbol, buy_price, buy_qty))

            if sell_qty > 0:
                print("SELL", sell_qty, "x", sell_price)
                orders.append(Order(self.macaron_symbol, sell_price, -sell_qty))

        result[self.macaron_symbol] = orders
        return result, conversions, traderData
