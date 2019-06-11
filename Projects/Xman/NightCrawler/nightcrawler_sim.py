import os
import sys
import pandas as pd
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[2]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_trader import outright_trader

context = 'nightcrawler-sim'
root_disk = 'c:' if os.path.exists('c:') else '/home/frankwang_trading'

if __name__ == '__main__':
	cmx_config = {
				'global_namespace': context,
				'global_instance': 'test',
				# 'global_mode': 'live', # 'live', 'paper', 'backtest'
				'global_mode': 'backtest', # 'live', 'paper', 'backtest'
				'global_bootstrap': False,

				'sim_maker_fee_pct': 0.001,
				'sim_taker_fee_pct': 0.001,
				'sim_slippage_pct': 0,

				# 'time_start': None,
				# 'time_end' : None,
				'time_start': pd.to_datetime('2018-7-1', utc=True),
				'time_end': pd.to_datetime('2018-7-22', utc=True),

				'exchange': 'binance',
				'symbol' : 'tusd_usdt',

				'risk_max_notional': 180,
				'risk_max_pos' : 180,
				'risk_max_long_pos': 180,
				'risk_max_short_pos': -180, # short_pos <= 0
				'risk_quote_currency': 'usdt',
				'risk_init_position': 0,

				'signal_window': 60 * 24 * 7,
				'signal_update_rate': 60, 
				'signal_minsd': 0.002,
				'signal_minsd': 0.002,
				'signal_ref_price' : None,
				'signal_candle_size' : '1T',
				'signal_hist_rate_limit': 1000,
				'signal_wait_for_full_hist': True,

				'invent_pm' : 1,
				'invent_e0' : 1,
				'invent_en' : 5,
				'invent_spn' : 20,
				'invent_ignore_partial_fill_value': 0.1,
				'invent_min_share': 20,
				'invent_ticksize': 1e-4,

				'log_path': '{}/comics_data/{}/log'.format(root_disk, context),
				'log_level': 'INFO'.upper(), #CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSE

				'record_path': '{}/comics_data/{}/record'.format(root_disk, context),
				'record_pickle': None,
				'record_rate': 1,

				'display_refresh_rate': 1,
				'display_plot': True,
				'display_sim': False,

				'plot_fig': True,
				'plot_path': '{}/comics_data/{}/plot'.format(root_disk, context),
				}
	outright_trader.run(cmx_config)