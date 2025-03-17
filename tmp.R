library(reticulate)

initial_capital <- 1000
arbitrage_threshold <- 0.5
trading_duration <- 30
exchange_1 <- 'Kraken'
exchange_2 <- 'Coinbase'
trading_pair <- 'XRP/USD'
simulation_mode <- TRUE

# use_python("C:/Users/cesai_b8mratk/AppData/Local/Programs/Python/Python311/python.exe")

py_run_string(sprintf("initial_capital = %f", initial_capital))
py_run_string(sprintf("arbitrage_threshold = %f / 100", arbitrage_threshold))
py_run_string(sprintf("trading_session_duration = %d", as.integer(trading_duration)))
py_run_string(sprintf("exchange1 = '%s'", exchange_1))
py_run_string(sprintf("exchange2 = '%s'", exchange_2))
py_run_string(sprintf("trading_pair = '%s'", trading_pair))
py_run_string(sprintf("simulate_data = %s", ifelse(simulation_mode, "True", "False")))

# Run the Python trading bot
py_run_file("fse_arbitrage_bot.py")
