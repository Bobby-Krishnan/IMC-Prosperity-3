from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import numpy as np
import math
import jsonpickle

class Trader:
    def __init__(self):
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }
        self.voucher_limit = 200
        self.base_iv = 0.35
        self.ttl_start = 2  # assume 2 days to expiry in Round 5

    def get_theoretical_price(self, S, K, T, sigma):
        if T <= 0:
            return max(S - K, 0)
        d1 = (math.log(S / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        from scipy.stats import norm
        price = S * norm.cdf(d1) - K * norm.cdf(d2)
        return price

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        trader_data = ""

        # Calculate mid price of VOLCANIC_ROCK to use as S
        rock_depth = state.order_depths.get("VOLCANIC_ROCK")
        if rock_depth is None:
            return {}, conversions, trader_data
        best_bid = max(rock_depth.buy_orders.keys()) if rock_depth.buy_orders else None
        best_ask = min(rock_depth.sell_orders.keys()) if rock_depth.sell_orders else None
        if best_bid is None or best_ask is None:
            return {}, conversions, trader_data
        S = (best_bid + best_ask) / 2

        T = self.ttl_start / 7  # convert to fraction of a week (from 7-day expiry originally)

        for symbol, K in self.voucher_strikes.items():
            order_depth = state.order_depths.get(symbol)
            if not order_depth:
                continue

            pos = state.position.get(symbol, 0)
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            orders: List[Order] = []

            theo_price = self.get_theoretical_price(S, K, T, self.base_iv)

            # Buy undervalued voucher
            if best_ask is not None and best_ask < theo_price:
                buy_vol = min(-order_depth.sell_orders[best_ask], self.voucher_limit - pos)
                if buy_vol > 0:
                    orders.append(Order(symbol, best_ask, buy_vol))

            # Sell overvalued voucher
            if best_bid is not None and best_bid > theo_price:
                sell_vol = min(order_depth.buy_orders[best_bid], self.voucher_limit + pos)
                if sell_vol > 0:
                    orders.append(Order(symbol, best_bid, -sell_vol))

            if orders:
                result[symbol] = orders

        return result, conversions, jsonpickle.encode(trader_data)