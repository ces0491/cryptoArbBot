library(shiny)
library(reticulate)
library(ggplot2)
library(plotly)
library(shinycssloaders)

# Set Python path
use_python("C:/Users/cesai_b8mratk/AppData/Local/Programs/Python/Python311/python.exe")

# Define UI
ui <- fluidPage(
  titlePanel("Crypto Arbitrage Trading Bot Simulator"),
  
  tabsetPanel(
    tabPanel("Trading Dashboard",
             sidebarLayout(
               sidebarPanel(
                 numericInput(inputId = "initial_capital", 
                              label = "Initial Capital (USD):", 
                              value = 1000, 
                              min = 100, 
                              step = 100),
                 
                 numericInput(inputId = "arbitrage_threshold", 
                              label = "Arbitrage Threshold (%):", 
                              value = 0.5, 
                              min = 0.1, 
                              step = 0.1),
                 
                 # Duration inputs side by side
                 fluidRow(
                   column(width = 6,
                          numericInput(inputId = "trading_duration", 
                                       label = "Trading Duration:", 
                                       value = 30, 
                                       min = 1, 
                                       step = 1)
                   ),
                   column(width = 6,
                          selectInput(inputId = "duration_unit", 
                                      label = "Duration Unit:", 
                                      choices = c("seconds", "minutes", "hours", "days"),
                                      selected = "seconds")
                   )
                 ),
                 
                 selectInput(inputId = "exchange_1", 
                             label = "Select First Exchange:", 
                             choices = c("Binance", "Coinbase", "Kraken", "Bitfinex"),
                             selected = "Kraken"),
                 
                 selectInput(inputId = "exchange_2", 
                             label = "Select Second Exchange:", 
                             choices = c("Binance", "Coinbase", "Kraken", "Bitfinex"),
                             selected = "Coinbase"),
                 
                 textInput(inputId = "trading_pair", 
                           label = "Trading Pair (e.g., XRP/USD, BTC/USDT):", 
                           value = "XRP/USD"),
                 
                 checkboxInput(inputId = "simulation_mode", 
                               label = "Simulate Price Data?", 
                               value = TRUE),
                 
                 actionButton(inputId = "start_trading", label = "Start Trading", 
                              icon = icon("play")),
                 
                 actionButton(inputId = "stop_trading", label = "Stop Trading", 
                              icon = icon("stop"))
               ),
               
               mainPanel(
                 h3("Trading Status"),
                 textOutput("trading_status"),
                 
                 tags$div(
                   style = "width: 65vw; height: 30vh; overflow-y: auto; border: 1px solid #ddd; padding: 10px;", # fix output size and make scrollable
                   verbatimTextOutput("summary_output") %>% withSpinner()
                 ),
                 
                 hr(),
                 h3("Price Comparison"),
                 plotlyOutput("price_plot_interactive", height = "300px") %>% withSpinner(),
                 
                 hr(),
                 h3("Cumulative Profit"),
                 plotlyOutput("profit_chart", height = "300px") %>% withSpinner()
               )
             )
    ),
    
    tabPanel("Trade Log",
             verbatimTextOutput("log_output") %>% withSpinner()
    )
  )
)

# Define server logic
server <- function(input, output, session) {
  
  # Reactive values
  trading_running <- reactiveVal(FALSE)
  countdown_time <- reactiveVal(0)
  trade_data <- reactiveVal(data.frame(Time = numeric(0), 
                                       Exchange1_Price = numeric(0), 
                                       Exchange2_Price = numeric(0), 
                                       Trade_Executed = character(0),
                                       Cumulative_Profit = numeric(0)))
  log_content <- reactiveVal("")
  
  # Reactive values to store current file paths
  current_files <- reactiveValues(
    data_file = "",
    log_file = ""
  )
  
  # Create a timer that fires every second (1000 millis)
  observe({
    invalidateLater(1000, session)
    
    # Update countdown if trading is running
    if (trading_running() && countdown_time() > 0) {
      countdown_time(countdown_time() - 1)
      output$trading_status <- renderText("Trading...")
    } else if (trading_running() && countdown_time() <= 0) {
      trading_running(FALSE)
      output$trading_status <- renderText("Trading complete.")
    }
    
    # Try to load trade data if file exists and we're running
    if (nchar(current_files$data_file) > 0 && file.exists(current_files$data_file)) {

      new_data <- tryCatch({
        tmp_data <- read.csv(current_files$data_file)
        if (nrow(tmp_data) > 0) tmp_data else NULL
      }, error = function(e) {
        print(paste("Error loading data:", e$message))
        return(NULL)
      })
      
      if (!is.null(new_data) && nrow(new_data) > 0) {
        trade_data(new_data)
        # Ensure is_running stays TRUE as long as we have data and haven't manually stopped
        if (!session_data$is_running && trading_running()) {
          session_data$is_running <- TRUE
        }
      }
    }
    
    # Update log content if file exists
    if (nchar(current_files$log_file) > 0 && file.exists(current_files$log_file)) {
      tryCatch({
        log_text <- readLines(current_files$log_file, warn = FALSE)
        if (length(log_text) > 0) {
          log_content(paste(log_text, collapse = "\n"))
        }
      }, error = function(e) {
        log_content("Error reading log file")
      })
    }
  })
  
  # Reactive values to store session-specific data
  session_data <- reactiveValues(prices = NULL, summary = NULL, is_running = FALSE)
  
  # Start trading
  observeEvent(input$start_trading, {
    # Create timestamped filenames
    timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
    data_file <- paste0("trade_data_", timestamp, ".csv")
    log_file <- paste0("trade_log_", timestamp, ".txt")
    
    # Update reactive values with new file paths
    current_files$data_file <- data_file
    current_files$log_file <- log_file
    
    session_data$is_running <- TRUE  # Mark session as running
    session_data$exchange1_prices <- NULL      # Clear old prices
    session_data$exchange2_prices <- NULL      # Clear old prices
    session_data$summary <- NULL     # Clear previous summary
    
    # Reset the trade data
    trade_data(data.frame(Time = numeric(0), 
                          Exchange1_Price = numeric(0), 
                          Exchange2_Price = numeric(0), 
                          Trade_Executed = character(0),
                          Cumulative_Profit = numeric(0)))
    
    # Ensure inputs are not NULL before passing them to Python
    if (is.null(input$initial_capital) || input$initial_capital == "" ||
        is.null(input$arbitrage_threshold) || input$arbitrage_threshold == "" ||
        is.null(input$trading_duration) || input$trading_duration == "" ||
        is.null(input$exchange_1) || input$exchange_1 == "" ||
        is.null(input$exchange_2) || input$exchange_2 == "" ||
        is.null(input$trading_pair) || input$trading_pair == "" ||
        is.null(input$simulation_mode)) {
      
      showNotification("Error: Missing input values!", type = "error")
      session_data$is_running <- FALSE
      return()
    }
    
    # Convert boolean input for Python (True/False vs TRUE/FALSE in R)
    simulate_data_python <- ifelse(input$simulation_mode, "True", "False")
    
    # Ensure all values are safely converted to strings for Python execution
    py_run_string(sprintf("initial_capital = %f", as.numeric(input$initial_capital)))
    py_run_string(sprintf("arbitrage_threshold = %f", as.numeric(input$arbitrage_threshold)))
    py_run_string(sprintf("trading_session_duration = %d", as.integer(input$trading_duration)))
    py_run_string(sprintf("duration_unit = '%s'", as.character(input$duration_unit)))
    py_run_string(sprintf("exchange1 = '%s'", as.character(input$exchange_1)))
    py_run_string(sprintf("exchange2 = '%s'", as.character(input$exchange_2)))
    py_run_string(sprintf("trading_pair = '%s'", as.character(input$trading_pair)))
    py_run_string(sprintf("simulate_data = %s", simulate_data_python))
    py_run_string(sprintf("data_file = '%s'", data_file))
    py_run_string(sprintf("log_file = '%s'", log_file))
    
    # Start Python trading bot
    py_run_file("fse_arbitrage_bot.py")
    
    # Update reactive values after completion
    session_data$summary <- py$summary_output
    session_data$exchange1_prices <- py$exchange1_prices
    session_data$exchange2_prices <- py$exchange2_prices
    session_data$is_running <- FALSE  # Mark session as stopped
    
    # Update status
    # output$trading_status <- renderText("Trading complete.")
  })
  
  # Stop trading
  observeEvent(input$stop_trading, {
    trading_running(FALSE)
    session_data$is_running <- FALSE
    output$trading_status <- renderText("Trading stopped manually")
  })
  
  # Display final summary when trading stops
  output$summary_output <- renderText({
    if (session_data$is_running) {
      return("No trading summary available yet")
    } else if (!is.null(session_data$summary) && nchar(session_data$summary) > 0) {
      return(session_data$summary)
    } else {
      return("No trading summary available")
    }
  })
  
  # Show trade log - this will update dynamically due to log_content reactive
  output$log_output <- renderText({
    log_content()
  })
  
  # Status indicator
  output$trading_status <- renderText({
    if (session_data$is_running) {
      return("Trading in progress...")
    } else {
      return("Ready to trade")
    }
  })
  
  # Render interactive plotly chart for price comparison
  output$price_plot_interactive <- renderPlotly({
    df <- trade_data()
    
    # Only render if we have data and trading has started
    if (nrow(df) == 0) {
      return(plotly_empty())
    }
    
    # Calculate price differences for tooltips
    df$Price_Diff <- abs(df$Exchange1_Price - df$Exchange2_Price)
    df$Price_Diff_Percent <- (df$Price_Diff / ((df$Exchange1_Price + df$Exchange2_Price)/2)) * 100
    
    # Create base ggplot
    p <- ggplot(df, aes(x = Time)) +
      geom_line(aes(y = Exchange1_Price, color = input$exchange_1), size = 1) +
      geom_line(aes(y = Exchange2_Price, color = input$exchange_2), size = 1) +
      labs(
        title = paste("Price Comparison:", input$exchange_1, "vs", input$exchange_2),
        x = paste0("Time (", input$duration_unit, ")"),
        y = "Price",
        color = "Exchange"
      ) +
      theme_minimal()
    
    # Add points for executed trades
    trades <- subset(df, Trade_Executed == "Yes")
    if (nrow(trades) > 0) {
      p <- geom_point(data = trades, aes(y = Exchange1_Price), size = 3) +
        geom_point(data = trades, aes(y = Exchange2_Price), size = 3)
    }
    
    # Convert to plotly with custom tooltips
    ply <- ggplotly(p, tooltip = c("x", "y")) %>%
      layout(hovermode = "closest")
    
    # Customize tooltip
    for (i in 1:length(ply$x$data)) {
      if (!is.null(ply$x$data[[i]]$name)) {
        ply$x$data[[i]]$text <- lapply(1:nrow(df), function(j) {
          sprintf(
            "Time: %.1fs<br>%s: $%.2f<br>%s: $%.2f<br>Diff: $%.2f<br>Diff %%: %.2f%%",
            df$Time[j],
            input$exchange_1, df$Exchange1_Price[j],
            input$exchange_2, df$Exchange2_Price[j],
            df$Price_Diff[j],
            df$Price_Diff_Percent[j]
          )
        })
        
        ply$x$data[[i]]$hoverinfo <- "text"
      }
    }
    
    ply
  })
  
  # Render profit chart
  output$profit_chart <- renderPlotly({
    df <- trade_data()
    
    # Only render if we have data and trading has started
    if (nrow(df) == 0 || !"Cumulative_Profit" %in% colnames(df)) {
      return(plotly_empty())
    }
    
    # Create profit chart
    p <- ggplot(df, aes(x = Time, y = Cumulative_Profit)) +
      geom_line(color = "#28a745", size = 1.5) +
      labs(
        title = "Cumulative Profit Over Time",
        x = paste0("Time (", input$duration_unit, ")"),
        y = "Profit (USD)"
      ) +
      theme_minimal()
    
    # Add points for trade executions
    trades <- subset(df, Trade_Executed == "Yes")
    if (nrow(trades) > 0) {
      p <- p +
        geom_point(data = trades, aes(y = Cumulative_Profit), color = "red", size = 3)
    }
    
    # Convert to plotly with custom tooltips
    ply <- ggplotly(p) %>%
      layout(hovermode = "closest")
    
    # Customize tooltip
    for (i in 1:length(ply$x$data)) {
      ply$x$data[[i]]$text <- lapply(1:nrow(df), function(j) {
        sprintf(
          "Time: %.1fs<br>Profit: $%.2f",
          df$Time[j],
          df$Cumulative_Profit[j]
        )
      })
      
      ply$x$data[[i]]$hoverinfo <- "text"
    }
    
    ply
  })
}

# Run the application 
shinyApp(ui = ui, server = server)