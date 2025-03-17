import random
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime

# Global variables
summary_output = ""
exchange1_prices = []
exchange2_prices = []
time_points = []
trade_executed_flags = []
cumulative_profits = []

# Exchange API endpoints
EXCHANGE_APIS = {
    "Binance": "https://api.binance.com/api/v3/ticker/price?symbol=",
    "Coinbase": "https://api.coinbase.com/v2/prices/",
    "Kraken": "https://api.kraken.com/0/public/Ticker?pair=",
    "Bitfinex": "https://api-pub.bitfinex.com/v2/ticker/t"
}

# Helper function to adjust Binance trading pairs
def format_binance_pair(trading_pair):
    base, quote = trading_pair.split("/")
    if quote == "USD":
        quote = "USDT"  # Binance primarily uses USDT
    return f"{base}{quote}"  # Binance API format (e.g., XRPUSDT)

# Modified random walk to attempt to replicate asset price movements over very short periods of just a few seconds
class ShortTermPriceSimulator:
    def __init__(self,
                 starting_price=10,
                 volatility=0.06,
                 mean_reversion=0.01,
                 oscillation_amplitude=0.05,
                 oscillation_period=15,
                 divergence_factor=0.1):
        self.current_price = starting_price
        self.base_price = starting_price
        self.volatility = volatility  # Exaggerated volatility for short timeframes
        self.mean_reversion = mean_reversion  # Strength of pull back to base price
        self.oscillation_amplitude = oscillation_amplitude  # Size of cyclic movements
        self.oscillation_period = oscillation_period  # Length of cycle in seconds
        self.divergence_factor = divergence_factor  # How strongly this exchange diverges from the other
        self.shock_probability = 0.05  # % chance of price shock each second - we define this here since price shocks should affect both exchanges equally (macro factor)
        self.time_counter = 0  # Counter to track time for oscillations

    def next_price(self, other_price=None):
        self.time_counter += 1

        # Random component (larger for short timeframes)
        random_change = random.normalvariate(0, 1) * self.volatility

        # Mean reversion component (pulls price back toward base_price)
        reversion = self.mean_reversion * (self.base_price - self.current_price) / self.base_price

        # Oscillation component (creates cyclic movements)
        oscillation = self.oscillation_amplitude * np.sin(2 * np.pi * self.time_counter / self.oscillation_period)

        # Occasional price shocks
        shock = 0
        if random.random() < self.shock_probability:
            shock = random.choice([-1, 1]) * random.uniform(0.2, 0.7)

        # Divergence from other exchange - optional
        divergence = 0
        if other_price is not None:
            # Occasionally create deliberate divergence from other exchange
            if random.random() < 0.1:  # 10% chance to start diverging
                divergence = self.divergence_factor * (self.current_price - other_price) / self.current_price

        # Calculate total percentage change
        total_change = random_change + reversion + oscillation + shock + divergence

        # Apply change to current price
        self.current_price *= (1 + total_change)

        # Ensure price doesn't go negative or explode
        self.current_price = max(self.current_price, self.base_price * 0.7)
        self.current_price = min(self.current_price, self.base_price * 1.3)

        return round(self.current_price, 4)

# Function to fetch market data or simulate it
def get_price(exchange, trading_pair, simulate_data, simulators={}, last_prices={}):
    if simulate_data:
        # Create simulator for this exchange if it doesn't exist
        key = f"{exchange}_{trading_pair}"
        if key not in simulators:
            # Base price with slight variation
            base_price = 10  # use 10 to make it very obvious when simulated data is being used vs real (XRP/USD ~ 2.50 as of Mar 25)

            # Different parameters for different exchanges
            if exchange == exchange1:  # First exchange
                starting_price = base_price * random.uniform(0.98, 1.02)
                volatility = random.uniform(0.02, 0.04)
                mean_reversion = random.uniform(0.05, 0.1)
                oscillation_amplitude = random.uniform(0.01, 0.02)
                oscillation_period = random.randint(5, 25)  # Seconds
                divergence_factor = random.uniform(0.01, 0.03)
            else:  # Second exchange
                starting_price = base_price * random.uniform(0.97, 1.03)  # Slightly more variance
                volatility = random.uniform(0.03, 0.06)  # Higher volatility
                mean_reversion = random.uniform(0.04, 0.08)  # Less mean reversion
                oscillation_amplitude = random.uniform(0.015, 0.025)  # Larger oscillations
                oscillation_period = random.randint(5, 25)
                divergence_factor = random.uniform(0.01, 0.04)

            simulators[key] = ShortTermPriceSimulator(
                starting_price,
                volatility,
                mean_reversion,
                oscillation_amplitude,
                oscillation_period,
                divergence_factor
            )

        # Get other exchange's last price if available for coordinated movements
        other_price = None
        other_exchange = exchange2 if exchange == exchange1 else exchange1
        other_key = f"{other_exchange}_{trading_pair}"
        if other_key in last_prices:
            other_price = last_prices[other_key]

        # Get new price
        new_price = simulators[key].next_price(other_price)

        # Store this price for reference by other exchange
        last_prices[key] = new_price

        return new_price
    else:
        try:
            if exchange == "Binance":
                symbol = format_binance_pair(trading_pair)
                response = requests.get(EXCHANGE_APIS["Binance"] + symbol)
                return float(response.json()["price"])

            elif exchange == "Coinbase":
                response = requests.get(EXCHANGE_APIS["Coinbase"] + f"{trading_pair.replace('/', '-')}/spot")
                return float(response.json()["data"]["amount"])

            elif exchange == "Kraken":
                response = requests.get(EXCHANGE_APIS["Kraken"] + trading_pair.replace("/", ""))
                result = list(response.json()["result"].values())[0]
                return float(result["c"][0])  # Closing price

            elif exchange == "Bitfinex":
                response = requests.get(EXCHANGE_APIS["Bitfinex"] + f"{trading_pair.replace('/', '')}")
                return float(response.json()[6])  # Last price

            else:
                log_message(log_file, f"Exchange {exchange} not supported.")
                return None
        except Exception as e:
            log_message(log_file, f"Error fetching price from {exchange}: {str(e)}")
            return None

# Function to simulate trade execution - here we simply print what should happen (no real execution logic)
def execute_trade(action, exchange, trading_pair, price, amount):
    trade_msg = f"{action} {amount:.4f} of {trading_pair} at {exchange} for ${price:.4f}"
    log_message(log_file, trade_msg)
    return trade_msg

# Function to save trade data as CSV
def save_trade_data(data_file):
    global time_points, exchange1_prices, exchange2_prices, trade_executed_flags, cumulative_profits

    # Create a DataFrame with the trading data
    trade_data_df = pd.DataFrame({
        'Time': time_points,
        'Exchange1_Price': exchange1_prices,
        'Exchange2_Price': exchange2_prices,
        'Trade_Executed': trade_executed_flags,
        'Cumulative_Profit': cumulative_profits
    })

    # Save to CSV with timestamp
    trade_data_df.to_csv(data_file, index=False)

# Convert duration to seconds so user doesn't need to do this - they can just specify the time unit
def convert_to_seconds(duration, unit):
    if unit == "seconds":
        return duration
    elif unit == "minutes":
        return duration * 60
    elif unit == "hours":
        return duration * 3600
    elif unit == "days":
        return duration * 86400
    return duration  # Default to seconds

# Arbitrage trading logic
def arbitrage_bot(initial_capital, arbitrage_threshold, trading_session_duration, duration_unit, exchange1, exchange2, trading_pair, simulate_data, data_file, log_file):
    global summary_output, time_points, exchange1_prices, exchange2_prices, trade_executed_flags, cumulative_profits

    # Initialize trade_summary with a default value
    trade_summary = "No arbitrage opportunities found."

    # Clear log file
    with open(log_file, "w") as f:
        f.write(f"Starting new trading session with {initial_capital} USD\n")

    log_message(log_file, f"Starting trading bot: {exchange1} vs {exchange2} for {trading_pair}")
    log_message(log_file, f"Initial capital: ${initial_capital}, Threshold: {arbitrage_threshold}%")
    log_message(log_file, f"Trading duration: {trading_session_duration} {duration_unit} ({convert_to_seconds(trading_session_duration, duration_unit)} seconds)")

    capital = initial_capital
    start_capital = initial_capital
    start_time = time.time()

    trades = []
    profits = 0
    trade_count = 0

    # Create price simulators and last prices dictionaries
    simulators = {}
    last_prices = {}

    # Loop for the duration of trading session
    elapsed = 0
    while elapsed < convert_to_seconds(trading_session_duration, duration_unit):
        current_time = time.time()
        elapsed = current_time - start_time

        # Get prices from exchanges - using our enhanced simulators if simulate_data is True
        price1 = get_price(exchange1, trading_pair, simulate_data, simulators, last_prices)
        price2 = get_price(exchange2, trading_pair, simulate_data, simulators, last_prices)

        if price1 is None or price2 is None:
            log_message(log_file, f"Could not fetch price from one or both exchanges. {exchange1}: {price1}, {exchange2}: {price2}")
            time.sleep(1)
            continue

        # Calculate price difference
        price_diff = abs(price1 - price2)
        avg_price = (price1 + price2) / 2
        percentage_diff = (price_diff / avg_price) * 100

        # Log the price comparison
        log_message(log_file, f"Time: {elapsed:.1f}s - {exchange1}: ${price1:.4f}, {exchange2}: ${price2:.4f}, Diff: ${price_diff:.4f} ({percentage_diff:.2f}%)")

        # Record data for visualisation
        time_points.append(elapsed)
        exchange1_prices.append(price1)
        exchange2_prices.append(price2)
        cumulative_profits.append(profits)  # Track cumulative profit at each time point

        # Check if arbitrage opportunity exists
        trade_executed = "No"
        if percentage_diff > arbitrage_threshold:
            trade_profit = 0
            if price1 < price2:
                buy_price = price1
                sell_price = price2
                buy_exchange = exchange1
                sell_exchange = exchange2
            else:
                buy_price = price2
                sell_price = price1
                buy_exchange = exchange2
                sell_exchange = exchange1

            # Calculate potential profit
            amount = capital / buy_price
            trade_profit = (sell_price - buy_price) * amount

            # Execute trades
            buy_msg = execute_trade("BUY", buy_exchange, trading_pair, buy_price, amount)
            sell_msg = execute_trade("SELL", sell_exchange, trading_pair, sell_price, amount)

            # Update capital
            capital += trade_profit
            profits += trade_profit
            trade_count += 1

            # Record trade
            trade_summary = f"[Time: {elapsed:.1f}s] ARBITRAGE OPPORTUNITY: {buy_exchange}(${buy_price:.4f}) -> {sell_exchange}(${sell_price:.4f}), Diff: ${price_diff:.4f} ({percentage_diff:.2f}%), Units: {amount:.4f}, Profit: ${trade_profit:.2f}, Capital: ${capital:.2f}"
            trades.append(trade_summary)
            log_message(log_file, trade_summary)

            trade_executed = "Yes"
            cumulative_profits[-1] = profits  # Update the latest cumulative profit

        trade_executed_flags.append(trade_executed)

        # Save data after each iteration for real time updates
        save_trade_data(data_file)

        # Sleep to avoid overwhelming the system - shorter interval more responsive for real time
        time.sleep(1)

    # Create summary
    final_profit_percent = ((capital - start_capital) / start_capital) * 100

    summary_lines = [
        f"Trading Complete: {exchange1} vs {exchange2} for {trading_pair}",
        f"Initial Capital: ${start_capital:.2f}",
        f"Final Capital: ${capital:.2f}",
        f"Total Profit: ${profits:.2f} ({final_profit_percent:.2f}%)",
        f"Number of Trades: {trade_count}",
        f"Trading Duration: {trading_session_duration} {duration_unit} ({convert_to_seconds(trading_session_duration, duration_unit)} seconds)"
    ]

    if trades:
        summary_lines.append("\nTrade Details:")
        summary_lines.extend(trades)
    else:
        summary_lines.append("\nNo arbitrage opportunities found.")

    summary_output = "\n".join(summary_lines)
    log_message(log_file, "Trading session ended.")
    log_message(log_file, summary_output)

    # Final save of trade data
    save_trade_data(data_file)

    return summary_output

# Helper function for logging messages to a file
def log_message(log_file, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"{timestamp} - {message}\n")

# Run the bot when called from R
if 'initial_capital' in globals():
    # Get the file paths - default to timestamped names if not provided
    data_file = globals().get('data_file', f"trade_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    log_file = globals().get('log_file', f"trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

    arbitrage_bot(
        initial_capital=initial_capital,
        arbitrage_threshold=arbitrage_threshold,
        trading_session_duration=trading_session_duration,
        duration_unit=duration_unit if 'duration_unit' in globals() else "seconds",
        exchange1=exchange1,
        exchange2=exchange2,
        trading_pair=trading_pair,
        simulate_data=simulate_data,
        data_file=data_file,
        log_file=log_file
    )
