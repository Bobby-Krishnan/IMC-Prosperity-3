from datamodel import Order, OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:
    def run(self, state: TradingState):
        # Logging for debug
        print("traderData:", state.traderData)
        print("Observations:", state.observations)

        result: Dict[str, List[Order]] = {}
        conversions = 0
        traderData = ""

        timestamp = state.timestamp

        ########################################################
        #                  RAINFOREST_RESIN
        ########################################################
        product_resin = "RAINFOREST_RESIN"
        position_limit_resin = 50
        fair_price_resin = 10000

        if product_resin in state.order_depths:
            order_depth_resin: OrderDepth = state.order_depths[product_resin]
            orders_resin: List[Order] = []
            current_position_resin = state.position.get(product_resin, 0)

            # Position-aware trade volume
            if abs(current_position_resin) > 40:
                trade_volume_resin = 5
            elif abs(current_position_resin) > 30:
                trade_volume_resin = 10
            else:
                trade_volume_resin = 15

            if len(order_depth_resin.sell_orders) > 0:
                best_ask = min(order_depth_resin.sell_orders.keys())
                best_ask_volume = -order_depth_resin.sell_orders[best_ask]
                if best_ask < fair_price_resin and current_position_resin + trade_volume_resin <= position_limit_resin:
                    buy_volume = min(best_ask_volume, position_limit_resin - current_position_resin, trade_volume_resin)
                    if buy_volume > 0:
                        print(f"[RESIN] BUY {buy_volume} @ {best_ask}")
                        orders_resin.append(Order(product_resin, best_ask, buy_volume))

            if len(order_depth_resin.buy_orders) > 0:
                best_bid = max(order_depth_resin.buy_orders.keys())
                best_bid_volume = order_depth_resin.buy_orders[best_bid]
                if best_bid > fair_price_resin and current_position_resin - trade_volume_resin >= -position_limit_resin:
                    sell_volume = min(best_bid_volume, trade_volume_resin, position_limit_resin + current_position_resin)
                    if sell_volume > 0:
                        print(f"[RESIN] SELL {sell_volume} @ {best_bid}")
                        orders_resin.append(Order(product_resin, best_bid, -sell_volume))

            result[product_resin] = orders_resin

        ########################################################
        #                       KELP
        ########################################################
        product_kelp = "KELP"
        position_limit_kelp = 50
        fair_price_kelp = 2025

        # Time gating: skip Kelp trades if timestamp in [75k, 90k]
        if 75000 <= timestamp <= 90000:
            # We do nothing for KELP in this zone
            result[product_kelp] = []
        else:
            if product_kelp in state.order_depths:
                order_depth_kelp: OrderDepth = state.order_depths[product_kelp]
                orders_kelp: List[Order] = []
                current_position_kelp = state.position.get(product_kelp, 0)

                if abs(current_position_kelp) > 40:
                    trade_volume_kelp = 5
                elif abs(current_position_kelp) > 30:
                    trade_volume_kelp = 10
                else:
                    trade_volume_kelp = 15

                # Implement your existing profitable KELP logic:
                # (For instance, an MA-based approach or a fair price approach)
                if len(order_depth_kelp.sell_orders) > 0:
                    best_ask_kelp = min(order_depth_kelp.sell_orders.keys())
                    best_ask_vol_kelp = -order_depth_kelp.sell_orders[best_ask_kelp]
                    if best_ask_kelp < fair_price_kelp and current_position_kelp + trade_volume_kelp <= position_limit_kelp:
                        buy_qty_kelp = min(best_ask_vol_kelp, position_limit_kelp - current_position_kelp, trade_volume_kelp)
                        if buy_qty_kelp > 0:
                            print(f"[KELP] BUY {buy_qty_kelp} @ {best_ask_kelp}")
                            orders_kelp.append(Order(product_kelp, best_ask_kelp, buy_qty_kelp))

                if len(order_depth_kelp.buy_orders) > 0:
                    best_bid_kelp = max(order_depth_kelp.buy_orders.keys())
                    best_bid_vol_kelp = order_depth_kelp.buy_orders[best_bid_kelp]
                    if best_bid_kelp > fair_price_kelp and current_position_kelp - trade_volume_kelp >= -position_limit_kelp:
                        sell_qty_kelp = min(best_bid_vol_kelp, trade_volume_kelp, position_limit_kelp + current_position_kelp)
                        if sell_qty_kelp > 0:
                            print(f"[KELP] SELL {sell_qty_kelp} @ {best_bid_kelp}")
                            orders_kelp.append(Order(product_kelp, best_bid_kelp, -sell_qty_kelp))

                result[product_kelp] = orders_kelp

        return result, conversions, traderData
