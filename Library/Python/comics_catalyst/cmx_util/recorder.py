import os
from catalyst.api import record
import datetime as dt
import logging
import pandas as pd
import numpy as np


class base_recorder:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = dt.timedelta(minutes = context.record_rate)
        self._last_update_ts = None
        self.file_prefix = '{}_{}_{}'.format(
                                            self.context.global_namespace,
                                            self.context.global_instance,
                                            self.context.global_mode
                                            )

        if self.context.trade_path is not None:
            if not os.path.exists(self.context.trade_path):
                os.makedirs(self.context.trade_path)
            self.trade_file = None
            self.trade_df = None
            self.new_trade_df = None
            # self.daily_start_position = 0
            # self.daily_start_cost_basis = 0

        if self.context.snapshot_path is not None:
            if not os.path.exists(self.context.snapshot_path):
                os.makedirs(self.context.snapshot_path)
            self.snapshot_file = None
            self.snapshot_df = None

    def run(self):
        ts = self.context.cmx_signal.ts
        if ts is None:
            return
        if self.context.snapshot_path is not None:
            self.update_snapshot()
        if self._last_update_ts is None or \
           ts - self._last_update_ts >= self.refresh_tdelta or \
           ts.time() >= dt.time(23,59):
            self._last_update_ts = ts
            if self.context.snapshot_path is not None:
                self.save_snapshot()
                logging.info('[cmx_record] saved snapshot for ts {}'.format(ts))

    def update_snapshot(self):
        if self.context.snapshot_path is None:
            return
        ts = self.context.cmx_signal.ts.replace(tzinfo = None)
        if ts is None:
            return
        
        if self.snapshot_df is not None:
            pre_ts = self.snapshot_df.dropna().index[-1]
            cur_ts = ts
            if cur_ts.date() - pre_ts.date() > dt.timedelta(days = 0):
                self.snapshot_file = '{}_{}.snapshot.csv'.format(self.file_prefix, ts.date())
                self.snapshot_df = None
        else:
            self.snapshot_file = '{}_{}.snapshot.csv'.format(self.file_prefix, ts.date())
            if os.path.exists(os.path.join(self.context.snapshot_path, self.snapshot_file)):
                self.snapshot_df = pd.read_csv(
                                                 os.path.join(self.context.snapshot_path, self.snapshot_file), 
                                                 index_col = 0, 
                                                 header = 0, 
                                                 parse_dates = True
                                                 )

        if self.snapshot_df is None:
            self.snapshot_df = pd.DataFrame({
                                             'open': self.context.cmx_signal.open,
                                             'high': self.context.cmx_signal.high,
                                             'low': self.context.cmx_signal.low,
                                             'close': self.context.cmx_signal.close,
                                             'volume': self.context.cmx_signal.volume,
                                             }, index = [ts])
            return
        self.snapshot_df.loc[ts] = {'open': self.context.cmx_signal.open,
                                    'high': self.context.cmx_signal.high,
                                    'low': self.context.cmx_signal.low,
                                    'close': self.context.cmx_signal.close,
                                    'volume': self.context.cmx_signal.volume
                                    }

    def save_snapshot(self):
        if self.snapshot_df is None or len(self.snapshot_df) == 0:
            return
        self.snapshot_df[['open','high','low','close','volume']].to_csv(os.path.join(self.context.snapshot_path, self.snapshot_file))


class outright_recorder:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = dt.timedelta(minutes = context.record_rate) if context.signal_candle_size == '1T' else None
        self._last_update_ts = None
        self.file_prefix = '{}_{}_{}'.format(
                                            self.context.global_namespace,
                                            self.context.global_instance,
                                            self.context.global_mode
                                            )

        if self.context.trade_path is not None:
            if not os.path.exists(self.context.trade_path):
                os.makedirs(self.context.trade_path)
            self.trade_file = None
            self.trade_df = None
            self.new_trade_df = None
            # self.daily_start_position = 0
            # self.daily_start_cost_basis = 0

        if self.context.snapshot_path is not None:
            if not os.path.exists(self.context.snapshot_path):
                os.makedirs(self.context.snapshot_path)
            self.snapshot_file = None
            self.snapshot_df = None

    def run(self):
        ts = self.context.cmx_signal.ts
        if ts is None:
            return
        self.save_perf_stat()
        if self.context.snapshot_path is not None:
            self.update_snapshot()
        if self._last_update_ts is None or \
           ts - self._last_update_ts >= self.refresh_tdelta or \
           ts.time() >= dt.time(23,59):
            self._last_update_ts = ts
            # self.context.cmx_logger.log_recorder_info(ts)
            self.save_record()
            logging.info('[cmx_record] saved mkt data for ts {}'.format(ts))
            if self.context.trade_path is not None:
                self.save_trades()
                logging.info('[cmx_record] saved trades for ts {}'.format(ts))
            if self.context.snapshot_path is not None:
                self.save_snapshot()
                logging.info('[cmx_record] saved snapshot for ts {}'.format(ts))

    def save_record(self):
        record(
                price        = self.context.cmx_signal.price,
                fair_price   = self.context.cmx_signal.fair_price,
                zscore       = self.context.cmx_signal.zscore,
                price_change = self.context.cmx_signal.price_change,
                invent_long_entry  =  self.context.cmx_signal.fair_price - self.context.invent_pm * self.context.cmx_signal.std,
                invent_short_entry = self.context.cmx_signal.fair_price + self.context.invent_pm * self.context.cmx_signal.std,
                base_pos  = self.context.cmx_risk.base_pos,
                quote_pos = self.context.cmx_risk.quote_pos,
                cmx_pnl = self.context.cmx_risk.pnl,
                cmx_max_pos = self.context.risk_max_long_pos
               )
    
    def _get_position_and_cost_basis(self, ts):
        if self.snapshot_df is None or len(self.snapshot_df) == 0:
            return{
                   'position'  : self.context.cmx_risk.base_pos, 
                   'cost_basis': self.context.cmx_risk.cost_basis
                   }
        local_snap_df = self.snapshot_df[
                                         (self.snapshot_df.index >= ts) & 
                                         (self.snapshot_df.index <= ts + self.refresh_tdelta)
                                        ]
        if len(local_snap_df) == 0:
            return{
                   'position'  : self.context.cmx_risk.base_pos, 
                   'cost_basis': self.context.cmx_risk.cost_basis
                   }
        return {
                'position'  : local_snap_df['position'][0],
                'cost_basis': local_snap_df['cost_basis'][0]
               }

    def save_perf_stat(self):
        self.context.cmx_risk.save_pnl_stat()

    def _update_trades(self):
        if self.trade_df is None:
            if os.path.exists(os.path.join(self.context.trade_path, self.trade_file)):
                self.trade_df = pd.read_csv(
                                        os.path.join(self.context.trade_path, self.trade_file), 
                                        index_col = 0, 
                                        header = 0, 
                                        parse_dates = True
                                        )
                self.trade_df = self.trade_df[self.trade_df.index >= dt.datetime.combine(self.context.cmx_signal.ts.date(), dt.time(0,0))]
        
        pre_ts = dt.datetime.combine(self.context.cmx_signal.ts.date(), dt.time(0,0))
        if self.trade_df is not None:
            self.trade_df = self.trade_df[self.trade_df.index >= pre_ts]
            if len(self.trade_df) > 0:
                pre_ts = self.trade_df.index[-1]
        
        if self.context.cmx_risk.trade_df is None:
            return False
        self.new_trade_df = self.context.cmx_risk.trade_df
        self.new_trade_df = self.new_trade_df[self.new_trade_df.index > pre_ts]
        if len(self.new_trade_df) == 0:
            return False
        self.trade_df = pd.concat([self.trade_df, self.new_trade_df])
        return True

    def save_trades(self):
        if self.context.trade_path is None:
            return

        ts = self.context.cmx_signal.ts.replace(tzinfo = None)
        if ts is None:
            return
        self.trade_file = '{}_{}.trade.csv'.format(self.file_prefix, ts.date())
        logging.debug('[cmx_record] trade_file: {}'.format(self.trade_file))

        trade_updated = self._update_trades()
        if trade_updated:
            self.trade_df[[
                           'symbol',
                           'side',
                           'price',
                           'amount',
                           'fee',
                           'fee_coin',
                           'position',
                           'cost_basis'
                         ]].to_csv(os.path.join(self.context.trade_path, self.trade_file))


    def update_snapshot(self):
        if self.context.snapshot_path is None:
            return
        ts = self.context.cmx_signal.ts.replace(tzinfo = None)
        if ts is None:
            return
        
        if self.snapshot_df is not None:
            pre_ts = self.snapshot_df.dropna().index[-1]
            cur_ts = ts
            if cur_ts.date() - pre_ts.date() > dt.timedelta(days = 0):
                self.snapshot_file = '{}_{}.snapshot.csv'.format(self.file_prefix, ts.date())
                self.snapshot_df = None
        else:
            self.snapshot_file = '{}_{}.snapshot.csv'.format(self.file_prefix, ts.date())
            if os.path.exists(os.path.join(self.context.snapshot_path, self.snapshot_file)):
                self.snapshot_df = pd.read_csv(
                                                 os.path.join(self.context.snapshot_path, self.snapshot_file), 
                                                 index_col = 0, 
                                                 header = 0, 
                                                 parse_dates = True
                                                 )
                # tmp hack, remove after stable
                if 'net' not in self.snapshot_df:
                    self.snapshot_df['net'] = np.nan

        if self.snapshot_df is None:
            self.snapshot_df = pd.DataFrame({
                                             'signal': self.context.cmx_signal.price, 
                                             'mean'  : self.context.cmx_signal.fair_price,
                                             'std'   : self.context.cmx_signal.std,
                                             'zscore': self.context.cmx_signal.zscore,
                                             'position': self.context.cmx_risk.base_pos,
                                             'pnl'     : self.context.cmx_risk.pnl,
                                             'net'     : self.context.cmx_risk.net,
                                             'cost_basis': self.context.cmx_risk.cost_basis,
                                             'max_pos': self.context.risk_max_long_pos
                                             }, index = [ts])
            return

        self.snapshot_df.loc[ts] = {
                                    'signal': self.context.cmx_signal.price, 
                                    'mean'  : self.context.cmx_signal.fair_price,
                                    'std'   : self.context.cmx_signal.std,
                                    'zscore': self.context.cmx_signal.zscore,
                                    'position': self.context.cmx_risk.base_pos,
                                    'pnl'     : self.context.cmx_risk.pnl,
                                    'net'     : self.context.cmx_risk.net,
                                    'cost_basis': self.context.cmx_risk.cost_basis,
                                    'max_pos': self.context.risk_max_long_pos
                                    }
    def save_snapshot(self):
        if self.snapshot_df is None or len(self.snapshot_df) == 0:
            return
        
        self.snapshot_df[[
                          'signal', 
                          'mean', 
                          'std', 
                          'zscore', 
                          'position', 
                          'pnl', 
                          'net',
                          'cost_basis',
                          'max_pos'
                          ]].to_csv(os.path.join(self.context.snapshot_path, self.snapshot_file))



####################################################################################
class multileg_recorder:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = dt.timedelta(minutes = self.context.cmx_config.record_rate) \
                            if self.context.cmx_config.signal_candle_size == '1T' else None
        self._last_update_ts = None

    def run(self):
        ts = self.context.cmx_signal.ts
        if ts is None:
            return
        if self._last_update_ts is None or ts - self._last_update_ts >= self.refresh_tdelta:
            record(
                    cmx_signal        = self.context.cmx_signal.signal,
                    cmx_signal_mean   = self.context.cmx_signal.mean,
                    cmx_signal_std    = self.context.cmx_signal.std,
                    cmx_signal_zscore = self.context.cmx_signal.zscore,
                    cmx_pnl           = self.context.cmx_risk.pnl,
                    cmx_position      = self.context.cmx_invent.positions[0],
                    cmx_amount        = self.context.cmx_invent.amounts[0],

                    cmx_prices        = self.context.cmx_invent.prices.copy(),
                    cmx_low_prices    = self.context.cmx_invent.lower_prices.copy(),
                    cmx_high_prices   = self.context.cmx_invent.upper_prices.copy(),
                    cmx_pnls          = self.context.cmx_risk.leg_pnls.copy(),
                    cmx_positions     = self.context.cmx_invent.positions.copy(),
                    cmx_amounts       = self.context.cmx_invent.amounts.copy(),
                    cmx_traded        = self.context.cmx_invent.trade_positions.copy(),
                    cmx_unhedged_amounts = self.context.cmx_invent.unhedged_amounts.copy(),
                    cmx_unhedged_positions = self.context.cmx_invent.unhedged_positions.copy(),
                   )
            self._last_update_ts = ts
