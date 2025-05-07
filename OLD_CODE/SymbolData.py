import pandas as pd
from ibapi.contract import *
from ibapi.order import Order
from ibapi.common import BarData
from Config import Config

i = Config(file_path="CONFIG.json")

FAST_EMA_PARAM = i.FAST_EMA_PARAMETER
SLOW_EMA_PARAM = i.SLOW_EMA_PARAMETER


class SymbolData:
    def __init__(self, symbol):
        self.symbol = symbol
        self.contract = None
        self.orders = {}
        self.active_position = 0
        self.historical_data = pd.DataFrame(
            columns=[
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "EMA_fast",
                "EMA_slow",
            ]
        )
        self.price = -1
        self.ask = -1
        self.bid = -1
        self.high_since_last_bullish = None
        self.prev_high_since_last_bullish = None  # New attribute

    def updateContract(self, contract):
        """Update contract information."""
        self.contract = contract

    def save_data_to_csv(self, file_name=None, directory=None):
        if file_name is None:
            file_name = self.symbol + ".csv"

        if directory is not None:
            file_name = directory + "/" + file_name

        self.historical_data.to_csv(file_name, index=False)

    def updateCurrentPrice(self, price):
        """Update the current price."""
        self.price = price

    def addOrder(self, order, flag):
        """Add an open order."""
        # [contract] [order_id] [order, flag -> '' | 'TP' | 'SL' OR PERSONALIZED, filled]
        self.orders[order.orderId] = {}
        self.orders[order.orderId]["order"] = order
        self.orders[order.orderId]["flag"] = flag
        self.orders[order.orderId]["filled"] = 0

    def updatePosition(self, quantity):
        """Update active position."""
        self.active_position += quantity

    def check_bearish_ema_crossover(self):
        # Verifica se ci sono almeno due candele con valori EMA validi
        if len(self.historical_data) < 3:
            return False

        # Ultima candela completata e la precedente
        prev_candle = self.historical_data.iloc[-3]
        current_candle = self.historical_data.iloc[-2]

        # Controlla il crossover ribassista: EMA_fast era sopra e ora è sotto EMA_slow
        if (
            prev_candle["EMA_fast"] > prev_candle["EMA_slow"]
            and current_candle["EMA_fast"] <= current_candle["EMA_slow"]
        ):
            return True

        return False

    def check_bullish_ema_crossover(self):
        # Verifica se ci sono almeno due candele con valori EMA validi
        if len(self.historical_data) < 3:
            return False

        # Ultima candela completata
        prev_candle = self.historical_data.iloc[-3]
        current_candle = self.historical_data.iloc[-2]

        # Controlla il crossover rialzista: EMA_fast era sotto e ora è sopra EMA_slow
        if (
            prev_candle["EMA_fast"] < prev_candle["EMA_slow"]
            and current_candle["EMA_fast"] >= current_candle["EMA_slow"]
        ):
            return True

        return False

    def addHistoricalData(self, bar: BarData):
        if bar.date not in self.historical_data["date"].values:
            new_row = pd.DataFrame(
                [
                    {
                        "date": bar.date,
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                        "EMA_fast": None,  # Placeholder
                        "EMA_slow": None,  # Placeholder
                    }
                ]
            )

            # Concatenare il nuovo dato al dataset esistente
            self.historical_data = pd.concat(
                [self.historical_data, new_row], ignore_index=True
            )

            # Calcolare EMA in modo incrementale
            if len(self.historical_data) >= 2:  # Evita errori con dataset vuoto
                self.historical_data.loc[:, "EMA_fast"] = (
                    self.historical_data["close"]
                    .ewm(span=FAST_EMA_PARAM, adjust=False)
                    .mean()
                    .round(6)
                )
                self.historical_data.loc[:, "EMA_slow"] = (
                    self.historical_data["close"]
                    .ewm(span=SLOW_EMA_PARAM, adjust=False)
                    .mean()
                    .round(6)
                )
            else:
                self.historical_data.iloc[
                    -1, self.historical_data.columns.get_loc("EMA_fast")
                ] = bar.close
                self.historical_data.iloc[
                    -1, self.historical_data.columns.get_loc("EMA_slow")
                ] = bar.close

    def update_high_since_last_bullish(self):
        if len(self.historical_data) < 3:
            return

        completed_candle = self.historical_data.iloc[-2]

        # Save previous value before any changes
        self.prev_high_since_last_bullish = self.high_since_last_bullish

        if completed_candle["EMA_fast"] < completed_candle["EMA_slow"]:
            self.high_since_last_bullish = None
        else:
            if self.check_bullish_ema_crossover():
                self.high_since_last_bullish = completed_candle["high"]
            else:
                if self.high_since_last_bullish is None:
                    self.high_since_last_bullish = completed_candle["high"]
                else:
                    self.high_since_last_bullish = max(
                        self.high_since_last_bullish, completed_candle["high"]
                    )
