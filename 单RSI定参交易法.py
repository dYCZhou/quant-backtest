#单MACD金叉死叉在强烈震荡的行情中表现不佳，机会抓不住，操作无效；
#在强上升行情中表现尚可，但不如单5日均线
#在波动下降行情中表现不佳，操作无效且亏损


import akshare as ak
import pandas as pd
import backtrader as bt
import plotly.graph_objects as go
#get dailyData from AKShare
symbol = input("symbol:")
start = input("start date:")
end = input("end date:")
setcash = float(input("set cash:"))
try:
    stock_pre = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
    print("successful get preData")
    #print(stock_pre.head(20))
except Exception as e:
    print("fail to get preData : ",e)

#data processing
try:
    # 正确复制DataFrame避免警告
    stock_deal = stock_pre[['date', 'open', 'close', 'high', 'low', 'volume']].copy()

    # 转换日期格式
    stock_deal.loc[:, 'date'] = pd.to_datetime(stock_deal['date'])
    stock_deal.set_index('date', inplace=True)

    #print("数据处理完成，前5行：")
    #print(stock_deal.head())

except Exception as e:
    print("数据处理出错:", e)
    exit()


#strategy
class RSIDivergenceStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('overbought', 70),
        ('oversold', 30),
    )

    def __init__(self):
        # 计算RSI指标
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

        # 存储最近的两个低点和两个高点
        self.low_prices = []  # 最近两个低点的价格
        self.low_rsis = []  # 最近两个低点的RSI值
        self.high_prices = []  # 最近两个高点的价格
        self.high_rsis = []  # 最近两个高点的RSI值

        # 存储当前仓位状态
        self.position_flag = 0  # 0:空仓，1:半仓

    def next(self):
        current_low = self.data.low[0]
        current_high = self.data.high[0]
        current_rsi = self.rsi[0]
        current_date = self.datetime.date(0).isoformat()

        # 更新低点数据
        if not self.low_prices or current_low < self.low_prices[-1]:
            if len(self.low_prices) >= 2:
                self.low_prices.pop(0)
                self.low_rsis.pop(0)
            self.low_prices.append(current_low)
            self.low_rsis.append(current_rsi)
            print(f"新低点记录: 日期={current_date}, 价格={current_low:.2f}, RSI={current_rsi:.2f}")

        # 更新高点数据
        if not self.high_prices or current_high > self.high_prices[-1]:
            if len(self.high_prices) >= 2:
                self.high_prices.pop(0)
                self.high_rsis.pop(0)
            self.high_prices.append(current_high)
            self.high_rsis.append(current_rsi)
            print(f"新高点记录: 日期={current_date}, 价格={current_high:.2f}, RSI={current_rsi:.2f}")

        # 检查底背离条件 (RSI<30 且 底背离)
        if (len(self.low_prices) >= 2 and
                self.low_prices[-1] < self.low_prices[-2] and  # 价格创新低
                self.low_rsis[-1] > self.low_rsis[-2] and  # RSI未创新低
                current_rsi < self.params.oversold):  # RSI<30

            # 半仓买入
            target_percent = 0.5
            self.order_target_percent(target=target_percent)
            self.position_flag = 1
            print(f"\n*** 底背离买入信号 *** 日期={current_date}")
            print(f"价格: 前低={self.low_prices[-2]:.2f}, 现低={self.low_prices[-1]:.2f}")
            print(f"RSI: 前值={self.low_rsis[-2]:.2f}, 现值={self.low_rsis[-1]:.2f}")
            print(f"执行半仓买入，当前仓位={target_percent * 100}%")

        # 检查顶背离条件 (RSI>70 且 顶背离)
        if (len(self.high_prices) >= 2 and
                self.high_prices[-1] > self.high_prices[-2] and  # 价格创新高
                self.high_rsis[-1] < self.high_rsis[-2] and  # RSI未创新高
                current_rsi > self.params.overbought):  # RSI>70

            # 全部卖出
            self.order_target_percent(target=0)
            self.position_flag = 0
            print(f"\n*** 顶背离卖出信号 *** 日期={current_date}")
            print(f"价格: 前高={self.high_prices[-2]:.2f}, 现高={self.high_prices[-1]:.2f}")
            print(f"RSI: 前值={self.high_rsis[-2]:.2f}, 现值={self.high_rsis[-1]:.2f}")
            print(f"执行全部卖出，当前仓位=0%")

        # 打印常规日志
        print(
            f"日期={current_date}, 收盘价={self.data.close[0]:.2f}, RSI={current_rsi:.2f}, 仓位={self.position_flag * 50}%")


#cerebro
try:
    data = bt.feeds.PandasData(dataname=stock_deal)

    cerebro = bt.Cerebro()
    print("—————————————————————————————start————————————————————————————")
    cerebro.addstrategy(RSIDivergenceStrategy)
    cerebro.adddata(data)
    cerebro.broker.setcash(setcash)  # 初始资金10万

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    result = cerebro.run()


    #analyze
    strat = result[0]
    # 计算年化收益率
    ret_analyzer = strat.analyzers.returns.get_analysis()
    annual_return = ret_analyzer['rnorm100']  # 年化收益率(百分比)

    # 计算夏普比率
    sharpe_ratio = strat.analyzers.sharpe.get_analysis()['sharperatio']

    # 计算最大回撤
    drawdown = strat.analyzers.drawdown.get_analysis()
    max_drawdown = drawdown['max']['drawdown']  # 百分比

    print('\n========== 策略表现 ==========')
    print('开始资金: %.2f' % setcash)
    print('结束资金: %.2f' % cerebro.broker.getvalue())
    print(f"年化收益率: {annual_return:.2f}%")
    print(f"夏普比率: {sharpe_ratio:.2f}")
    print(f"最大回撤: {max_drawdown:.2f}%")
    print('=============================')


    cerebro.plot(
        style='line',
        volume=False
    )


except Exception as e:
    print("cerebro error: %s" % e)

