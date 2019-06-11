import numpy as np
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parents[3]))
from cmx_execution.multileg_order_manager import side
from cmx_risk.invent_util import (is_almost_equal, is_not_larger, is_not_smaller,)
import logging


class anchor_linear_scalper:
	def __init__(self, context):
		self.context = context
		self.symbol  = self.context.cmx_config.catalyst_symbols[0]
		self.allowed_position_error = self.context.cmx_config.risk_deltas[0]
		self.min_share = 0
		self.max_bid_level = 0
		if self.context.cmx_config.risk_max_long_position > 0:
			self.max_bid_level = int(self.context.cmx_config.risk_max_long_position
									 / self.context.cmx_config.invent_spn)
		self.max_ask_level = 0
		if self.context.cmx_config.risk_max_short_position < 0:
			self.max_ask_level = int(-1 * self.context.cmx_config.risk_max_short_position
									 / self.context.cmx_config.invent_spn)

	def _get_price_from_ror(self, ror):
		if self.context.cmx_config.base_quote_flips[0]:
			price = self.context.cmx_signal.init_prices[0] / (ror + 1)
		else:
			price = (ror + 1) * self.context.cmx_signal.init_prices[0]
		return price

	def get_entry_signal(self, level, anchor_side):
		if level < 0 or level >= self.context.cmx_config.invent_n:
			return np.nan
		ei = (self.context.cmx_config.invent_en - self.context.cmx_config.invent_e0) \
		   / self.context.cmx_config.invent_n * level + self.context.cmx_config.invent_e0
		if anchor_side == side.buy:
			signal = self.context.cmx_signal.mean - ei * self.context.cmx_signal.std
		else:
			signal = self.context.cmx_signal.mean + ei * self.context.cmx_signal.std
		return signal

	def get_entry_bidprice(self, level):
		if level >= self.max_bid_level:
			return np.nan
		lower_sig = self.get_entry_signal(level, side.buy)
		if np.isnan(lower_sig):
			return np.nan
		anchor_ror = (lower_sig 
				   - np.dot(self.context.cmx_invent.lower_rors[1:], self.context.cmx_invent.betas[1:])) \
				   / self.context.cmx_invent.betas[0]
		return max(0, self._get_price_from_ror(anchor_ror))

	def get_entry_askprice(self, level):
		if level >= self.max_ask_level:
			return np.nan
		upper_sig = self.get_entry_signal(level, side.sell)
		if np.isnan(upper_sig):
			return np.nan
		anchor_ror = (upper_sig 
				   - np.dot(self.context.cmx_invent.upper_rors[1:], self.context.cmx_invent.betas[1:])) \
				   / self.context.cmx_invent.betas[0]
		return max(0, self._get_price_from_ror(anchor_ror))

	def get_exit_askprice(self, level):
		if level < 0 or level >= self.context.cmx_config.invent_n:
			return np.nan
		signal  = self.get_entry_signal(level, side.buy) + self.context.cmx_invent.pm_std
		signal2 = self.get_entry_signal(0, side.sell)
		signal  = min(signal, signal2)
		anchor_ror = (signal
				   - np.dot(self.context.cmx_invent.upper_rors[1:], self.context.cmx_invent.betas[1:]))\
				   / self.context.cmx_invent.betas[0]
		return max(0, self._get_price_from_ror(anchor_ror))

	def get_exit_bidprice(self, level):
		if level < 0 or level >= self.context.cmx_config.invent_n:
			return np.nan
		signal  = self.get_entry_signal(level, side.sell) - self.context.cmx_invent.pm_std
		signal2 = self.get_entry_signal(0, side.buy)
		signal  = max(signal, signal2)
		anchor_ror = (signal
				   - np.dot(self.context.cmx_invent.lower_rors[1:], self.context.cmx_invent.betas[1:]))\
				   / self.context.cmx_invent.betas[0]
		return max(0, self._get_price_from_ror(anchor_ror))

	def cancel_all(self):
		self.context.cmx_exec.send_orders(self.symbol, None, side.buy)
		self.context.cmx_exec.send_orders(self.symbol, None, side.sell)

	def assert_orders(self, price_qty_map, tradeside):
		if tradeside == side.buy:
			for k,v in price_qty_map.items():
				assert v >= 0 and is_not_larger(
												v + self.context.cmx_invent.positions[0], 
												self.context.cmx_config.risk_max_long_position, 
												self.allowed_position_error
												), \
				'illegal bid order {} * {} is adding to position {} exceeding max long position of {}'.format(k, v, self.context.cmx_invent.positions[0], self.context.cmx_config.risk_max_long_position)
		else:
			for k,v in price_qty_map.items():
				assert v <= 0 and is_not_smaller(
												 v + self.context.cmx_invent.positions[0], 
												 self.context.cmx_config.risk_max_short_position, 
												 self.allowed_position_error
												 ), \
				'illegal ask order {} * {} is adding to position {} exceeding max short position of {}'.format(k, v, self.context.cmx_invent.positions[0], self.context.cmx_config.risk_max_short_position)

	def _convert_amount_to_qty(self, price_amount_map):
		price_qty_map = price_amount_map.copy()
		price_qty_map.pop(np.nan, None)
		if not self.context.cmx_config.base_quote_flips[0]:
			for k,v in price_qty_map.items():
				price_qty_map[k] = v / k
		return price_qty_map

	def trade_normal(self):
		# return True if order updated.
		bids = {}
		asks = {}
		update_bids = False
		update_asks = False

		if is_almost_equal(self.context.cmx_invent.positions[0], 0, self.allowed_position_error):
			# currently flat:
			self.context.cmx_signal.enable_reset()
			bid_price = self.get_entry_bidprice(0)
			if np.isnan(bid_price):
				bids = {}
			else:
				bid_qty   = self.context.cmx_config.invent_spn
				bids      = {bid_price: bid_qty}
			update_bids = True
			
			ask_price = self.get_entry_askprice(0)
			if np.isnan(ask_price):
				asks = {}
			else:
				ask_qty   = -1 * self.context.cmx_config.invent_spn
				asks      = {ask_price: ask_qty}
			update_asks = True
		else:
			self.context.cmx_signal.disable_reset()
			# position != 0
			pre_level = int(np.floor(abs(self.context.cmx_invent.positions[0]) \
					  / self.context.cmx_config.invent_spn)) # [0, n]
			fully_filled = False
			#TODO: fully_filled based on amount is faulty
			if is_almost_equal(
							   abs(self.context.cmx_invent.positions[0]), 
							   pre_level * self.context.cmx_config.invent_spn,
							   self.allowed_position_error
							   ):
				# example: pos = 20.01, spn = 20
				fully_filled = True
				working_qty = 0
				filled_qty = self.context.cmx_config.invent_spn
				pre_level -= 1
			elif is_almost_equal(
								 abs(self.context.cmx_invent.positions[0]), 
								 (pre_level + 1) * self.context.cmx_config.invent_spn,
								 self.allowed_position_error
								 ):
				# example: pos = 19.98, spn = 20
				fully_filled = True
				working_qty = 0
				filled_qty = self.context.cmx_config.invent_spn
			else:
				# example: pos = 15, spn = 20
				fully_filled = False
				working_qty = (pre_level + 1) * self.context.cmx_config.invent_spn \
							- abs(self.context.cmx_invent.positions[0])
				filled_qty = self.context.cmx_config.invent_spn - working_qty

			if self.context.cmx_invent.positions[0] > 0:
				if fully_filled:
					self.context.cmx_signal.enable_update()
					next_level = pre_level + 1
					if next_level < self.context.cmx_config.invent_n:
						update_bids = True
						bid_price = self.get_entry_bidprice(next_level)
						if np.isnan(bid_price):
							bids = {}
						else:
							bid_qty = self.context.cmx_config.invent_spn + working_qty
							bids = {bid_price: bid_qty}
					else:
						update_bids = True
						bids = {}
						next_level = self.context.cmx_config.invent_n
						pre_level = next_level - 1
					update_asks = True
					if filled_qty >= self.context.cmx_config.invent_min_shares[0]:
						ask_price = self.get_exit_askprice(pre_level)
						ask_qty = -1 * filled_qty
						asks = {ask_price: ask_qty}
					else:
						if pre_level == 0:
							asks = {}
						else:
							ask_price = self.get_exit_askprice(pre_level - 1)
							ask_qty = -1 * (filled_qty + self.context.cmx_config.invent_spn)
							asks = {ask_price : ask_qty}
				else: # not fully filled
					# The partial fill could come from previous buy / sell. 
					self.context.cmx_signal.disable_update()
					if self.context.cmx_invent.pre_positions[0] < self.context.cmx_invent.positions[0]:
						# this is a bid partial fill (adding position)
						next_level = pre_level
						update_bids = False
						bids = {}
						update_asks = True
						if filled_qty >= self.context.cmx_config.invent_min_shares[0]:
							ask_price = self.get_exit_askprice(pre_level)
							ask_qty = -1 * filled_qty
							asks = {ask_price: ask_qty}
						else:
							if pre_level == 0:
								asks = {}
							else:
								ask_price = self.get_exit_askprice(pre_level - 1)
								ask_qty = -1 * (filled_qty + self.context.cmx_config.invent_spn)
								asks = {ask_price: ask_qty}
					else:
						# this is a ask partial fill (reducing position)
						if working_qty < self.context.cmx_config.invent_min_shares[0]:
							next_level = pre_level + 1
							if next_level >= self.context.cmx_config.invent_n:
								bids = {}
							else:
								bid_price = self.get_entry_bidprice(next_level)
								if np.isnan(bid_price):
									bids = {}
								else:
									bid_qty = self.context.cmx_config.invent_spn + working_qty
									bids = {bid_price : bid_qty}
						else:
							next_level = pre_level
							bid_price = self.get_entry_bidprice(next_level)
							if np.isnan(bid_price):
								bids = {}
							else:
								bid_qty = working_qty
								bids = {bid_price : bid_qty}
						update_bids = True
						update_asks = False
						asks = {}
				
			else: # position < 0
				if fully_filled:
					self.context.cmx_signal.enable_update()
					next_level = pre_level + 1
					if next_level < self.context.cmx_config.invent_n:
						update_asks = True
						ask_price = self.get_entry_askprice(next_level)
						if np.isnan(ask_price):
							asks = {}
						else:
							ask_qty = -self.context.cmx_config.invent_spn - working_qty
							asks = {ask_price: ask_qty}
					else:
						update_asks = True
						asks = {}
						next_level = self.context.cmx_config.invent_n
						pre_level = next_level - 1
					update_bids = True
					if filled_qty >= self.context.cmx_config.invent_min_shares[0]:
						bid_price = self.get_exit_bidprice(pre_level)
						bid_qty = filled_qty
						bids = {bid_price: bid_qty}
					else:
						if pre_level == 0:
							bids = {}
						else:
							bid_price = self.get_exit_bidprice(pre_level - 1)
							bid_qty = self.context.cmx_config.invent_spn + filled_qty
							bids = {bid_price: bid_qty}
				else: # not fully filled
					self.context.cmx_signal.disable_update()
					if self.context.cmx_invent.pre_positions[0] > self.context.cmx_invent.positions[0]:
						# this is a ask partial fill (adding position)
						next_level = pre_level
						update_asks = False
						asks = {}
						update_bids = True
						if filled_qty >= self.context.cmx_config.invent_min_shares[0]:
							bid_price = self.get_exit_bidprice(pre_level)
							bid_qty = filled_qty
							bids = {bid_price: bid_qty}
						else:
							if pre_level == 0:
								bids = {}
							else:
								bid_price = self.get_exit_bidprice(pre_level - 1)
								bid_qty = self.context.cmx_config.invent_spn + filled_qty
								bids = {bid_price: bid_qty}
					else:
						# this is a bid partial fill (reducing position)
						if working_qty < self.context.cmx_config.invent_min_shares[0]:
							next_level = pre_level + 1
							if next_level >= self.context.cmx_config.invent_n:
								asks = {}
							else:
								ask_price = self.get_entry_askprice(next_level)
								if np.isnan(ask_price):
									asks = {}
								else:
									ask_qty = -1 * (self.context.cmx_config.invent_spn + working_qty)
									asks = {ask_price: ask_qty}
						else:
							next_level = pre_level
							ask_price = self.get_entry_askprice(next_level)
							if np.isnan(ask_price):
								asks = {}
							else:
								ask_qty = -1 * working_qty
								asks = {ask_price: ask_qty}
						update_asks = True
						update_bids = False
						bids = {}
		updated = False
		if update_bids:
			if self.context.cmx_invent.buy_flags[0]:
				self.assert_orders(bids, side.buy)
				bid_str = '|'.join([' {} * {} '.format(k, v) for k, v in bids.items()])
				logging.info('[cmx_invent] sent {} bids: {}'.format(self.symbol.symbol, bid_str))
				self.context.cmx_exec.send_orders(self.symbol, bids, side.buy)
				updated = True
			else:
				logging.info('[cmx_invent] clean {} bids'.format(self.symbol.symbol))
				self.context.cmx_exec.send_orders(self.symbol, None, side.buy)

		if update_asks:
			if self.context.cmx_invent.sell_flags[0]:
				self.assert_orders(asks, side.sell)
				ask_str = '|'.join(['{} * {}'.format(k, v) for k, v in asks.items()])
				logging.info('[cmx_invent] sent {} asks: {}'.format(self.symbol.symbol, ask_str))
				self.context.cmx_exec.send_orders(self.symbol, asks, side.sell)
				updated = True
			else:
				logging.info('[cmx_invent] clean {} asks'.format(self.symbol.symbol))
				self.context.cmx_exec.send_orders(self.symbol, None, side.sell)
		return updated

		

