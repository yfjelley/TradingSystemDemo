from collections import OrderedDict as ord_dict
from catalyst.api import (cancel_order, get_open_orders, order, get_orderbook)
from enum import Enum
import logging
from decimal import Decimal
import logging
import datetime as dt

class side(Enum):
	buy = 1
	sell = -1

class order_partial_fill_info:
	def __init__(self, catalyst_order):
		self.ts = dt.datetime.utcnow()
		self.id = catalyst_order.id
		self.filled = catalyst_order.filled
		self.amount = catalyst_order.amount

	def update(self, catalyst_order):
		if self.id != catalyst_order.id:
			return
		if self.filled != catalyst_order.filled:
			self.ts = dt.datetime.utcnow()
			self.filled = catalyst_order.filled

class outright_orders:
	def __init__(self, context):
		self.context = context
		self.bid_map = {} # price: order_list
		self.ask_map = {} # price: order_list
		self.cancel_failure_map = {} # id: failure times
		self.cancel_failure_threshold = 1
		self.partial_bid_map = {} # price: qty
		self.partial_ask_map = {} # price: qty
		self.partial_bid_qty = 0
		self.partial_ask_qty = 0
		self.ignored_orderid = []
		self.is_live = False
		self.initialized = False
		self.initialize()

	def initialize(self):
		if self.initialized:
			return
		try:
			self.is_live = self.context.mode_name == 'live'
		except:
			self.is_live = False

		if self.is_live:
			exchange_orders = get_open_orders(self.context.asset)
			if exchange_orders is None:
				self.ignored_orderid = []
			else:
				for o in exchange_orders:
					self.ignored_orderid.append(o.id)
		self.initialized = True

	def update(self):
		context_orders  = self.context.blotter.open_orders[self.context.asset]
		cbids, casks = self._update_order_maps(context_orders)
		self.bid_map = cbids
		self.ask_map = casks

		# do not consider order that placed by a different algo or previous algo
		# if self.is_live:
		# 	exchange_orders = get_open_orders(self.context.asset)
		# 	ebids, easks = self._update_order_maps(exchange_orders)
		# 	self.bid_map = self._concat_ordermaps(cbids, ebids)
		# 	self.ask_map = self._concat_ordermaps(casks, easks)
		# else:
		# 	self.bid_map = cbids
		# 	self.ask_map = casks

		self.partial_bid_map = {}
		self.partial_bid_qty = 0
		for p, ord_list in self.bid_map.items():
			for o in ord_list:
				if o.filled != 0:
					self.partial_bid_qty += o.amount - o.filled
					if o.limit in self.partial_bid_map:
						self.partial_bid_map[o.limit] += o.amount - o.filled
					else:
						self.partial_bid_map[o.limit] = o.amount - o.filled
					logging.debug('[cmx_order] partial bid @ {} * {}'.format(o.limit, o.amount - o.filled))

		self.partial_ask_map = {}
		self.partial_ask_qty = 0
		for p, ord_list in self.ask_map.items():
			for o in ord_list:
				if o.filled != 0:
					self.partial_ask_qty += o.amount - o.filled
					if o.limit in self.partial_ask_map:
						self.partial_ask_map[o.limit] += o.amount - o.filled
					else:
						self.partial_ask_map[o.limit] = o.amount - o.filled
					logging.debug('[cmx_order] partial ask @ {} * {}'.format(o.limit, o.amount - o.filled))

	def _concat_orderlists(self, order_list_a, order_list_b):
		if order_list_a is None and order_list_b is None:
			return {}
		if order_list_a is None:
			return order_list_b
		if order_list_b is None:
			return order_list_a

		id_order_map = {}
		for o in order_list_a + order_list_b:
			if o.id not in id_order_map:
				id_order_map[o.id] = o
		return list(id_order_map.values())

	def _concat_ordermaps(self, order_map_a, order_map_b):
		if order_map_a is None and order_map_b is None:
			return {}
		if order_map_a is None:
			return order_map_b
		if order_map_b is None:
			return order_map_a

		price_orders_map = {}
		for p, ord_ls in order_map_a.items():
			if p in price_orders_map:
				price_orders_map[p] = self._concat_orderlists(price_orders_map[p], ord_ls)
			else:
				price_orders_map[p] = ord_ls
		for p, ord_ls in order_map_b.items():
			if p in price_orders_map:
				price_orders_map[p] = self._concat_orderlists(price_orders_map[p], ord_ls)
			else:
				price_orders_map[p] = ord_ls
		return price_orders_map

	def _get_decimal_price(self, price):
		if price is None:
			return None
		return Decimal(price).quantize(Decimal(str(self.context.invent_ticksize)))

	def _update_order_maps(self, order_list):
		bid_map = {}
		ask_map = {}
		if order_list is None:
			return bid_map, ask_map

		for o in order_list:
			if o.id in self.ignored_orderid:
				continue
			price = self._get_decimal_price(o.limit)
			qty = o.amount
			if qty > 0:
				if price in bid_map:
					bid_map[price].append(o)
				else:
					bid_map[price] = [o]
			else:
				if price in ask_map:
					ask_map[price].append(o)
				else:
					ask_map[price] = [o]
		return bid_map, ask_map

	def cancel_orders(self, order_list):
		if order_list is None or len(order_list) == 0:
			return True

		if self.is_live:
			depth = get_orderbook(order_list[0].asset)
			mkt_bidprc = depth['bids'][0]['rate']
			mkt_askprc = depth['asks'][0]['rate']

		cancelled = True
		for o in order_list:
			if o.filled != 0 and o.amount != o.filled:
				logging.warning('[cmx_order][cancel_orders] skip partial filled order: {}|{}|{}|{}'.format(o.id, o.limit, o.amount, o.filled))
				cancelled = False
				continue
			good_to_cancel = True
			if self.is_live:
				if o.amount > 0:
					if o.limit >= mkt_bidprc:
						logging.warning('[cmx_order][cancel_orders] skip bids that is making market: {}|{} >= {}|{}|{}'.format(
																											   o.id, 
																											   o.limit, 
																											   mkt_bidprc, 
																											   o.amount, 
																											   o.filled
																											   ))
						good_to_cancel = False
				else:
					if o.limit <= mkt_askprc:
						logging.warning('[cmx_order][cancel_orders] skip asks that is making market: {}|{} <= {}|{}|{}'.format(
																											   o.id, 
																											   o.limit, 
																											   mkt_askprc, 
																											   o.amount, 
																											   o.filled
																											   ))
						good_to_cancel = False

			try:
				if not good_to_cancel:
					cancelled = False
				else:
					if self.context.asset.exchange == 'binance' and self.is_live:
						cancel_order(o, symbol = self.context.asset)
					else:
						cancel_order(o)
			except Exception as e:
				logging.warning(str(e))
				if self.cancel_failure_map.get(o.id):
					self.cancel_failure_map[o.id] += 1
				else:
					self.cancel_failure_map[o.id] = 1

				if self.is_live:
					if self.cancel_failure_map[o.id] >= self.cancel_failure_threshold:
						self.ignored_orderid.append(o.id)
						logging.warning('[cmx_order][cancel_orders] failed to cancel order:{} in {} trials, ignore it.'.format(o.id, self.cancel_failure_threshold))
					else:
						logging.warning('[cmx_order][cancel_orders] failed to cancel order - id:{}|exchange:{}|symbol:{}|price:{}|qty:{}, will try {} times'\
								 .format(o.id, o.sid.exchange, o.sid.symbol, o.limit, o.amount, \
										 self.cancel_failure_threshold - self.cancel_failure_map[o.id]))
				else:
					logging.warning('[cmx_order][cancel_orders] failed to cancel order - id:{}|exchange:{}|symbol:{}|price:{}|qty:{}, tried {} times'\
								 .format(o.id, o.sid.exchange, o.sid.symbol, o.limit, o.amount, self.cancel_failure_map[o.id]))
				cancelled = False
		return cancelled

	def _get_ts_based_orders(self, order_list):
		if order_list is None:
			return []
		if len(order_list) <= 1:
			return order_list
		
		ts_order_map = {}
		for o in order_list:
			if ts_order_map.get(o.created):
				ts_order_map[o.created].append(o)
			else:
				ts_order_map[o.created] = [o]
		ts_order_map = ord_dict(sorted(ts_order_map.items()))

		sorted_orders = []
		for k, v in ts_order_map.items():
			sorted_orders += v
		return sorted_orders

	def update_order(self, price, qty, order_side):
		qty = int(qty / self.context.invent_ignore_partial_fill_value) \
			* self.context.invent_ignore_partial_fill_value
		updated_all = True
		cum_qty = 0
		remained_orders = []
		if order_side == side.buy:
			ts_based_orders = self._get_ts_based_orders(self.bid_map.get(price))
			for o in ts_based_orders:
				logging.info('[cmx_order][update_order] updating bid #{}: ts = {}|price = {}|amount = {}|filled = {}'.format(o.id, o.created, o.limit, o.amount, o.filled))
				if o.filled != 0 and o.amount != o.filled:
					# ignore partial filled orders
					logging.info('[cmx_order][update_order] bid #{} is partially filled, skipping...'.format(o.id))
					cum_qty += o.amount
					continue
				if cum_qty + o.amount >= qty + self.context.invent_min_share:
					# from this order and forward, we need to cancel:
					cancelled = self.cancel_orders([o])
					updated_all &= cancelled
					if not cancelled:
						cum_qty += o.amount
						logging.info('[cmx_order][update_order] cannot cancel bid #{}, skipping...'.format(o.id))
					else:
						logging.info('[cmx_order][update_order] cancelled bid #{}'.format(o.id))
				else:
					remained_orders.append(o)
					cum_qty += o.amount
					logging.info('[cmx_order][update_order] bid #{} is good to keep'.format(o.id))
		else:
			ts_based_orders = self._get_ts_based_orders(self.ask_map.get(price))
			for o in ts_based_orders:
				logging.info('[cmx_order][update_order] updating ask #{}: ts = {}|price = {}|amount = {}|filled = {}'.format(o.id, o.created, o.limit, o.amount, o.filled))
				if o.filled != 0 and o.amount != o.filled:
					# ignore partial filled orders
					logging.info('[cmx_order][update_order] ask #{} is partially filled, skipping...'.format(o.id))
					cum_qty += o.amount
					continue
				if cum_qty + o.amount <= qty - self.context.invent_min_share:
					cancelled = self.cancel_orders([o])
					updated_all &= cancelled
					if not cancelled:
						cum_qty += o.amount
						logging.info('[cmx_order][update_order] cannot cancel ask #{}, skipping...'.format(o.id))
					else:
						logging.info('[cmx_order][update_order] cancelled ask #{}'.format(o.id))
				else:
					remained_orders.append(o)
					cum_qty += o.amount
					logging.info('[cmx_order][update_order] ask #{} is good to keep'.format(o.id))
				
		if cum_qty != qty:
			if abs(qty - cum_qty) >= self.context.invent_min_share:
				self.split_order(self.context.asset, qty - cum_qty, limit_price = float(price))
				logging.info('[cmx_order][update_order] send out new orders: {} * {}'.format(price, qty - cum_qty))
			else:
				# new order qty is too small. Cancel more orders to trade min shares
				new_qty = qty - cum_qty
				for o in remained_orders[::-1]:
					cancelled = self.cancel_orders([o])
					if cancelled:
						new_qty += o.amount
						logging.info('[cmx_order][update_order] cancelled order #{} in order to trade invent_min_share: ts = {}|price = {}|amount = {}|filled = {}'.format(o.id, o.created, o.limit, o.amount, o.filled))
						if abs(new_qty) >= self.context.invent_min_share:
							break
				if abs(new_qty) >= self.context.invent_min_share:
					self.split_order(self.context.asset, new_qty, limit_price = float(price))
					logging.info('[cmx_order][update_order] send out new orders: {} * {}'.format(price, new_qty))
				else:
					updated_all = False
					logging.info('[cmx_order][update_order] new order qty is too small')
			
		return updated_all

	def split_order(self, asset, qty, limit_price):
		min_qty = self.context.invent_min_share
		residual_qty = qty
		if qty > 0:
			while residual_qty >= 2 * min_qty:
				order(asset, min_qty, limit_price)
				residual_qty -= min_qty
			order(asset, residual_qty, limit_price)
		elif qty < 0:
			while residual_qty <= -2 * min_qty:
				order(asset, -1 * min_qty, limit_price)
				residual_qty += min_qty
			order(asset, residual_qty, limit_price)

	def send_orders(self, price_qty_map, order_side):
		self.update()
		updated_all = True
		# clean orders only:
		if price_qty_map is None or len(price_qty_map) == 0:
			# clean current orders on this side
			if order_side == side.buy:
				if len(self.bid_map) == 0:
					logging.info('[cmx_order][send_orders] successful|no bids to cancel')
					return updated_all
				order_count = 0
				for p, ord_ls in self.bid_map.items():
					order_count += len(ord_ls)
					updated_all &= self.cancel_orders(ord_ls)
				if updated_all:
					logging.info('[cmx_order][send_orders] successful|{} bids are cancelled'.format(order_count))
				else:
					logging.warning('[cmx_order][send_orders] failed to cancel all bids')
				return updated_all
			if order_side == side.sell:
				if len(self.ask_map) == 0:
					logging.info('[cmx_order][send_orders] successful|no asks to cancel')
					return updated_all
				order_count = 0
				for p, ord_ls in self.ask_map.items():
					order_count += len(ord_ls)
					updated_all &= self.cancel_orders(ord_ls)
				if updated_all:
					logging.info('[cmx_order][send_orders] successful|{} asks are cancelled'.format(order_count))
				else:
					logging.warning('[cmx_order][send_orders] failed to cancel all asks')
				return updated_all

		decimal_price_qty_map = {self._get_decimal_price(x) : price_qty_map[x] for x in price_qty_map}
		price_update_map = {x : False for x in decimal_price_qty_map}
		
		if order_side == side.buy:
			cancel_order_count = 0
			update_order_count = 0
			for p, ord_ls in self.bid_map.items():
				if p not in decimal_price_qty_map:
					cancel_order_count += len(ord_ls)
					updated_all &= self.cancel_orders(ord_ls)
				else:
					if decimal_price_qty_map[p] > 0:
						update_order_count += 1
						updated_all &= self.update_order(p, decimal_price_qty_map[p], order_side)
						price_update_map[p] = True
					elif decimal_price_qty_map[p] == 0:
						cancel_order_count += len(ord_ls)
						updated_all &= self.cancel_orders(ord_ls)
						price_update_map[p] = True
			# add new orders:
			if updated_all:
				logging.info('[cmx_order][send_orders] successful|{} bids are cancelled, {} bids are updated'.format(
																										cancel_order_count, 
																										update_order_count
																									   ))
			else:
				logging.warning('[cmx_order][send_orders] failed to update all bids')
			# if updated_all or not self.is_live:
			for p, q in decimal_price_qty_map.items():
				if p is None:
					continue
				if not price_update_map[p] and q >= self.context.invent_min_share:
					self.split_order(self.context.asset, q, limit_price = float(p))
					logging.info('[cmx_order][send_orders] send bid {} * {}'.format(p, q))
			return updated_all

		if order_side == side.sell:
			cancel_order_count = 0
			update_order_count = 0
			for p, ord_ls in self.ask_map.items():
				if p not in decimal_price_qty_map:
					cancel_order_count += len(ord_ls)
					updated_all &= self.cancel_orders(ord_ls)
				else:
					if decimal_price_qty_map[p] < 0:
						update_order_count += 1
						updated_all &= self.update_order(p, decimal_price_qty_map[p], order_side)
						price_update_map[p] = True
					elif decimal_price_qty_map[p] == 0:
						cancel_order_count += len(ord_ls)
						updated_all &= self.cancel_orders(ord_ls)
						decimal_price_qty_map[p] = True
			if updated_all:
				logging.info('[cmx_order][send_orders] successful|{} asks are cancelled, {} asks are updated'.format(
																										cancel_order_count, 
																										update_order_count
																									   ))
			else:
				logging.warning('[cmx_order][send_orders] failed to update all asks')
			# if updated_all or not self.is_live:
			for p, q in decimal_price_qty_map.items():
				if not price_update_map[p] and q <= -1 * self.context.invent_min_share:
					self.split_order(self.context.asset, q, limit_price = float(p))
					logging.info('[cmx_order][send_orders] send ask {} * {}'.format(p, q))
			return updated_all
