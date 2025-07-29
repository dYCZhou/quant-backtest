#单MACD红绿柱斜率不适合独立使用，强上升、强下降、强震荡均无优势表现
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
# strategy
class MACDHistoStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('signal', 9),
    )

    def __init__(self):
        # 计算MACD指标
        self.macd = bt.indicators.MACDHisto(
            self.data,
            period_me1=self.params.macd1,
            period_me2=self.params.macd2,
            period_signal=self.params.signal
        )
        self.histo = self.macd.histo  # MACD柱状图
        self.order = None  # 跟踪当前订单状态
        self.buy_price = None  # 记录买入价格
        self.position_size = 0  # 记录持仓数量

    def log(self, txt, dt=None):
        '''日志函数'''
        dt = dt or self.data.datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行: 价格={order.executed.price:.2f}, '
                    f'数量={order.executed.size}, 成本={order.executed.value:.2f}, '
                    f'佣金={order.executed.comm:.2f}'
                )
                self.buy_price = order.executed.price
                self.position_size = order.executed.size
            elif order.issell():
                self.log(
                    f'卖出执行: 价格={order.executed.price:.2f}, '
                    f'数量={order.executed.size}, 收入={order.executed.value:.2f}, '
                    f'佣金={order.executed.comm:.2f}'
                )
                self.position_size = 0
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/被拒绝')
        self.order = None

    def next(self):
        # 避免重复下单
        if self.order:
            return

        # 计算柱状图斜率（当前柱与前一根柱比较）
        slope = self.histo[0] - self.histo[-1]

        # 绿柱斜率>0（绿柱缩短）且无持仓时半仓买入
        if self.histo[0] < 0 and slope > 0 and not self.position:
            cash = self.broker.getcash()
            target_value = cash * 0.5  # 半仓
            size = int(target_value / self.data.close[0])

            if size > 0:
                self.log(f'信号触发：绿柱斜率({slope:.4f})>0，半仓买入{size}股')
                self.order = self.buy(size=size)

        # 红柱斜率<0（红柱缩短）且有持仓时全仓卖出
        elif self.histo[0] > 0 and slope < 0 and self.position:
            self.log(f'信号触发：红柱斜率({slope:.4f})<0，全仓卖出')
            self.order = self.sell(size=self.position_size)



#cerebro
try:
    data = bt.feeds.PandasData(dataname=stock_deal)

    cerebro = bt.Cerebro()
    print("—————————————————————————————start————————————————————————————")
    cerebro.addstrategy(MACDHistoStrategy)
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

