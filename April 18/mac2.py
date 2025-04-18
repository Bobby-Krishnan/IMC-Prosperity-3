from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import jsonpickle
import statistics

class Trader:
    def __init__(self):
        self.price_history: List[float] = []
        self.max_history = 20
        self.position_limit = 75
        self.macaron = "MAGNIFICENT_MACARONS"
        self.critical_sunlight_index = 50

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

        result = {}
        conversions = 0
        traderData = state.traderData

        if self.macaron not in state.order_depths:
            return result, conversions, traderData

        order_depth: OrderDepth = state.order_depths[self.macaron]
        orders: List[Order] = []
        position = state.position.get(self.macaron, 0)

        # Get sunlight index safely
        sunlight = 100.0
        if self.macaron in state.observations.conversionObservations:
            sunlight = state.observations.conversionObservations[self.macaron].sunlightIndex

        bids = sorted(order_depth.buy_orders.items(), reverse=True)
        asks = sorted(order_depth.sell_orders.items())

        if bids and asks:
            fair_price = (bids[0][0] + asks[0][0]) / 2
        elif bids:
            fair_price = bids[0][0]
        elif asks:
            fair_price = asks[0][0]
        else:
            fair_price = 700

        self.price_history.append(fair_price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        volatility = statistics.stdev(self.price_history) if len(self.price_history) > 1 else 0

        print("Acceptable price : " + str(fair_price))
        print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
        print("Volatility : " + str(volatility))

        if sunlight < self.critical_sunlight_index:
            for ask_price, ask_volume in asks:
                if ask_price < fair_price:
                    buy_qty = min(-ask_volume, self.position_limit - position)
                    if buy_qty > 0:
                        print("BUY", str(buy_qty) + "x", ask_price)
                        orders.append(Order(self.macaron, ask_price, buy_qty))
                        position += buy_qty

            for bid_price, bid_volume in bids:
                if bid_price > fair_price + 5:
                    sell_qty = min(bid_volume, position + self.position_limit)
                    if sell_qty > 0:
                        print("SELL", str(sell_qty) + "x", bid_price)
                        orders.append(Order(self.macaron, bid_price, -sell_qty))
                        position -= sell_qty

        else:
            spread = max(3, int(volatility))
            buy_price = int(fair_price - spread)
            sell_price = int(fair_price + spread)

            size_modifier = 1 if volatility < 5 else 0.5
            buy_qty = int(min(10 * size_modifier, self.position_limit - position))
            sell_qty = int(min(10 * size_modifier, position + self.position_limit))

            if buy_qty > 0:
                print("BUY", str(buy_qty) + "x", buy_price)
                orders.append(Order(self.macaron, buy_price, buy_qty))

            if sell_qty > 0:
                print("SELL", str(sell_qty) + "x", sell_price)
                orders.append(Order(self.macaron, sell_price, -sell_qty))

        result[self.macaron] = orders
        return result, conversions, jsonpickle.encode(traderData)