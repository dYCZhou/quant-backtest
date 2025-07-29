import akshare as ak
import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt

# 定义三只股票的配置信息
stocks = [
    {"symbol": "sh600774", "start": "20230925", "end": "20250717"},
    {"symbol": "sz002623", "start": "20230117", "end": "20240718"},
    {"symbol": "bj872392", "start": "20240308", "end": "20250718"}
]
setcash = 10000  # 统一设置初始资金


# 策略类保持不变
class SMADerivativeStrategy(bt.Strategy):
    params = (
        ('sma_period', 5),  # 5日均线周期
    )

    def __init__(self):
        # 初始化5日均线指标
        self.sma5 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period
        )
        # 记录交易订单
        self.order = None
        # 跟踪每日导数值
        self.derivative = 0

    def next(self):
        # 检查是否有未完成订单
        if self.order:
            return

        # 确保有足够数据计算导数（至少2个数据点）
        if len(self.sma5) > 1:
            # 计算5日均线导数：当前值 - 前一日值
            self.derivative = self.sma5[0] - self.sma5[-1]

            # 导数 > 0 且无持仓：半仓买入
            if self.derivative > 0 and not self.position:
                # 计算可买入数量（可用资金的一半 / 当前收盘价）
                cash_available = self.broker.getcash()
                size = (cash_available * 0.8) / self.data.close[0]
                # 执行买入订单（按收盘价）
                self.order = self.buy(size=size, exectype=bt.Order.Close)

            # 导数 < 0 且有持仓：全部卖出
            elif self.derivative < 0 and self.position:
                # 卖出全部持仓（按收盘价）
                self.order = self.sell(size=self.position.size, exectype=bt.Order.Close)

    def notify_order(self, order):
        # 订单完成处理
        if order.status in [order.Completed]:
            # 重置订单状态
            self.order = None


# 遍历三只股票进行回测
for i, stock in enumerate(stocks):
    symbol = stock["symbol"]
    start = stock["start"]
    end = stock["end"]

    print(f"\n{'=' * 50}")
    print(f"开始处理第 {i + 1} 只股票: {symbol}")
    print(f"{'=' * 50}")

    try:
        # 获取股票数据
        stock_pre = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
        print(f"成功获取 {symbol} 数据")

        # 数据处理
        stock_deal = stock_pre[['date', 'open', 'close', 'high', 'low', 'volume']].copy()
        stock_deal['date'] = pd.to_datetime(stock_deal['date'])
        stock_deal.set_index('date', inplace=True)
        print(f"{symbol} 数据处理完成")

        # 创建回测引擎
        data = bt.feeds.PandasData(dataname=stock_deal)
        cerebro = bt.Cerebro()
        cerebro.addstrategy(SMADerivativeStrategy)
        cerebro.adddata(data)
        cerebro.broker.setcash(setcash)

        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, annualize=True)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        # 运行回测
        result = cerebro.run()
        strat = result[0]

        # 打印策略表现
        ret_analyzer = strat.analyzers.returns.get_analysis()
        annual_return = ret_analyzer['rnorm100']

        sharpe_ratio = strat.analyzers.sharpe.get_analysis()['sharperatio']

        drawdown = strat.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown['max']['drawdown']

        trade_analyzer = strat.analyzers.trades.get_analysis()
        total_trades = trade_analyzer.total.closed

        print(f"\n{symbol} 策略表现:")
        print(f"开始资金: {setcash:.2f}")
        print(f"结束资金: {cerebro.broker.getvalue():.2f}")
        print(f"总收益率: {(cerebro.broker.getvalue() / setcash - 1) * 100:.2f}%")
        print(f"年化收益率: {annual_return:.2f}%")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"总交易次数: {total_trades}")

        # 生成图表
        fig = cerebro.plot(style='candle', volume=False)[0][0]
        fig.suptitle(f"{symbol} 回测结果", fontsize=16)
        plt.savefig(f"{symbol}_result.png", dpi=300)
        plt.close()
        print(f"已生成图表: {symbol}_result.png")

    except Exception as e:
        print(f"处理 {symbol} 时出错: {e}")

print("\n所有股票回测完成!")
#Btbu@093210