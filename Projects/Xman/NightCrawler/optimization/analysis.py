import pandas as pd
import os
import datetime as dt

def pickle_resample(df, tdelta):
	res = []
	t0 = df.index[0]
	t1 = t0 + tdelta
	while t1 < df.index[-1]:
		df_slice = df[(df.index >= t0) & (df.index < t1)]
		pnl = df_slice['portfolio_value'] - df_slice['portfolio_value'].iloc[0]
		dd = pnl.min()
		end_pnl = pnl.iloc[-1]
		res.append([t1.date(), end_pnl, dd])
		t0 = t1
		t1 += tdelta
	out_df = pd.DataFrame(res, columns = ['ts', 'pnl', 'dd'])
	out_df.set_index('ts', inplace = True)
	return out_df

def get_stats(res_df):
	days = len(res_df)
	mean = res_df.pnl.mean()
	total = res_df.pnl.sum()
	sharpe = res_df.pnl.mean() / res_df.pnl.std()
	win_rate = len(res_df[res_df['pnl'] >= 0]) / len(res_df)
	dd = res_df.dd.min()
	return{'days':days, 'mean':mean, 'total':total, 'sharpe':sharpe, 'win_rate':win_rate, 'dd':dd}

namespace = 'nightcrawler'
instances = range(815001, 815017)
folder = r'C:\comics_data\{}\record'.format(namespace)
stat_df = []
index = []
for i in instances:
	df = pd.DataFrame()
	for f in os.listdir(folder):
		prefix = '{}_{}_backtest'.format(namespace, i)
		if prefix in f and 'pickle' in f:
			perf = pd.read_pickle(os.path.join(folder, f)) # read in perf DataFrame
			perf_daily = pickle_resample(perf, dt.timedelta(days = 1))
			df = pd.concat([df, perf_daily], axis = 0)

	df = df[ ~ df.index.duplicated(keep = 'first')]
	df.sort_index(inplace = True)
	df.to_csv('{}_daily.csv'.format(i))

	stats = get_stats(df)
	stat_df.append(stats)
	index.append(i)
	for k,v in stats.items():
		print(k,v)
stat_df = pd.DataFrame(stat_df, index = index)
print(stat_df)