from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

        # Deserialize memory
        memory = jsonpickle.decode(state.traderData) if state.traderData else {
            "spread_history": []
        }

        result: Dict[str, List[Order]] = {}
        conversions = 0

        CROISSANT = "CROISSANTS"
        JAM = "JAMS"
        POS_LIMITS = {CROISSANT: 250, JAM: 350}
        positions = {
            CROISSANT: state.position.get(CROISSANT, 0),
            JAM: state.position.get(JAM, 0)
        }

        def mid_price(depth: OrderDepth):
            if depth.buy_orders and depth.sell_orders:
                return (max(depth.buy_orders) + min(depth.sell_orders)) / 2
            return None

        order_depths = state.order_depths
        croissant_depth = order_depths.get(CROISSANT)
        jam_depth = order_depths.get(JAM)
        croissant_mid = mid_price(croissant_depth)
        jam_mid = mid_price(jam_depth)

        if croissant_mid and jam_mid:
            hedge_ratio = 0.75
            spread = jam_mid - hedge_ratio * croissant_mid
            memory["spread_history"].append(spread)
            if len(memory["spread_history"]) > 100:
                memory["spread_history"].pop(0)

            spread_hist = memory["spread_history"]
            mean = np.mean(spread_hist)
            std = np.std(spread_hist)
            z_score = (spread - mean) / std if std > 0 else 0

            entry_z = 1.0
            exit_z = 0.2
            volume = 10

            orders_croissant: List[Order] = []
            orders_jam: List[Order] = []

            if z_score > entry_z:
                # Sell JAM, Buy CROISSANTS
                best_bid_jam = max(jam_depth.buy_orders.keys(), default=None)
                best_ask_cros = min(croissant_depth.sell_orders.keys(), default=None)
                if best_bid_jam and positions[JAM] - volume >= -POS_LIMITS[JAM]:
                    orders_jam.append(Order(JAM, best_bid_jam, -volume))
                if best_ask_cros and positions[CROISSANT] + volume <= POS_LIMITS[CROISSANT]:
                    orders_croissant.append(Order(CROISSANT, best_ask_cros, volume))

            elif z_score < -entry_z:
                # Buy JAM, Sell CROISSANTS
                best_ask_jam = min(jam_depth.sell_orders.keys(), default=None)
                best_bid_cros = max(croissant_depth.buy_orders.keys(), default=None)
                if best_ask_jam and positions[JAM] + volume <= POS_LIMITS[JAM]:
                    orders_jam.append(Order(JAM, best_ask_jam, volume))
                if best_bid_cros and positions[CROISSANT] - volume >= -POS_LIMITS[CROISSANT]:
                    orders_croissant.append(Order(CROISSANT, best_bid_cros, -volume))

            elif abs(z_score) < exit_z:
                # Exit both sides
                if positions[JAM] > 0:
                    best_bid = max(jam_depth.buy_orders.keys(), default=None)
                    if best_bid:
                        orders_jam.append(Order(JAM, best_bid, -min(volume, positions[JAM])))
                if positions[JAM] < 0:
                    best_ask = min(jam_depth.sell_orders.keys(), default=None)
                    if best_ask:
                        orders_jam.append(Order(JAM, best_ask, min(volume, -positions[JAM])))
                if positions[CROISSANT] > 0:
                    best_bid = max(croissant_depth.buy_orders.keys(), default=None)
                    if best_bid:
                        orders_croissant.append(Order(CROISSANT, best_bid, -min(volume, positions[CROISSANT])))
                if positions[CROISSANT] < 0:
                    best_ask = min(croissant_depth.sell_orders.keys(), default=None)
                    if best_ask:
                        orders_croissant.append(Order(CROISSANT, best_ask, min(volume, -positions[CROISSANT])))

            if orders_croissant:
                result[CROISSANT] = orders_croissant
            if orders_jam:
                result[JAM] = orders_jam

        traderData = jsonpickle.encode(memory)
        return result, conversions, traderData
