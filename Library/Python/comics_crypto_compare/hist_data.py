import crypto_compare_url_parser as cc_api
import datetime as dt
import pandas as pd
import os
# import matplotlib.pyplot as plt

# Instruction: 2018-11-3
# 1. all timestamps are in UTC
# 2. latest available hourly and minute data is around 2-hr before utcnow()

def root_path():
    return os.path.abspath(os.sep)
# CACHE_PATH = root_path()
if os.path.exists('/Volumes/Tamedog_2T/AirPort_Work/'):
	CACHE_PATH = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/historical/crypto_compare/tmp'
else:
	CACHE_PATH = None
if CACHE_PATH and not os.path.exists(CACHE_PATH):
	os.makedirs(CACHE_PATH)

def get_coin_df():
	coin_list = cc_api.get_coin_list()
	columns = []
	for coin in coin_list.keys():
		columns = list(set(columns + list(coin_list[coin].keys())))

	df = pd.DataFrame(columns = columns)
	for coin in coin_list.keys():
		df.loc[coin] = pd.Series(coin_list[coin])
	return df
# df = get_coin_df()
# print(df)
# df.to_csv('coin_df.csv')

def get_mkt_cap_df(filepath = None):
	if filepath is None:
		folder = CACHE_PATH
		filepath = os.path.join(folder, 'coin_market_cap.csv')
	# df = pd.read_csv(filepath, header = 0).replace('$?', '0').replace('[\$,]', '', regex=True)
	df = pd.read_csv(filepath, header = 0)
	df['Market Cap'] = df['Market Cap'].astype(float)
	df.set_index('Symbol', inplace = True)
	df.sort_values(by = 'Market Cap', ascending = False, inplace = True)
	return df
# df = get_mkt_cap_df()
# print(df)

def get_top_coins_by_mkt_cap(top = 20):
	df = get_mkt_cap_df()
	symbols = list(df.index)[:top]
	symbols = [x if x != 'MIOTA' else 'IOTA' for x in symbols]
	return symbols
# print(get_top_coins_by_mkt_cap())

def save_daily(base, quote, start, end, exchange = 'CCCAGG', filepath = None, overwritten = False):
	if filepath is None:
		filepath = os.path.join(CACHE_PATH, '{}_{}_daily.csv'.format(base, quote))
	df = None
	if not overwritten and os.path.exists(filepath):
		df = pd.read_csv(filepath, header = 0, index_col = 0)
        

def _get_single_product_df(base, quote, start, end, bartype, exchange = 'CCCAGG'):
	# ts is at the left (beginning) border
	if base == quote:
		if isinstance(start, dt.date):
			start = dt.datetime.combine(start, dt.time(0,0))
		if isinstance(end, dt.date):
			end = dt.datetime.combine(end, dt.time(0,0))
		df = pd.DataFrame([[1] * 4 + [0,0]], columns = ['close','high', 'low', 'open', 'volumefrom', 'volumeto'], index = [start, end])
		if bartype == 'hourly' or bartype == 'hour':
			df = df.resample('1H').ffill()
		elif bartype == 'minute':
			df = df.resample('1T').ffill()
		return df
	if bartype == 'daily' or bartype == 'day':
		raw_data = cc_api.get_hist_daily(base, quote, start, end, exchange = exchange)	
	elif bartype == 'hourly' or bartype == 'hour':
		raw_data = cc_api.get_hist_hourly(base, quote, start, end, exchange = exchange)	
	elif bartype == 'minute':
		raw_data = cc_api.get_hist_minute(base, quote, start, end, exchange = exchange)	
	else:
		raw_data = None

	if raw_data is None:
		return None
	df = pd.DataFrame(raw_data['Data'])
	df.sort_values(by = 'time', ascending = True)
	df.set_index('time', inplace = True)
	df.index = df.index.map(dt.datetime.utcfromtimestamp)
	# df.index = df.index.map(dt.datetime.fromtimestamp)
	return df

def get_daily_df(base, quote, start, end, exchange = 'CCCAGG'):
	return _get_single_product_df(base, quote, start, end, 'daily', exchange)
# df = get_daily_df('BTC', 'USD', dt.date(2018,7,20), dt.date(2017,7,22))

def get_hourly_df(base, quote, start, end, exchange = 'CCCAGG'):
	return _get_single_product_df(base, quote, start, end, 'hourly', exchange)

def get_minute_df(base, quote, start, end, exchange = 'CCCAGG'):
	return _get_single_product_df(base, quote, start, end, 'minute', exchange)

def get_daily_close_price_df(symbols, quote, start, end, exchange = 'CCCAGG'):
	close_df = pd.DataFrame()
	for sym in symbols:
		if sym == quote:
			close_df[sym] = 1
			continue
		df = get_daily_df(sym, quote, start, end, exchange)
		if df is None:
			close_df[sym] = None
		else:
			close_df[sym] = df['close']
	return close_df
# df = get_daily_close_price_df(['BTC', 'ETH'], 'BTC', dt.date(2018,7,10), dt.date(2018,7,22))
# print(df)

def get_daily_volume_df_in_quote(symbols, quote, start, end, exchange = 'CCCAGG'):
	volume_df = pd.DataFrame()
	for sym in symbols:
		if sym == quote:
			volume_df[sym] = 1
			continue
		df = get_daily_df(sym, quote, start, end, exchange)
		if df is None:
			volume_df[sym] = None
		else:
			volume_df[sym] = df['volumeto']
	return volume_df

def get_daily_volume_df_in_base(symbols, quote, start, end, exchange = 'CCCAGG'):
	volume_df = pd.DataFrame()
	for sym in symbols:
		if sym == quote:
			volume_df[sym] = 1
			continue
		df = get_daily_df(sym, quote, start, end, exchange)
		if df is None:
			volume_df[sym] = None
		else:
			volume_df[sym] = df['volumefrom']
	return volume_df

def get_hourly_close_price_df(symbols, quote, start, end, exchange = 'CCCAGG'):
	close_df = pd.DataFrame()
	for sym in symbols:
		if sym == quote:
			close_df[sym] = 1
			continue
		df = get_hourly_df(sym, quote, start, end, exchange)
		if df is None:
			close_df[sym] = None
		else:
			close_df[sym] = df['close']
	return close_df

def get_top_daily_close_price_df(quote, start, end, exchange = 'CCCAGG', top = 20):
	symbols = get_top_coins_by_mkt_cap(top)
	return get_daily_close_price_df(symbols, quote, start, end, exchange)

def get_top_daily_volume_df(quote, start, end, exchange = 'CCCAGG', top = 20):
	symbols = get_top_coins_by_mkt_cap(top)
	return get_daily_volume_df_in_quote(symbols, quote, start, end, exchange)

def get_top_hourly_close_price_df(quote, start, end, exchange = 'CCCAGG', top = 20):
	symbols = get_top_coins_by_mkt_cap(top)
	return get_hourly_close_price_df(symbols, quote, start, end, exchange)

# start = dt.datetime(2016,12,2)
# end = dt.datetime(2018,12,1)
# # df = get_top_hourly_close_price_df('BTC', start, end, top = 50)
# # df = get_top_daily_close_price_df('BTC', start, end, top = 50)
# df = get_top_daily_volume_df('BTC', start, end, top = 50)
# print(df)
# df.to_csv('top50_daily_volume_in_btc_{}_{}.csv'.format(start.date(), end.date()))






