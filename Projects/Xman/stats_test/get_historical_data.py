import os
import numpy as np
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[2]
import sys
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare'))
sys.path.append(os.path.join(cmx_rootpath,'Library/Python/comics_crypto_compare/*'))
import hist_data

start = dt.datetime(2018,9,5)
end   = dt.datetime(2018,9,9)
# minutes_data = hist_data.get_minute_df('xem'.upper(), 'eth'.upper(), start, end)
daily_data = hist_data.get_daily_df('btc'.upper(), 'usdt'.upper(), start, end)
hourly_data = hist_data.get_hourly_df('btc'.upper(), 'usdt'.upper(), start, end)
print(daily_data)


# def get_pair_signal(coin_a, coin_b, quote, start, end, rev_corr = False):
# 	# if coin_a == quote or coin_b == quote:
# 	# 	return None
# 	if quote == 'ETH':
# 		if coin_a == 'BTC':
# 			ohlcv_a = 1 / hist_data.get_hourly_df(quote, coin_a, start, end)
# 			ohlcv_b = hist_data.get_hourly_df(coin_b, quote, start, end)
# 		elif coin_b == 'BTC':
# 			ohlcv_a = hist_data.get_hourly_df(coin_a, quote, start, end)
# 			ohlcv_b = 1 / hist_data.get_hourly_df(quote, coin_b, start, end)
# 		else:
# 			ohlcv_a = hist_data.get_hourly_df(coin_a, quote, start, end)
# 			ohlcv_b = hist_data.get_hourly_df(coin_b, quote, start, end)
# 	else:
# 		ohlcv_a = hist_data.get_hourly_df(coin_a, quote, start, end)
# 		ohlcv_b = hist_data.get_hourly_df(coin_b, quote, start, end)

# 	if ohlcv_a is None or ohlcv_b is None:
# 		return None
# 	price_a = ohlcv_a['close']
# 	price_b = ohlcv_b['close']
# 	price_df = pd.concat([price_a, price_b], axis = 1)
# 	price_df.columns = ['a', 'b']
# 	price_df.fillna(method = 'ffill', inplace = True)
# 	price_df.dropna(axis = 0, inplace = True)

# 	ror_df = price_df / price_df.iloc[0, :] - 1
# 	if rev_corr:
# 		signal = ror_df['a'] + ror_df['b']
# 	else:
# 		signal = ror_df['a'] - ror_df['b']
# 	return signal


# def get_stats(coins, quote, start, end, rev_corr = False):
# 	result = []
# 	for i in range(len(coins)):
# 		for j in range(i, len(coins)):
# 			ca = coins[i]
# 			cb = coins[j]
# 			if ca == cb: continue
# 			signal = get_pair_signal(ca, cb, quote, start, end, rev_corr)
# 			if signal is None:
# 				continue
# 			try:
# 				adf = adfuller(signal)[1]
# 			except Exception as e:
# 				print(e)
# 				adf = None
# 			std = np.std(signal)
# 			result.append(['{}.{}'.format(ca, cb), adf, std])
# 	return result

# if __name__ == '__main__':
# 	coins = hist_data.get_top_coins_by_mkt_cap(top = 20)
# 	print(coins)
# 	quotes = ['BTC', 'ETH', 'USDT']
# 	# quotes = ['USDT']
# 	rev_corr = True
# 	for quote in quotes:
# 		start = dt.datetime(2018,2,2)
# 		end = dt.datetime(2018,5,1)
# 		stats = get_stats(coins, quote, start, end, rev_corr)
# 		stats = pd.DataFrame(stats, columns = ['symbol', 'adf', 'std'])
# 		stats.set_index('symbol', inplace = True)
# 		print(stats)
# 		if rev_corr:
# 			stats.to_csv('hourly_neg_stats_on_{}_{}_{}.csv'.format(quote, start.date(), end.date()))
# 		else:
# 			stats.to_csv('hourly_posi_stats_on_{}_{}_{}.csv'.format(quote, start.date(), end.date()))
