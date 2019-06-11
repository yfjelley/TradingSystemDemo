import datetime as dt
import logging
import numpy as np
from cmx_util.parser import get_legel_bar_info


class base_signal:
    def __init__(self, context):
        self.context = context
        self.ts = None
        self.price = np.nan
        self.open = np.nan
        self.high = np.nan
        self.low = np.nan
        self.close = np.nan
        self.volume = np.nan

    def update(self, data):
        self.ts = data.current_dt
        self.price = data.current(self.context.asset, 'price')
        self.open = data.current(self.context.asset, 'open')
        self.high = data.current(self.context.asset, 'high')
        self.low  = data.current(self.context.asset, 'low')
        self.close = data.current(self.context.asset, 'close')
        self.volume = data.current(self.context.asset, 'volume')

class sma:
    def __init__(self, context):
        self.context = context
        
        self.ts = None
        self.init_price = None
        self.price = np.nan
        self.price_change = np.nan
        self.fair_price = np.nan
        self.std = np.nan
        self.zscore = np.nan
        self.is_updated = False
        self.can_update = True

        self._last_update_ts = None
        # if context.signal_candle_size == '1T':
        self._update_min_tdelta = dt.timedelta(minutes = context.signal_update_rate)
        self._window_info = get_legel_bar_info(context)
        self.context.cmx_logger.log_signal_window_info(self._window_info)

    def disable_update(self):
        # disable update when there is working orders
        self.can_update = False
        self.context.cmx_logger.log_signal_disable()

    def enable_update(self):
        self.can_update = True
        self.context.cmx_logger.log_signal_enable()

    def update(self, data):
        self.ts = data.current_dt
        self.price = data.current(self.context.asset, 'price')
        if self.init_price is None:
            self.init_price = self.price
        self.price_change = self.price / self.init_price - 1 if self.init_price != 0 else np.nan
        self.zscore = (self.price - self.fair_price) / self.std if self.std != 0 else np.nan

        hist_data = data.history(self.context.asset,
                                 'price',
                                 bar_count = int(self._window_info['barcount'] * 1.2),
                                 frequency = self._window_info['barsize'],
                                )
        if self.context.signal_wait_for_full_hist and \
            len(hist_data) < self._window_info['barcount']:
            logging.warning(
                            '[sma] halt updating till receive full historical data|' + 
                            'receive = {}|need = {}|t0 = {}|t1 = {}'.format(
                                                                            len(hist_data), 
                                                                            self._window_info['barcount'],
                                                                            hist_data.index[0],
                                                                            hist_data.index[-1]
                                                                            ))
            self.is_updated = False
            return False

        need_update = False
        if self._last_update_ts is None:
            need_update = True
        else:
            if self.ts - self._last_update_ts >= self._update_min_tdelta:
                need_update = True
                if self.ts - hist_data.index[-1] > 1.5 * self._update_min_tdelta:
                    need_update = False
                    logging.warning('[sma] insufficient historical data end at {} when update at {}'.format(
                                                                                       hist_data.index[-1], 
                                                                                       self.ts
                                                                                       ))
        if need_update and self.can_update:
            self.fair_price = hist_data.iloc[-self._window_info['barcount'] : ].mean()
            self.std = hist_data.iloc[-self._window_info['barcount'] : ].std()
            self.std = max(self.std, self.context.signal_minsd * self.price)
            self.zscore = (self.price - self.fair_price) / self.std if self.std != 0 else np.nan
            self.is_updated = True
            self._last_update_ts = self.ts
        else:
            self.is_updated = False

        self.context.cmx_logger.log_signal(data)
        return need_update

