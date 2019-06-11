import os
import logging
import pandas as pd
import pathlib
import sys
cmx_rootpath = str(pathlib.Path(__file__).parents[4])
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_config.load_config import (get_pickle_file, load_outright_config)
from cmx_signal.dynamic import sma
from cmx_risk.acct_manager import outright_account
from cmx_risk.invent_manager import outright_linear_scalper
from cmx_risk.risk_manager import outright_risk
from cmx_log.logger import outright_logger
from cmx_util.recorder import outright_recorder
from cmx_util.display import outright_display
from cmx_util.plotter import outright_plotter
from cmx_execution.order_manager import outright_orders
from catalyst import run_algorithm
from cmx_execution.order_manager import side
from catalyst.api import (cancel_order, get_open_orders, order, get_orderbook)

# To disable catalyst log:
# os.environ['CATALYST_LOG_LEVEL'] = '13' #CRITICAL = 15,ERROR = 14,WARNING = 13,NOTICE = 12,INFO = 11,DEBUG = 10,TRACE = 9
# Windows: use cmd and set env variable. instruction below
# http://www.dowdandassociates.com/blog/content/howto-set-an-environment-variable-in-windows-command-line-and-registry/

cmx_config = {}
def initialize(context):
	load_outright_config(context, cmx_config)
	context.cmx_logger  = outright_logger(context)
	context.cmx_signal  = sma(context)
	context.cmx_account = outright_account(context)
	context.cmx_invent  = outright_linear_scalper(context)
	context.cmx_risk    = outright_risk(context)
	context.cmx_exec    = outright_orders(context)
	context.cmx_recoder = outright_recorder(context)
	context.cmx_display = outright_display(context)
	context.cmx_plotter = outright_plotter(context)
	context.can_buy = True
	context.can_sell = False

def before_trading_start(context, data):
	# this is being called daily at 0:00 UTC
	context.cmx_display.run_daily()
	context.cmx_risk.update_daily()
	return

def handle_data(context, data):
	

	bid_price = 0
	ask_price = 1e9
	quantity = 5
	min_price = 1e-6

	bid_price = get_orderbook(context.asset, order_type = 'bids')['bids'][0]['rate']
	ask_price = get_orderbook(context.asset, order_type = 'asks')['asks'][0]['rate']
    
	exist_orders = context.blotter.open_orders[context.asset]
	logging.info('orders = {}'.format(exist_orders))
	pos = context.portfolio.positions[context.asset].amount
	logging.info('position = {}'.format(pos))
	trans = context.perf_tracker.todays_performance.processed_transactions
	logging.info('transaction = {}'.format(trans))
    
    # order(context.asset, 0, bid_price + context.invent_ticksize)
    # cancel_order('17656746', symbol = context.asset.symbol)

	
def analyze(context, perf):
	context.cmx_invent.cancel_all()
	context.cmx_display.run_daily()
	context.cmx_plotter.plot(perf)

def run(app_config):
	global cmx_config
	cmx_config = app_config
	record_pickle_file = get_pickle_file(cmx_config)
	cmx_config['record_pickle'] = record_pickle_file
	run_algorithm(
				  live = True if cmx_config['global_mode'] in ['live', 'paper'] else False,
				  live_graph = False,
				  analyze_live = None, # pass a function
				  simulate_orders = False if cmx_config['global_mode'] == 'live' else True,
				  capital_base = cmx_config['risk_max_notional'],
				  data_frequency = 'minute' if cmx_config['signal_candle_size'] == '1T' else 'daily',
				  data = None,
				  bundle = None,
				  bundle_timestamp = None,
				  default_extension = True,
				  extensions = (),
				  strict_extensions = True,
				  environ = os.environ,
				  # initialize = (initialize, cmx_config),
				  initialize = initialize,
				  before_trading_start = before_trading_start,
				  handle_data = handle_data,
				  analyze = analyze,
				  exchange_name = cmx_config['exchange'],
				  algo_namespace = cmx_config['global_namespace'],
				  quote_currency = cmx_config['risk_quote_currency'],
				  start = cmx_config['time_start'],
				  end = cmx_config['time_end'],
				  output = cmx_config['record_pickle'],
				  auth_aliases = None, # For example: 'binance,auth2,bittrex,auth2'
				 )


if __name__ == '__main__':
	context = 'live_tester'
	if os.path.exists('c:'):
		root_disk = 'c:'  
	elif os.path.exists('/Users/fw/Trading/projects/xman'):
		root_disk = '/Users/fw/Trading/projects/xman'
	else:
		root_disk = '/home/frankwang_trading'
	cmx_config = {
				'global_namespace': context,
				'global_instance': 'tester',
				'global_mode': 'live', # 'live', 'paper', 'backtest'
				'global_bootstrap': False,

				'sim_maker_fee_pct': 0.001,
				'sim_taker_fee_pct': 0.001,
				'sim_slippage_pct': 0.0005,

				'time_start': None,
				'time_end' : None,
				# 'time_start': pd.to_datetime('2018-8-16', utc=True),
				# 'time_end': pd.to_datetime('2018-8-18', utc=True),

				'exchange': 'binance',
				'symbol' : 'ae_eth',

				'risk_max_notional': 0.1,
				'risk_max_pos' : 500,
				'risk_max_long_pos': 500,
				'risk_max_short_pos': -500, # short_pos <= 0
				'risk_quote_currency': 'eth',
				'risk_init_position': -0,

				'signal_window': 360,
				'signal_update_rate': 60, 
				'signal_minsd': 0.003,
				'signal_ref_price' : 1.0013,
				'signal_candle_size' : '1T',
				'signal_hist_rate_limit': 1000,
				'signal_wait_for_full_hist': True,

				'invent_pm' : 2,
				'invent_e0' : 1,
				'invent_en' : 3,
				'invent_spn' : 100,
				'invent_ignore_partial_fill_value': 10,
				'invent_min_share': 10,
				'invent_ticksize': 1e-6,

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
				
	run(cmx_config)