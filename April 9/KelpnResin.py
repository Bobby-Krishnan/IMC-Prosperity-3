from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def __init__(self):
        self.kelp_window_size = 6
        self.kelp_position_limit = 50
        self.kelp_seed_fair_price = 2000

        self.resin_fair_price = 10000
        self.resin_position_limit = 50

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        traderDataOut = {}

        orders_kelp: List[Order] = []
        orders_resin: List[Order] = []

        # --------- KELP STRATEGY ---------
        kelp_price_history = []

        if state.traderData:
            try:
                traderDataIn = jsonpickle.decode(state.traderData)
                kelp_price_history = traderDataIn.get("kelp_price_history", [])
            except Exception:
                kelp_price_history = []

        kelp_depth: OrderDepth = state.order_depths.get("KELP", OrderDepth())
        kelp_position = state.position.get("KELP", 0)

        kelp_best_bid = max(kelp_depth.buy_orders.keys(), default=None)
        kelp_best_ask = min(kelp_depth.sell_orders.keys(), default=None)

        if kelp_best_bid is not None and kelp_best_ask is not None:
            kelp_mid_price = (kelp_best_bid + kelp_best_ask) / 2
            kelp_price_history.append(kelp_mid_price)
            kelp_price_history = kelp_price_history[-self.kelp_window_size:]

        kelp_fair_price = (
            np.mean(kelp_price_history)
            if kelp_price_history
            else self.kelp_seed_fair_price
        )

        if abs(kelp_position) > 40:
            kelp_trade_volume = 5
        elif abs(kelp_position) > 30:
            kelp_trade_volume = 10
        else:
            kelp_trade_volume = 15

        if kelp_best_ask is not None and kelp_best_ask < kelp_fair_price and kelp_position < self.kelp_position_limit:
            kelp_ask_volume = -kelp_depth.sell_orders[kelp_best_ask]
            kelp_buy_volume = min(kelp_ask_volume, self.kelp_position_limit - kelp_position, kelp_trade_volume)
            if kelp_buy_volume > 0:
                orders_kelp.append(Order("KELP", kelp_best_ask, kelp_buy_volume))

        if kelp_best_bid is not None and kelp_best_bid > kelp_fair_price and kelp_position > -self.kelp_position_limit:
            kelp_bid_volume = kelp_depth.buy_orders[kelp_best_bid]
            kelp_sell_volume = min(kelp_bid_volume, kelp_trade_volume, self.kelp_position_limit + kelp_position)
            if kelp_sell_volume > 0:
                orders_kelp.append(Order("KELP", kelp_best_bid, -kelp_sell_volume))

        result["KELP"] = orders_kelp

        # --------- RESIN STRATEGY ---------
        resin_depth: OrderDepth = state.order_depths.get("RAINFOREST_RESIN", OrderDepth())
        resin_position = state.position.get("RAINFOREST_RESIN", 0)

        if abs(resin_position) > 40:
            resin_trade_volume = 5
        elif abs(resin_position) > 30:
            resin_trade_volume = 10
        else:
            resin_trade_volume = 15

        if len(resin_depth.sell_orders) > 0:
            resin_best_ask = min(resin_depth.sell_orders.keys())
            resin_ask_volume = resin_depth.sell_orders[resin_best_ask]
            if resin_best_ask < self.resin_fair_price and resin_position + resin_trade_volume <= self.resin_position_limit:
                resin_buy_volume = min(-resin_ask_volume, self.resin_position_limit - resin_position, resin_trade_volume)
                if resin_buy_volume > 0:
                    orders_resin.append(Order("RAINFOREST_RESIN", resin_best_ask, resin_buy_volume))

        if len(resin_depth.buy_orders) > 0:
            resin_best_bid = max(resin_depth.buy_orders.keys())
            resin_bid_volume = resin_depth.buy_orders[resin_best_bid]
            if resin_best_bid > self.resin_fair_price and resin_position - resin_trade_volume >= -self.resin_position_limit:
                resin_sell_volume = min(resin_bid_volume, resin_trade_volume, self.resin_position_limit + resin_position)
                if resin_sell_volume > 0:
                    orders_resin.append(Order("RAINFOREST_RESIN", resin_best_bid, -resin_sell_volume))

        result["RAINFOREST_RESIN"] = orders_resin

        # --------- Save Combined State ---------
        traderDataOut["kelp_price_history"] = kelp_price_history
        traderDataEncoded = jsonpickle.encode(traderDataOut)

        return result, conversions, traderDataEncoded
