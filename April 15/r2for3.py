from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import numpy as np
import jsonpickle

class Trader:
    def __init__(self):
        self.limits = {
            "PICNIC_BASKET1": 60,
            "PICNIC_BASKET2": 100,
            "CROISSANTS": 250,
            "JAMS": 350,
            "DJEMBES": 60
        }
        self.spread_window = 20
        self.zscore_threshold = 2

    def get_mid(self, depth: OrderDepth):
        bids = depth.buy_orders
        asks = depth.sell_orders
        if bids and asks:
            return (max(bids.keys()) + min(asks.keys())) / 2
        return None

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # Load trader data
        spread_data = {
            "pb1_spreads": [],
            "pb2_spreads": []
        }
        if state.traderData:
            try:
                spread_data = jsonpickle.decode(state.traderData)
            except:
                pass

        # Get mid-prices
        mids = {}
        for prod in ["CROISSANTS", "JAMS", "DJEMBES"]:
            depth = state.order_depths.get(prod, OrderDepth())
            mid = self.get_mid(depth)
            if mid is not None:
                mids[prod] = mid

        # --- BASKET 1 ---
        orders_pb1 = []
        if all(x in mids for x in ["CROISSANTS", "JAMS", "DJEMBES"]):
            pb1_fair = 6 * mids["CROISSANTS"] + 3 * mids["JAMS"] + 1 * mids["DJEMBES"]
            depth_pb1 = state.order_depths.get("PICNIC_BASKET1", OrderDepth())
            pos_pb1 = state.position.get("PICNIC_BASKET1", 0)
            best_bid = max(depth_pb1.buy_orders.keys(), default=None)
            best_ask = min(depth_pb1.sell_orders.keys(), default=None)

            new_spread = None
            if best_ask is not None:
                new_spread = best_ask - pb1_fair
                spread_data["pb1_spreads"].append(new_spread)
            if best_bid is not None:
                new_spread = best_bid - pb1_fair
                spread_data["pb1_spreads"].append(new_spread)

            pb1_history = spread_data["pb1_spreads"][-self.spread_window:]
            z1 = 0
            if len(pb1_history) >= 2:
                mean = np.mean(pb1_history)
                std = np.std(pb1_history)
                if std > 0 and new_spread is not None:
                    z1 = (new_spread - mean) / std

            if best_ask is not None and z1 < -self.zscore_threshold and pos_pb1 < self.limits["PICNIC_BASKET1"]:
                vol = min(-depth_pb1.sell_orders[best_ask], self.limits["PICNIC_BASKET1"] - pos_pb1)
                if vol > 0:
                    orders_pb1.append(Order("PICNIC_BASKET1", best_ask, vol))

            if best_bid is not None and z1 > self.zscore_threshold and pos_pb1 > -self.limits["PICNIC_BASKET1"]:
                vol = min(depth_pb1.buy_orders[best_bid], self.limits["PICNIC_BASKET1"] + pos_pb1)
                if vol > 0:
                    orders_pb1.append(Order("PICNIC_BASKET1", best_bid, -vol))

        result["PICNIC_BASKET1"] = orders_pb1

        # --- BASKET 2 ---
        orders_pb2 = []
        if all(x in mids for x in ["CROISSANTS", "JAMS"]):
            pb2_fair = 4 * mids["CROISSANTS"] + 2 * mids["JAMS"]
            depth_pb2 = state.order_depths.get("PICNIC_BASKET2", OrderDepth())
            pos_pb2 = state.position.get("PICNIC_BASKET2", 0)
            best_bid = max(depth_pb2.buy_orders.keys(), default=None)
            best_ask = min(depth_pb2.sell_orders.keys(), default=None)

            new_spread = None
            if best_ask is not None:
                new_spread = best_ask - pb2_fair
                spread_data["pb2_spreads"].append(new_spread)
            if best_bid is not None:
                new_spread = best_bid - pb2_fair
                spread_data["pb2_spreads"].append(new_spread)

            pb2_history = spread_data["pb2_spreads"][-self.spread_window:]
            z2 = 0
            if len(pb2_history) >= 2:
                mean = np.mean(pb2_history)
                std = np.std(pb2_history)
                if std > 0 and new_spread is not None:
                    z2 = (new_spread - mean) / std

            if best_ask is not None and z2 < -self.zscore_threshold and pos_pb2 < self.limits["PICNIC_BASKET2"]:
                vol = min(-depth_pb2.sell_orders[best_ask], self.limits["PICNIC_BASKET2"] - pos_pb2)
                if vol > 0:
                    orders_pb2.append(Order("PICNIC_BASKET2", best_ask, vol))

            if best_bid is not None and z2 > self.zscore_threshold and pos_pb2 > -self.limits["PICNIC_BASKET2"]:
                vol = min(depth_pb2.buy_orders[best_bid], self.limits["PICNIC_BASKET2"] + pos_pb2)
                if vol > 0:
                    orders_pb2.append(Order("PICNIC_BASKET2", best_bid, -vol))

        result["PICNIC_BASKET2"] = orders_pb2

        # --- Encode traderData ---
        traderDataEncoded = jsonpickle.encode({
            "pb1_spreads": spread_data["pb1_spreads"][-self.spread_window:],
            "pb2_spreads": spread_data["pb2_spreads"][-self.spread_window:]
        })

        return result, conversions, traderDataEncoded
