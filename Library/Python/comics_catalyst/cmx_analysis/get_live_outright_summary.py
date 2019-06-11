import os
import datetime as dt
import numpy as np
import pandas as pd
from util import concat_perf

def _get_traded(pos_df):
	df = pos_df - pos_df.shift(1)
	return df.abs().sum()

def single_summary(perf, title = 'live'):
	pnl = perf['pnl']
	pos = perf['base_pos']
	dd = (pnl - pnl.iloc[0]).min()
	df = pd.DataFrame([[pnl.iloc[-1] - pnl.iloc[0], dd, _get_traded(pos), pnl.iloc[0], pnl.iloc[-1], pos.max(), pos.min()]])
	df.columns = ['pnl', 'dd', 'traded', 'init_pnl', 'end_pnl', 'max_pos', 'min_pos']
	df.index = [title]
	return df

def double_summary(perf_a, perf_b, titles = ['live', 'sim']):
	pnl = concat_perf(perf_a, perf_b, 'pnl')
	pos = concat_perf(perf_a, perf_b, 'base_pos')

	df_a = pd.concat([pnl['a'], pos['a']], axis = 1)
	df_a.columns = ['pnl', 'base_pos']
	df_a = single_summary(df_a)
	df_b = pd.concat([pnl['b'], pos['b']], axis = 1)
	df_b.columns = ['pnl', 'base_pos']
	df_b = single_summary(df_b)

	df = pd.concat([df_a, df_b])
	df.index = titles
	return df