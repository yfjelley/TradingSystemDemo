import numpy as np
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parents[3]))
from cmx_execution.multileg_order_manager import side
from cmx_risk.anchor_manager import anchor_linear_scalper
from cmx_risk.hedging_manager import hedging_linear_scalper
import logging
from catalyst.api import get_orderbook

class twoleg_anchor:
    def __init__(self, context):
        self.ts = None
        self.context = context
        self.catalyst_asset = self.context.cmx_config.catalyst_assets[0]
        self.leg_num = self.context.cmx_config.global_leg_num
        self.e0 = self.context.cmx_config.invent_e0
        self.en = self.context.cmx_config.invent_en
        self.n  = self.context.cmx_config.invent_n
        self.pm = self.context.cmx_config.invent_profit_margin
        self.spl = self.context.cmx_config.invent_share_per_level
        self.min_pos = self.context.cmx_config.risk_min_notional
        self.max_pos = self.context.cmx_config.risk_max_notional
        self.flat_pos = (self.min_pos + self.max_pos) / 2
        self.ignore_partial_fill = self.context.cmx_config.invent_ignore_partial_fills[0]
        self.min_share = self.context.cmx_config.invent_min_shares[0]
        self.bid_ask_signal_offsets = self.context.cmx_config.signal_bid_ask_diffs.copy()
        self.bid_ask_offsets = self.context.cmx_config.invent_bid_ask_offsets.copy()
        self.is_live = self.context.cmx_config.global_mode != 'backtest'
        # self.ref_prices = [np.nan] * self.leg_num
        self.prices = [np.nan] * self.leg_num
        self.base_pos  = np.nan
        self.quote_pos = np.nan
        self.pre_pos   = np.nan
        self.pm_price  = np.nan
        self.traded = 0
        self.level = 0
        self.fully_filled = True
        self.filled_qty = 0
        self.trading_status = self.context.cmx_risk.trading_status

    def reload_config(self):
        self.catalyst_asset = self.context.cmx_config.catalyst_assets[0]
        self.leg_num = self.context.cmx_config.global_leg_num
        self.e0 = self.context.cmx_config.invent_e0
        self.en = self.context.cmx_config.invent_en
        self.pm = self.context.cmx_config.invent_profit_margin
        self.spl = self.context.cmx_config.invent_share_per_level
        self.min_pos = self.context.cmx_config.risk_min_notional
        self.max_pos = self.context.cmx_config.risk_max_notional
        self.flat_pos = (self.min_pos + self.max_pos) / 2
        self.ignore_partial_fill = self.context.cmx_config.invent_ignore_partial_fills[0]
        self.min_share = self.context.cmx_config.invent_min_shares[0]
        self.bid_ask_signal_offsets = self.context.cmx_config.signal_bid_ask_diffs.copy()
        self.bid_ask_offsets = self.context.cmx_config.invent_bid_ask_offsets.copy()

    def _update(self):
        self.ts = self.context.cmx_signal.ts
        # self.ref_prices = self.context.cmx_risk.init_prices.copy()
        self.prices = self.context.cmx_signal.prices.copy()
        # self.spl = self.context.cmx_risk.leg_share_ratios[0]
        # self.min_pos = self.context.cmx_config.risk_min_notional / self.ref_prices[0]
        # self.max_pos = self.context.cmx_config.risk_max_notional / self.ref_prices[0]
        # self.flat_pos = (self.min_pos + self.max_pos) / 2
        # self.ignore_partial_fill = self.context.cmx_config.invent_ignore_partial_fills[0] / self.ref_prices[0]
        # self.min_share = self.context.cmx_config.invent_min_shares[0] / self.ref_prices[0]
        self.pre_pos = self.quote_pos
        self.base_pos = self.context.cmx_risk.leg_positions[0]
        self.quote_pos = self.context.cmx_risk.leg_quote_positions[0]
        self.pm_price = self._get_pm_in_price()
        self.traded = self.context.cmx_risk.leg_traded_amounts[0]
        self.trading_status = self.context.cmx_risk.trading_status
        if self.quote_pos >= self.flat_pos:
            self.level = int(np.floor((self.quote_pos - self.flat_pos) / self.spl))
            self.filled_qty = self.quote_pos - self.flat_pos - self.level * self.spl
            self.fully_filled = (self.filled_qty <= self.ignore_partial_fill) or (self.spl - self.filled_qty <= self.ignore_partial_fill)
        else:
            self.level = -1 * int(np.floor((self.flat_pos - self.quote_pos) / self.spl))
            self.filled_qty = self.quote_pos - self.flat_pos - self.level * self.spl
            self.fully_filled = (-self.filled_qty <= self.ignore_partial_fill) or (self.spl + self.filled_qty <= self.ignore_partial_fill)

    def _get_adding_bidprice(self, level):
        if level < 0 or level >= self.n:
            return None
        if self.n > 1:
            ei = self.e0 + (self.en - self.e0) * level / (self.n - 1)
        else:
            ei = self.e0
        mean = self.context.cmx_signal.mean
        std  = self.context.cmx_signal.std
        bid_signal = mean - ei * std
        hedger_price = self.prices[1] - self.bid_ask_signal_offsets[1]
        bid_price = bid_signal * hedger_price
        return bid_price

    def _get_adding_askprice(self, level):
        if level > 0 or level <= -self.n:
            return None
        if self.n > 1:
            ei = self.e0 - (self.en - self.e0) * level / (self.n - 1)
        else:
            ei = self.e0
        mean = self.context.cmx_signal.mean
        std  = self.context.cmx_signal.std
        ask_signal = mean + ei * std
        hedger_price = self.prices[1] + self.bid_ask_signal_offsets[1]
        ask_price = ask_signal * hedger_price
        return ask_price

    def _get_pm_in_price(self):
        pm_sig = self.pm * self.context.cmx_signal.std
        pm_prc = self.prices[1] * pm_sig
        return pm_prc

    def _trade(self, min_pos, max_pos):
        # call self._update() before running this function
        if self.quote_pos >= self.flat_pos:
            bids = {}
            if self.trading_status != 'hedge_only' or self.pre_pos > self.quote_pos:
                if max_pos - self.quote_pos >= self.min_share:
                    if self.spl - self.filled_qty >= self.min_share:
                        bprc = self._get_adding_bidprice(self.level)
                        if bprc:
                            bqty = min(self.spl - self.filled_qty, max_pos - self.quote_pos)
                            bids = {bprc: bqty / bprc}
                    else:
                        bprc = self._get_adding_bidprice(self.level + 1)
                        if bprc:
                            bqty = min(2 * self.spl - self.filled_qty, max_pos - self.quote_pos)
                            bids = {bprc: bqty / bprc}
            asks = {}
            if self.trading_status != 'hedge_only' or self.pre_pos < self.quote_pos:
                if min_pos - self.quote_pos <= -self.min_share:
                    aprc = self._get_adding_askprice(0)
                    if self.filled_qty >= self.min_share:
                        aqty = max(-self.filled_qty, min_pos - self.quote_pos)
                        bprc = self._get_adding_bidprice(self.level)
                    else:
                        aqty = max(-self.spl - self.filled_qty, min_pos - self.quote_pos)
                        bprc = self._get_adding_bidprice(self.level - 1)
                    if bprc:
                        aprc = min(aprc, bprc + self.pm_price)
                    asks = {aprc: aqty / aprc}
        else: 
            asks = {}
            if self.trading_status != 'hedge_only' or self.pre_pos < self.quote_pos:
                if min_pos - self.quote_pos <= -self.min_share:
                    if self.spl + self.filled_qty >= self.min_share:
                        aqty = -min(self.spl + self.filled_qty, self.quote_pos - min_pos)
                        aprc = self._get_adding_askprice(self.level)
                        if aprc:
                            asks = {aprc: aqty / aprc}
                    else:
                        aprc = self._get_adding_askprice(self.level - 1)
                        if aprc:
                            aqty = -min(2 * self.spl + self.filled_qty, self.quote_pos - min_pos)
                            asks = {aprc: aqty / aprc}
            bids = {}
            if self.trading_status != 'hedge_only' or self.pre_pos > self.quote_pos:
                if max_pos - self.quote_pos >= self.min_share:
                    bprc = self._get_adding_bidprice(0)
                    if -self.filled_qty >= self.min_share:
                        bqty = min(-self.filled_qty, max_pos - self.quote_pos)
                        aprc = self._get_adding_askprice(self.level)
                    else:
                        bqty = min(self.spl - self.filled_qty, max_pos - self.quote_pos)
                        aprc = self._get_adding_askprice(self.level + 1)
                    if aprc:
                        bprc = max(bprc, aprc - self.pm_price)
                    bids = {bprc: bqty / bprc}

        self.context.cmx_exec.send_orders(self.catalyst_asset, bids, side.buy)
        self.context.cmx_exec.send_orders(self.catalyst_asset, asks, side.sell)

    def trade_normal(self):
        self._update()
        self._trade(self.min_pos, self.max_pos)

    def hedge_only(self):
        # reduce only
        self._update()
        self._trade(self.min_pos, self.max_pos)

    def exit_nonew(self):
        self._update()
        if abs(self.quote_pos - self.flat_pos) <= self.min_share:
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
            return
        if self.quote_pos < self.flat_pos:
            self._trade(self.quote_pos, self.flat_pos)
            return
        if self.quote_pos > self.flat_pos:
            self._trade(self.flat_pos, self.quote_pos)
            return

    def exit_passive(self):
        self._update()
        if not self.is_live:
            return
        if abs(self.quote_pos - self.flat_pos) <= self.min_share or self.trading_status == 'hedge_only':
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
            return
        depth = get_orderbook(self.catalyst_asset)
        if self.quote_pos > self.flat_pos:
            aprc = depth['asks'][0]['rate']
            aqty = -min(self.spl, self.quote_pos - self.flat_pos)
            asks = {aprc: aqty / aprc}
            self.context.cmx_exec.send_orders(asks, side.sell)
            self.context.cmx_exec.send_orders({}, side.buy)
            return
        if self.quote_pos < self.flat_pos:
            bprc = depth['bids'][0]['rate']
            bqty = min(self.spl, self.flat_pos - self.quote_pos)
            bids = {bprc: bqty}
            self.context.cmx_exec.send_orders(bids, side.buy)
            self.context.cmx_exec.send_orders({}, side.sell)
            return

    def exit_active(self):
        self._update()
        if not self.is_live:
            return
        if abs(self.quote_pos - self.flat_pos) <= self.min_share or self.trading_status == 'hedge_only':
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
            return
        depth = get_orderbook(self.catalyst_asset)
        bbprc = depth['bids'][0]['rate']
        baprc = depth['asks'][0]['rate']
        mprc  = (bbprc + baprc) / 2
        if self.quote_pos > self.flat_pos:
            aprc = mprc
            aqty = -min(self.spl, self.quote_pos - self.flat_pos)
            asks = {aprc: aqty / aprc}
            self.context.cmx_exec.send_orders(self.catalyst_asset, asks, side.sell)
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
            return
        if self.quote_pos < self.flat_pos:
            bprc = mprc
            bqty = min(self.spl, self.flat_pos - self.quote_pos)
            bids = {bprc: bqty / bprc}
            self.context.cmx_exec.send_orders(self.catalyst_asset, bids, side.buy)
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
            return

    def cancel_all(self):
        self._update()
        self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
        self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
        return

class twoleg_hedger:
    def __init__(self, context):
        self.ts = None
        self.context = context
        self.catalyst_asset = self.context.cmx_config.catalyst_assets[1]
        self.leg_num = self.context.cmx_config.global_leg_num
        self.ignore_partial_fill = self.context.cmx_config.invent_ignore_partial_fills[1]
        self.min_share = self.context.cmx_config.invent_min_shares[1]
        self.spl = self.context.cmx_config.invent_share_per_level
        # self.spl = self.context.cmx_risk.leg_share_ratios[1]
        self.bid_ask_offset = self.context.cmx_config.invent_bid_ask_offsets[1]
        self.hedge_rate = self.context.cmx_config.invent_hedge_rates[1]
        self.init_hedge_level = self.context.cmx_config.invent_init_hedge_levels[1]
        self.is_live = self.context.cmx_config.global_mode != 'backtest'

        self.prices = [np.nan] * self.leg_num
        # self.ref_prices = [np.nan] * self.leg_num
        self.share_ratios = [np.nan] * self.leg_num
        self.base_pos  = np.nan
        self.quote_pos = np.nan
        self.traded = 0
        self.trading_status = self.context.cmx_risk.trading_status
        self.anchor_pos = np.nan
        self.target_pos = np.nan
        self.hedge_level = self.init_hedge_level # <0: passive, >0: active
        self.unhedged_unit = np.nan
        self.trading_status = None

    def reload_config(self):
        self.catalyst_asset = self.context.cmx_config.catalyst_assets[1]
        self.leg_num = self.context.cmx_config.global_leg_num
        self.ignore_partial_fill = self.context.cmx_config.invent_ignore_partial_fills[1]
        self.min_share = self.context.cmx_config.invent_min_shares[1]
        self.spl = self.context.cmx_config.invent_share_per_level
        self.bid_ask_offset = self.context.cmx_config.invent_bid_ask_offsets[1]
        self.hedge_rate = self.context.cmx_config.invent_hedge_rates[1]
        self.is_live = self.context.cmx_config.global_mode != 'backtest'

    def _update(self):
        self.ts = self.context.cmx_signal.ts
        self.prices = self.context.cmx_signal.prices.copy()
        # self.ref_prices = self.context.cmx_risk.init_prices.copy()
        # self.share_ratios = self.context.cmx_risk.leg_share_ratios.copy()
        # self.ignore_partial_fill = self.context.cmx_config.invent_ignore_partial_fills[1]
        # self.min_share = self.context.cmx_config.invent_min_shares[1] / self.ref_prices[1]
        # self.spl = self.context.cmx_risk.leg_share_ratios[1]
        self.base_pos = self.context.cmx_risk.leg_positions[1]
        self.quote_pos = self.context.cmx_risk.leg_quote_positions[1]
        self.traded = self.context.cmx_risk.leg_traded_amounts[1]
        self.trading_status = self.context.cmx_risk.trading_status
        self.anchor_pos = self.context.cmx_risk.leg_quote_positions[0]
        # self.target_pos = -1 * self.anchor_pos / self.share_ratios[0] * self.share_ratios[1]
        self.target_pos = -1 * self.anchor_pos
        self.trading_status = self.context.cmx_risk.trading_status
        unhedged_unit = round((self.target_pos - self.quote_pos) / self.spl)
        if unhedged_unit != self.unhedged_unit:
            self.hedge_level = self.init_hedge_level
            self.unhedged_unit = unhedged_unit

    def _trade(self):
        if abs(self.quote_pos - self.target_pos) < self.min_share:
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
            self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
            return
        bids = {}
        asks = {}
        if self.quote_pos > self.target_pos:
            aqty = self.target_pos - self.quote_pos
            if aqty < -self.min_share:
                aqty = max(aqty, -self.spl)
                if self.is_live:
                    # depth = get_orderbook(self.catalyst_asset)
                    # aprc = depth
                    pass
                else:
                    # if self.hedge_level == 0:
                    #     aprc = self.prices[1] + self.bid_ask_offset
                    # elif self.hedge_level < 1:
                    #     aprc = self.prices[1]
                    # else:
                    #     aprc = self.prices[1] - self.bid_ask_offset
                    aprc = self.prices[1] - self.hedge_level * self.bid_ask_offset
                    asks = {aprc: aqty / aprc}
        else:
            bqty = self.target_pos - self.quote_pos
            if bqty > self.min_share:
                bqty = min(bqty, self.spl)
                if self.is_live:
                    pass
                else:
                    # if self.hedge_level == 0:
                    #     bprc = max(0, self.prices[1] - self.bid_ask_offsets[1])
                    # elif self.hedge_level < 1:
                    #     bprc = self.prices[1]
                    # else:
                    #     bprc = self.prices[1] + self.bid_ask_offsets[1]
                    bprc = self.prices[1] + self.hedge_level * self.bid_ask_offset
                    bids = {bprc: bqty / bprc}
        self.hedge_level += self.hedge_rate
        self.context.cmx_exec.send_orders(self.catalyst_asset, bids, side.buy)
        self.context.cmx_exec.send_orders(self.catalyst_asset, asks, side.sell)

    def trade_normal(self):
        self._update()
        self._trade()

    def hedge_only(self):
        self._update()
        self._trade()
        
    def exit_nonew(self):
        self._update()
        self._trade()

    def exit_passive(self):
        self._update()
        self._trade()

    def exit_active(self):
        self._update()
        self._trade()

    def cancel_all(self):
        self._update()
        self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.buy)
        self.context.cmx_exec.send_orders(self.catalyst_asset, {}, side.sell)
        return

class twoleg_invent:
    def __init__(self, context):
        self.context = context
        self.anchor_invent = twoleg_anchor(context)
        self.hedger_invent = twoleg_hedger(context)

    def reload_config(self):
        self.anchor_invent.reload_config()
        self.hedger_invent.reload_config()

    def trade_normal(self):
        self.anchor_invent.trade_normal()
        self.hedger_invent.trade_normal()

    def hedge_only(self):
        self.anchor_invent.hedge_only()
        self.hedger_invent.hedge_only()

    def exit_nonew(self):
        self.anchor_invent.exit_nonew()
        self.hedger_invent.exit_nonew()

    def exit_passive(self):
        self.anchor_invent.exit_passive()
        self.hedger_invent.exit_passive()

    def exit_active(self):
        self.anchor_invent.exit_active()
        self.hedger_invent.exit_active()

    def cancel_all(self):
        self.anchor_invent.cancel_all()
        self.hedger_invent.cancel_all()