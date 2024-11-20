# app/extract_and_load.py

import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta

def fetch_and_save_stock_data():
    # Read the list of stock tickers, number of stocks, and buy-in prices from the file
    stocks_data = pd.read_csv('stocks.txt', sep=';', header=None, names=['symbol', 'num_stocks', 'buy_in'])

    # Connect to PostgreSQL database
    engine = create_engine('postgresql://postgres:postgres@db:5432/stockdata')

    # Create an empty DataFrame to store all stock information
    all_info = pd.DataFrame()

    # Fetch stock data for each ticker and save it to the database
    for _, row in stocks_data.iterrows():
        stock = row['symbol']
        num_stocks = row['num_stocks']
        buy_in = row['buy_in']
        print(f"Fetching data for {stock}")
        ticker = yf.Ticker(stock)
        
        # Fetch daily stock data
        df_daily = ticker.history(period="10y", interval="1d", prepost=True)
        df_daily.reset_index(inplace=True)
        table_name_daily = f"{stock.lower()}_daily"
        df_daily.to_sql(table_name_daily, engine, if_exists='replace', index=False)
        print(f"Daily data for {stock} saved to database")
        
        # Fetch additional stock information
        info = ticker.info
        stock_name = info.get('shortName', None)
        pe_ratio = info.get('trailingPE', None)
        dividend_yield = info.get('dividendYield', None)
        eps = info.get('trailingEps', None)
        ps_ratio = info.get('priceToSalesTrailing12Months', None)
        
        # Calculate KPIs
        latest_data = df_daily.iloc[-1]
        current_price = round(latest_data['Close'], 2)
        high_52w = round(df_daily['High'].rolling(window=252, min_periods=1).max().iloc[-1], 2)
        low_52w = round(df_daily['Low'].rolling(window=252, min_periods=1).min().iloc[-1], 2)
        all_time_high = round(df_daily['High'].max(), 2)
        percentage_to_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)

        roll_max = df_daily['Close'].cummax()
        drawdown = df_daily['Close'] / roll_max - 1
        max_drawdown = round(drawdown.min() * 100, 2)
        end_date = drawdown.idxmin()
        start_date = df_daily.loc[:end_date, 'Close'].idxmax()
    

        # Append the information to the all_info DataFrame
        df_info = pd.DataFrame({
            'symbol': [stock],
            'stock_name': [stock_name],
            'num_stocks': [num_stocks],
            'buy_in': [buy_in],
            'pe_ratio': [round(pe_ratio, 2) if pe_ratio is not None else None],
            'dividend_yield': [round(dividend_yield * 100, 2) if dividend_yield is not None else None],
            'eps': [round(eps, 2) if eps is not None else None],
            'ps_ratio': [round(ps_ratio, 2) if ps_ratio is not None else None],
            'current_price': [current_price],
            'high_52w': [high_52w],
            'low_52w': [low_52w],
            'all_time_high': [all_time_high],
            'percentage_to_ath': [percentage_to_ath],
            'max_drawdown': [max_drawdown]
        })
        all_info = pd.concat([all_info, df_info], ignore_index=True)

    # Save all stock information to a single table in the database
    all_info.to_sql('information', engine, if_exists='replace', index=False)
    print("All stock information saved to database")

if __name__ == "__main__":
    fetch_and_save_stock_data()