import akshare as ak
import pandas as pd
import plotly as pl
import plotly.graph_objs as go
from plotly.graph_objs import Candlestick


#get data from akshare
try:
    df = ak.stock_zh_a_hist(
        symbol="000001",
        period="daily",
        start_date="20240716",
        end_date="20250718",
        adjust="qfq"
    )
    #print(df.head())
except Exception as e:
    print("fail to get data from akshare :",e)

#data processing
# df.set_index('日期', inplace=True)#reset the index
# print(df.head())

#figure
try:
    fig = go.Figure(data=[Candlestick(
        x=df["日期"],
        open=df["开盘"],
        high=df["最高"],
        low=df["最低"],
        close=df["收盘"]
    )])

    fig.update_layout(
        title="000001daily",
        xaxis_title="date",
        yaxis_title="price",
        xaxis_rangeslider_visible=False

    )
    fig.show()

except Exception as e:
    print("fail to show :",e)