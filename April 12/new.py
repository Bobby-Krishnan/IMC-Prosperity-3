from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict

class Trader:
    def __init__(self):
        self.limits = {
            "PICNIC_BASKET1": 60,
            "PICNIC_BASKET2": 100,
            "CROISSANTS": 250,
            "JAMS": 350,
            "DJEMBES": 60
        }

        self.pb1_threshold = 30  # Spread threshold for basket1
        self.pb2_threshold_high = 15  # Spread thresholds for basket2
        self.pb2_threshold_low = -10

    def get_mid(self, depth: OrderDepth):
        bids = depth.buy_orders
        asks = depth.sell_orders
        if bids and asks:
            return (max(bids.keys()) + min(asks.keys())) / 2
        return None

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # Compute component mid-prices
        mids = {}
        for prod in ["CROISSANTS", "JAMS", "DJEMBES"]:
            depth = state.order_depths.get(prod, OrderDepth())
            mid = self.get_mid(depth)
            if mid:
                mids[prod] = mid

        if len(mids) < 3:
            return {}, conversions, ""  # can't compute synthetic values

        # --- Synthetic Fair Prices ---
        pb1_fair = 6 * mids["CROISSANTS"] + 3 * mids["JAMS"] + mids["DJEMBES"]
        pb2_fair = 4 * mids["CROISSANTS"] + 2 * mids["JAMS"]

        # --- Basket 1 Trading ---
        orders_b1 = []
        depth_b1 = state.order_depths.get("PICNIC_BASKET1", OrderDepth())
        pos_b1 = state.position.get("PICNIC_BASKET1", 0)
        best_bid_b1 = max(depth_b1.buy_orders.keys(), default=None)
        best_ask_b1 = min(depth_b1.sell_orders.keys(), default=None)

        if best_ask_b1 is not None:
            spread = best_ask_b1 - pb1_fair
            if spread < -self.pb1_threshold and pos_b1 < self.limits["PICNIC_BASKET1"]:
                vol = min(-depth_b1.sell_orders[best_ask_b1], self.limits["PICNIC_BASKET1"] - pos_b1)
                if vol > 0:
                    orders_b1.append(Order("PICNIC_BASKET1", best_ask_b1, int(vol)))

        if best_bid_b1 is not None:
            spread = best_bid_b1 - pb1_fair
            if spread > self.pb1_threshold and pos_b1 > -self.limits["PICNIC_BASKET1"]:
                vol = min(depth_b1.buy_orders[best_bid_b1], self.limits["PICNIC_BASKET1"] + pos_b1)
                if vol > 0:
                    orders_b1.append(Order("PICNIC_BASKET1", best_bid_b1, -int(vol)))

        result["PICNIC_BASKET1"] = orders_b1

        # --- Basket 2 Trading ---
        orders_b2 = []
        depth_b2 = state.order_depths.get("PICNIC_BASKET2", OrderDepth())
        pos_b2 = state.position.get("PICNIC_BASKET2", 0)
        best_bid_b2 = max(depth_b2.buy_orders.keys(), default=None)
        best_ask_b2 = min(depth_b2.sell_orders.keys(), default=None)

        if best_ask_b2 is not None:
            spread = best_ask_b2 - pb2_fair
            if spread < self.pb2_threshold_low and pos_b2 < self.limits["PICNIC_BASKET2"]:
                vol = min(-depth_b2.sell_orders[best_ask_b2], self.limits["PICNIC_BASKET2"] - pos_b2)
                if vol > 0:
                    orders_b2.append(Order("PICNIC_BASKET2", best_ask_b2, int(vol)))

        if best_bid_b2 is not None:
            spread = best_bid_b2 - pb2_fair
            if spread > self.pb2_threshold_high and pos_b2 > -self.limits["PICNIC_BASKET2"]:
                vol = min(depth_b2.buy_orders[best_bid_b2], self.limits["PICNIC_BASKET2"] + pos_b2)
                if vol > 0:
                    orders_b2.append(Order("PICNIC_BASKET2", best_bid_b2, -int(vol)))

        result["PICNIC_BASKET2"] = orders_b2

        return result, conversions, ""
