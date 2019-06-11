import numpy as np
import pathlib
import sys
from cmx_execution.order_manager import side
import logging
from catalyst.api import get_orderbook

class base_invent:
    def __init__(self, context):
        self.ts = None
        self.context = context
        self.position = np.nan
        self.traded = 0
        self.pm_std = 1e9

    def update_position(self):
        return self.position

    def cancel_all(self):
        pass

    def trade_normal(self):
        pass

    def exit_nonew(self):
        pass

    def exit_passive(self):
        pass

    def exit_active(self):
        pass


class outright_linear_scalper:
    def __init__(self, context):
        self.ts = None
        self.context = context
        self.position = np.nan
        self.pre_position = np.nan
        self.bid_prices = []
        self.ask_prices = []
        self.traded = 0 
        self.pm_std = 1e9
        self.mean_position = (self.context.risk_max_long_pos + self.context.risk_max_short_pos) / 2
        self.mean_position = int(np.floor(self.mean_position / self.context.invent_spn)) * self.context.invent_spn
        self.last_exit_ts = None
        self.exit_offset = 0
        self.quote_live = self.context.global_mode != 'backtest'

    def update_position(self):
        self.ts = self.context.cmx_signal.ts
        self.pre_position = self.position
        self.position = self.context.cmx_risk.position
        self.traded = self.context.cmx_risk.traded
        return self.position
    
    def update_entry_prices(self, buy_signal_offset = 0, sell_signal_offset = 0):
        if self.context.cmx_signal.is_updated or\
           buy_signal_offset != 0 or \
           sell_signal_offset != 0:
            fair_price = self.context.cmx_signal.fair_price
            fair_buy_price  = fair_price + buy_signal_offset
            fair_sell_price = fair_price + sell_signal_offset
            self.pm_std = self.context.invent_pm * self.context.cmx_signal.std
            self.bid_prices = fair_buy_price - self.context.cmx_signal.std \
                                             * np.linspace(self.context.invent_e0, 
                                                           self.context.invent_en, 
                                                           self.context.invent_n)
            self.ask_prices = fair_sell_price + self.context.cmx_signal.std \
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
        self.context.cmx_exec.send_orders({}, side.buy)
        self.context.cmx_exec.send_orders({}, side.sell)

    def assert_orders(self, price_qty_map, tradeside, min_pos, max_pos):
        if tradeside == side.buy:
            new_map = {}
            for k,v in price_qty_map.items():
                if k < 0:
                    logging.warning('[cmx_invent] illegal bid price {}, ignore'.format(k))
                    new_amount = 0
                elif v <= 0:
                    logging.warning('[cmx_invent] illegal bid size {}, ignore'.format(v))
                    new_amount = 0
                elif v + self.position > max_pos:
                    new_amount = max_pos - self.position
                    if new_amount < self.context.invent_min_share:
                        new_amount = 0
                    logging.warning('[cmx_invent] illegal bid order {} * {} is adding to position {}'.format(k, v, self.position) + 
                                    'exceeding max long position of {}. '.format(max_pos) +
                                    'trim order amount from {} to {}'.format(v, new_amount))
                else:
                    new_amount = v

                if new_amount > 0:
                    if new_map.get(k):
                        new_map[k] += new_amount
                    else:
                        new_map[k] = new_amount
            return new_map

        if tradeside == side.sell:
            new_map = {}
            for k,v in price_qty_map.items():
                if k < 0:
                    logging.warning('[cmx_invent] illegal ask price {}, ignroe'.format(k))
                    new_amount = 0
                elif v >= 0:
                    logging.warning('[cmx_invent] illegal ask size {}, ignore'.format(v))
                    new_amount = 0
                elif v + self.position < min_pos:
                    new_amount = min_pos - self.position
                    if new_amount > -1 * self.context.invent_min_share:
                        new_amount = 0
                    logging.warning('[cmx_invent] illegal ask order {} * {} is adding to position {}'.format(k, v, self.position) + 
                                    'exceeding max short position of {}. '.format(min_pos) +
                                    'trim order amount from {} to {}'.format(v, new_amount))
                else:
                    new_amount = v
                
                if new_amount < 0:
                    if new_map.get(k):
                        new_map[k] += new_amount
                    else:
                        new_map[k] = new_amount
            return new_map

    def _round_qty(self, qty):
        return round(qty / self.context.invent_ignore_partial_fill_value) * self.context.invent_ignore_partial_fill_value

    def _trade(self, min_pos = None, max_pos = None, buy_signal_offset = 0, sell_signal_offset = 0):
        # return True if order updated.
        self.update_position()
        if min_pos is None:
            min_pos = self.context.risk_max_short_pos
        if max_pos is None:
            max_pos = self.context.risk_max_long_pos

        self.update_entry_prices(buy_signal_offset, sell_signal_offset)
        if len(self.bid_prices) != self.context.invent_n or len(self.ask_prices) != self.context.invent_n:
            return False
        bids = {}
        asks = {}
        update_bids = False
        update_asks = False

        # tmp hack of partial fills
        # self.context.cmx_exec.update()
        # partial_bid_qty = self.context.cmx_exec.partial_bid_qty
        # partial_ask_qty = self.context.cmx_exec.partial_ask_qty
        
        if self._is_almost_equal(self.position, self.mean_position):
            # currently flat:
            self.context.cmx_signal.enable_update()
            bid_price = self.bid_prices[0]
            # bid_qty = self.context.invent_spn - partial_bid_qty
            bid_qty = self.context.invent_spn
            if bid_qty < self.context.invent_min_share:
                if len(self.bid_prices) > 1:
                    bid_price = self.bid_prices[1]
                    bid_qty += self.context.invent_spn
                else:
                    bid_qty = 0
            bid_qty = self._round_qty(bid_qty)
            bids = {bid_price: bid_qty}
            update_bids = True

            ask_price = self.ask_prices[0]
            # ask_qty = -1 * self.context.invent_spn - partial_ask_qty
            ask_qty = -1 * self.context.invent_spn
            if ask_qty > -1 * self.context.invent_min_share:
                if len(self.ask_prices) > 1:
                    ask_qty -= self.context.invent_spn
                    ask_price = self.ask_prices[1]
                else:
                    ask_qty = 0
            ask_qty = self._round_qty(ask_qty)
            asks = {ask_price: ask_qty}
            update_asks = True
        else:
            # position != mean_position
            pre_level = int(np.floor(abs(self.position - self.mean_position) / self.context.invent_spn)) # [0, n]
            fully_filled = False

            if self._is_almost_equal(abs(self.position - self.mean_position), pre_level * self.context.invent_spn):
                # example: pos = 20.01, spn = 20
                fully_filled = True
                working_qty = 0
                filled_qty = self.context.invent_spn \
                           + abs(self.position - self.mean_position) - pre_level * self.context.invent_spn
                pre_level -= 1
            elif self._is_almost_equal(abs(self.position - self.mean_position), (pre_level + 1) * self.context.invent_spn):
                # example: pos = 19.98, spn = 20
                fully_filled = True
                # working_qty = 0
                # filled_qty = self.context.invent_spn
                working_qty = (pre_level + 1) * self.context.invent_spn - abs(self.position - self.mean_position)
                filled_qty = self.context.invent_spn - working_qty
                if filled_qty < self.context.invent_min_share:
            
                    filled_qty = self.context.invent_spn
            elif self.position > max_pos:
                working_qty = 0
                filled_qty  = self.position - max_pos
                pre_level   = self.context.invent_n - 1 
            elif self.position < min_pos:
                working_qty = 0
                filled_qty  = min_pos - self.position
                pre_level   = self.context.invent_n - 1 
            else:
                # example: pos = 15, spn = 20
                fully_filled = False
                working_qty = (pre_level + 1) * self.context.invent_spn - abs(self.position - self.mean_position)
                filled_qty = self.context.invent_spn - working_qty
            logging.info('[cmx_invent] pre_level = {}|fully_filled = {}|position = {}|working_qty = {}|filled_qty = {}'.format(
                                                                                                            pre_level,
                                                                                                            fully_filled,
                                                                                                            self.position,
                                                                                                            working_qty,
                                                                                                            filled_qty
                                                                                                            ))
            if self.position > self.mean_position:
                if fully_filled:
                    self.context.cmx_signal.enable_update()
                    next_level = min(pre_level + 1, self.context.invent_n)
                    if next_level < self.context.invent_n:
                        update_bids = True
                        bid_price = self.bid_prices[next_level]
                        bid_qty = self.context.invent_spn + working_qty
                        if bid_qty < self.context.invent_min_share:
                            if next_level + 1 < self.context.invent_n:
                                bid_price = self.bid_prices[next_level + 1]
                                bid_qty += self.context.invent_spn
                            else:
                                bid_qty = 0
                        bid_qty = self._round_qty(bid_qty)
                        bids = {bid_price: bid_qty}
                    else:
                        update_bids = True
                        bids = {}
                        next_level = self.context.invent_n
                        pre_level = next_level - 1
                    update_asks = True
                    ask_price = self.bid_prices[pre_level] + self.pm_std
                    # ask_qty = -1 * filled_qty - partial_ask_qty
                    ask_qty = -1 * filled_qty
                    if ask_qty > -1 * self.context.invent_min_share:
                        if pre_level > 0:
                            ask_price = self.bid_prices[pre_level - 1] + self.pm_std
                            ask_qty -= self.context.invent_spn
                        else:
                            ask_qty = 0
                    ask_price = min(self.ask_prices[0], ask_price)
                    ask_qty = self._round_qty(ask_qty)
                    asks = {ask_price : ask_qty}
                else: # not fully filled
                    # The partial fill could come from previous buy / sell. 
                    # self.context.cmx_signal.disable_update()
                    if np.isnan(self.pre_position) or self.pre_position <= self.position:
                        # this is a bid partial fill (adding position)
                        update_bids = True
                        bid_price = self.bid_prices[pre_level]
                        # bid_qty = working_qty - partial_bid_qty
                        bid_qty = working_qty
                        if bid_qty < self.context.invent_min_share:
                            if pre_level >= self.context.invent_n - 1:
                                bid_qty = 0
                            else:
                                bid_price = self.bid_prices[pre_level + 1]
                                bid_qty += self.context.invent_spn
                        bid_qty = self._round_qty(bid_qty)
                        bids = {bid_price: bid_qty}

                        update_asks = True
                        # ask_qty = -1 * filled_qty - partial_ask_qty
                        ask_qty = -1 * filled_qty
                        ask_price = self.bid_prices[pre_level] + self.pm_std
                        if ask_qty > -1 * self.context.invent_min_share:
                            if pre_level > 0:
                                ask_price = self.bid_prices[pre_level - 1] + self.pm_std
                            else:
                                ask_price = self.ask_prices[0]
                            ask_qty -= self.context.invent_spn
                        ask_qty = self._round_qty(ask_qty)
                        ask_price = min(self.ask_prices[0], ask_price)
                        asks = {ask_price: ask_qty}

                    else: # self.pre_position > self.position:
                        # this is a ask partial fill (reducing position)
                        update_bids = True
                        # bid_qty = working_qty - partial_bid_qty
                        bid_qty = working_qty
                        bid_price = self.bid_prices[pre_level]
                        if bid_qty < self.context.invent_min_share:
                            if pre_level >= self.context.invent_n - 1:
                                bid_qty = 0
                            else:
                                bid_price = self.bid_prices[pre_level + 1]
                                bid_qty += self.context.invent_spn
                        bid_qty = self._round_qty(bid_qty)
                        bids = {bid_price: bid_qty}

                        update_asks = True
                        # ask_qty = -1 * filled_qty - partial_ask_qty
                        ask_qty = -1 * filled_qty
                        ask_price = self.bid_prices[pre_level] + self.pm_std
                        if ask_qty > -1 * self.context.invent_min_share:
                            ask_qty -= self.context.invent_spn
                            if pre_level > 0:
                                ask_price = self.bid_prices[pre_level - 1] + self.pm_std
                            else:
                                ask_price = self.ask_prices[0]
                        ask_qty = self._round_qty(ask_qty)
                        ask_price = min(self.ask_prices[0], ask_price)
                        asks = {ask_price: ask_qty}

            else: # position < mean_position
                if fully_filled:
                    self.context.cmx_signal.enable_update()
                    next_level = min(pre_level + 1, self.context.invent_n)
                    if next_level < self.context.invent_n:
                        update_asks = True
                        ask_price = self.ask_prices[next_level]
                        # ask_qty = -self.context.invent_spn - working_qty - partial_ask_qty
                        ask_qty = -1 * self.context.invent_spn - working_qty
                        if ask_qty > -1 * self.context.invent_min_share:
                            if next_level + 1 < self.context.invent_n:
                                ask_price = self.ask_prices[next_level + 1]
                                ask_qty -= self.context.invent_spn
                            else:
                                ask_qty = 0
                        ask_qty = self._round_qty(ask_qty)
                        asks = {ask_price: ask_qty}
                    else:
                        update_asks = True
                        asks = {}
                        next_level = self.context.invent_n
                        pre_level = next_level - 1
                    update_bids = True
                    bid_price = self.ask_prices[pre_level] - self.pm_std
                    # bid_qty = filled_qty - partial_bid_qty
                    bid_qty = filled_qty
                    if bid_qty < self.context.invent_min_share:
                        if pre_level > 0:
                            bid_price = self.ask_prices[pre_level - 1] - self.pm_std
                            bid_qty += self.context.invent_spn
                        else:
                            bid_qty = 0
                    bid_price = max(self.bid_prices[0], bid_price)
                    bid_qty = self._round_qty(bid_qty)
                    bids = {bid_price : bid_qty}
                else: # not fully filled
                    # self.context.cmx_signal.disable_update()
                    if np.isnan(self.pre_position) or self.pre_position >= self.position:
                        # this is a ask partial fill (adding position)
                        update_asks = True
                        ask_price = self.ask_prices[pre_level]
                        # ask_qty = -1 * working_qty - partial_ask_qty
                        ask_qty = -1 * working_qty
                        if ask_qty > -1 * self.context.invent_min_share:
                            if pre_level >= self.context.invent_n - 1:
                                ask_qty = 0
                            else:
                                ask_price = self.ask_prices[pre_level + 1]
                                ask_qty -= self.context.invent_spn
                        ask_qty = self._round_qty(ask_qty)
                        asks = {ask_price : ask_qty}

                        update_bids = True
                        # bid_qty = filled_qty - partial_bid_qty
                        bid_qty = filled_qty
                        bid_price = self.ask_prices[pre_level] - self.pm_std
                        if bid_qty < self.context.invent_min_share:
                            bid_qty += self.context.invent_spn
                            if pre_level > 0:
                                bid_price = self.ask_prices[pre_level - 1] - self.pm_std
                            else:
                                bid_price = self.bid_prices[0]
                        bid_price = max(self.bid_prices[0], bid_price)
                        bid_qty = self._round_qty(bid_qty)
                        bids = {bid_price : bid_qty}
                            
                    else: # self.pre_position < self.position
                        # this is a bid partial fill (reducing position)
                        update_asks = True
                        # ask_qty = -1 * working_qty - partial_ask_qty
                        ask_qty = -1 * working_qty
                        ask_price = self.ask_prices[pre_level]
                        if ask_qty > -1 * self.context.invent_min_share:
                            if pre_level >= self.context.invent_n - 1:
                                ask_qty = 0
                            else:
                                ask_qty -= self.context.invent_spn
                                ask_price = self.ask_prices[pre_level + 1]
                        ask_qty = self._round_qty(ask_qty)
                        asks = {ask_price: ask_qty}

                        update_bids = True
                        # bid_qty = filled_qty - partial_bid_qty
                        bid_qty = filled_qty
                        bid_price = self.ask_prices[pre_level] - self.pm_std
                        if bid_qty < self.context.invent_min_share:
                            bid_qty = self.context.invent_spn
                            if pre_level > 0:
                                bid_price = self.ask_prices[pre_level - 1] - self.pm_std
                            else:
                                bid_price = self.bid_prices[0]
                        bid_price = max(self.bid_prices[0], bid_price)
                        bid_qty = self._round_qty(bid_qty)
                        bids = {bid_price: bid_qty}

        if update_bids:
            bids = self.assert_orders(bids, side.buy, min_pos, max_pos)
            self.context.cmx_logger.log_sent_orders(bids, side.buy)
            self.context.cmx_exec.send_orders(bids, side.buy)
        if update_asks:
            asks = self.assert_orders(asks, side.sell, min_pos, max_pos)
            self.context.cmx_logger.log_sent_orders(asks, side.sell)
            self.context.cmx_exec.send_orders(asks, side.sell)
        if update_bids or update_asks:
            return True
        return False

    def trade_normal(self):
        return self._trade(self.context.risk_max_short_pos, self.context.risk_max_long_pos)

    def exit_nonew(self):
        self.update_position()
        if abs(self.position) <= self.context.invent_min_share:
            logging.info('[cmx_invent][exit_nonew] position = {}, removed all orders'.format(self.position))
            self.context.cmx_exec.send_orders({}, side.buy)
            self.context.cmx_exec.send_orders({}, side.sell)
            return True
        if self.position > 0:
            logging.info('[cmx_invent][exit_nonew] position = {}, sell only'.format(self.position))
            return self._trade(0, self.position)
        if self.position < 0:
            # this will be called when trade on margins:
            logging.info('[cmx_invent][exit_nonew] position = {}, buy only'.format(self.position))
            return self._trade(self.position, 0)

    def exit_passive(self):
        # if position > 0: reduce by selling at best ask, v.v.
        if not self.quote_live:
            return False

        self.update_position()
        if abs(self.position) <= self.context.invent_min_share:
            self.context.cmx_exec.send_orders({}, side.buy)
            self.context.cmx_exec.send_orders({}, side.sell)
            logging.info('cmx_invent][exit_passive] position = {}, removed all orders'.format(self.position))
            return True

        depth = get_orderbook(self.context.asset)
        if self.position > 0:
            askprice = depth['asks'][0]['rate']         
            askqty   = -1 * self.context.invent_spn
            if self.position < self.context.invent_spn:
                askqty = -1 * self.position
            self.context.cmx_exec.send_orders({askprice: askqty}, side.sell)
            self.context.cmx_exec.send_orders({}, side.buy)
            logging.info('cmx_invent][exit_passive] position = {}, selling passively {} * {}'.format(self.position, askprice, askqty))
            return True

        if self.position < 0:
            # this will be called when trade on margins:
            bidprice = depth['bids'][0]['rate']
            bidqty   = self.context.invent_spn
            if self.position > -1 * self.context.invent_spn:
                bidqty = -1 * self.position
            self.context.cmx_exec.send_orders({bidprice: bidqty}, side.buy)
            self.context.cmx_exec.send_orders({}, side.sell)
            logging.info('cmx_invent][exit_passive] position = {}, buying passively {} * {}'.format(self.position, bidprice, bidqty))
            return True

    def exit_active(self):
        # if position > 0: reduce by selling at midprice, v.v.
        if not self.quote_live:
            return False

        self.update_position()
        if abs(self.position) <= self.context.invent_min_share:
            self.context.cmx_exec.send_orders({}, side.buy)
            self.context.cmx_exec.send_orders({}, side.sell)
            logging.info('cmx_invent][exit_active] position = {}, removed all orders'.format(self.position))
            return True

        depth = get_orderbook(self.context.asset)
        bestbidprice = depth['bids'][0]['rate']
        bestaskprice = depth['asks'][0]['rate']
        midprice = (bestbidprice + bestaskprice) / 2
        
        if self.position > 0:
            askprice = midprice
            askqty   = -1 * self.context.invent_spn
            if self.position < self.context.invent_spn:
                askqty = -1 * self.position
            self.context.cmx_exec.send_orders({askprice: askqty}, side.sell)
            self.context.cmx_exec.send_orders({}, side.buy)
            logging.info('cmx_invent][exit_active] position = {}, selling actively {} * {}'.format(self.position, askprice, askqty))
            return True

        if self.position < 0:
            # this will be called when trade on margins:
            bidprice = midprice
            bidqty   = self.context.invent_spn
            if self.position > -1 * self.context.invent_spn:
                bidqty = -1 * self.position
            self.context.cmx_exec.send_orders({bidprice: bidqty}, side.buy)
            self.context.cmx_exec.send_orders({}, side.sell)
            logging.info('cmx_invent][exit_active] position = {}, buying actively {} * {}'.format(self.position, bidprice, bidqty))
            return True

