
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import numpy as np
import jsonpickle
import math

STRIKE_MAP = {
    "VOLCANIC_ROCK_VOUCHER_9500": 9500,
    "VOLCANIC_ROCK_VOUCHER_9750": 9750,
    "VOLCANIC_ROCK_VOUCHER_10000": 10000,
    "VOLCANIC_ROCK_VOUCHER_10250": 10250,
    "VOLCANIC_ROCK_VOUCHER_10500": 10500,
}

MAX_HISTORY = 60
MIN_CONFIDENCE = 0.06
MAX_UNREALIZED_LOSS = 750
MAX_HOLD_TICKS = 4000
MAX_TRADE_QTY = 5
ROCK_HISTORY = 30
ROCK_TRADE_QTY = 10
ROCK_LIMIT = 30

def normal_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_call(S, K, T, sigma):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0)
    d1 = (math.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * normal_cdf(d1) - K * normal_cdf(d2)

def approximate_iv(C_market, S, K, T):
    if T <= 0 or C_market < max(S - K, 0):
        return None
    low, high = 0.01, 2.0
    for _ in range(20):
        mid = (low + high) / 2
        price = black_scholes_call(S, K, T, mid)
        if price > C_market:
            high = mid
        else:
            low = mid
    return (low + high) / 2

def compute_rock_momentum(prices):
    if len(prices) < 5:
        return 0
    x = np.arange(len(prices))
    y = np.array(prices)
    slope, _ = np.polyfit(x, y, 1)
    return slope

class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        traderDataOut = {}

        if state.traderData:
            try:
                traderDataOut = jsonpickle.decode(state.traderData)
            except:
                traderDataOut = {}

        traderDataOut.setdefault("historical_data", [])
        traderDataOut.setdefault("rock_prices", [])
        traderDataOut.setdefault("entry_book", {})

        orders_to_place = []
        rock_price = None

        if "VOLCANIC_ROCK" in state.order_depths:
            rock_depth = state.order_depths["VOLCANIC_ROCK"]
            if rock_depth.buy_orders and rock_depth.sell_orders:
                best_bid = max(rock_depth.buy_orders)
                best_ask = min(rock_depth.sell_orders)
                rock_price = (best_bid + best_ask) / 2
                traderDataOut["rock_prices"].append(rock_price)
                if len(traderDataOut["rock_prices"]) > ROCK_HISTORY:
                    traderDataOut["rock_prices"] = traderDataOut["rock_prices"][-ROCK_HISTORY:]

                rock_ma = np.mean(traderDataOut["rock_prices"])
                rock_pos = state.position.get("VOLCANIC_ROCK", 0)
                if rock_price < 0.985 * rock_ma and rock_pos + ROCK_TRADE_QTY <= ROCK_LIMIT:
                    orders_to_place.append(Order("VOLCANIC_ROCK", best_ask, ROCK_TRADE_QTY))
                elif rock_price > 1.015 * rock_ma and rock_pos - ROCK_TRADE_QTY >= -ROCK_LIMIT:
                    orders_to_place.append(Order("VOLCANIC_ROCK", best_bid, -ROCK_TRADE_QTY))

        momentum = compute_rock_momentum(traderDataOut["rock_prices"]) if traderDataOut["rock_prices"] else 0

        if rock_price is not None:
            for product, strike in STRIKE_MAP.items():
                if product not in state.order_depths:
                    continue
                depth = state.order_depths[product]
                if depth.buy_orders and depth.sell_orders:
                    best_bid = max(depth.buy_orders)
                    best_ask = min(depth.sell_orders)
                    market_price = (best_bid + best_ask) / 2
                    TTE = max(1, 7 - state.timestamp // 1000)
                    if TTE <= 2:
                        continue
                    m = math.log(strike / rock_price) / math.sqrt(TTE)
                    iv = approximate_iv(market_price, rock_price, strike, TTE)
                    if iv is None:
                        continue
                    traderDataOut["historical_data"].append({
                        "product": product,
                        "m": m,
                        "iv": iv,
                        "strike": strike,
                        "S": rock_price,
                        "T": TTE,
                        "V": market_price
                    })

        if len(traderDataOut["historical_data"]) > MAX_HISTORY:
            traderDataOut["historical_data"] = traderDataOut["historical_data"][-MAX_HISTORY:]

        data = traderDataOut["historical_data"]
        if len(data) >= 20:
            m_vals = np.array([x["m"] for x in data])
            iv_vals = np.array([x["iv"] for x in data])
            weights = np.linspace(0.1, 1.0, len(iv_vals))
            coeffs = np.polyfit(m_vals, iv_vals, 2, w=weights)

            def fitted_iv(m):
                return coeffs[0] * m ** 2 + coeffs[1] * m + coeffs[2]

            for product, strike in STRIKE_MAP.items():
                if product not in state.order_depths:
                    continue
                depth = state.order_depths[product]
                position = state.position.get(product, 0)
                position_limit = 200
                best_bid = max(depth.buy_orders)
                best_ask = min(depth.sell_orders)
                market_price = (best_bid + best_ask) / 2
                TTE = max(1, 7 - state.timestamp // 1000)
                m = math.log(strike / rock_price) / math.sqrt(TTE)
                theo_iv = fitted_iv(m)
                theo_price = black_scholes_call(rock_price, strike, TTE, theo_iv)
                mispricing = theo_price - market_price
                confidence = abs(mispricing) / theo_price if theo_price > 0 else 0

                if confidence < MIN_CONFIDENCE:
                    continue

                qty = min(MAX_TRADE_QTY, max(1, int(confidence * MAX_TRADE_QTY)))

                if mispricing > 0 and position + qty <= position_limit:
                    bias_boost = 1.5 if momentum > 0.1 else 1.0
                    orders_to_place.append(Order(product, best_ask, int(qty * bias_boost)))
                    traderDataOut["entry_book"][product] = {"price": market_price, "timestamp": state.timestamp}
                elif mispricing < 0 and position - qty >= -position_limit:
                    bias_boost = 1.5 if momentum < -0.1 else 1.0
                    orders_to_place.append(Order(product, best_bid, -int(qty * bias_boost)))
                    traderDataOut["entry_book"][product] = {"price": market_price, "timestamp": state.timestamp}

        for order in orders_to_place:
            if order.symbol not in result:
                result[order.symbol] = []
            result[order.symbol].append(order)

        return result, 0, jsonpickle.encode(traderDataOut)
