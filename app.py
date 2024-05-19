import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Function to get stock data
def get_stock_data(ticker, period='1y', interval='1d'):
    return yf.download(ticker, period=period, interval=interval)


# Function to calculate MACD
def calculate_macd(data):
    data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
    data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = data['EMA12'] - data['EMA26']
    data['Signal Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['Hist'] = data['MACD'] - data['Signal Line']
    return data


# Function to calculate RSI
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    return data


# Function to identify MACD crossovers
def identify_macd_crossovers(data):
    crossovers = []
    for i in range(1, len(data)):
        if data['MACD'].iloc[i - 1] < data['Signal Line'].iloc[i - 1] and data['MACD'].iloc[i] > \
                data['Signal Line'].iloc[i]:
            crossovers.append((data.index[i], data['Close'].iloc[i], 'Bullish'))
        elif data['MACD'].iloc[i - 1] > data['Signal Line'].iloc[i - 1] and data['MACD'].iloc[i] < \
                data['Signal Line'].iloc[i]:
            crossovers.append((data.index[i], data['Close'].iloc[i], 'Bearish'))
    return crossovers


# Streamlit app
st.title('Stock Analysis Dashboard')

st.sidebar.header('Settings')

# Sidebar input for stock symbol
ticker = st.sidebar.text_input('Enter Stock Symbol', value='AAPL')

# Sidebar input for time frame
period = st.sidebar.selectbox('Select Time Frame', ['1y', '2y', '5y', '10y'])

# Sidebar input for chart type
chart_type = st.sidebar.radio('Select Chart Type', ['Daily', 'Weekly'])

# Set interval based on chart type
interval = '1d' if chart_type == 'Daily' else '1wk'

# Educational content
with st.sidebar.expander("Learn about MACD and RSI"):
    st.write("""
    **MACD (Moving Average Convergence Divergence):**
    - The MACD is a trend-following momentum indicator that shows the relationship between two moving averages of a security’s price.
    - It is calculated by subtracting the 26-period Exponential Moving Average (EMA) from the 12-period EMA.
    - A 9-period EMA of the MACD, called the "Signal Line," is plotted on top of the MACD line, which can act as a trigger for buy and sell signals.
    - When the MACD crosses above the Signal Line, it is a bullish signal, indicating that it may be time to buy.
    - When the MACD crosses below the Signal Line, it is a bearish signal, indicating that it may be time to sell.

    **RSI (Relative Strength Index):**
    - The RSI measures the speed and change of price movements.
    - RSI values range from 0 to 100. Traditionally, RSI is considered overbought when above 70 and oversold when below 30.
    - It can be used to identify general market trends and potential reversal points.
    """)

if ticker:
    # Fetch stock data
    data = get_stock_data(ticker, period=period, interval=interval)

    if not data.empty:
        # Calculate MACD and RSI
        data = calculate_macd(data)
        data = calculate_rsi(data)

        # Identify MACD crossovers
        crossovers = identify_macd_crossovers(data)

        # Plotting
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                            subplot_titles=('Stock Price', 'MACD', 'RSI'),
                            row_width=[0.2, 0.2, 0.6])

        # Line chart for stock price
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Stock Price'), row=1, col=1)

        # MACD chart
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], mode='lines', name='MACD'), row=2, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Signal Line'], mode='lines', name='Signal Line'), row=2, col=1)
        fig.add_trace(go.Bar(x=data.index, y=data['Hist'], name='Histogram'), row=2, col=1)

        # RSI chart
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], mode='lines', name='RSI'), row=3, col=1)
        fig.add_shape(type='line', x0=data.index[0], y0=70, x1=data.index[-1], y1=70,
                      line=dict(color='Red', ), row=3, col=1)
        fig.add_shape(type='line', x0=data.index[0], y0=30, x1=data.index[-1], y1=30,
                      line=dict(color='Green', ), row=3, col=1)

        fig.update_layout(height=800, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Display crossovers in a DataFrame
        if crossovers:
            crossover_df = pd.DataFrame(crossovers, columns=['Date', 'Close Price', 'Type'])
            st.subheader('MACD Crossovers')
            st.dataframe(crossover_df)
    else:
        st.error('Invalid stock symbol or no data available.')
else:
    st.info('Please enter a stock symbol to get started.')
