import os
import sys
import pandas as pd
import pathlib
cmx_rootpath = pathlib.Path(os.getcwd()).parents[3]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_trader import outright_trader
from multiprocessing import Process


if __name__ == '__main__':
	context = 'nightcrawler-opt'
	root_disk = 'c:' if os.path.exists('c:') else '/home/frankwang_trading'
	cmx_config = {
					'global_namespace': context,
					'global_instance': 815001,
					'global_mode': 'backtest', # 'live', 'paper', 'backtest'
					'global_bootstrap': False,

					'sim_maker_fee_pct': 0.001,
					'sim_taker_fee_pct': 0.001,
					'sim_slippage_pct': 0.0005,

					# 'time_start': None,
					# 'time_end' : None,
					'time_start': pd.to_datetime('2018-6-15', utc=True),
					'time_end': pd.to_datetime('2018-9-1', utc=True),

					'exchange': 'binance',
					'symbol' : 'tusd_usdt',

					'risk_max_notional': 1000,
					'risk_max_pos' : 1000,
					'risk_max_long_pos': 1000,
					'risk_max_short_pos': -1000, # short_pos <= 0
					'risk_quote_currency': 'usdt',
					'risk_init_position': 0,

					'signal_window': 60 * 24 * 7,
					'signal_update_rate': 60,
					'signal_minsd': 0.003, 
					'signal_ref_price' : 1.0013,
					'signal_candle_size' : '1T',
					'signal_hist_rate_limit': 1000,
					'signal_wait_for_full_hist': True,

					'invent_pm' : 1.5,
					'invent_e0' : 0.5,
					'invent_en' : 4,
					'invent_spn' : 100,
					'invent_ignore_partial_fill_value': 0.2,
					'invent_min_share': 20,
					'invent_ticksize': 1e-4,

					'log_path': '{}/comics_data/{}/log'.format(root_disk, context),
					'log_level': 'WARNING'.upper(), #CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSE

					'record_path': '{}/comics_data/{}/record'.format(root_disk, context),
					'record_pickle': None,
					'record_rate': 1,

					'display_refresh_rate': 1,
					'display_plot': True,
					'display_sim': False,

					'plot_fig': True,
					'plot_path': '{}/comics_data/{}/plot'.format(root_disk, context),
				}

	instance = 903017
	win_scan = [1440]
	pm_scan = [0.5, 1]
	e0_scan = [1, 2]
	ed_scan = [1]
	opt_processes = []
	for win in win_scan:
		for pm in pm_scan:
			for e0 in e0_scan:
				# for en in en_scan:
				for ed in ed_scan:
					cmx_config['global_instance'] = instance
					cmx_config['signal_window'] = win
					cmx_config['invent_pm'] = pm
					cmx_config['invent_e0'] = e0
					cmx_config['invent_en'] = e0 + ed
					# print(instance, pm, e0, en)
					p = Process(target = outright_trader.run, args = (cmx_config,))
					opt_processes.append(p)
					p.start()
					instance += 1
	for p in opt_processes:
		p.join()
