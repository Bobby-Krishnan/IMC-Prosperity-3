from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def __init__(self):
        self.bot_profiles = {
            "Charlie": {"tag": "tight_mm"},
            "Paris": {"tag": "trend_follower"},
            "Penelope": {"tag": "aggressive_filler"},
            "Caesar": {"tag": "liquidity_sink"},
            "Camilla": {"tag": "accumulator"},
            "Gary": {"tag": "neutral"},
            "Gina": {"tag": "neutral"},
            "Olivia": {"tag": "neutral"},
            "Pablo": {"tag": "neutral"}
        }
        self.rock_price_history = []
        self.boll_window = 20
        self.boll_alpha = 2.0
        self.max_rock_position = 400
        self.rock_peak_pnl = 0
        self.rock_entry_price = None
        self.rock_stop_loss = 2500
        self.rock_trailing_stop_pct = 0.15

    def adjust_order_size(self, base_qty: int, recent_trades: List, product: str) -> int:
        bot_trade_counts = {}
        for trade in reversed(recent_trades):
            bot = getattr(trade, 'counter_party', None)
            if bot in self.bot_profiles:
                tag = self.bot_profiles[bot]["tag"]
                bot_trade_counts[tag] = bot_trade_counts.get(tag, 0) + 1

        if "liquidity_sink" in bot_trade_counts or "trend_follower" in bot_trade_counts:
            return int(base_qty * 1.5)
        elif "tight_mm" in bot_trade_counts or "accumulator" in bot_trade_counts:
            return int(base_qty * 0.5)
        return base_qty

    def trade_volcanic_rock(self, state: TradingState, result: Dict[str, List[Order]]):
        product = "VOLCANIC_ROCK"
        if product not in state.order_depths:
            return

        order_depth = state.order_depths[product]
        recent_trades = state.own_trades.get(product, [])
        position = state.position.get(product, 0)
        orders = []

        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        if best_bid is None or best_ask is None:
            return

        mid = (best_bid + best_ask) / 2
        self.rock_price_history.append(mid)
        if len(self.rock_price_history) > self.boll_window:
            self.rock_price_history.pop(0)

        mean = np.mean(self.rock_price_history)
        std = np.std(self.rock_price_history)
        upper = mean + self.boll_alpha * std
        lower = mean - self.boll_alpha * std

        if self.rock_entry_price is not None:
            unrealized = (mid - self.rock_entry_price) * position
            self.rock_peak_pnl = max(self.rock_peak_pnl, unrealized)
            trailing_exit = self.rock_peak_pnl - self.rock_trailing_stop_pct * abs(self.rock_peak_pnl)
            if unrealized < -self.rock_stop_loss or unrealized < trailing_exit:
                if position > 0:
                    orders.append(Order(product, best_bid, -position))
                elif position < 0:
                    orders.append(Order(product, best_ask, -position))
                result[product] = orders
                self.rock_entry_price = None
                self.rock_peak_pnl = 0
                return

        for ask, volume in sorted(order_depth.sell_orders.items()):
            if ask < lower and position + abs(volume) <= self.max_rock_position:
                qty = self.adjust_order_size(abs(volume), recent_trades, product)
                if qty > 0:
                    orders.append(Order(product, ask, qty))
                    if self.rock_entry_price is None:
                        self.rock_entry_price = ask

        for bid, volume in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid > upper and position - abs(volume) >= -self.max_rock_position:
                qty = self.adjust_order_size(abs(volume), recent_trades, product)
                if qty > 0:
                    orders.append(Order(product, bid, -qty))
                    if self.rock_entry_price is None:
                        self.rock_entry_price = bid

        result[product] = orders

    def trade_other_products(self, state: TradingState, result: Dict[str, List[Order]], kelp_history: List):
        products = ["RAINFOREST_RESIN", "KELP", "SQUID_INK", "CROISSANTS", "JAMS", "DJEMBES", "PICNIC_BASKET1", "PICNIC_BASKET2"]
        limits = {
            "RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50,
            "CROISSANTS": 250, "JAMS": 350, "DJEMBES": 60,
            "PICNIC_BASKET1": 60, "PICNIC_BASKET2": 100
        }

        for product in products:
            if product not in state.order_depths:
                continue
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            recent_trades = state.own_trades.get(product, [])
            orders: List[Order] = []

            best_bid = max(order_depth.buy_orders.keys(), default=None)
            best_ask = min(order_depth.sell_orders.keys(), default=None)
            if best_bid is None or best_ask is None:
                continue

            mid = (best_bid + best_ask) / 2
            if product == "KELP":
                kelp_history.append(mid)
                if len(kelp_history) > 6:
                    kelp_history.pop(0)
                fair_price = np.mean(kelp_history)
            elif product == "SQUID_INK":
                fair_price = 7000
            elif product == "RAINFOREST_RESIN":
                fair_price = 10000
            else:
                fair_price = mid

            pos_limit = limits[product]

            for ask, volume in sorted(order_depth.sell_orders.items()):
                if ask < fair_price and position + abs(volume) <= pos_limit:
                    qty = self.adjust_order_size(abs(volume), recent_trades, product)
                    if qty > 0:
                        orders.append(Order(product, ask, qty))
                        position += qty

            for bid, volume in sorted(order_depth.buy_orders.items(), reverse=True):
                if bid > fair_price and position - abs(volume) >= -pos_limit:
                    qty = self.adjust_order_size(abs(volume), recent_trades, product)
                    if qty > 0:
                        orders.append(Order(product, bid, -qty))
                        position -= qty

            result[product] = orders

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        kelp_history = []

        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                kelp_history = prior_data.get("kelp_history", [])
            except:
                kelp_history = []

        self.trade_volcanic_rock(state, result)
        self.trade_other_products(state, result, kelp_history)

        traderData = jsonpickle.encode({"kelp_history": kelp_history})
        return result, conversions, traderData