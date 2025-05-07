import csv
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict
from ibapi.order_condition import TimeCondition
import numpy as np
import pandas as pd
from ibapi.account_summary_tags import AccountSummaryTags
from ibapi.client import EClient
from ibapi.contract import *
from ibapi.execution import Execution
from ibapi.order import Order
from ibapi.wrapper import EWrapper
from ibapi.common import BarData, SetOfFloat, SetOfString
import pytz
from Config import Config
from Log import Log
from utils import nyTimeTools
from SymbolData import SymbolData


class Bot(EWrapper, EClient):

    def __init__(self, log: Log, config: Config, connect=False):
        # INITIALIZAZION # ----------------------------------------------------- #

        bot_version = 1.0
        EWrapper.__init__(self)
        EClient.__init__(self, self)

        # VARIABLES STRATEGY RELATED #

        # INTERNAL VARIABLES #
        self.trading_is_active = False
        self.option_chain_dict = {}
        self.stock_contracts = {}
        self.log = log
        self.CONNECTED = False
        self.i = config
        self.ID = 0
        self.temp_orderId = -1
        self.symbol_datas: Dict[str, SymbolData] = {}  # Symbol -> SymbolData()
        self.port = 0
        self.strike_list = None
        self.expiry_list = None
        self.delete_orders_list_of_contract = None
        self.delayed_data = False
        self.connection_failed = False
        self.pending_trades = {}
        self.trade_commissions = {}  # Store commissions by execution ID
        self.timer = None
        self.flag_test = True
        self.start_trading_time = nyTimeTools.createNyDatetime(
            self.i.START_TRADING_TIME
        )
        self.current_openorder_id = 999
        self.end_strategy_time = nyTimeTools.createNyDatetime(self.i.END_TRADING_TIME)
        self.nine_thirty_half = nyTimeTools.createNyDatetime("09:30:30")
        self.stop_thread = threading.Event()
        self.prices = []
        self.log_returns = []
        self.print_counter = 0
        self.trails_id = {"SOXS": None, "SOXL": None}
        self.closing_position_is_active = {"SOXS": False, "SOXL": False}

        self.ids_to_contract = {
            "hist": {},
            "live": {},
            "order": {},
            "contract": {},
            "other": {},
        }
        self.contract_to_ids = {
            "hist": {},
            "live": {},
            "order": {},
            "contract": {},
            "other": {},
        }

        # EVENTS() || id -> Event()

        self.historicalData_events = {}
        self.contractDetails_events = {}
        self.liveData_events = {}
        self.openOrders_events = {}
        self.option_events = {}
        self.account_summary = {}

    def start(self):
        self.port = 7496 if self.i.RUN_ON_REAL else 7497
        self.connect("127.0.0.1", self.port, 1)

        t = threading.Thread(target=self.run)
        t.start()
        time.sleep(1)

        self.reqIds(1)

        # Wait for IBKR's servers to answer back.
        while self.temp_orderId == -1:
            time.sleep(0.01)

        if not self.connection_failed:
            self.CONNECTED = True
            self.log.printAndLog("Bot connected to IBKR on port: " + str(self.port))
            self.log.printAndLog("")
            self.log.printAndLog("Running on real account: " + str(self.i.RUN_ON_REAL))

    def myRequest_currentPositions(self, contract_list: list):
        print()
        self.log.printAndLog("Checking if there is an active position on symbols.")
        self.temp_contract_list_for_pos_request = contract_list

        self.liveData_events[1234567] = threading.Event()

        self.reqPositions()

        self.liveData_events[1234567].wait()
        self.liveData_events[1234567].clear()
        del self.liveData_events[1234567]

        self.cancelPositions()

    def position(
        self, account: str, contract: Contract, position: float, avgCost: float
    ):

        for ct in self.temp_contract_list_for_pos_request:
            if contract.symbol == ct.symbol and contract.secType == ct.secType:

                for _, symboldata in self.symbol_datas.items():
                    if (
                        symboldata.contract.symbol == contract.symbol
                        and symboldata.contract.secType == contract.secType
                        and position != 0.0
                    ):
                        self.log.printAndLog(
                            f"Updating position of {contract.symbol} to: {position}"
                        )
                        symboldata.active_position = position

                        return

    def positionEnd(self):
        self.liveData_events[1234567].set()

    def writeTradeToCSV(self, trade_details):
        file_path = (
            f"TRADES/TRADES_{nyTimeTools.currentTimeInNy().strftime('%d%m%Y')}.csv"
        )

        # Check if TRADES directory exists, if not, create it
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Check if file exists and write headers if it does not
        file_exists = os.path.isfile(file_path)
        with open(file_path, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=trade_details.keys())
            if not file_exists:
                writer.writeheader()  # File doesn't exist, write a header
            writer.writerow(trade_details)  # Write the trade details

    def commissionReport(self, commissionReport):
        execId = commissionReport.execId
        commission = commissionReport.commission

        # If the execId is in pending_trades, update it with commission
        if execId in self.pending_trades:
            self.pending_trades[execId]["COMMISSIONS"] = commission
            self.writeTradeToCSV(self.pending_trades[execId])
            # Remove the trade from pending_trades as it's now complete
            del self.pending_trades[execId]

    def myRequest_deleteOrders(self, list_of_contracts):
        self.delete_orders_list_of_contract = [
            contract.conId for contract in list_of_contracts
        ]

        self.openOrders_events[self.current_openorder_id] = threading.Event()
        self.reqOpenOrders()
        self.openOrders_events[self.current_openorder_id].wait()
        del self.openOrders_events[self.current_openorder_id]
        self.current_openorder_id += 1

    def openOrder(self, orderId, contract: Contract, order: Order, orderState):

        if self.openOrders_events.get(self.current_openorder_id):
            if (
                contract.conId in self.delete_orders_list_of_contract
                and order.orderType == "TRAIL"
            ):
                self.log.debugAndLog(
                    f"{contract.symbol} -  Deleting TRAIL order if any."
                )
                self.cancelOrder(order.orderId)

    def openOrderEnd(self):
        if self.openOrders_events.get(self.current_openorder_id):
            self.openOrders_events.get(self.current_openorder_id).set()

    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        if contract.secType == "STK":
            try:
                symbol = self.ids_to_contract["order"][execution.orderId].symbol
            except:
                return

            # Update variables
            flag = self.symbol_datas[symbol].orders[execution.orderId]["flag"]

            self.symbol_datas[symbol].orders[execution.orderId][
                "filled"
            ] += execution.shares

            if execution.side == "BOT":
                self.symbol_datas[symbol].active_position += execution.shares
            else:
                self.symbol_datas[symbol].active_position -= execution.shares

            self.log.printAndLog(
                f'{symbol} - [Order ID: {execution.orderId}] - EXECUTION - Filled {flag} order: {self.symbol_datas[symbol].orders[execution.orderId]["filled"]}/'
                f'{self.symbol_datas[symbol].orders[execution.orderId]["order"].totalQuantity}. Avg Price: {execution.avgPrice}'
            )
            self.log.printAndLog(
                f"{symbol} - Current position: {self.symbol_datas[symbol].active_position}"
            )

            if flag == "SL_TRAIL":
                self.log.debugAndLog(f"Clearing SL_TRAIL ID.")
                self.trails_id[contract.symbol] = None

        partial_fill = self.symbol_datas[contract.symbol].orders[execution.orderId][
            "filled"
        ]

        tot_qty = (
            self.symbol_datas[contract.symbol]
            .orders[execution.orderId]["order"]
            .totalQuantity
        )

        if partial_fill == tot_qty:

            flag = self.symbol_datas[symbol].orders[execution.orderId]["flag"]
            if flag == "CLOSE":
                self.closing_position_is_active[symbol] = False

            symbol = contract.symbol
            fill_time = nyTimeTools.currentTimeInNy().strftime("%H:%M:%S")
            quantity = execution.shares
            avg_price = execution.avgPrice
            df_flag = flag

            self.pending_trades[execution.execId] = {
                "SYMBOL": symbol,
                "FILL_TIME": fill_time,
                "ACTION": execution.side,
                "QUANTITY": quantity,
                "AVG_PRICE": avg_price,
                "COMMISSIONS": 0,
                "FLAG": df_flag,
            }

    def myRequest_PlaceOrder(
        self,
        contract,
        order_type,
        order_action,
        qty,
        transmit=True,
        lmt_price=None,
        aux_price=None,
        parent_id=None,
        flag="",
        # Trailing-stop parameter (use if order_type == "TRAIL")
        trailing_percent=None,
        # Time condition parameters
        time_condition_type=None,  # can be "cancel", "trigger", or None
        time_condition_secs=0,
    ):

        # Create the IB Order
        order = Order()
        order.orderId = self.getNextOrderID(contract)

        if parent_id:
            order.parentId = parent_id

        order.action = order_action

        # Set the main prices
        if lmt_price is not None:
            order.lmtPrice = lmt_price
        if aux_price is not None:
            order.auxPrice = aux_price

        order.orderType = order_type
        order.totalQuantity = qty
        order.triggerMethod = 7  # default or your preference
        order.transmit = transmit

        # If it's a trailing stop
        if order_type.upper() == "TRAIL":
            if trailing_percent is None:
                raise ValueError(
                    "If order_type='TRAIL', you must provide trailing_percent."
                )
            order.trailingPercent = trailing_percent

            self.trails_id[contract.symbol] = order.orderId

        # Attempt eTradeOnly / firmQuoteOnly
        try:
            order.eTradeOnly = False
        except:
            pass
        try:
            order.firmQuoteOnly = False
        except:
            pass

        # ---- Add the order to your SymbolData tracking (STK vs OPT) ----
        if contract.secType == "STK":
            self.symbol_datas[contract.symbol].addOrder(order, flag)

        # ---- Time Condition logic (use US/Eastern for the time) ----
        if time_condition_type is not None and time_condition_secs > 0:
            eastern_tz = pytz.timezone("US/Eastern")
            now_eastern = datetime.now(eastern_tz)
            target_time = now_eastern + timedelta(seconds=time_condition_secs)

            tc = TimeCondition()
            # "IsMore=True" => triggers once 'current time' > 'target_time'
            tc.isMore = True
            tc.time = target_time.strftime("%Y%m%d %H:%M:%S US/Eastern")
            tc.isConjunctionConnection = True  # single condition => doesn't matter

            order.conditions = [tc]

            # If "cancel", TWS will cancel the unfilled portion after the condition is met.
            # If "trigger", TWS will *activate* this order after the condition is met.
            if time_condition_type == "cancel":
                order.conditionsCancelOrder = True
            else:  # e.g. "trigger"
                order.conditionsCancelOrder = False

        # ---- Logging output ----
        ct_string_identifier = (
            f"{contract.symbol}{contract.right}{contract.lastTradeDateOrContractMonth}"
        )

        if order_type in ["MKT", "LMT"]:
            self.log.printAndLog(
                f"{ct_string_identifier} - [Order ID: {order.orderId}] || "
                f"Placing {flag} {order_action} order with size {qty}"
            )
        elif order_type.upper() == "TRAIL":
            self.log.printAndLog(
                f"{ct_string_identifier} - [Order ID: {order.orderId}] || "
                f"Placing {flag} {order_action} TRAIL order with trailingPercent={trailing_percent} "
                f"and size {qty}"
            )
        else:
            price = lmt_price if lmt_price is not None else aux_price
            self.log.printAndLog(
                f"{ct_string_identifier} - [Order ID: {order.orderId}] || "
                f"Placing {flag} {order_action} {order_type} order at price: {price}, with size {qty}"
            )

        # ---- Place the order ----
        self.placeOrder(order.orderId, contract, order)

        return order

    def myRequest_fillContract(self, contracts, US_stock):
        self.stock_contracts = {}

        if not isinstance(contracts, list):
            contracts = [contracts]

        contract_details_ids = []

        for ct in contracts:

            if US_stock:
                ct.secType = "STK"
                ct.currency = "USD"
                ct.exchange = "SMART"

            if ct.secType == "STK":
                self.log.printAndLog(f"Filling contract for: {ct.symbol}")
            elif ct.secType in [
                "OPT",
                "FUT",
            ]:  # Assuming other types like 'OPT', 'FUT', etc.
                ct_string_identifier = (
                    f"{ct.symbol}{ct.right}{ct.lastTradeDateOrContractMonth}{ct.strike}"
                )
                ct_string_identifier.replace(" ", "")
                self.log.printAndLog(f"Filling contract for: {ct_string_identifier}")

            contract_details_id = self.getNewReqID(category="contract", contract=ct)
            self.contractDetails_events[contract_details_id] = threading.Event()
            self.reqContractDetails(contract_details_id, ct)
            contract_details_ids.append(contract_details_id)
            time.sleep(0.05)

        for id in contract_details_ids:
            self.contractDetails_events[id].wait()
            self.contractDetails_events[id].clear()
            del self.contractDetails_events[id]
            self.log.debugAndLog(f"Contract filled for: {self.stock_contracts.get(id)}")

        if len(contracts) == 1:
            return self.stock_contracts.get(contract_details_ids[0])
        else:
            return self.stock_contracts

    def contractDetails(self, reqId: int, cd: ContractDetails):
        self.stock_contracts[reqId] = cd.contract

    def contractDetailsEnd(self, reqId: int):
        self.contractDetails_events[reqId].set()

    def myRequest_HistoricalData(
        self, contract, query_time, time_amount, bar_string_size, only_rth, up_to_date
    ):
        temp_id = self.getNewReqID(category="hist", contract=contract)
        self.historicalData_events[temp_id] = threading.Event()
        self.reqHistoricalData(
            temp_id,
            contract,
            query_time,
            time_amount,
            bar_string_size,
            "TRADES",
            only_rth,
            1,
            up_to_date,
            [],
        )

        self.historicalData_events[temp_id].wait()
        self.historicalData_events[temp_id].clear()
        del self.historicalData_events[temp_id]

    def historicalData(self, reqId: int, bar: BarData):
        symbol = self.ids_to_contract["hist"][reqId].symbol
        self.symbol_datas[symbol].addHistoricalData(bar)
        self.symbol_datas[symbol].update_high_since_last_bullish()

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        self.historicalData_events[reqId].set()

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        symbol = self.ids_to_contract["hist"][reqId].symbol

        # Create a new row from the incoming bar datass
        new_row = {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "EMA_fast": None,
            "EMA_slow": None,
        }

        # Check if the DataFrame is not empty and the last row's date matches the bar's date
        if (
            len(self.symbol_datas[symbol].historical_data) >= 1
            and self.symbol_datas[symbol].historical_data.iloc[-1]["date"] == bar.date
        ):
            # Update the existing row at the bottom of the DataFrame
            self.symbol_datas[symbol].historical_data.iloc[-1] = new_row

        else:
            # BAR IS FORMED
            if not self.trading_is_active:
                self.trading_is_active = True

            self.symbol_datas[symbol].addHistoricalData(bar)

            completed_bar = self.symbol_datas[symbol].historical_data.iloc[-2]

            self.symbol_datas[symbol].update_high_since_last_bullish()

            # On new candle we call Callbacktrading
            if (
                self.start_trading_time
                < nyTimeTools.currentTimeInNy()
                < self.end_strategy_time
                and nyTimeTools.currentTimeInNy() > self.nine_thirty_half
            ):

                self.log.printAndLog(
                    f'{symbol} || NEW BAR  || {completed_bar["date"]} || O: {completed_bar["open"]}, H: {completed_bar["high"]}, '
                    f'L: {completed_bar["low"]}, C: {completed_bar["close"]}, EMA Fast: {completed_bar["EMA_fast"]:.3f}, EMA slow: {completed_bar["EMA_slow"]:.3f} || Current high from BULL cross: {self.symbol_datas[symbol].prev_high_since_last_bullish}'
                )

                self.print_counter += 1
                if self.print_counter % 2 == 0:
                    print()

                self.on_candle_formation(symbol)

    def close_position_if_any(self, symbol):
        position = self.symbol_datas[symbol].active_position
        contract = self.symbol_datas[symbol].contract

        if position != 0 and not self.closing_position_is_active[symbol]:
            self.closing_position_is_active[symbol] = True
            self.log.printAndLog(f"{symbol} - Closing positions and deleting orders.")
            # self.myRequest_deleteOrders([contract])
            order_action = "BUY" if position < 0 else "SELL"
            total_quantity = abs(position)

            order_id = self.trails_id[contract.symbol]

            if self.trails_id[contract.symbol] is not None:
                self.log.debugAndLog(f"Modifying TRAIL into MKT order.")

                if self.symbol_datas[contract.symbol].orders[order_id]["filled"] == 0:
                    self.cancelOrder(order_id)

                # ts_order: Order = self.symbol_datas[contract.symbol].orders[order_id][
                #     "order"
                # ]
                # # empty_order = Order()
                # # empty_order.orderId = ts_order
                # # empty_order.orderType = "MKT"
                # # empty_order.action = order_action
                # # empty_order.totalQuantity = total_quantity
                # # empty_order.transmit = True

                # # try:
                # #     empty_order.eTradeOnly = False
                # # except:
                # #     pass
                # # try:
                # #     empty_order.firmQuoteOnly = False
                # # except:
                # #     pass
                # # empty_order.triggerMethod = 7

                # ts_order.trailingPercent = -1

                # self.symbol_datas[contract.symbol].orders[order_id]["order"] = ts_order
                # self.placeOrder(ts_order.orderId, contract, ts_order)

                self.trails_id[contract.symbol] = None

            time.sleep(1)

            if self.symbol_datas[symbol].active_position == position:
                _ = self.myRequest_PlaceOrder(
                    contract,
                    "MKT",
                    order_action,
                    total_quantity,
                    transmit=True,
                    flag="CLOSE",
                )

    def place_buy_orders(self, symbol):

        position_size = (
            self.i.DOLLARS_PER_TRADE
            // self.symbol_datas[symbol].historical_data.iloc[-1]["close"]
        )

        # Go long
        parent_order = self.myRequest_PlaceOrder(
            contract=self.symbol_datas[symbol].contract,
            order_type="LMT",
            order_action="BUY",
            qty=position_size,
            transmit=False,
            lmt_price=round(
                1.09 * self.symbol_datas[symbol].historical_data.iloc[-1]["close"]
            ),
            flag="LONG_ENTRY",
        )

        # time.sleep(2.5)

        _ = self.myRequest_PlaceOrder(
            contract=self.symbol_datas[symbol].contract,
            order_type="TRAIL",
            order_action="SELL",
            qty=position_size,
            transmit=True,
            parent_id=parent_order.orderId,
            trailing_percent=self.i.TRAILING_STOP_PERCENTAGE,
            flag="SL_TRAIL",
        )

    # def on_candle_formation(self, symbol):
    #
    #     last_candle = self.symbol_datas[symbol].historical_data.iloc[-2]
    #
    #     if (
    #             self.symbol_datas[symbol].check_bearish_ema_crossover()
    #             or last_candle["EMA_fast"] < last_candle["EMA_slow"]
    #     ):
    #         self.close_position_if_any(symbol)
    #
    #     crossing_verified = self.symbol_datas[symbol].check_bullish_ema_crossover()
    #
    #     if crossing_verified:
    #     # if True and symbol == "SOXS":
    #         self.log.printAndLog(f"{symbol} - Bullish crossing verified.")
    #
    #         # If there is position on the other -> close it
    #         opposite_symbol = "SOXL" if symbol == "SOXS" else "SOXS"
    #         self.close_position_if_any(opposite_symbol)
    #
    #         # Proceed to place the order
    #         self.place_buy_orders(symbol)
    #
    #         return
    #
    #     # Consecutive buy trigger
    #     current_high_from_cross = self.symbol_datas[symbol].high_since_last_bullish
    #     last_candle_close = self.symbol_datas[symbol].historical_data.iloc[-2]["close"]
    #     if (
    #             self.i.REBUY_TRIGGER
    #             and current_high_from_cross is not None
    #             and self.symbol_datas[symbol].active_position == 0
    #             and last_candle_close > current_high_from_cross
    #     ):
    #         self.log.printAndLog(f'{symbol} - RE-TRIGGER BUY CONDITION VERIFIED. Current close: {last_candle_close}. High from BULL cross: {current_high_from_cross}')
    #         self.place_buy_orders(symbol)

    def on_candle_formation(self, symbol):
        last_candle = self.symbol_datas[symbol].historical_data.iloc[-2]

        # Close position if ema_fast < ema_slow
        if (
            last_candle["EMA_fast"] < last_candle["EMA_slow"]
            and self.symbol_datas[symbol].active_position != 0
        ):
            self.log.printAndLog(
                f'Curr EMA_fast: {last_candle["EMA_fast"]} < Curr EMA_slow: {last_candle["EMA_slow"]}'
            )
            self.close_position_if_any(symbol)
            return

        # Se non siamo in posizione, controlla il segnale bullish
        if self.symbol_datas[symbol].check_bullish_ema_crossover():
            # if symbol == "SOXS":
            self.log.printAndLog(f"# ------------------------ #")
            self.log.printAndLog(f"{symbol} - Bullish crossing verified.")
            prev_candle = self.symbol_datas[symbol].historical_data.iloc[-3]
            current_candle = self.symbol_datas[symbol].historical_data.iloc[-2]

            self.log.printAndLog(
                f'Prev EMA_fast: {prev_candle["EMA_fast"]} < Prev EMA_slow: {prev_candle["EMA_slow"]}'
            )

            self.log.printAndLog(
                f'Curr EMA_fast: {current_candle["EMA_fast"]} >= Curr EMA_slow: {current_candle["EMA_slow"]}'
            )

            # Se il simbolo opposto è in posizione, chiudila
            opposite_symbol = "SOXL" if symbol == "SOXS" else "SOXS"
            if self.symbol_datas[opposite_symbol].active_position != 0:
                self.close_position_if_any(opposite_symbol)

            self.place_buy_orders(symbol)

            self.log.printAndLog(f"# ------------------------ #")
            return

        # Controllo per eventuale riacquisto se abilitato
        current_high_from_cross = self.symbol_datas[symbol].prev_high_since_last_bullish
        last_candle_close = last_candle["close"]
        last_candle_high = last_candle["high"]
        if (
            self.i.REBUY_TRIGGER
            and current_high_from_cross is not None
            and last_candle_high >= current_high_from_cross
            and self.symbol_datas[symbol].active_position == 0
        ):
            self.log.printAndLog(f"# ------------------------ #")
            self.log.printAndLog(
                f"{symbol} - RE-TRIGGER BUY CONDITION VERIFIED. Current close: {last_candle_close}. High from BULL cross: {current_high_from_cross}"
            )
            self.place_buy_orders(symbol)
            self.log.printAndLog(f"# ------------------------ #")

    # DO NOT MODIFY # ---------------------------------------------------------------- #

    # Categories: 'hist' , 'live' , 'order' , 'contract' , 'other'
    def addMapping(self, category, reqId, contract: Contract):
        """Adds a two-way mapping between reqId and symbol"""

        self.ids_to_contract[category][reqId] = contract
        self.contract_to_ids[category][contract] = reqId

    def removeMapping(self, category, reqId=None, symbol=None):
        """Removes a two-way mapping. Can specify either reqId or symbol"""
        if reqId:
            symbol = self.ids_to_contract[category][reqId]
            del self.ids_to_contract[category][reqId]
            del self.contract_to_ids[category][symbol]
        elif symbol:
            reqId = self.contract_to_ids[category][symbol]
            del self.contract_to_ids[category][symbol]
            del self.ids_to_contract[category][reqId]

    def getNewReqID(self, category, contract: Contract):
        self.ID += 1
        self.addMapping(category, self.ID - 1, contract)
        return self.ID - 1

    def nextValidId(self, orderId: int):
        self.temp_orderId = orderId

    def getNextOrderID(self, contract: Contract):
        self.temp_orderId += 1
        self.addMapping("order", self.temp_orderId - 1, contract)
        return self.temp_orderId - 1

    def error(self, reqId, errorCode, errorString):

        if errorCode not in [
            2108,
            2168,
            2169,
            2108,
            399,
            2176,
            202,
            10147,
            10148,
            2104,
            1100,
            1102,
            10090,
            10167,
            504,
        ]:
            self.log.printAndLog(
                "Message: "
                + str(errorCode)
                + ", ID: "
                + str(reqId)
                + " => "
                + str(errorString)
            )

        else:
            if errorCode != 2176:
                self.log.debugAndLog(
                    "Message: "
                    + str(errorCode)
                    + ", ID: "
                    + str(reqId)
                    + " => "
                    + str(errorString)
                )

        if reqId in self.historicalData_events and errorCode != 2176:
            self.historicalData_events[reqId].set()

        if reqId in self.contractDetails_events:
            self.contractDetails_events[reqId].set()

        if errorCode == 504:
            self.log.printAndLog(f"[WARNING] Failed to connect to TWS")
            self.connection_failed = True
            self.temp_orderId = -99
