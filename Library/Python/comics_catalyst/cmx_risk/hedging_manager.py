import numpy as np
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parents[3]))
from cmx_execution.multileg_order_manager import side
from cmx_risk.invent_util import (is_not_larger, is_not_smaller,)
import logging


class hedging_linear_scalper:
	def __init__(self, context, leg_index):
		self.context = context
		self.leg_index = leg_index
		self.symbol  = self.context.cmx_config.catalyst_symbols[self.leg_index]
		self.allowed_position_error = self.context.cmx_config.risk_deltas[self.leg_index]
		self._failed_bid_count = 0
		self._failed_ask_count = 0

	def cancel_all(self):
		self.context.cmx_exec.send_orders(self.symbol, None, side.buy)
		self.context.cmx_exec.send_orders(self.symbol, None, side.sell)

	def assert_orders(self, price_amount_map, tradeside):
		# if tradeside == side.buy:
		# 	for k,v in price_amount_map.items():
		# 		assert v >= 0 and is_not_larger(
		# 										v + self.context.cmx_invent.positions[0], 
		# 										self.context.risk_max_long_position, 
		# 										self.allowed_position_error
		# 										), \
		# 		'illegal bid order {} * {} is adding to position {} exceeding max long position of {}'.format(k, v, self.context.cmx_invent.amounts[0], self.context.risk_max_long_pos)
		# else:
		# 	for k,v in price_amount_map.items():
		# 		assert v <= 0 and is_not_smaller(
		# 										 v + self.context.cmx_invent.amounts[0], 
		# 										 self.context.risk_max_short_pos, 
		# 										 self.allowed_position_error
		# 										 ), \
		# 		'illegal ask order {} * {} is adding to position {} exceeding max short position of {}'.format(k, v, self.context.cmx_invent.amounts[0], self.context.risk_max_short_pos)
		pass

	def _convert_amount_to_qty(self, price_amount_map):
		price_qty_map = price_amount_map.copy()
		if not slef.context.cmx_config.base_quote_flips[0]:
			for k,v in price_qty_map:
				price_qty_map[k] = v / price_qty_map[k]
		return price_qty_map

	def trade_normal(self):
		# return True if order updated.
		if self.context.cmx_invent.buy_flags[self.leg_index]:
			bidqty = self.context.cmx_invent.unhedged_positions[self.leg_index]
			if bidqty >= self.context.cmx_config.invent_min_shares[self.leg_index]:
				if np.isnan(self.context.cmx_signal.prc_smas[self.leg_index].get_std()):
					bidprice = self.context.cmx_invent.upper_prices[self.leg_index] \
							 + self.context.cmx_config.invent_price_offsets[self.leg_index] \
							 * self._failed_bid_count
				else:
					bidprice = self.context.cmx_invent.upper_prices[self.leg_index] \
							 + self.context.cmx_config.invent_price_offsets[self.leg_index] \
							 * self.context.cmx_signal.prc_smas[self.leg_index].get_std() \
							 * self._failed_bid_count
				bids = {bidprice: bidqty}
				bid_str = '|'.join(['{} * {}'.format(k,v) for k,v in bids.items()])
				logging.info('[cmx_invent] send {} bids {} after {} failures'.format(self.symbol.symbol, bid_str, self._failed_bid_count))
				self.context.cmx_exec.send_orders(self.symbol, bids, side.buy)
				self._failed_bid_count += 1
		else:
			self._failed_bid_count = 0

		if self.context.cmx_invent.sell_flags[self.leg_index]:
			askqty = self.context.cmx_invent.unhedged_positions[self.leg_index]
			if askqty <= -1 * self.context.cmx_config.invent_min_shares[self.leg_index]:
				if np.isnan(self.context.cmx_signal.prc_smas[self.leg_index].get_std()):
					askprice = self.context.cmx_invent.lower_prices[self.leg_index] \
							 - self.context.cmx_config.invent_price_offsets[self.leg_index] \
							 * self._failed_ask_count
				else:
					askprice = self.context.cmx_invent.lower_prices[self.leg_index] \
							 - self.context.cmx_config.invent_price_offsets[self.leg_index] \
							 * self.context.cmx_signal.prc_smas[self.leg_index].get_std() \
							 * self._failed_ask_count
				asks = {askprice: askqty}
				ask_str = '|'.join(['{} * {}'.format(k,v) for k,v in asks.items()])
				logging.info('[cmx_invent] send {} asks {} after {} failures'.format(self.symbol.symbol, ask_str, self._failed_ask_count))
				self.context.cmx_exec.send_orders(self.symbol, asks, side.sell)
				self._failed_ask_count += 1
		else:
			self._failed_ask_count = 0

		

