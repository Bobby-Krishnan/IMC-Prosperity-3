from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import numpy as np

class Trader:
    def __init__(self):
        self.PRICE_WINDOW = 12
        self.price_history: Dict[str, List[float]] = {}
        self.positions: Dict[str, int] = {}
        self.last_trade_price: Dict[str, float] = {}
        self.stop_loss_threshold = 2500

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        trader_data = ""

        product = "VOLCANIC_ROCK"
        order_depth: OrderDepth = state.order_depths[product]
        orders: List[Order] = []

        if product not in self.price_history:
            self.price_history[product] = []
        if product not in self.positions:
            self.positions[product] = 0

        # Calculate mid price
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

        if best_bid is not None and best_ask is not None:
            mid_price = (best_bid + best_ask) / 2
            self.price_history[product].append(mid_price)
            if len(self.price_history[product]) > self.PRICE_WINDOW:
                self.price_history[product].pop(0)
        else:
            return {}, conversions, trader_data

        # Compute Bollinger Bands
        if len(self.price_history[product]) >= self.PRICE_WINDOW:
            prices = np.array(self.price_history[product])
            mean = np.mean(prices)
            std = np.std(prices)
            upper_band = mean + 2.5 * std
            lower_band = mean - 2.5 * std

            position = state.position.get(product, 0)
            self.positions[product] = position

            # Entry signals
            if best_ask < lower_band and position < 20:
                buy_volume = min(order_depth.sell_orders[best_ask], 20 - position)
                orders.append(Order(product, best_ask, buy_volume))
                self.last_trade_price[product] = best_ask

            elif best_bid > upper_band and position > -20:
                sell_volume = min(order_depth.buy_orders[best_bid], 20 + position)
                orders.append(Order(product, best_bid, -sell_volume))
                self.last_trade_price[product] = best_bid

            # Smarter exit logic
            # If long and price returns to mean or drops 100 below entry, exit
            if position > 0 and best_bid >= mean:
                orders.append(Order(product, best_bid, -position))
            elif position > 0 and best_bid <= self.last_trade_price[product] - 100:
                orders.append(Order(product, best_bid, -position))

            # If short and price returns to mean or rises 100 above entry, exit
            if position < 0 and best_ask <= mean:
                orders.append(Order(product, best_ask, -position))
            elif position < 0 and best_ask >= self.last_trade_price[product] + 100:
                orders.append(Order(product, best_ask, -position))

            # Stop loss check
            if abs(position * mid_price) > self.stop_loss_threshold:
                orders.append(Order(product, best_bid if position > 0 else best_ask, -position))

        result[product] = orders
        return result, conversions, trader_data
