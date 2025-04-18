from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle
import numpy as np

class Trader:
    def __init__(self):
        self.z_threshold = 0.4
        self.conversion_limit = 10
        self.position_limit = 75
        self.risk_factor = 0.1

        self.trailing_stop_pct = 0.3
        self.signal_fade_threshold = 0.1
        self.stop_loss = -300
        self.storage_cost = 0.1

        self.stats = {
            "market_long": {"mean": -30.876, "std": 454.717},
            "market_short": {"mean": -62.253, "std": 898.244},
            "conversion_long": {"mean": 2.100, "std": 50.524},
            "conversion_short": {"mean": -11.742, "std": 56.559},
        }

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        conversions = 0
        traderDataOut = {}

        product = "MAGNIFICENT_MACARONS"
        orders: List[Order] = []
        order_depth: OrderDepth = state.order_depths.get(product, OrderDepth())
        position = state.position.get(product, 0)

        open_trades = []
        cooldowns = {}
        if state.traderData:
            try:
                prior_data = jsonpickle.decode(state.traderData)
                open_trades = prior_data.get("open_trades", [])
                cooldowns = prior_data.get("cooldowns", {})
            except:
                open_trades = []
                cooldowns = {}

        # Clean expired cooldowns
        cooldowns = {k: v for k, v in cooldowns.items() if v > state.timestamp}

        obs = state.observations.conversionObservations.get(product)
        if not obs or not order_depth.sell_orders or not order_depth.buy_orders:
            return {}, 0, jsonpickle.encode({
                "open_trades": open_trades,
                "cooldowns": cooldowns
            })

        sugar = obs.sugarPrice
        sunlight = obs.sunlightIndex
        panic = 1 if sunlight <= 50 else 0
        import_tariff = obs.importTariff
        export_tariff = obs.exportTariff
        transport = obs.transportFees

        fair_value = (
            3.155351 * sugar - 1.499776 * sunlight + 499.0012 * panic
            - 1.649462 * sugar * panic - 2.887912 * sunlight * panic + 97.7277
        )

        conv_ask = obs.askPrice + import_tariff + transport
        conv_bid = obs.bidPrice - export_tariff - transport

        model_ask = (
            3.786397 * sugar - 1.363971 * sunlight - 28.70506 * import_tariff
            + 41.11547 * transport - 241.935 * panic + 1.766829 * sugar * panic
            - 2.391809 * sunlight * panic - 202.7528
        )

        model_bid = (
            4.506189 * sugar - 2.063251 * sunlight - 6.822738 * export_tariff
            + 57.85397 * transport + 655.1511 * panic - 2.422644 * sugar * panic
            - 2.622453 * sunlight * panic - 169.2709
        )

        best_ask = min(order_depth.sell_orders.keys(), default=None)
        best_bid = max(order_depth.buy_orders.keys(), default=None)
        if best_ask is None or best_bid is None:
            return {}, 0, jsonpickle.encode({
                "open_trades": open_trades,
                "cooldowns": cooldowns
            })

        ask_vol = order_depth.sell_orders[best_ask]
        bid_vol = order_depth.buy_orders[best_bid]

        raw_signals = {
            "market_long": (fair_value - best_ask) * ask_vol,
            "market_short": (best_bid - fair_value) * bid_vol,
            "conversion_long": model_ask - obs.askPrice,
            "conversion_short": obs.bidPrice - model_bid,
        }

        z_signals = {
            k: (v - self.stats[k]["mean"]) / self.stats[k]["std"]
            for k, v in raw_signals.items()
        }

        best_signal = max(z_signals, key=z_signals.get)
        signal_value = z_signals[best_signal]

        new_open_trades = []
        for trade in open_trades:
            direction = trade["dir"]
            qty = trade["qty"]
            entry_px = trade["entry"]
            age = state.timestamp - trade["entry_ts"]
            peak_pnl = trade.get("peak_pnl", 0.0)
            signal_key = trade.get("signal_key", "market_long")
            signal_now = z_signals.get(signal_key, 0)
            current_px = best_bid if direction == "long" else best_ask
            pnl = (current_px - entry_px) * qty if direction == "long" else (entry_px - current_px) * qty
            peak_pnl = max(peak_pnl, pnl)
            trade["peak_pnl"] = peak_pnl

            exit = False

            if signal_key.startswith("conversion"):
                conversion_stop = -15 * qty
                if pnl < conversion_stop or signal_now < self.signal_fade_threshold:
                    exit = True
            else:
                if direction == "long":
                    adjusted_stop = self.stop_loss + (age * self.storage_cost * qty)
                    if pnl < adjusted_stop:
                        exit = True
                else:
                    if pnl < self.stop_loss:
                        exit = True

                if peak_pnl > 0 and pnl < peak_pnl * (1 - self.trailing_stop_pct):
                    exit = True
                elif signal_now < self.signal_fade_threshold:
                    exit = True

            if exit:
                exit_px = best_bid if direction == "long" else best_ask
                orders.append(Order(product, exit_px, -qty if direction == "long" else qty))
                position -= qty if direction == "long" else -qty
                # cooldown that signal key
                cooldowns[signal_key] = state.timestamp + 5000
            else:
                new_open_trades.append(trade)

        # === Entry Logic ===
        if signal_value > self.z_threshold:
            # Respect per-signal cooldown
            if best_signal in cooldowns and cooldowns[best_signal] > state.timestamp:
                traderDataOut["open_trades"] = new_open_trades
                traderDataOut["cooldowns"] = cooldowns
                return {product: orders}, conversions, jsonpickle.encode(traderDataOut)

            z_abs = abs(signal_value)
            raw_size = max(1, int(z_abs * self.position_limit * self.risk_factor))

            if best_signal == "market_long" and position < self.position_limit:
                size = min(raw_size, ask_vol, self.position_limit - position)
                if size > 0:
                    orders.append(Order(product, best_ask, size))
                    new_open_trades.append({
                        "dir": "long", "entry": best_ask, "qty": size,
                        "entry_ts": state.timestamp, "peak_pnl": 0.0, "signal_key": best_signal
                    })
                    position += size

            elif best_signal == "market_short" and position > -self.position_limit:
                size = min(raw_size, bid_vol, position + self.position_limit)
                if size > 0:
                    orders.append(Order(product, best_bid, -size))
                    new_open_trades.append({
                        "dir": "short", "entry": best_bid, "qty": size,
                        "entry_ts": state.timestamp, "peak_pnl": 0.0, "signal_key": best_signal
                    })
                    position -= size

            elif best_signal == "conversion_long" and position < self.position_limit:
                size = min(raw_size, self.conversion_limit, self.position_limit - position)
                if size > 0:
                    conversions = size
                    new_open_trades.append({
                        "dir": "long", "entry": conv_ask, "qty": size,
                        "entry_ts": state.timestamp, "peak_pnl": 0.0, "signal_key": best_signal
                    })
                    position += size

            elif best_signal == "conversion_short" and position > -self.position_limit:
                size = min(raw_size, self.conversion_limit, position + self.position_limit)
                if size > 0:
                    conversions = -size
                    new_open_trades.append({
                        "dir": "short", "entry": conv_bid, "qty": size,
                        "entry_ts": state.timestamp, "peak_pnl": 0.0, "signal_key": best_signal
                    })
                    position -= size

        traderDataOut["open_trades"] = new_open_trades
        traderDataOut["cooldowns"] = cooldowns
        return {product: orders}, conversions, jsonpickle.encode(traderDataOut)