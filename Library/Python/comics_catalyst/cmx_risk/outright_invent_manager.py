import numpy as np
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parents[3]))
from cmx_execution.order_manager import side
from cmx_risk.anchor_manager import anchor_linear_scalper
from cmx_risk.hedging_manager import hedging_linear_scalper
import logging

class outright_linear_scalper:
	def __init__(self, context):
		self.context = context
		self.position = np.nan
		self.pre_position = np.nan
		self.bid_prices = []
		self.ask_prices = []
		self.traded = 0 
		self.pm_std = 1e9

	def update_position(self):
		self.pre_position = self.position
		self.position = self.context.portfolio.positions[self.context.asset].amount \
					  + (self.context.risk_init_position or 0)
		traded = self.pre_position - self.position
		if not np.isnan(traded):
			self.traded += abs(traded)
			self.context.cmx_logger.log_traded(self.traded)
		return self.position
	
	def update_entry_prices(self):
		if self.context.cmx_signal.is_updated:
			fair_price = self.context.cmx_signal.fair_price
			self.pm_std = max(self.context.signal_minsd * self.context.cmx_signal.price,\
							  self.context.invent_pm * self.context.cmx_signal.std)
			self.bid_prices = fair_price - self.pm_std \
										 * np.linspace(self.context.invent_e0, 
													   self.context.invent_en, 
													   self.context.invent_n)
			self.ask_prices = fair_price + self.pm_std \
										 * np.linspace(self.context.invent_e0, 
													   self.context.invent_en, 
													   self.context.invent_n)
			self.context.cmx_logger.log_invent_entry_price_update()

	def _is_almost_equal(self, p0, p1, allowed_err = None):
		if allowed_err is None:
			allowed_err = self.context.invent_ignore_partial_fill_value
		assert allowed_err >= 0, 'allowed_err < 0!'

		if p0 == 0 and p1 == 0:
			return True
		
		if abs(p0 - p1) < allowed_err:
			return True
		return False

	def _is_not_larger(self, p0, p1, allowed_err = None):
		if allowed_err is None:
			allowed_err = self.context.invent_ignore_partial_fill_value
		assert allowed_err >= 0, 'allowed_err < 0!'

		return p0 - allowed_err <= p1

	def _is_not_smaller(self, p0, p1, allowed_err = None):
		if allowed_err is None:
			allowed_err = self.context.invent_ignore_partial_fill_value
		assert allowed_err >= 0, 'allowed_err < 0!'

		return p0 + allowed_err >= p1

	def cancel_all(self):
		self.context.cmx_exec.send_orders(None, side.buy)
		self.context.cmx_exec.send_orders(None, side.sell)

	def assert_orders(self, price_qty_map, tradeside):
		if tradeside == side.buy:
			for k,v in price_qty_map.items():
				assert v >= 0 and self._is_not_larger(v + self.position, self.context.risk_max_long_pos), \
				'illegal bid order {} * {} is adding to position {} exceeding max long position of {}'.format(k, v, self.position, self.context.risk_max_long_pos)
		elif tradeside == side.sell:
			for k,v in price_qty_map.items():
				assert v <= 0 and self._is_not_smaller(v + self.position, self.context.risk_max_short_pos), \
				'illegal ask order {} * {} is adding to position {} exceeding max short position of {}'.format(k, v, self.position, self.context.risk_max_short_pos)

	def trade_normal(self):
		# return True if order updated.
		self.update_position()
		self.update_entry_prices()

		bids = {}
		asks = {}
		update_bids = False
		update_asks = False

		if self._is_almost_equal(self.position, 0):
			# currently flat:
			self.context.cmx_signal.enable_update()
			bid_price = self.bid_prices[0]
			ask_price = self.ask_prices[0]
			bid_qty = self.context.invent_spn
			ask_qty = -1 * self.context.invent_spn
			bids = {bid_price: bid_qty}
			asks = {ask_price: ask_qty}
			update_bids = True
			update_asks = True
		else:
			# position != 0
			pre_level = int(np.floor(abs(self.position) / self.context.invent_spn)) # [0, n]
			fully_filled = False
			if self._is_almost_equal(abs(self.position), pre_level * self.context.invent_spn):
				# example: pos = 20.01, spn = 20
				fully_filled = True
				working_qty = 0
				filled_qty = self.context.invent_spn
				pre_level -= 1
			elif self._is_almost_equal(abs(self.position), (pre_level + 1) * self.context.invent_spn):
				# example: pos = 19.98, spn = 20
				fully_filled = True
				working_qty = 0
				filled_qty = self.context.invent_spn
			else:
				# example: pos = 15, spn = 20
				fully_filled = False
				working_qty = (pre_level + 1) * self.context.invent_spn - abs(self.position)
				filled_qty = self.context.invent_spn - working_qty

			if self.position > 0:
				if fully_filled:
					self.context.cmx_signal.enable_update()
					next_level = pre_level + 1
					if next_level < self.context.invent_n:
						update_bids = True
						bid_price = self.bid_prices[next_level]
						bid_qty = self.context.invent_spn + working_qty
						bids = {bid_price: bid_qty}
					else:
						update_bids = True
						bids = {}
						next_level = self.context.invent_n
						pre_level = next_level - 1
					update_asks = True
					ask_price = self.bid_prices[pre_level] + self.pm_std
					ask_qty = -1 * filled_qty if filled_qty >= self.context.invent_min_share else 0
					asks = {ask_price : ask_qty}
				else: # not fully filled
					# The partial fill could come from previous buy / sell. 
					self.context.cmx_signal.disable_update()
					if self.pre_position < self.position:
						# this is a bid partial fill (adding position)
						next_level = pre_level
						update_bids = False
						bids = {}
						update_asks = True
						ask_price = self.bid_prices[pre_level] + self.pm_std
						ask_qty = -1 * filled_qty if filled_qty >= self.context.invent_min_share else 0
						asks = {ask_price : ask_qty}
					else:
						# this is a ask partial fill (reducing position)
						if working_qty < self.context.invent_min_share:
							next_level = pre_level + 1
							if next_level >= self.context.invent_n:
								bids = {}
							else:
								bid_price = self.bid_prices[next_level]
								bid_qty = self.context.invent_spn + working_qty
								bids = {bid_price : bid_qty}
						else:
							next_level = pre_level
							bid_price = self.bid_prices[next_level]
							bid_qty = working_qty
							bids = {bid_price : bid_qty}
						update_bids = True
						update_asks = False
						asks = {}
				
			else: # position < 0
				if fully_filled:
					self.context.cmx_signal.enable_update()
					next_level = pre_level + 1
					if next_level < self.context.invent_n:
						update_asks = True
						ask_price = self.ask_prices[next_level]
						ask_qty = -self.context.invent_spn - working_qty
						asks = {ask_price: ask_qty}
					else:
						update_asks = True
						asks = {}
						next_level = self.context.invent_n
						pre_level = next_level - 1
					update_bids = True
					bid_price = self.ask_prices[pre_level] - self.pm_std
					bid_qty = filled_qty if filled_qty >= self.context.invent_min_share else 0
					bids = {bid_price : bid_qty}
				else: # not fully filled
					self.context.cmx_signal.disable_update()
					if self.pre_position > self.position:
						# this is a ask partial fill (adding position)
						next_level = pre_level
						update_asks = False
						asks = {}
						update_bids = True
						bid_price = self.ask_prices[pre_level] - self.pm_std
						bid_qty = filled_qty if filled_qty >= self.context.invent_min_share else 0
						bids = {bid_price : bid_qty}
					else:
						# this is a bid partial fill (reducing position)
						if working_qty < self.context.invent_min_share:
							next_level = pre_level + 1
							if next_level >= self.context.invent_n:
								asks = {}
							else:
								ask_price = self.ask_prices[next_level]
								ask_qty = -1 * (self.context.invent_spn + working_qty)
								asks = {ask_price: ask_qty}
						else:
							next_level = pre_level
							ask_price = self.ask_prices[next_level]
							ask_qty = -1 * working_qty
							asks = {ask_price: ask_qty}
						update_asks = True
						update_bids = False
						bids = {}

		if update_bids:
			self.context.cmx_exec.send_orders(bids, side.buy)
			self.assert_orders(bids, side.buy)
			self.context.cmx_logger.log_sent_orders(bids, side.buy)
		if update_asks:
			self.context.cmx_exec.send_orders(asks, side.sell)
			self.assert_orders(asks, side.sell)
			self.context.cmx_logger.log_sent_orders(asks, side.sell)
		if update_bids or update_asks:
			return True
		return False

class multileg_linear_scalper:
	def __init__(self, context):
		#TODO: 
		# 1. add anchor manager and hedging manager
		# 2. manage hedging status and pass can/need buy/sell and positions / amounts to all leg managers
		self.context       = context
		self.symbols       = self.context.cmx_config.catalyst_symbols
		self.leg_num       = self.context.cmx_config.leg_num
		self.betas         = [x for x in self.context.cmx_config.betas]
		self.positions     = [np.nan] * self.leg_num
		self.pre_positions = [np.nan] * self.leg_num
		self.amounts       = [np.nan] * self.leg_num
		self.pre_amounts   = [np.nan] * self.leg_num
		self.prices        = [np.nan] * self.leg_num
		self.trade_amounts = [0] * self.leg_num
		self.pm_std        = 1e9
		self.buy_flags     = [False] * self.leg_num
		self.sell_flags    = [False] * self.leg_num
		self.leg_invent_managers = [anchor_linear_scalper(context)]
		self.leg_invent_managers += [hedging_linear_scalper(context, i) for i in range(1, self.leg_num)]

	def update_positions(self):
		for i in range(self.leg_num):
			self.pre_amounts[i] = self.amounts[i]
			self.pre_positions[i] = self.positions[i]
			self.prices[i] = self.context.cmx_signal.prices[i]
			self.positions[i] = self.context.portfolio.positions[self.context.cmx_config.catalyst_symbols[i]].amount
			if self.context.cmx_config.base_quote_flips[i]:
				self.positions[i] += self.context.cmx_config.init_amounts[i] or 0
				self.amounts[i] = self.positions[i]
			else:
				self.positions[i] += (self.context.cmx_config.init_amounts[i] or 0) / self.prices[i]
				self.amounts[i] =  self.positions[i] * self.prices[i]
			
			if i != 0:
				hedged = self.amounts[i] / self.betas[i] * self.betas[0]
				unhedged = self.amounts[0] - hedged
				if unhedged > self.context.cmx_config.deltas[i]:
					self.buy_flags[0] = False
					logging.info('disable anchor buying')
					self.buy_flags[i] = (self.betas[i] * self.betas[0] > 0)
					self.sell_flags[i] = not self.buy_flags[i]
				elif unhedged < -1 * self.context.cmx_config.deltas[i]:
					self.sell_flags[0] = False
					logging.info('disable anchor selling')
					self.sell_flags[i] = (self.betas[i] * self.betas[0] > 0)
					self.buy_flags[i] = not self.sell_flags[i]
			traded = self.pre_amounts[i] - self.amounts[i]
			if not np.isnan(traded):
				self.trade_amounts[i] += abs(traded)

	def cancel_all(self):
		for sym in self.symbols:
			self.context.cmx_exec.send_orders(sym, None, side.buy)
			self.context.cmx_exec.send_orders(sym, None, side.sell)

	def trade_normal(self):
		self.update_positions()
		return [x.trade_normal() for x in self.leg_invent_managers]
