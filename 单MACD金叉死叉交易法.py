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
class MACDStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsignal', 9),
        ('printlog', True),
    )

    def __init__(self):
        # 初始化MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd1,
            period_me2=self.params.macd2,
            period_signal=self.params.macdsignal
        )
        # 监控金叉死叉
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        self.order = None
        self.buy_count = 0

    def log(self, txt, dt=None, doprint=True):
        '''日志函数'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        # 订单状态通知
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行, 价格: {order.executed.price:.2f}, 数量: {order.executed.size}, 成本: {order.executed.value:.2f}, 佣金: {order.executed.comm:.2f}')
                self.buy_count = order.executed.size
            elif order.issell():
                self.log(
                    f'卖出执行, 价格: {order.executed.price:.2f}, 数量: {order.executed.size}, 收入: {order.executed.value:.2f}, 佣金: {order.executed.comm:.2f}')
                self.buy_count = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/被拒绝')

        self.order = None

    def next(self):
        # 主交易逻辑
        if self.order:
            return  # 有未完成订单则跳过

        cash = self.broker.getcash()
        current_price = self.data.close[0]
        size = int((cash * 0.5) / current_price)  # 计算可买入数量

        # 金叉信号：半仓买入
        if self.crossover > 0 and not self.position:
            self.log(f'MACD金叉信号 @ {current_price:.2f}')
            if cash > current_price:
                self.order = self.buy(size=size)
            else:
                self.log('现金不足，无法买入')

        # 死叉信号：全部卖出
        elif self.crossover < 0 and self.position:
            self.log(f'MACD死叉信号 @ {current_price:.2f}')
            self.order = self.close()

#cerebro
try:
    data = bt.feeds.PandasData(dataname=stock_deal)

    cerebro = bt.Cerebro()
    print("—————————————————————————————start————————————————————————————")
    cerebro.addstrategy(MACDStrategy)
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

