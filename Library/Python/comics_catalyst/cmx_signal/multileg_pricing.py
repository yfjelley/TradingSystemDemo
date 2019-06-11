import logging
import numpy as np
from cmx_signal.util import get_legel_bar_info
from cmx_signal.indicators import sma
import logging
from catalyst.api import symbol


class price_ratio:
    def __init__(self, context):
        self.context = context
        self.leg_num = context.cmx_config.global_leg_num
        self.catalyst_assets   = self.context.cmx_config.catalyst_assets
        self.prices = [np.nan] * self.leg_num
        self._window_info = get_legel_bar_info(
                                               barsize  = self.context.cmx_config.signal_candle_size,
                                               barcount = self.context.cmx_config.signal_window,
                                               limit    = self.context.cmx_config.signal_hist_bar_limit,
                                               mode     = self.context.cmx_config.global_mode
                                              )

        self.window  = self._window_info['barcount']
        self.barsize = self._window_info['barsize']
        self.bid_ask_offsets = self.context.cmx_config.signal_bid_ask_diffs
        self._update_min_tdelta = self.context.cmx_config.signal_update_rate
        self.sig_sma = sma(self.window, minsd = self.context.cmx_config.signal_minsd)

        self.ts = None
        self.signal  = np.nan
        self.mean    = np.nan
        self.std     = np.nan
        self.zscore  = np.nan
        self.is_updated = False
        self.can_update = True
        self._last_update_ts = None
        
    def reload_config(self, data):
        self.leg_num = self.context.cmx_config.global_leg_num
        self.catalyst_assets   = self.context.cmx_config.catalyst_assets
        self.prices = [np.nan] * self.leg_num
        self._window_info = get_legel_bar_info(
                                               barsize  = self.context.cmx_config.signal_candle_size,
                                               barcount = self.context.cmx_config.signal_window,
                                               limit    = self.context.cmx_config.signal_hist_bar_limit,
                                               mode     = self.context.cmx_config.global_mode
                                              )

        self.window  = self._window_info['barcount']
        self.barsize = self._window_info['barsize']
        self.bid_ask_offsets = self.context.cmx_config.signal_bid_ask_diffs
        self._update_min_tdelta = self.context.cmx_config.signal_update_rate
        self.sig_sma = sma(self.window, minsd = self.context.cmx_config.signal_minsd)
        self._reload_sma(data)

    def disable_update(self):
        self.can_update = False
        logging.info('[price_ratio] disabled signal.')

    def enable_update(self):
        self.can_update = True
        logging.info('[price_ratio] enabled signal.')

    def _reload_sma(self, data):
        hist_data_list = [
                          data.history(
                                       self.catalyst_assets[i],
                                       'price',
                                       bar_count = self.window,
                                       frequency = self.barsize
                                      )
                          for i in range(self.leg_num)
                         ]
        for i in range(self.leg_num):
            if len(hist_data_list[i]) != len(hist_data_list[0]):
                logging.warning('[price_ratio] historical data of {} incomplete.'.format(self.context.cmx_config.global_symbols[i]))
                return False

        hist_signals = hist_data_list[0] / hist_data_list[1]
        hist_signals.dropna(inplace = True)
        
        self.sig_sma.flush(hist_signals)
        self._last_update_ts = self.sig_sma.ts
        self.ts     = self.sig_sma.ts
        self.signal = self.sig_sma.signal
        self.mean   = self.sig_sma.mean
        self.std    = self.sig_sma.std
        self.zscore = self.sig_sma.zscore
        logging.info('[price_ratio] reloaded historical data: ts = {}|signal = {}|mean = {}|std = {}|zscore = {}'.format(
                                                                                                                         self.ts,
                                                                                                                         self.signal,
                                                                                                                         self.mean,
                                                                                                                         self.std,
                                                                                                                         self.zscore
                                                                                                                        ))
        return True

    def update(self, data):
        if data is None:
            self.is_updated = False
            logging.warning('[price_ratio] failed to update: None Data Received.')
            return self.is_updated

        if np.isnan(self.mean):
            reloaded = self._reload_sma(data)
            if not reloaded:
                self.is_updated = False
                return self.is_updated

        if not self.can_update:
            logging.info('[price_ratio] cannot update.')
            self.is_updated = False
            return self.is_updated

        need_udpate = False
        if not self._last_update_ts:
            self._last_update_ts = self.sig_sma.ts

        self.ts = data.current_dt
        if self.ts - self._last_update_ts >= self._update_min_tdelta:
            need_udpate = True

        if not need_udpate:
            logging.info('[price_ratio] no need to update.')
            self.is_updated = False
            return self.is_updated

        self.prices = [data.current(self.catalyst_assets[i], 'price') for i in range(self.leg_num)]
        if self.prices[1] != 0:
            self.signal = self.prices[0] / self.prices[1]
            self.is_updated = self.sig_sma.update(self.signal, self.ts)
            if self.is_updated:
                self.mean   = self.sig_sma.mean
                self.std    = self.sig_sma.std
                self.zscore = self.sig_sma.zscore 
        else:
            self.is_updated = False
        return self.is_updated



