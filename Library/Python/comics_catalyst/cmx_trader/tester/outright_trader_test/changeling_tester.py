import os
import sys
import pandas as pd
import datetime as dt
if 'Projects' in os.getcwd():
	cmx_rootpath = os.getcwd().split('Projects')[0]
else:
	cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_trader import outright_trader

context = 'changeling-test'
if os.path.exists('c:'):
    root_disk = 'c:'  
elif os.path.exists('/Users/fw/Trading/projects/xman'):
    root_disk = '/Users/fw/Trading/projects/xman'
else:
    root_disk = '/home/frankwang_trading'
    
if __name__ == '__main__':
	cmx_config = {
				'global_namespace': context,
				'global_instance': 'xman-live-c1',
				'global_mode': 'paper', # 'live', 'paper', 'backtest'
				'global_bootstrap': False,

				'sim_maker_fee_pct': 0.00075,
				'sim_taker_fee_pct': 0.00075,
				'sim_slippage_pct': 0.0005,

				'time_start': None,
				'time_end' : None,
				# 'time_start': pd.to_datetime('2018-7-16', utc=True),
				# 'time_end': pd.to_datetime('2018-7-18', utc=True),

				'exchange': 'binance',
				'symbol' : 'dash_eth',

				'risk_max_notional': 0.5,
				'risk_max_pos' : 2,
				'risk_max_long_pos': 2,
				'risk_max_short_pos': 0, # short_pos <= 0
				'risk_quote_currency': 'eth',
				'risk_init_position': 0,

				'signal_window': 60 * 24,
				'signal_update_rate': 60, 
				'signal_minsd': 0.003,
				'signal_ref_price' : None,
				'signal_candle_size' : '1T',
				'signal_hist_rate_limit': 1000,
				'signal_wait_for_full_hist': True,

				'invent_pm' : 3,
				'invent_e0' : 1,
				'invent_en' : 2,
				'invent_spn' : 0.1,
				'invent_ignore_partial_fill_value': 0.001,
				'invent_min_share': 0.025,
				'invent_ticksize': 1e-5,

				'exit_start_dt': pd.to_datetime('2019-8-4 17:00:00', utc = True),
				'exit_signal_shift': 1e-4,
				'exit_shift_interval': dt.timedelta(minutes = 1),

				'log_path': '{}/comics_data/{}/log'.format(root_disk, context),
				'log_level': 'INFO'.upper(), #CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSE

				'record_path': '{}/comics_data/{}/record'.format(root_disk, context),
				'trade_path' : '{}/comics_data/{}/trade'.format(root_disk, context),
				'snapshot_path': '{}/comics_data/{}/snapshot'.format(root_disk, context),
				'perf_stat_path': '{}/comics_data/{}/perf_stat'.format(root_disk, context),
				'record_pickle': None,
				'record_rate': 1,

				'display_refresh_rate': 1,
				'display_plot': True,
				'display_sim': False,

				'plot_fig': True,
				'plot_path': '{}/comics_data/{}/plot'.format(root_disk, context),
				}
t	outright_trader.run(cmx_config)