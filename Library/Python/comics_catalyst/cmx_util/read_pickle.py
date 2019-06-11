import pandas as pd

f = r'C:\Users\Penny\.catalyst\data\live_algos\sway\frame_stats\2018-09-16.p'
# f = r'C:\Users\Penny\.catalyst\data\live_algos\changeling\cumulative_performance_live.p'
raw = pd.read_pickle(f)
df = pd.DataFrame(columns = ['trans', 'pos'])
for r in raw:
	ts = r['period_open']
	tran = r['transactions']
	pos = r['positions']
	df.loc[ts] = [tran, pos]

print(df)
df.to_csv('test.csv')