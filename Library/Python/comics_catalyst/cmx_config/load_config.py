import os
import logging
from logbook import Logger as catalyst_logger
import datetime as dt
import time
import numpy as np
from catalyst.api import (symbol, set_commission, set_slippage)
import random

def _join_path(folder, file):
	if folder is None:
		return file
	if not os.path.exists(folder):
		os.makedirs(folder)
	return os.path.join(folder, file)

def _get_log_level(level_str):
	if level_str.upper() == 'CRITICAL':
		return logging.CRITICAL
	if level_str.upper() == 'ERROR':
		return logging.ERROR
	if level_str.upper() == 'WARNING':
		return logging.WARNING
	if level_str.upper() == 'INFO':
		return logging.INFO
	if level_str.upper() == 'DEBUG':
		return logging.DEBUG
	return logging.NOTSE

def _get_file_prefix(comics_config):
	file_prefix = '{}_{}_{}_{}_{}'.format(
									   comics_config['global_namespace'],
									   comics_config['global_instance'],
									   comics_config['global_mode'],
									   int(time.mktime(dt.datetime.utcnow().timetuple())),
									   random.randint(1001,10000),
									   )
	return file_prefix

def _round_position(p0, p1):
	if p1 == 0:
		return p0
	return np.floor(p0 / p1) * p1 if p0 > 0 else -(np.floor(-p0 / p1) * p1)

def get_pickle_file(comics_config):
	file_prefix = _get_file_prefix(comics_config)
	file = '{}.pickle'.format(file_prefix)
	return _join_path(comics_config['record_path'], file)

def load_base_config(context, comics_config):
	context.global_namespace = comics_config.get('global_namespace')
	context.global_instance  = str(comics_config.get('global_instance'))
	context.global_mode      = comics_config.get('global_mode')
	context.global_bootstrap = comics_config.get('global_bootstrap')

	context.exchange_str   = comics_config.get('exchange')
	context.symbol_str     = comics_config.get('symbol')
	context.asset          = symbol(comics_config.get('symbol'))
	context.exchange       = context.exchanges[comics_config.get('exchange')]
	context.base_currency  = comics_config.get('symbol').split('_')[0]
	context.quote_currency = comics_config.get('symbol').split('_')[1]

	context.file_prefix = _get_file_prefix(comics_config)
	context.record_path = comics_config.get('record_path')
	context.record_pickle = '{}.pickle'.format(context.file_prefix)
	context.record_pickle = _join_path(context.record_path, context.record_pickle)
	context.record_rate = comics_config.get('record_rate')
	context.trade_path  = comics_config.get('trade_path')
	context.snapshot_path = comics_config.get('snapshot_path')
	context.perf_stat_path = comics_config.get('perf_stat_path')

	context.catalyst_logger = catalyst_logger(context.global_namespace)
	context.log_file = '{}.comics.log'.format(context.file_prefix)
	context.log_file = _join_path(comics_config.get('log_path'), context.log_file)
	context.display_refresh_rate = comics_config.get('display_refresh_rate')
	context.display_plot = comics_config.get('display_plot')
	context.display_sim  = comics_config.get('display_sim')
	
	logging.basicConfig(
						filename = context.log_file,\
						format = '%(asctime)s - %(levelname)s - %(message)s', 
						level = _get_log_level(comics_config.get('log_level'))
						)
	logging.info('#######################################################')
	logging.info('initializing outrigt_trader & loading configurations...')
	for k,v in comics_config.items():
		logging.info('{}: {}'.format(k,v))
	logging.info('initialization finished')
	logging.info('#######################################################')


def load_outright_config(context, comics_config):
	context.global_namespace = comics_config['global_namespace']
	context.global_instance  = str(comics_config['global_instance'])
	context.global_mode      = comics_config['global_mode']
	context.global_bootstrap = comics_config['global_bootstrap']

	if context.global_mode != 'live':
		set_commission(maker = comics_config['sim_maker_fee_pct'], \
					   taker = comics_config['sim_taker_fee_pct'])
		set_slippage(slippage = comics_config['sim_slippage_pct'])

	context.exchange_str   = comics_config['exchange']
	context.symbol_str     = comics_config['symbol']
	context.asset          = symbol(comics_config['symbol'])
	context.exchange       = context.exchanges[comics_config['exchange']]
	context.base_currency  = comics_config['symbol'].split('_')[0]
	context.quote_currency = comics_config['symbol'].split('_')[1]

	context.risk_max_notional   = comics_config['risk_max_notional']
	context.risk_max_position   = comics_config['risk_max_pos']
	context.risk_max_long_pos   = comics_config['risk_max_long_pos']
	context.risk_max_short_pos  = comics_config['risk_max_short_pos']
	context.risk_quote_currency = comics_config['risk_quote_currency']
	context.risk_init_position  = comics_config.get('risk_init_position')
	context.risk_init_cost_basis= comics_config.get('risk_init_cost_basis')
	
	context.signal_window             = comics_config['signal_window']
	context.signal_update_rate        = comics_config['signal_update_rate']
	context.signal_minsd              = comics_config['signal_minsd']
	context.signal_ref_price          = comics_config['signal_ref_price']
	context.signal_candle_size        = comics_config['signal_candle_size']
	context.signal_hist_rate_limit    = comics_config['signal_hist_rate_limit']
	context.signal_wait_for_full_hist = comics_config['signal_wait_for_full_hist']
	
	context.invent_pm  = comics_config['invent_pm'] # profit margin
	context.invent_e0  = comics_config['invent_e0']
	context.invent_en  = comics_config['invent_en']
	context.invent_spn = comics_config['invent_spn']
	context.invent_min_share = comics_config['invent_min_share']
	context.invent_ticksize  = comics_config['invent_ticksize']

	# rounded risk positions by invent_spn, otherwise algo will continuously see working positions:
	context.risk_max_position = _round_position(context.risk_max_position, context.invent_spn)
	context.risk_max_long_pos = _round_position(context.risk_max_long_pos, context.invent_spn)
	context.risk_max_short_pos = _round_position(context.risk_max_short_pos, context.invent_spn)
	context.risk_init_position = context.risk_init_position

	context.invent_n = int((context.risk_max_long_pos - context.risk_max_short_pos) / context.invent_spn / 2)
	context.invent_ignore_partial_fill_value = comics_config['invent_ignore_partial_fill_value']
	assert context.invent_spn >= context.invent_min_share, 'invent_spn < invent_min_share!'

	context.exit_nonew_dt   = comics_config.get('exit_nonew_dt')
	context.exit_passive_dt = comics_config.get('exit_passive_dt')
	context.exit_active_dt  = comics_config.get('exit_active_dt')
	# context.exit_signal_shift = comics_config.get('exit_signal_shift')
	# context.exit_shift_interval = comics_config.get('exit_shift_interval')

	context.file_prefix = _get_file_prefix(comics_config)
	context.record_path = comics_config['record_path']
	context.record_pickle = '{}.pickle'.format(context.file_prefix)
	context.record_pickle = _join_path(context.record_path, context.record_pickle)
	context.record_rate = comics_config['record_rate']
	context.trade_path  = comics_config.get('trade_path')
	context.snapshot_path = comics_config.get('snapshot_path')
	context.perf_stat_path = comics_config.get('perf_stat_path')

	context.catalyst_logger = catalyst_logger(context.global_namespace)
	context.log_file = '{}.comics.log'.format(context.file_prefix)
	context.log_file = _join_path(comics_config['log_path'], context.log_file)
	context.display_refresh_rate = comics_config['display_refresh_rate']
	context.display_plot = comics_config['display_plot']
	context.display_sim  = comics_config['display_sim']
	context.plot_fig = comics_config['plot_fig']
	context.plot_path = comics_config['plot_path']
	context.plot_file = '{}.png'.format(context.file_prefix)
	context.plot_file = _join_path(comics_config['plot_path'], context.plot_file)
	context.pnl_stat_file = _join_path(context.perf_stat_path, 'pnl.stat.csv') if context.global_mode != 'backtest' else None

	logging.basicConfig(
						filename = context.log_file,\
						format = '%(asctime)s - %(levelname)s - %(message)s', 
						level = _get_log_level(comics_config['log_level'])
						)
	logging.info('#######################################################')
	logging.info('initializing outrigt_trader & loading configurations...')
	for k,v in comics_config.items():
		logging.info('{}: {}'.format(k,v))
	logging.info('initialization finished')
	logging.info('#######################################################')