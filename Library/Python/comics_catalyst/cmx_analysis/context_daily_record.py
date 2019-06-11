import pandas as pd
import datetime as dt
import os
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[1]
import sys
sys.path.append(os.path.join(cmx_rootpath,'comics_crypto_compare'))
sys.path.append(os.path.join(cmx_rootpath,'comics_crypto_compare/*'))
import matplotlib.pyplot as plt

if os.path.exists('c:'):
	ROOT_DISK = 'c:'
	SYSTEM_OS = 'windows'
else:
	ROOT_DISK = '/home/frankwang_trading'
	SYSTEM_OS = 'linux'

class outright_record:
	def __init__(self, namespace, instance, mode):
		self.namespace = namespace
		self.instance = instance
		self.mode = mode # 'live, paper', 'backtest'
		if self.mode == 'live':
			if SYSTEM_OS == 'windows':
				self.in_folder = os.path.join(ROOT_DISK, '/Users/Penny/.catalyst/data/live_algos/{}/frame_stats'.format(self.namespace))
			else:
				self.in_folder = os.path.join(ROOT_DISK, '/.catalyst/data/live_algos/{}/frame_stats'.format(self.namespace))
		elif self.mode == 'paper':
			if SYSTEM_OS == 'windows':
				self.in_folder = os.path.join(ROOT_DISK, '/Users/Penny/.catalyst/data/live_algos/{}_sim/frame_stats'.format(self.namespace))
			else:
				self.in_folder = os.path.join(ROOT_DISK, '/.catalyst/data/live_algos/{}_sim/frame_stats'.format(self.namespace))
		else:
			self.in_folder = os.path.join(ROOT_DISK, '/comics_data/{}/record'.format(self.namespace))

		self.out_trade_folder = os.path.join(ROOT_DISK, '/comics_data/{}/{}/trade'.format(self.namespace, self.instance))
		self.out_snapshot_folder = os.path.join(ROOT_DISK, '/comics_data/{}/{}/snapshot'.format(self.namespace, self.instance))
		if not os.path.exists(self.out_trade_folder):
			os.makedirs(self.out_trade_folder)
		if not os.path.exists(self.out_snapshot_folder):
			os.makedirs(self.out_snapshot_folder)
		self.file_prefix = '_'.join([str(x) for x in [self.namespace, self.instance, self.mode]])

	def _get_backtest_pickles(self):
		pickles = []
		for f in os.listdir(self.in_folder):
			if '.pickle' in f and self.file_prefix in f:
				pickles.append(f)
		return pickles

	def _get_trade_df(self, catalyst_df):
		trade_df = pd.DataFrame(columns = ['symbol', 'amount', 'side', 'price', 'fee', 'fee_coin', 'position', 'cost_basis'])
		for i in range(len(catalyst_df)):
			trades = catalyst_df['transactions'][i]
			if len(trades) == 0:
				continue
			if len(catalyst_df['positions'][i]) != 0:
				position = catalyst_df['positions'][i][0]['amount']
				cost_basis = catalyst_df['positions'][i][0]['cost_basis']
			else:
				position = 0
				cost_basis = 0
			for t in trades:
				ts = t['dt']
				symbol = t['sid']
				amount = t['amount']
				side = 'buy' if amount > 0 else 'sell'
				price = t['price']
				fee   = t['commission']
				fee_coin = t['fee_currency']
				trade_df.loc[ts] = [symbol, amount, side, price, fee, fee_coin, position, cost_basis]
		if len(trade_df) == 0:
			if len(catalyst_df['positions'][-1]) != 0:
				position = catalyst_df['positions'][-1][0]['amount']
				cost_basis = catalyst_df['positions'][-1][0]['cost_basis']
			else:
				position = 0
				cost_basis = 0
			trade_df.loc[catalyst_df.index[-1]] = [None, 0, None, 0, 0, None, position, cost_basis]
		return trade_df

	def _save_df_to_file(self, df, filepath, columns = None):
		if os.path.exists(filepath):
			old_df = pd.read_csv(filepath, header = 0, index_col = 0, parse_dates = True)
			old_df.index = old_df.index.map(lambda x: x.replace(tzinfo = None))
			if len(old_df) != 0:
				new_df = df[df.index > old_df.index[-1]]
			else:
				new_df = df.copy()
			new_df.index = new_df.index.map(lambda x: x.replace(tzinfo = None))
			new_df = pd.concat([old_df, new_df], axis = 0)
			new_df.sort_index(inplace = True)
			if columns is not None:
				new_df = new_df[columns]
			new_df.to_csv(filepath, index_label = 'ts')
		else:
			df[columns].to_csv(filepath, index_label = 'ts')

	def _save_daily_from_df(self, df):
		# split df by days, save sanp and trade using df data
		start = df.index[0]
		end   = dt.datetime.combine(start.date() + dt.timedelta(days = 1), dt.time(0,0))
		cur_df = df[(df.index >= start) & (df.index <= end)]
		while len(cur_df) != 0:
			snapshot_df = cur_df[['price', 'fair_price', 'zscore', 'base_pos', 'pnl']]
			cost_basis = cur_df['positions'].map(lambda x: x[0]['cost_basis'] if len(x) != 0 else 0)
			catalyst_pos = cur_df['positions'].map(lambda x: x[0]['amount'] if len(x) != 0 else 0)
			snapshot_df.loc[:, 'cost_basis'] = cost_basis
			snapshot_df.loc[:, 'catalyst_pos'] = catalyst_pos
			snapshot_file = '{}_{}.snapshot.csv'.format(self.file_prefix, end.date())
			self._save_df_to_file(
								  snapshot_df, 
								  os.path.join(self.out_snapshot_folder, snapshot_file), 
								  ['price', 'fair_price', 'zscore', 'base_pos', 'pnl', 'catalyst_pos', 'cost_basis']
								  )

			trade_df = self._get_trade_df(cur_df)
			trade_file = '{}_{}.trade.csv'.format(self.file_prefix, end.date())
			self._save_df_to_file(
								  trade_df,
								  os.path.join(self.out_trade_folder, trade_file),
								  ['symbol', 'amount', 'side', 'price', 'fee', 'fee_coin', 'position', 'cost_basis']
								  )
			start = end + dt.timedelta(minutes = 1)
			end  += dt.timedelta(days = 1)
			cur_df = df[(df.index >= start) & (df.index <= end)]

	def save_backtest_by_days(self, start, end):
		pickles = self._get_backtest_pickles()
		for p in pickles:
			df = pd.read_pickle(os.path.join(self.in_folder, p))
			df = df[(df.index >= start) & (df.index <= end)]
			if len(df) == 0:
				continue
			self._save_daily_from_df(df)

	def _convert_raw_to_df(self, raw_data):
		if raw_data is None or len(raw_data) == 0:
			return None
		df = pd.DataFrame([raw_data[0]], index = [0])
		for i in range(1, len(raw_data)):
			df.loc[i] = raw_data[i]
		df.set_index('period_close', inplace = True)
		return df

	def save_live_by_days(self, start, end):
		cur_ts = start
		while cur_ts <= end:
			pfile = '{}.p'.format(cur_ts.date())
			if os.path.exists(os.path.join(self.in_folder, pfile)):
				raw_data = pd.read_pickle(os.path.join(self.in_folder, pfile))
				catalyst_df = self._convert_raw_to_df(raw_data)
				self._save_daily_from_df(catalyst_df)
			cur_ts += dt.timedelta(days = 1)


contexts = ['nightcrawler', 'changeling', 'cyclops', 'polaris', 'sway', 'havok', 'cannonball', 'colossus', 'cecilia', 'husk', 'sunfire']
for c in contexts:
	my_record = outright_record(c, 'xman-live-c1', 'live')
	my_record.save_live_by_days(dt.datetime(2018,8,2), dt.datetime(2018,9,19))
	my_record = outright_record(c, 'xman-live-c1', 'paper')
	my_record.save_live_by_days(dt.datetime(2018,8,2), dt.datetime(2018,9,19))
# f = r'C:\Users\Penny\.catalyst\data\live_algos\sway\frame_stats\2018-09-13.p'
# raw = pd.read_pickle(f)
# df = my_record._convert_raw_to_df(raw)
# df.set_index('period_close', inplace = True)
# df.to_csv('test_live.csv')
# print(df.tail())

# df = pd.DataFrame(columns = ['trans', 'pos'])
# for r in raw:
# 	ts = r['period_open']
# 	tran = r['transactions']
# 	pos = r['positions']
# 	df.loc[ts] = [tran, pos]

# print(df)
# df.to_csv('test_live.csv')

# my_record = outright_record('changeling-opt', 917000, 'backtest')
# my_record.save_backtest_by_days(dt.datetime(2018,8,1), dt.datetime(2018,8,5))

# f = r'C:\comics_data\changeling-opt\record\changeling-opt_917000_backtest_1537258077_1019.pickle'
# df = pd.read_pickle(f)
# for i in range(len(df)):
# 	if df['positions'][i] is None or len(df['positions'][i]) == 0:
# 		print(df.iloc[i])

# df[(df.index >= dt.datetime(2018,8,2)) & (df.index <= dt.datetime(2018,8,3))].to_csv('test-sim.csv')
# print(df['positions'].iloc[:10])
# print(type(df['positions'][0]), len(df['positions'][0]))

# trade_df = my_record._get_trade_df(df)
# print(trade_df)

# df.to_csv('test_sim.csv')

