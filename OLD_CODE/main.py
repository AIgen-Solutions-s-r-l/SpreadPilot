import os
import socket
import time

import numpy as np
import requests
from requests import RequestException
from ibapi.contract import *
from Bot import Bot
from Config import Config
from ConnectionMonitor import ConnectionMonitor
from Log import Log
from SymbolData import SymbolData
from utils import *

import warnings


DEBUG = True

# Ignore all FutureWarnings
warnings.simplefilter(action="ignore", category=FutureWarning)
i = Config(file_path="CONFIG.json")

hostname = socket.gethostname()
delayed_data = False

# Directory for storing trade files
trades_dir = "TRADES"

# Check if the directory exists, if not, create it
if not os.path.exists(trades_dir):
    os.makedirs(trades_dir)

market_open_time = nyTimeTools.createNyDatetime("9:30:00")
market_closing_time = nyTimeTools.createNyDatetime("16:29:30")
end_strategy_time = nyTimeTools.createNyDatetime(i.END_TRADING_TIME)
start_strategy_time = nyTimeTools.createNyDatetime(i.START_TRADING_TIME)

logger = Log(debug=DEBUG)

logger.printAndLog("For any question contact me: julianvene@gmail.com")
TEST_DISCONNECTION = False


def execution_main_body(bot: Bot):

    # - # - # - # - # - # - # - # - # - # - #
    # START OF THE EXECUTION - TRADING LOGIC GOES HERE
    # - # - # - # - # - # - # - # - # - # - #

    # # Fill contract
    symbols = ["SOXS", "SOXL"]
    contracts = []
    for symbol in symbols:
        contract = Contract()
        contract.symbol = symbol
        contract = bot.myRequest_fillContract(contract, US_stock=True)

        bot.symbol_datas[contract.symbol] = SymbolData(contract.symbol)
        bot.symbol_datas[contract.symbol].updateContract(contract)

        contracts.append(contract)

    # Get current position
    bot.myRequest_currentPositions(contracts)

    if nyTimeTools.currentTimeInNy() < market_open_time:
        logger.printAndLog("Waiting for the market to open.")
        nyTimeTools.waitTillTime(market_open_time)

    time.sleep(2)
    query_time = ""

    for contract in contracts:
        logger.printAndLog(f"{contract.symbol} - Requesting historical bars.")
        time_amount = i.calculate_time_amount()
        bot.myRequest_HistoricalData(
            contract=contract,
            query_time=query_time,
            time_amount=time_amount,
            bar_string_size=i.BAR_PERIOD,
            only_rth=True,
            up_to_date=True,
        )

    time.sleep(2)
    print()

    # Se siamo già in posizione, controlla solo se c'è bisogno di uscire
    for contract in contracts:
        symbol = contract.symbol
        last_candle = bot.symbol_datas[symbol].historical_data.iloc[-2]
        if bot.symbol_datas[symbol].active_position != 0:
            if (
                bot.symbol_datas[symbol].check_bearish_ema_crossover()
                or last_candle["EMA_fast"] < last_candle["EMA_slow"]
            ):
                bot.close_position_if_any(symbol)

    logger.printAndLog("CONNECTION ARE SET UP.")
    print()

    return True


# Ignore following function
def run_bot():
    logger.debugAndLog(f"run_bot executed.")

    new_bot_instance = Bot(logger, config=i)

    # Start connection
    logger.printAndLog(f"Connecting now to TWS")
    new_bot_instance.start()

    if delayed_data:
        new_bot_instance.delayed_data = True
        new_bot_instance.reqMarketDataType(3)

    all_good = execution_main_body(new_bot_instance)

    if not all_good:
        sys.exit()

    while (
        connection_monitor.connectionStatus()
        and nyTimeTools.currentTimeInNy() < end_strategy_time
        and nyTimeTools.currentTimeInNy() < market_closing_time
    ):
        time.sleep(0.5)

    return (
        not connection_monitor.connectionStatus(),
        new_bot_instance.connection_failed,
        new_bot_instance,
    )


if __name__ == "__main__":

    backup_bot = None
    disconnection_time = None
    print("\n\n")

    # Execute MonitorConnection
    connection_monitor = ConnectionMonitor(
        logger,
        forced_wait=1,
        disconnection_threshold=5,
    )

    connection_monitor.waitConnectionBack()
    connection_monitor.start()
    time.sleep(1)

    connection_lost, connection_failed, bot = run_bot()

    connection_monitor.stop()
    if connection_lost or connection_failed:
        logger.printAndLog(
            "[WARNING] Connection lost. Restart manually the bot for resuming operations"
        )

        connection_monitor.stop()
        bot.disconnect()
        end_operations()

    else:

        # - # - # - # - # - # - # - # - # - # - #
        # END OF DAY - TRADING LOGIC GOES HERE
        # - # - # - # - # - # - # - # - # - # - #
        logger.printAndLog(f"END OF TRADING DAY reached.")

        # Delete orders
        if i.CLOSE_POSITION_AT_EOD:
            logger.printAndLog(f"Proceeding to close position and delete orders.")

            contract1 = bot.symbol_datas["SOXS"].contract
            contract2 = bot.symbol_datas["SOXL"].contract

            # Close positions
            end_of_day_operations = {
                contract1: bot.symbol_datas[contract1.symbol].active_position,
                contract2: bot.symbol_datas[contract2.symbol].active_position,
            }

            for contract, position in end_of_day_operations.items():
                if position != 0:
                    order_action = "BUY" if position < 0 else "SELL"
                    total_quantity = abs(position)

                    _ = bot.myRequest_PlaceOrder(
                        contract, "MKT", order_action, total_quantity
                    )

            time.sleep(5)
            bot.myRequest_deleteOrders([contract1, contract2])

        timer = datetime.now() + timedelta(seconds=7.5)

        while datetime.now() < timer:
            time.sleep(0.5)

        bot.disconnect()
        bot.log.printAndLog(f"Bot is now disconnected.")

        time.sleep(2)
        del bot
        del connection_monitor

        input("You can now close the bot...")
        sys.exit()
