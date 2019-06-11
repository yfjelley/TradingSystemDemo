import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parents[3]))
from cmx_execution.order_manager import side
import logging

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

class multileg_logger:
	def __init__(self, context):
		self.context = context
		logging.basicConfig(
                        filename = context.cmx_config.log_file,\
                        format = '%(asctime)s - %(levelname)s - %(message)s', 
                        level = _get_log_level(context.cmx_config.log_level)
                        )

class outright_logger:
	def __init__(self, context):
		self.context = context

	# def log_init_info(self):
	# 	for k,v in self.context.__dict__.items():
	# 		logging.info('{}: {}'.format(k,v))
	# 	logging.info('######################################')	

	def log_acct_info(self):
		logging.info('######################################')
		logging.info('collecting account info...............')
		logging.info('account_available_balances = {}'.format(self.context.cmx_account.available_balances))
		logging.info('account_total_balances = {}'.format(self.context.cmx_account.total_balances))
		logging.info('account_value = {}'.format(self.context.cmx_account.value))
		logging.info('account_position = {}'.format(self.context.cmx_account.position))
		logging.info('######################################')

	def log_risk_adjust(self):
		logging.info('[cmx_risk]adjust max long/short positions to {}/{}'.format(
																		   self.context.risk_max_long_pos,\
																		   self.context.risk_max_long_pos
																		   ))

	def log_risk_updates(self):
		logging.info('[cmx_risk]ts = {}|pnl = {}|base_pos = {}|quote_pos = {}|traded = {}'.format(
																 self.context.cmx_risk.ts, \
															     self.context.cmx_risk.pnl,\
															     self.context.cmx_risk.base_pos,\
															     self.context.cmx_risk.quote_pos,\
															     self.context.cmx_risk.traded
															     ))

	def log_risk_daily(self):
		if self.context.cmx_risk.ts is None:
			return

		logging.info('######################################')
		logging.info('[cmx_risk]daily risk summary on {}'.format(self.context.cmx_risk.ts.floor('1D')))
		logging.info('[cmx_risk]net={}|dd={}|end_pos={}|min_pos={}|max_pos={}|trade={}'.format(
													  self.context.cmx_risk.daily_end_net,
													  self.context.cmx_risk.daily_min_net,
													  self.context.cmx_risk.daily_end_position,
													  self.context.cmx_risk.daily_min_position,
													  self.context.cmx_risk.daily_max_position,
													  self.context.cmx_risk.daily_end_traded
													  ))

												   

	def log_signal(self, data):
		# return
		logging.info('[cmx_signal]ts = {}|price = {}|fair_price = {}|std = {}|zscore = {}'.format(
																 data.current_dt, \
																 self.context.cmx_signal.price,\
															     self.context.cmx_signal.fair_price,\
															     self.context.cmx_signal.std,\
															     self.context.cmx_signal.zscore
															     ))

	def log_signal_window_info(self, bar_info):
		logging.info('[cmx_signal]update signal window bar -> {} | count -> {}'.format(
																		bar_info['barsize'], \
																		bar_info['barcount'])
																		  )

	def log_signal_disable(self):
		logging.info('[cmx_signal]signal update disabled.')

	def log_signal_enable(self):
		logging.info('[cmx_signal]signal update enabled.')

	def log_risk_control(self):
		logging.info('[cmx_risk]pnl = {}|base_pos = {}|quote_pos = {}'.format(
																	  self.context.cmx_risk.pnl, \
																	  self.context.cmx_risk.base_pos, \
																	  self.context.cmx_risk.quote_pos
																	 ))
	def log_invent_entry_price_update(self):
		info_str = '[cmx_invent]updated entry bid prices\n'
		info_str += '|'.join(['bid_{} = {}'.format(i, p) for i, p in enumerate(self.context.cmx_invent.bid_prices)])
		logging.info(info_str)
		info_str = '[cmx_invent]updated entry ask prices\n'
		info_str += '|'.join(['ask_{} = {}'.format(i, p) for i, p in enumerate(self.context.cmx_invent.ask_prices)])
		logging.info(info_str)

	def log_sent_orders(self, price_qty_map, order_side):
		if price_qty_map is None or len(price_qty_map) == 0:
			if order_side == side.buy:
				logging.info('[cmx_invent]send bids: {}, cancelling all bids')
			else:
				logging.info('[cmx_invent]send asks: {}, cancelling all asks')

		for k,v in price_qty_map.items():
			if order_side == side.buy:
				logging.info('[cmx_invent]send bids: {} * {}'.format(k, v))
			if order_side == side.sell:
				logging.info('[cmx_invent]send asks: {} * {}'.format(k, v))

	def log_traded(self, traded):
		if abs(traded) != 0:
			logging.info('[cmx_invent]traded {}'.format(traded))

	def log_recorder_info(self, ts):
		logging.info('[cmx_recorder]recorded mkt data for ts {}'.format(ts))

	def log_plot_info(self):
		logging.info('[cmx_plot]plot is saved to {}'.format(self.context.plot_file))

	def log_error(self, e):
		logging.error(e)