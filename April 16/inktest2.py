from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def __init__(self):
        self.max_position = 50
        self.max_trade_size = 10
        self.ema_window = 100
        self.std_window = 30
        self.threshold_multiplier = 1.5

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
            squid_price_history = squid_price_history[-self.ema_window:]

        # Compute adaptive fair price and thresholds
        if len(squid_price_history) >= self.std_window:
            prices = np.array(squid_price_history)
            weights = np.exp(np.linspace(-1., 0., len(prices)))
            weights /= weights.sum()
            fair_price = np.dot(prices, weights)

            std_dev = np.std(prices[-self.std_window:])
            buy_threshold = fair_price - self.threshold_multiplier * std_dev
            sell_threshold = fair_price + self.threshold_multiplier * std_dev

            # BUY logic
            for ask, qty in sorted(squid_depth.sell_orders.items()):
                if ask < buy_threshold and squid_position + self.max_trade_size <= self.max_position:
                    trade_volume = min(-qty, self.max_trade_size, self.max_position - squid_position)
                    if trade_volume > 0:
                        orders_squid.append(Order("SQUID_INK", ask, trade_volume))
                        squid_position += trade_volume

            # SELL logic
            for bid, qty in sorted(squid_depth.buy_orders.items(), reverse=True):
                if bid > sell_threshold and squid_position - self.max_trade_size >= -self.max_position:
                    trade_volume = min(qty, self.max_trade_size, self.max_position + squid_position)
                    if trade_volume > 0:
                        orders_squid.append(Order("SQUID_INK", bid, -trade_volume))
                        squid_position -= trade_volume

        result["SQUID_INK"] = orders_squid
        traderDataOut["squid_price_history"] = squid_price_history
        traderDataEncoded = jsonpickle.encode(traderDataOut)

        return result, conversions, traderDataEncoded