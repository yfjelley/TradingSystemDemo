import os
import datetime as dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from catalyst.exchange.utils.stats_utils import extract_transactions



def plot_single(perf, filepath = None):
	plt.figure(figsize=(20,10))
	ax1 = plt.subplot(411)
	perf.loc[:, ['cmx_pnl']].plot(ax=ax1)
	ax1.legend_.remove()
	ax1.set_ylabel('pnl\n(quote)')
	ymin, ymax = ax1.get_ylim()
	ax1.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	# Second chart: Plot asset price, moving averages and buys/sells
	ax2 = plt.subplot(412, sharex=ax1)
	perf.loc[:, ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']].plot(
	    ax=ax2,
	    label='Price')
	ax2.legend_.remove()
	ax2.set_ylabel('price')
	ymin, ymax = ax2.get_ylim()
	ax2.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	transaction_df = extract_transactions(perf)
	if transaction_df is not None and not transaction_df.empty:
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

	# Third chart: Plot our position
	position_series = perf['positions'].map(lambda x: x[0]['amount'] if len(x) > 0 else 0)
	# position_series -= self.context.risk_init_position
	ax3 = plt.subplot(413, sharex=ax1)
	position_series.plot(ax = ax3)
	ax3.set_ylabel('position\n(base)')
	ymin, ymax = ax3.get_ylim()
	ax3.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	# Fourth chart: Compare percentage change between our portfolio
	# and the price of the asset
	ax4 = plt.subplot(414, sharex=ax1)
	perf.loc[:, ['algorithm_period_return', 'price_change']].plot(ax=ax4)
	ax4.legend_.remove()
	ax4.set_ylabel('pct change')
	ymin, ymax = ax4.get_ylim()
	ax4.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	if filepath is not None:
		folder= os.path.dirname(os.path.abspath(filepath))
		if not os.path.exists(folder):
			os.makedirs(folder)
		plt.savefig(filepath, dpi = 300)

# perf = pd.read_pickle(r'C:\comics_data\xmreth-sim\record\xmreth-sim_local_backtest_1533773974.pickle')
# plot_single(perf, 'tmp.png')

def _concat(perf_a, perf_b, column = None):
	if perf_a is None:
		return perf_b
	if perf_b is None:
		return perf_a
	if column is not None:
		df = pd.concat([perf_a[column], perf_b[column]], axis = 1)
	else:
		df = pd.concat([perf_a, perf_b], axis = 1)
	df.fillna(method = 'ffill', inplace = True)
	df.columns = ['a', 'b']
	return df

def plot_double(perf_a, perf_b, titles = ['live', 'sim'], filepath = None):
	pnl_df   = _concat(perf_a, perf_b, 'cmx_pnl')
	price_df = _concat(perf_a, perf_b, 'price')
	fair_df  = _concat(perf_a, perf_b, 'fair_price')
	sig_long_df  = _concat(perf_a, perf_b, 'invent_long_entry')
	sig_short_df = _concat(perf_a, perf_b, 'invent_short_entry')

	pos_a  = perf_a['positions'].map(lambda x: x[0]['amount'] if len(x) > 0 else 0)
	pos_b  = perf_b['positions'].map(lambda x: x[0]['amount'] if len(x) > 0 else 0)
	pos_df = _concat(pos_a, pos_b)

	return_df  = _concat(perf_a, perf_b, 'algorithm_period_return')
	prc_chg_df = _concat(perf_a, perf_b, 'price_change')
 	###################################################################
	plt.figure(figsize = (20,10))
	ax1 = plt.subplot(421)
	pnl_df['a'].plot(ax=ax1)
	ax1.set_ylabel('pnl\n(quote)')
	ymin = pnl_df.min().min()
	ymax = pnl_df.max().max()
	ax1.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))
	ax1.set_title(titles[0])

	ax5 = plt.subplot(422, sharex=ax1)
	pnl_df['b'].plot(ax=ax5)
	ax5.set_ylabel('pnl\n(quote)')
	ax5.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))
	ax5.set_title(titles[1])

	# Second chart: Plot asset price, moving averages and buys/sells
	ax2 = plt.subplot(423, sharex=ax1)
	df = pd.concat([price_df['a'], fair_df['a'], sig_long_df['a'], sig_short_df['a']], axis = 1)
	df.columns = ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']
	df.plot(ax=ax2, label='Price')
	ax2.legend_.remove()
	ax2.set_ylabel('price')
	ymin = df.min().min()
	ymax = df.max().max()
	ax2.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	transaction_df = extract_transactions(perf_a)
	if transaction_df is not None and not transaction_df.empty:
		buy_df = transaction_df[transaction_df['amount'] > 0]
		sell_df = transaction_df[transaction_df['amount'] < 0]
		ax2.scatter(
					buy_df.index.to_pydatetime(),
					perf_a.loc[buy_df.index, 'price'],
					marker='^',
					s=100,
					c='green',
					label=''
					)
		ax2.scatter(
					sell_df.index.to_pydatetime(),
					perf_a.loc[sell_df.index, 'price'],
					marker='v',
					s=100,
					c='red',
					label=''
					)

	ax6 = plt.subplot(424, sharex=ax1)
	df = pd.concat([price_df['b'], fair_df['b'], sig_long_df['b'], sig_short_df['b']], axis = 1)
	df.columns = ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']
	df.plot(ax=ax6, label='Price')
	ax6.legend_.remove()
	ax6.set_ylabel('price')
	ax6.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	transaction_df = extract_transactions(perf_b)
	if transaction_df is not None and not transaction_df.empty:
		buy_df = transaction_df[transaction_df['amount'] > 0]
		sell_df = transaction_df[transaction_df['amount'] < 0]
		ax6.scatter(
					buy_df.index.to_pydatetime(),
					perf_b.loc[buy_df.index, 'price'],
					marker='^',
					s=100,
					c='green',
					label=''
					)
		ax6.scatter(
					sell_df.index.to_pydatetime(),
					perf_b.loc[sell_df.index, 'price'],
					marker='v',
					s=100,
					c='red',
					label=''
					)

	# Third chart: Plot our position
	ax3 = plt.subplot(425, sharex=ax1)
	pos_df['a'].plot(ax = ax3)
	ax3.set_ylabel('position\n(base)')
	ymin = pos_df.min().min()
	ymax = pos_df.max().max()
	ax3.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin)/ 5))

	ax7 = plt.subplot(426, sharex=ax1)
	pos_df['b'].plot(ax = ax7)
	ax7.set_ylabel('position\n(base)')
	ax7.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin)/ 5))

	# Fourth chart: Compare percentage change between our portfolio
	# and the price of the asset
	ax4 = plt.subplot(427, sharex=ax1)
	df = pd.concat([return_df['a'], prc_chg_df['a']], axis = 1)
	df.columns = ['algorithm_period_return', 'price_change']
	df.plot(ax=ax4)
	ax4.legend_.remove()
	ax4.set_ylabel('returns')
	ymin = df.min().min()
	ymax = df.max().max()
	ax4.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	ax8 = plt.subplot(428, sharex=ax1)
	df = pd.concat([return_df['b'], prc_chg_df['b']], axis = 1)
	df.columns = ['algorithm_period_return', 'price_change']
	df.plot(ax=ax8)
	ax8.legend_.remove()
	ax8.set_ylabel('returns')
	ax8.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	if filepath is not None:
		folder= os.path.dirname(os.path.abspath(filepath))
		if not os.path.exists(folder):
			os.makedirs(folder)
		plt.savefig(filepath, dpi = 300)

# perf_a = pd.read_pickle(r'C:\comics_data\xmreth-sim\record\xmreth-sim_local_backtest_1533773974.pickle')
# perf_b = pd.read_pickle(r'C:\comics_data\xmreth-sim\record\xmreth-sim_local_backtest_1533771766.pickle')
# plot_double(perf_a, perf_b, titles = ['a', 'b'], filepath = 'tmp.png')