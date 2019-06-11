import pandas as pd

def concat_perf(perf_a, perf_b, column = None):
	if perf_a is None:
		return perf_b
	if perf_b is None:
		return perf_a
	if column is not None:
		df = pd.concat([perf_a[column], perf_b[column]], axis = 1)
	else:
		df = pd.concat([perf_a, perf_b], axis = 1)
	df.fillna(method = 'ffill', inplace = True)
	df.dropna(axis = 0, inplace = True)
	df.columns = ['a', 'b']
	return df