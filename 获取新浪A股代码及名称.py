import akshare as ak
import pandas as pd

list = ak.stock_zh_a_spot()
#print(list.head())
list.to_excel('xinlang_stock_list.xlsx')