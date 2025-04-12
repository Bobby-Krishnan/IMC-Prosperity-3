from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        traderData = ""
        conversions = 0

        position_limits = {
            "CROISSANT": 250,
            "JAM": 350,
            "PICNIC_BASKET2": 100
        }

        # Get current positions or default to 0
        positions = {
            product: state.position.get(product, 0)
            for product in position_limits
        }

        # Shortcut access
        depths = state.order_depths
        orders: Dict[str, List[Order]] = {
            "CROISSANT": [],
            "JAM": [],
            "PICNIC_BASKET2": []
        }

        def get_best_prices(order_depth: OrderDepth):
            """Returns (best_bid, best_bid_volume), (best_ask, best_ask_volume)"""
            best_bid = max(order_depth.buy_orders.items()) if order_depth.buy_orders else (None, 0)
            best_ask = min(order_depth.sell_orders.items()) if order_depth.sell_orders else (None, 0)
            return best_bid, best_ask

        if "CROISSANT" in depths and "JAM" in depths and "PICNIC_BASKET2" in depths:
            croissant_depth = depths["CROISSANT"]
            jam_depth = depths["JAM"]
            basket_depth = depths["PICNIC_BASKET2"]

            (croissant_bid, croissant_bid_vol), (croissant_ask, croissant_ask_vol) = get_best_prices(croissant_depth)
            (jam_bid, jam_bid_vol), (jam_ask, jam_ask_vol) = get_best_prices(jam_depth)
            (basket_bid, basket_bid_vol), (basket_ask, basket_ask_vol) = get_best_prices(basket_depth)

            # Theoretical basket price from components (4 CROISSANTS + 2 JAMS)
            if all(x is not None for x in [croissant_bid, croissant_ask, jam_bid, jam_ask, basket_bid, basket_ask]):

                # Buy basket, sell components
                basket_buy_price = basket_ask
                components_sell_value = croissant_bid * 4 + jam_bid * 2

                if components_sell_value - basket_buy_price > 3:  # arbitrage spread threshold
                    basket_buy_qty = min(basket_ask_vol, 10, position_limits["PICNIC_BASKET2"] - positions["PICNIC_BASKET2"])
                    croissant_sell_qty = min(croissant_bid_vol, 4 * basket_buy_qty, position_limits["CROISSANT"] + positions["CROISSANT"])
                    jam_sell_qty = min(jam_bid_vol, 2 * basket_buy_qty, position_limits["JAM"] + positions["JAM"])

                    if basket_buy_qty > 0 and croissant_sell_qty >= 4 and jam_sell_qty >= 2:
                        orders["PICNIC_BASKET2"].append(Order("PICNIC_BASKET2", basket_buy_price, basket_buy_qty))
                        orders["CROISSANT"].append(Order("CROISSANT", croissant_bid, -croissant_sell_qty))
                        orders["JAM"].append(Order("JAM", jam_bid, -jam_sell_qty))

                # Buy components, sell basket
                basket_sell_price = basket_bid
                components_buy_cost = croissant_ask * 4 + jam_ask * 2

                if basket_sell_price - components_buy_cost > 3:
                    basket_sell_qty = min(basket_bid_vol, 10, position_limits["PICNIC_BASKET2"] + positions["PICNIC_BASKET2"])
                    croissant_buy_qty = min(croissant_ask_vol, 4 * basket_sell_qty, position_limits["CROISSANT"] - positions["CROISSANT"])
                    jam_buy_qty = min(jam_ask_vol, 2 * basket_sell_qty, position_limits["JAM"] - positions["JAM"])

                    if basket_sell_qty > 0 and croissant_buy_qty >= 4 and jam_buy_qty >= 2:
                        orders["PICNIC_BASKET2"].append(Order("PICNIC_BASKET2", basket_sell_price, -basket_sell_qty))
                        orders["CROISSANT"].append(Order("CROISSANT", croissant_ask, croissant_buy_qty))
                        orders["JAM"].append(Order("JAM", jam_ask, jam_buy_qty))

        # Combine final orders into result
        for product in orders:
            if orders[product]:
                result[product] = orders[product]

        return result, conversions, traderData
