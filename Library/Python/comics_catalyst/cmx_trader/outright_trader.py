import os
import logging
import pandas as pd
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
	context.cmx_recorder = outright_recorder(context)
	context.cmx_display = outright_display(context)
	context.cmx_plotter = outright_plotter(context)

def before_trading_start(context, data):
	# this is being called daily at 0:00 UTC
	context.cmx_display.run_daily()
	# context.cmx_risk.reset_daily()
	return

def handle_data(context, data):
	today = data.current_dt.floor('1D')
	if today != context.current_day:
		context.current_day = today
		context.cmx_invent.cancel_all()
		if context.global_mode == 'live':
			context.cmx_account.update(data)
			context.cmx_risk.adjust_position_limits(data)
			
	context.cmx_signal.update(data)
	context.cmx_risk.run(data)
	if context.cmx_risk.trading_enabled:
		if context.cmx_risk.trading_status == 'normal':
			context.cmx_invent.trade_normal()
		else:
			if context.cmx_risk.trading_status == 'exit_active':
				context.cmx_invent.exit_active()
			elif context.cmx_risk.trading_status == 'exit_passive':
				context.cmx_invent.exit_passive()
			elif context.cmx_risk.trading_status == 'exit_nonew':
				context.cmx_invent.exit_nonew()	  
	context.cmx_recorder.run()
	context.cmx_display.run()

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