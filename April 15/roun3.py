from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import numpy as np
import jsonpickle
from scipy.stats import norm
from scipy.optimize import minimize_scalar

# Set strike prices
STRIKE_MAP = {
    "VOLCANIC_ROCK_VOUCHER_9500": 9500,
    "VOLCANIC_ROCK_VOUCHER_9750": 9750,
    "VOLCANIC_ROCK_VOUCHER_10000": 10000,
    "VOLCANIC_ROCK_VOUCHER_10250": 10250,
    "VOLCANIC_ROCK_VOUCHER_10500": 10500,
}

def black_scholes_call_price(S, K, T, sigma, r=0):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0)
    d1 = (np.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def implied_volatility(C_market, S, K, T):
    if C_market < max(S - K, 0):
        return None
    try:
        result = minimize_scalar(
            lambda sigma: (black_scholes_call_price(S, K, T, sigma) - C_market) ** 2,
            bounds=(0.01, 2.0), method='bounded'
        )
        return result.x if result.success else None
    except:
        return None

class Trader:

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        traderDataOut = {}

        # Load previous data from traderData string
        if state.traderData:
            try:
                traderDataOut = jsonpickle.decode(state.traderData)
            except:
                traderDataOut = {}
        
        # Initialize memory
        if 'historical_data' not in traderDataOut:
            traderDataOut['historical_data'] = []

        orders_to_place = []
        rock_price = None

        # Get current rock price (mid)
        if "VOLCANIC_ROCK" in state.order_depths:
            rock_depth = state.order_depths["VOLCANIC_ROCK"]
            if rock_depth.buy_orders and rock_depth.sell_orders:
                best_bid = max(rock_depth.buy_orders)
                best_ask = min(rock_depth.sell_orders)
                rock_price = (best_bid + best_ask) / 2

        if rock_price is not None:
            # Gather voucher data and record
            for product, strike in STRIKE_MAP.items():
                if product not in state.order_depths:
                    continue
                depth = state.order_depths[product]
                if depth.buy_orders and depth.sell_orders:
                    best_bid = max(depth.buy_orders)
                    best_ask = min(depth.sell_orders)
                    market_price = (best_bid + best_ask) / 2
                    TTE = max(1, 7 - state.timestamp // 1000)  # Rough approximation
                    moneyness = np.log(strike / rock_price) / np.sqrt(TTE)
                    iv = implied_volatility(market_price, rock_price, strike, TTE)
                    if iv is not None:
                        traderDataOut['historical_data'].append({
                            'product': product,
                            'm': moneyness,
                            'iv': iv,
                            'strike': strike,
                            'S': rock_price,
                            'T': TTE,
                            'V': market_price
                        })

        # Only act when we have enough data
        data = traderDataOut['historical_data']
        if len(data) >= 20:
            m_vals = np.array([x['m'] for x in data])
            iv_vals = np.array([x['iv'] for x in data])
            coeffs = np.polyfit(m_vals, iv_vals, 2)

            def fitted_iv(m):
                return coeffs[0]*m**2 + coeffs[1]*m + coeffs[2]

            for product, strike in STRIKE_MAP.items():
                if product not in state.order_depths:
                    continue

                depth = state.order_depths[product]
                position = state.position.get(product, 0)
                position_limit = 200

                if depth.buy_orders and depth.sell_orders and rock_price:
                    best_bid = max(depth.buy_orders)
                    best_ask = min(depth.sell_orders)
                    market_price = (best_bid + best_ask) / 2
                    TTE = max(1, 7 - state.timestamp // 1000)
                    m = np.log(strike / rock_price) / np.sqrt(TTE)
                    theo_iv = fitted_iv(m)
                    theo_price = black_scholes_call_price(rock_price, strike, TTE, theo_iv)

                    # Buy if underpriced
                    if market_price < 0.95 * theo_price and position < position_limit:
                        orders_to_place.append(Order(product, best_ask, 5))

        # Compile results
        for order in orders_to_place:
            if order.symbol not in result:
                result[order.symbol] = []
            result[order.symbol].append(order)

        # Return order decisions
        return result, 0, jsonpickle.encode(traderDataOut)
