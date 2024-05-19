import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots


# Function to calculate MACD and signal line
def calculate_macd(df):
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD Hist'] = df['MACD'] - df['Signal Line']
    return df


# Function to calculate RSI
def calculate_rsi(df, period=14):
    delta = df['Close'].diff(1)
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


# Function to find MACD crossovers
def find_macd_crossovers(df):
    df['MACD Diff'] = df['MACD'] - df['Signal Line']
    df['MACD Zero Crossover'] = df['MACD'].apply(np.sign).diff()
    df['MACD Signal Crossover'] = df['MACD Diff'].apply(np.sign).diff()
    zero_crossovers = df[df['MACD Zero Crossover'].abs() == 2].copy()
    signal_crossovers = df[df['MACD Signal Crossover'].abs() == 2].copy()
    crossovers = pd.concat([zero_crossovers, signal_crossovers]).sort_index()

    # Determine crossover type correctly
    crossovers['Crossover Type'] = np.where(
        crossovers['MACD Signal Crossover'] == 2, 'Bullish',
        np.where(crossovers['MACD Signal Crossover'] == -2, 'Bearish',
                 np.where(crossovers['MACD Zero Crossover'] == 2, 'Bullish', 'Bearish')))
    crossovers['Date'] = crossovers.index
    crossovers['MACD Value'] = crossovers['MACD']
    crossovers['Crossover Description'] = np.where(crossovers['MACD Zero Crossover'].abs() == 2,
                                                   'MACD Crosses Zero Line',
                                                   'MACD Crosses Signal Line')
    crossovers = crossovers[~crossovers.index.duplicated(keep='first')]
    return crossovers


# Function to calculate price changes after crossovers
def calculate_price_changes(df, crossovers):
    for days in [5, 14, 30, 45]:
        crossovers[f'{days}D Change'] = ((df['Close'].shift(-days) - df['Close']) / df['Close'] * 100).reindex(
            crossovers.index)
    return crossovers


# Streamlit app layout
st.title('MACD Analysis Dashboard')

# Sidebar for educational content
with st.sidebar:
    st.header("About MACD Analysis")
    st.write("""
    ### What is MACD?
    The Moving Average Convergence Divergence (MACD) is a trend-following momentum indicator that shows the relationship between two moving averages of a stock's price.
    - **MACD Line**: The difference between the 12-day and 26-day exponential moving averages (EMA).
    - **Signal Line**: A 9-day EMA of the MACD line.
    - **Histogram**: The difference between the MACD line and the signal line.

    ### MACD Crossovers
    - **Signal Line Crossover**: When the MACD line crosses above the signal line, it indicates a bullish signal (potential buy). When the MACD line crosses below the signal line, it indicates a bearish signal (potential sell).
    - **Zero Line Crossover**: When the MACD line crosses above the zero line, it indicates bullish momentum. When it crosses below the zero line, it indicates bearish momentum.

    ### What is RSI?
    The Relative Strength Index (RSI) is a momentum oscillator that measures the speed and change of price movements.
    - **RSI Values**: RSI values range from 0 to 100. Typically, an RSI above 70 indicates that a stock is overbought, while an RSI below 30 indicates that a stock is oversold.
    """)

stock_symbol = st.text_input('Enter Stock Symbol', 'AAPL')

if stock_symbol:
    df = yf.download(stock_symbol, period='1y', interval='1d')

    if not df.empty:
        df = calculate_macd(df)
        df = calculate_rsi(df)
        crossovers = find_macd_crossovers(df)

        crossovers = calculate_price_changes(df, crossovers)

        # Reverse the order of crossovers
        crossovers = crossovers.iloc[::-1]

        # Format the date column properly
        crossovers['Date'] = crossovers['Date'].dt.strftime('%Y-%m-%d')
        crossovers = crossovers.reset_index(drop=True)

        # Create subplots
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            vertical_spacing=0.02,
                            row_heights=[0.4, 0.3, 0.3])

        # Add price trace
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price'), row=1, col=1)

        # Add MACD traces
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal Line'], mode='lines', name='Signal Line'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACD Hist'], name='MACD Histogram'), row=2, col=1)

        # Add RSI trace
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI'), row=3, col=1)

        # Add overbought/oversold lines to RSI
        fig.add_hline(y=70, line=dict(color='red', dash='dash'), row=3, col=1)
        fig.add_hline(y=30, line=dict(color='green', dash='dash'), row=3, col=1)

        # Update layout
        fig.update_layout(height=800, showlegend=False,
                          title_text="Stock Price, MACD, and RSI",
                          yaxis1=dict(title="Close Price"),
                          yaxis2=dict(title="MACD"),
                          yaxis3=dict(title="RSI"))

        st.plotly_chart(fig, use_container_width=True)

        st.subheader('MACD Crossovers and Price Changes')
        st.write("""
        The table below shows the MACD crossovers and the percentage changes in stock price after 5, 14, 30, and 45 days.
        - **Bullish crossovers** indicate a potential upward trend.
        - **Bearish crossovers** suggest a potential downward trend.
        """)

        # Filters for crossovers
        col1, col2 = st.columns(2)
        with col1:
            show_bullish = st.checkbox('Show Bullish Crossovers', value=True)
        with col2:
            show_bearish = st.checkbox('Show Bearish Crossovers', value=True)

        # Apply filters
        if not show_bullish:
            crossovers = crossovers[crossovers['Crossover Type'] != 'Bullish']
        if not show_bearish:
            crossovers = crossovers[crossovers['Crossover Type'] != 'Bearish']

        crossovers = crossovers[
            ['Date', 'Close', 'MACD Value', 'Crossover Type', 'Crossover Description', '5D Change', '14D Change',
             '30D Change', '45D Change']]
        crossovers.columns = ['Date', 'Close Price', 'MACD Value', 'Crossover Type', 'Crossover Description',
                              '5D Change (%)', '14D Change (%)', '30D Change (%)', '45D Change (%)']

        # Replace NaN with 'NA' for changes
        crossovers['5D Change (%)'] = crossovers['5D Change (%)'].apply(lambda x: f'{x:+.2f}%' if pd.notna(x) else 'NA')
        crossovers['14D Change (%)'] = crossovers['14D Change (%)'].apply(
            lambda x: f'{x:+.2f}%' if pd.notna(x) else 'NA')
        crossovers['30D Change (%)'] = crossovers['30D Change (%)'].apply(
            lambda x: f'{x:+.2f}%' if pd.notna(x) else 'NA')
        crossovers['45D Change (%)'] = crossovers['45D Change (%)'].apply(
            lambda x: f'{x:+.2f}%' if pd.notna(x) else 'NA')

        crossovers['Close Price'] = crossovers['Close Price'].apply(lambda x: f'${x:.2f}')
        crossovers['MACD Value'] = crossovers['MACD Value'].apply(lambda x: f'{x:.2f}')


        # Apply conditional formatting to the percentage columns only
        def style_crossover(row):
            styles = []
            for col in row.index:
                value = row[col]
                if col.endswith('Change (%)'):
                    if value.startswith('+'):
                        styles.append('color: green')
                    elif value.startswith('-'):
                        styles.append('color: red')
                    else:
                        styles.append('')
                else:
                    styles.append('')
            return styles


        styled_crossovers = crossovers.style.apply(style_crossover, axis=1)

        st.dataframe(styled_crossovers)

    else:
        st.error('Invalid stock symbol or no data available.')
else:
    st.info('Please enter a stock symbol to get started.')
