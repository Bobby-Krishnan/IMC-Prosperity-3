from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def __init__(self):
        self.squid_window_size = 10
        self.squid_position_limit = 50
        self.momentum_threshold = 2.0
        self.exit_threshold = 0.25  # exit when z-score returns near 0
        self.trade_size = 5

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        traderDataOut = {}

        orders_squid: List[Order] = []
        squid_price_history = []

        if state.traderData:
            try:
                traderDataIn = jsonpickle.decode(state.traderData)
                squid_price_history = traderDataIn.get("squid_price_history", [])
            except Exception:
                squid_price_history = []

        squid_depth: OrderDepth = state.order_depths.get("SQUID_INK", OrderDepth())
        squid_position = state.position.get("SQUID_INK", 0)

        squid_best_bid = max(squid_depth.buy_orders.keys(), default=None)
        squid_best_ask = min(squid_depth.sell_orders.keys(), default=None)

        if squid_best_bid is not None and squid_best_ask is not None:
            squid_mid_price = (squid_best_bid + squid_best_ask) / 2
            squid_price_history.append(squid_mid_price)
            squid_price_history = squid_price_history[-self.squid_window_size:]

        if len(squid_price_history) >= self.squid_window_size:
            short_term_mean = np.mean(squid_price_history)
            price_now = squid_price_history[-1]
            recent_volatility = np.std(squid_price_history)

            if recent_volatility > 0:
                z_score = (price_now - short_term_mean) / recent_volatility
            else:
                z_score = 0

            # Momentum Buy (breakout above upper band)
            if (
                z_score > self.momentum_threshold
                and squid_best_ask is not None
                and squid_position < self.squid_position_limit
            ):
                ask_volume = -squid_depth.sell_orders[squid_best_ask]
                buy_volume = min(ask_volume, self.trade_size, self.squid_position_limit - squid_position)
                if buy_volume > 0:
                    orders_squid.append(Order("SQUID_INK", squid_best_ask, buy_volume))

            # Momentum Sell (breakout below lower band)
            if (
                z_score < -self.momentum_threshold
                and squid_best_bid is not None
                and squid_position > -self.squid_position_limit
            ):
                bid_volume = squid_depth.buy_orders[squid_best_bid]
                sell_volume = min(bid_volume, self.trade_size, self.squid_position_limit + squid_position)
                if sell_volume > 0:
                    orders_squid.append(Order("SQUID_INK", squid_best_bid, -sell_volume))

            # EXIT condition: z-score near 0
            if (
                abs(z_score) <= self.exit_threshold
                and squid_position != 0
                and squid_best_bid is not None
                and squid_best_ask is not None
            ):
                if squid_position > 0:
                    sell_volume = min(squid_position, squid_depth.buy_orders.get(squid_best_bid, 0))
                    if sell_volume > 0:
                        orders_squid.append(Order("SQUID_INK", squid_best_bid, -sell_volume))
                elif squid_position < 0:
                    buy_volume = min(-squid_position, -squid_depth.sell_orders.get(squid_best_ask, 0))
                    if buy_volume > 0:
                        orders_squid.append(Order("SQUID_INK", squid_best_ask, buy_volume))

        result["SQUID_INK"] = orders_squid

        traderDataOut["squid_price_history"] = squid_price_history
        traderDataEncoded = jsonpickle.encode(traderDataOut)

        return result, conversions, traderDataEncoded
