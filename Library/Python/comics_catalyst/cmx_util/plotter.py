import numpy as np
# import matplotlib
# matplotlib.use('agg')
import matplotlib.pyplot as plt
plt.switch_backend('agg')
from catalyst.exchange.utils.stats_utils import extract_transactions
import pandas as pd
import logging

class multileg_plotter:
	def __init__(self, context):
		self.context = context

	def plot(self, perf):
		if not self.context.cmx_config.plot_fig:
			return False
		plt.figure(figsize=(20,10))
		plt.subplot(411)
		plt.plot(perf.index, perf['cmx_pnl'])
		plt.ylabel('pnl\n({})'.format(self.context.cmx_config.risk_quote_currency))
		plt.xlim(perf.index[0], perf.index[-1])
		plt.xticks([],[])

		# Second chart: Plot asset price, moving averages and buys/sells
		plt.subplot(412)
		signal = perf['cmx_signal']
		mean   = perf['cmx_signal_mean']
		std    = perf['cmx_signal_std']
		lower0 = mean - self.context.cmx_config.invent_e0 * std
		lower1 = mean - self.context.cmx_config.invent_en * std
		upper0 = mean + self.context.cmx_config.invent_e0 * std
		upper1 = mean + self.context.cmx_config.invent_en * std
		df = pd.concat([signal, mean, lower0, lower1, upper0, upper1], axis = 1)
		plt.plot(perf.index, df)
		plt.ylabel('signal\n(ror)')
		plt.xlim(perf.index[0], perf.index[-1])
		plt.xticks([],[])

		# third chart: Plot our cash
		plt.subplot(413)
		position_df = pd.DataFrame(list(perf['cmx_positions'])) - self.context.cmx_config.risk_init_positions
		position_df.columns = self.context.cmx_config.str_symbols
		plt.plot(perf.index, position_df)
		plt.ylabel('positions')
		plt.legend(position_df.columns)
		plt.xlim(perf.index[0], perf.index[-1])
		plt.xticks([],[])

		# Forth chart: Plot rors
		plt.subplot(414)
		price_df = pd.DataFrame(list(perf['cmx_prices']))
		price_df.columns = self.context.cmx_config.str_symbols
		ror_df = price_df / price_df.iloc[0] - 1
		plt.plot(perf.index, ror_df)
		plt.legend(ror_df.columns)
		plt.xlim(perf.index[0], perf.index[-1])
		plt.ylabel('prices')

		plt.savefig(self.context.cmx_config.plot_file, dpi = 300)
		# self.context.cmx_logger.log_plot_info()

class outright_plotter:
	def __init__(self, context):
		self.context = context

	def plot(self, perf):
		if not self.context.plot_fig:
			return False
		plt.figure(figsize=(20,10))
		ax1 = plt.subplot(411)
		perf.loc[:, ['cmx_pnl']].plot(ax=ax1)
		ax1.legend_.remove()
		ax1.set_ylabel('pnl\n({})'.format(self.context.quote_currency))
		ymin, ymax = ax1.get_ylim()
		ax1.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 4))

		# Second chart: Plot asset price, moving averages and buys/sells
		ax2 = plt.subplot(412, sharex=ax1)
		perf.loc[:, ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']].plot(
		    ax=ax2,
		    label='Price')
		ax2.legend_.remove()
		ax2.set_ylabel('price\n({})'.format(self.context.symbol_str))
		ymin, ymax = ax2.get_ylim()
		ax2.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 4))

		transaction_df = extract_transactions(perf)
		try:
			if not transaction_df.empty:
				buy_df = transaction_df[transaction_df['amount'] > 0]
				sell_df = transaction_df[transaction_df['amount'] < 0]
				ax2.scatter(
							buy_df.index.to_pydatetime(),
							perf.loc[buy_df.index, 'price'],
							marker='^',
							s=100,
							c='green',
							label=''
							)
				ax2.scatter(
							sell_df.index.to_pydatetime(),
							perf.loc[sell_df.index, 'price'],
							marker='v',
							s=100,
							c='red',
							label=''
							)
		except Exception as e:
			self.context.cmx_logger.log_error(e)


		# Third chart: Compare percentage change between our portfolio
		# and the price of the asset
		ax3 = plt.subplot(413, sharex=ax1)
		perf.loc[:, ['algorithm_period_return', 'price_change']].plot(ax=ax3)
		ax3.legend_.remove()
		ax3.set_ylabel('pct change')
		ymin, ymax = ax3.get_ylim()
		ax3.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 4))

		# Fourth chart: Plot our cash
		position_series = perf['positions'].map(lambda x: x[0]['amount'] if len(x) > 0 else 0)
		position_series -= self.context.risk_init_position if self.context.risk_init_position is not None else 0
		ax4 = plt.subplot(414, sharex=ax1)
		position_series.plot(ax = ax4)
		ax4.set_ylabel('position\n({})'.format(self.context.base_currency))
		ymin, ymax = ax4.get_ylim()
		ax4.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 4))

		plt.savefig(self.context.plot_file, dpi = 300)
		self.context.cmx_logger.log_plot_info()
