"""
By: LukeLab
Created on 09/20/2023
Version: 1.0
Last Modified: 09/27/2023

Major Updated: 04/04/2024, decision and order function furnish
Still in testing

updated: 04/09/2024, output formatting

The most basic core trading data and its strategy:
Price and volume

Abstract:
Long-only, swing trading strategy, using RSI indicator to determine the entry and exit point, using probability and
portfolio management to determine the position size and risk management.
"""
import time

# import talib
import yfinance as yf
from moomoo import *

# from TradingBOT import BOT_MAX_TRADING_LIMIT, ACCOUNT_CASH_THRESHOLD
from telegram_bot.telegram_notify import send_msg_to_telegram
from env._secrete import telegram_bot_token, telegram_chat_id
from strategy.Strategy import Strategy
import pandas_ta as pta
from utils import play_sound
from utils.dataIO import read_json_file, write_json_file, get_current_time, logging_info


class Your_Strategy(Strategy):
    """
    Class Name must be the same as the file name
    """

    def __init__(self, trader):
        super().__init__()
        self.strategy_name = "AlphaBets"
        self.trader = trader

        """⬇️⬇️⬇️ Strategy Settings ⬇️⬇️⬇️"""

        self.stock_tracking_list = ["SPY", "QQQ", "AAPL", "MSFT"]
        self.stock_trading_list = ["SPY", "QQQ"]

        # self.cash_balance = 0
        self.strategy_market_value = 0
        self.strategy_market_limit = 9999
        self.strategy_cash_threshold = 9999

        # set the trading settings for the strategy
        self.enable_buy = True
        self.enable_sell = True

        """⬆️⬆️⬆️ Strategy Settings ⬆️⬆️⬆️"""

        self.strategy_position = {}
        self.init_strategy_position()

        print(f"Strategy {self.strategy_name} initialized...")

    """ 
    You only need to define the strategy_decision() function below, and click run strategy button on the App.
    Other functions are defined in the parent class, Strategy.py, you can use them directly.
    Define your own strategy here:
    """

    def get_candles_frame(self, symbol, period, interval):
        """
        Fetches candle data for a given symbol using the moomoo API.

        :param symbol: The stock symbol to fetch data for.
        :param period: The number of periods to fetch.
        :param interval: The interval for each candle (e.g., '1d', '1h').
        :return: A DataFrame containing the candle data.
        """
        try:
            # Assuming moomooapi has a method to get historical data
            candles = self.trader.get_historical_data(symbol, period=period, interval=interval)
            # Convert the data to a DataFrame if needed
            df = pd.DataFrame(candles)
            return df
        except Exception as e:
            print(f"Error fetching candle data: {e}")
            return None

    def strategy_decision(self):
        print("Strategy Decision running...")

        dfstream = self.get_candles_frame("SPY", 70, "1d")
        if dfstream is None:
            print("Failed to retrieve candle data.")
            return

        signal = self.total_signal(dfstream, dfstream.index[-1], 7)  # current candle looking for open price entry

        slatr = self.slatrcoef * dfstream.ATR.iloc[-1]
        TPSLRatio = self.TPSLRatio_coef
        max_spread = 16e-5

        candle = self.get_candles(1)[-1]
        candle_open_bid = float(str(candle.bid.o))
        candle_open_ask = float(str(candle.ask.o))
        spread = candle_open_ask - candle_open_bid

        print(f"Signal: {signal}, Spread: {spread}, Opened Trades: {self.count_opened_trades()}")

        SLBuy = candle_open_bid - slatr - spread
        SLSell = candle_open_ask + slatr + spread

        TPBuy = candle_open_ask + slatr * TPSLRatio + spread
        TPSell = candle_open_bid - slatr * TPSLRatio - spread

        current_balance = self.get_account_balance()
        if current_balance < self.previous_balance:
            self.i += 1  # Increment 'i' on a loss
        else:
            self.i = 0

        # Determine whether to invert the signal logic
        if self.i == 1:  # If 'i' is odd, invert the trading logic
            signal = 3 - signal  # 1 becomes 2 (sell), and 2 becomes 1 (buy)

        self.previous_balance = current_balance
        self.last_signal = signal  # Store the last signal used

        # Sell
        if signal == 1 and self.count_opened_trades() == 0 and spread < max_spread:
            print("Sell Signal Found...")
            # Replace with moomoo API call for selling
            # Example: self.trader.sell("EUR_USD", self.lotsize, TPSell, SLSell)

        # Buy
        elif signal == 2 and self.count_opened_trades() == 0 and spread < max_spread:
            print("Buy Signal Found...")
            # Replace with moomoo API call for buying
            # Example: self.trader.buy("EUR_USD", self.lotsize, TPBuy, SLBuy)

        print("Strategy checked... Waiting next decision called...")
        print('-----------------------------------------------')

    """ ⬇️⬇️⬇️ Order and notification related functions ⬇️⬇️⬇️"""

    def init_strategy_position(self):
        position = read_json_file("strategy_position.json")
        if position:
            # stock_scope = [stock['name'] for stock in position]
            self.strategy_position = position
            for stock in self.stock_trading_list:
                self.strategy_market_value += self.strategy_position[stock]["market_value"]
        else:
            for stock in self.stock_tracking_list:
                self.strategy_position[stock] = {
                    "ticker": stock,
                    "quantity": 0,
                    "market_value": 0,
                    "price": 0,
                    "avg_price": 0,
                    "total_cost": 0,
                    "profit": 0,
                    "profit_percent": 0,
                }
            write_json_file("strategy_position.json", self.strategy_position)

    def save_trading_status(self, order_direction, stock, order_price, called_by):
        logging_info(f'{get_current_time()}: {order_direction}, {stock} @ ${order_price}, {called_by} \n')
        # send the message to telegram channel
        msg_body = ""
        msg_body += f"{order_direction}, {stock} @ ${order_price} \n"
        print(msg_body)
        # uncomment the code below if you need to send the notification to telegram
        send_msg_to_telegram(msg_body)

    def save_order_history(self, data, called_by):
        file_data = read_json_file("order_history.json")
        data_dict = data.to_dict()
        new_dict = {}
        for key, v in data_dict.items():
            new_dict[key] = v[0]
        new_dict['called_by'] = called_by
        logging_info(f'{self.strategy_name}: {str(new_dict)}')

        if file_data:
            file_data.append(new_dict)
        else:
            file_data = [new_dict]
        write_json_file("order_history.json", file_data)

    def update_strategy_position(self, action_res, stock, price, qty, order_direction):
        if action_res == "success":
            # stock = action_res["stock"]
            price = float(price)
            qty = int(qty)
            crt_order_value = round(price * qty, 2)
            # order_direction = action_res["order_direction"]
            if order_direction == "BUY":
                self.strategy_position[stock]["quantity"] += qty
                self.strategy_position[stock]["price"] = price
                self.strategy_position[stock]["market_value"] = round(self.strategy_position[stock]["quantity"] * price,
                                                                      2)
                self.strategy_position[stock]["total_cost"] += crt_order_value
                self.strategy_position[stock]["avg_price"] = round(
                    self.strategy_position[stock]["total_cost"] / self.strategy_position[stock]["quantity"], 2)

                self.strategy_position[stock]["profit"] = round(self.strategy_position[stock]["market_value"] - self.strategy_position[stock]["total_cost"], 2)

                self.strategy_position[stock]["profit_percent"] = round(
                    self.strategy_position[stock]["profit"] / self.strategy_position[stock]["total_cost"], 2)
                self.strategy_market_value += crt_order_value

            elif order_direction == "SELL":
                self.strategy_position[stock]["quantity"] -= qty
                self.strategy_position[stock]["price"] = price
                self.strategy_position[stock]["market_value"] = round(self.strategy_position[stock]["quantity"] * price,
                                                                      2)
                self.strategy_position[stock]["total_cost"] -= crt_order_value
                # self.strategy_position[stock]["avg_price"] = self.strategy_position[stock]["total_cost"] / self.strategy_position[stock]["quantity"]
                # in this method, no change for the avg price when sell
                self.strategy_position[stock]["profit"] = round(self.strategy_position[stock]["market_value"] - self.strategy_position[stock]["total_cost"], 2)

                self.strategy_position[stock]["profit_percent"] = round(
                    self.strategy_position[stock]["profit"] / self.strategy_position[stock]["total_cost"], 2)
                self.strategy_market_value -= crt_order_value
            else:
                print("wrong order direction")

            write_json_file("strategy_position.json", self.strategy_position)
