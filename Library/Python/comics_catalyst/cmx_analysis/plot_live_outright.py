import os
import datetime as dt
import numpy as np
import pandas as pd
# import matplotlib
# matplotlib.use('agg')
import matplotlib.pyplot as plt
from util import concat_perf

def plot_single(perf, filepath = None):
	if perf is None or len(perf) == 0:
		return
	symbol = perf['symbol'].iloc[-1]
	base_sym, quote_sym = symbol.split('_')

	plt.figure(figsize=(20,10))
	ax1 = plt.subplot(311)
	perf.loc[:, ['pnl']].plot(ax=ax1)
	ax1.legend_.remove()
	ax1.set_ylabel('pnl\n({})'.format(quote_sym))
	ymin, ymax = ax1.get_ylim()
	ax1.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	# Second chart: Plot asset price, moving averages and buys/sells
	ax2 = plt.subplot(312, sharex=ax1)
	perf.loc[:, ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']].plot(
	    ax=ax2,
	    label='Price')
	ax2.legend_.remove()
	ax2.set_ylabel('price')
	ymin, ymax = ax2.get_ylim()
	ax2.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	# Third chart: Plot our position
	position_series = perf['base_pos']
	ax3 = plt.subplot(313, sharex=ax1)
	position_series.plot(ax = ax3)
	ax3.set_ylabel('position\n({})'.format(base_sym))
	ymin, ymax = ax3.get_ylim()
	ax3.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	if filepath is not None:
		folder= os.path.dirname(os.path.abspath(filepath))
		if not os.path.exists(folder):
			os.makedirs(folder)
		plt.savefig(filepath, dpi = 300)
		plt.close()

# pd.read_csv(r'C:\Users\Penny\.catalyst\data\live_algos\changeling\stats_live\20180809.csv', index_col = 0, parse_dates = True)
# plot_single(perf, 'tmp.png')



def plot_double(perf_a, perf_b, titles = ['live', 'sim'], filepath = None):
	if (perf_a is None or len(perf_a) == 0) and (perf_b is None or len(perf_b) == 0):
		return
	if perf_a is not None and len(perf_a) > 0 and 'symbol' in perf_a.columns:
		symbol = perf_a['symbol'].dropna().iloc[-1]
		base_sym, quote_sym = symbol.split('_')
	elif perf_b is not None and len(perf_b) > 0 and 'symbol' in perf_b.columns:
		symbol = perf_b['symbol'].dropna().iloc[-1]
		base_sym, quote_sym = symbol.split('_')
	else:
		return
	pnl_df   = concat_perf(perf_a, perf_b, 'pnl')
	pnl_df = pnl_df - pnl_df.iloc[0]
	price_df = concat_perf(perf_a, perf_b, 'price')
	fair_df  = concat_perf(perf_a, perf_b, 'fair_price')
	sig_long_df  = concat_perf(perf_a, perf_b, 'invent_long_entry')
	sig_short_df = concat_perf(perf_a, perf_b, 'invent_short_entry')
	pos_df = concat_perf(perf_a, perf_b, 'base_pos')
 	###################################################################
	plt.figure(figsize = (20,10))
	ax1 = plt.subplot(321)
	pnl_df['a'].plot(ax=ax1)
	ax1.set_ylabel('pnl\n({})'.format(quote_sym))
	ymin = min(pnl_df.min().min(), 0)
	ymax = max(pnl_df.max().max(), 0)
	ax1.set_title(titles[0])
	if not np.isnan(ymin) and not np.isnan(ymax):
		ax1.set_ylim(ymin, ymax)
		if ymin != ymax:
			ax1.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))
	

	ax5 = plt.subplot(322, sharex=ax1)
	pnl_df['b'].plot(ax=ax5)
	ax5.set_ylabel('pnl\n({})'.format(quote_sym))
	if not np.isnan(ymin) and not np.isnan(ymax):
		ax5.set_ylim(ymin, ymax)
		if ymin != ymax:
			ax5.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))
	ax5.set_title(titles[1])

	# Second chart: Plot asset price, moving averages and buys/sells
	ax2 = plt.subplot(323, sharex=ax1)
	df = pd.concat([price_df['a'], fair_df['a'], sig_long_df['a'], sig_short_df['a']], axis = 1)
	df.columns = ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']
	df.plot(ax=ax2, label='Price')
	ax2.legend_.remove()
	ax2.set_ylabel('price')
	ymin = df.min().min()
	ymax = df.max().max()
	if not np.isnan(ymin) and not np.isnan(ymax):
		ax2.set_ylim(ymin, ymax)
		if ymin != ymax:
			ax2.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	ax6 = plt.subplot(324, sharex=ax1)
	df = pd.concat([price_df['b'], fair_df['b'], sig_long_df['b'], sig_short_df['b']], axis = 1)
	df.columns = ['price', 'fair_price', 'invent_long_entry', 'invent_short_entry']
	df.plot(ax=ax6, label='Price')
	ax6.legend_.remove()
	ax6.set_ylabel('price')
	if not np.isnan(ymin) and not np.isnan(ymax):
		ax6.set_ylim(ymin, ymax)
		if ymin != ymax:
			ax6.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin) / 5))

	# Third chart: Plot our position
	ax3 = plt.subplot(325, sharex=ax1)
	pos_df['a'].plot(ax = ax3)
	ax3.set_ylabel('position\n({})'.format(base_sym))
	ymin = min(pos_df.min().min(), 0)
	ymax = max(pos_df.max().max(), 0)
	if not np.isnan(ymin) and not np.isnan(ymax):
		ax3.set_ylim(ymin, ymax)
		if ymin != ymax:
			ax3.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin)/ 5))

	ax7 = plt.subplot(326, sharex=ax1)
	pos_df['b'].plot(ax = ax7)
	ax7.set_ylabel('position\n({})'.format(base_sym))
	if not np.isnan(ymin) and not np.isnan(ymax):
		ax7.set_ylim(ymin, ymax)
		if ymin != ymax:
			ax7.yaxis.set_ticks(np.arange(ymin, ymax, (ymax - ymin)/ 5))

	if filepath is not None:
		folder= os.path.dirname(os.path.abspath(filepath))
		if not os.path.exists(folder):
			os.makedirs(folder)
		plt.savefig(filepath, dpi = 300)
		plt.close()

# perf_a = pd.read_csv(r'C:\Users\Penny\.catalyst\data\live_algos\changeling\stats_live\20180808.csv', index_col = 0, parse_dates = True)
# perf_b = pd.read_csv(r'C:\Users\Penny\.catalyst\data\live_algos\changeling-sim\stats_paper\20180808.csv', index_col = 0, parse_dates = True)
# plot_double(perf_a, perf_b, titles = ['live', 'paper'], filepath = 'tmp.png')

# perf_a = pd.read_csv(r'C:\Users\Penny\.catalyst\data\live_algos\nightcrawler\stats_live\20180808.csv', index_col = 0, parse_dates = True)
# perf_b = pd.read_csv(r'C:\Users\Penny\.catalyst\data\live_algos\nightcrawler-sim\stats_paper\20180808.csv', index_col = 0, parse_dates = True)
# plot_double(perf_a, perf_b, titles = ['live', 'paper'], filepath = 'tmp2.png')