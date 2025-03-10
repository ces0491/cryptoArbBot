import time
import random
import logging
import pandas as pd
import requests
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


# handler and logging config
handler = logging.FileHandler(log_file)
handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

logger.info("Starting trading bot...")

# Helper function to adjust Binance trading pairs
def format_binance_pair(trading_pair):
    base, quote = trading_pair.split("/")
    if quote == "USD":
        quote = "USDT"  # Binance primarily uses USDT
    return f"{base}{quote}"  # Binance API format (e.g., XRPUSDT)

# Function to fetch market data
def get_price(exchange, trading_pair, simulate_data):
    if simulate_data:
        base_price = 100  # Set base price for asset to randomly vary prices about
        variation = random.uniform(0.95, 1.05) # Add small variation between exchanges +-5% from base
        return round(base_price * variation, 2)
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
                logging.error(f"Exchange {exchange} not supported.")
                return None
        except Exception as e:
            logging.error(f"Error fetching price from {exchange}: {str(e)}")
            return None

# Function to simulate trade execution - here we simply print what should happen (no real execution logic)
def execute_trade(action, exchange, trading_pair, price, amount):
    trade_msg = f"{action} {amount:.4f} of {trading_pair} at {exchange} for ${price:.4f}"
    logging.info(trade_msg)
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
    
    # Configure logging to write to the timestamped log file
    logging.basicConfig(
        filename=log_file, 
        level=logging.INFO, 
        format="%(asctime)s - %(message)s", 
        force=True
    )

    logging.info(trade_summary)
    logging.info("Trading session ended.")
    logging.info(summary_output)
    
    # Convert duration to seconds
    duration_in_seconds = convert_to_seconds(trading_session_duration, duration_unit)
    
    # Reset data collection arrays
    time_points = []
    exchange1_prices = []
    exchange2_prices = []
    trade_executed_flags = []
    cumulative_profits = []
    
    # Clear log file
    with open(log_file, "w") as f:
        f.write(f"Starting new trading session with {initial_capital} USD\n")
    
    logging.info(f"Starting trading bot: {exchange1} vs {exchange2} for {trading_pair}")
    logging.info(f"Initial capital: ${initial_capital}, Threshold: {arbitrage_threshold}%")
    logging.info(f"Trading duration: {trading_session_duration} {duration_unit} ({duration_in_seconds} seconds)")
    
    capital = initial_capital
    start_capital = initial_capital
    start_time = time.time()
    
    trades = []
    profits = 0
    trade_count = 0
    
    # Loop for the duration of trading session
    elapsed = 0
    while elapsed < duration_in_seconds:
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Get prices from exchanges
        price1 = get_price(exchange1, trading_pair, simulate_data)
        price2 = get_price(exchange2, trading_pair, simulate_data)

        if price1 is None or price2 is None:
            logging.warning(f"Could not fetch price from one or both exchanges. {exchange1}: {price1}, {exchange2}: {price2}")
            time.sleep(1)
            continue
        
        # Calculate price difference
        price_diff = abs(price1 - price2)
        avg_price = (price1 + price2) / 2
        percentage_diff = (price_diff / avg_price) * 100
        
        # Log the price comparison
        logging.info(f"Time: {elapsed:.1f}s - {exchange1}: ${price1:.3f}, {exchange2}: ${price2:.3f}, Diff: ${price_diff:.3f} ({percentage_diff:.2f}%)")
        
        # Record data for visualization
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
            trade_summary = f"[Time: {elapsed:.1f}s] ARBITRAGE OPPORTUNITY: {buy_exchange}(${buy_price:.3f}) -> {sell_exchange}(${sell_price:.3f}), Diff: ${price_diff:.3f} ({percentage_diff:.2f}%), Units: {amount:.2f}, Profit: ${trade_profit:.2f}, Capital: ${capital:.2f}"
            trades.append(trade_summary)
            logging.info(trade_summary)
            
            trade_executed = "Yes"
            cumulative_profits[-1] = profits  # Update the latest cumulative profit
        
        trade_executed_flags.append(trade_executed)
        
        # Save data after each iteration for real time updates
        save_trade_data(data_file) # maybe don't do this - real time probably overkill
        
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
        f"Trading Duration: {trading_session_duration} {duration_unit} ({duration_in_seconds} seconds)"
    ]
    
    if trades:
        summary_lines.append("\nTrade Details:")
        summary_lines.extend(trades)
    else:
        summary_lines.append("\nNo arbitrage opportunities found.")
    
    summary_output = "\n".join(summary_lines)
    logging.info("Trading session ended.")
    logging.info(summary_output)
    
    # Final save of trade data
    save_trade_data(data_file)
    
    return summary_output

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
