import os
from catalyst.api import record
import datetime as dt
import logging
import pandas as pd



class multileg_recorder:
    def __init__(self, context):
        self.context = context
        self.ts = None
        self.refresh_tdelta = self.context.cmx_config.storage_refresh_rate
        self._last_update_ts = None
        self.is_live = self.context.cmx_config.global_mode != 'backtest'
        
        self.perf_df = pd.DataFrame(
                                    columns = [
                                               'leg_pos',
                                               'leg_cost',
                                               'leg_realized',
                                               'leg_unrealized_offset',
                                               'leg_fee',
                                               'leg_traded',
                                               'leg_net',
                                               'leg_price'
                                              ]
                                   )
        self.trade_df = pd.DataFrame(
                                     columns = [
                                                'symbol',
                                                'side',
                                                'price',
                                                'amount',
                                                'fee',
                                                'fee_coin',
                                                'position',
                                                'cost_basis'
                                               ]
                                    )
        self.new_trade_df = pd.DataFrame(
                                         columns = [
                                                    'symbol',
                                                    'side',
                                                    'price',
                                                    'amount',
                                                    'fee',
                                                    'fee_coin',
                                                    'position',
                                                    'cost_basis'
                                                   ]
                                        )
        self.snapshot_df = pd.DataFrame(
                                        columns = [
                                                   'signal',
                                                   'mean',
                                                   'std',
                                                   'zscore',
                                                   'leg_price',
                                                   'pnl',
                                                   'net',
                                                   'leg_pos',
                                                   'leg_pnl',
                                                   'leg_net',
                                                   'leg_cost',
                                                   'leg_max_pos'
                                                  ]
                                        )
        self.trade_path    = None
        self.snapshot_path = None

    def reset(self):
        self.snapshot_df = pd.DataFrame(
                                        columns = [
                                                   'signal',
                                                   'mean',
                                                   'std',
                                                   'zscore',
                                                   'leg_price',
                                                   'pnl',
                                                   'net',
                                                   'leg_pos',
                                                   'leg_pnl',
                                                   'leg_net',
                                                   'leg_cost',
                                                   'leg_max_pos'
                                                  ]
                                        )

    def run(self):
        ts = self.context.cmx_signal.ts
        if not ts:
            return
        if self.ts and ts.date() != self.ts.date():
            self.reset()
        
        self.ts = ts
        # self.save_perf_stat()
        self.save_trades()
        snap_updated = self.update_snapshot()
        if self._last_update_ts is None or \
           self.ts - self._last_update_ts >= self.refresh_tdelta or \
           self.ts.time() >= dt.time(23,59):
            self._last_update_ts = self.ts
            if snap_updated:
                self.save_snapshot()
                

    def save_record(self):
        record(
              )
    
    def _get_position_and_cost_basis(self, ts):
        # if self.snapshot_df is None or len(self.snapshot_df) == 0:
        #     return{
        #            'position'  : self.context.cmx_risk.base_pos, 
        #            'cost_basis': self.context.cmx_risk.cost_basis
        #            }
        # local_snap_df = self.snapshot_df[
        #                                  (self.snapshot_df.index >= ts) & 
        #                                  (self.snapshot_df.index <= ts + self.refresh_tdelta)
        #                                 ]
        # if len(local_snap_df) == 0:
        #     return{
        #            'position'  : self.context.cmx_risk.base_pos, 
        #            'cost_basis': self.context.cmx_risk.cost_basis
        #            }
        # return {
        #         'position'  : local_snap_df['position'][0],
        #         'cost_basis': local_snap_df['cost_basis'][0]
        #        }
        pass

    def save_perf_stat(self):
        # self.context.cmx_risk.save_pnl_stat()
        pass

    def _update_trades(self):
        if self.ts is None:
            return False
        ts = self.ts.replace(tzinfo = None)
        self.trade_path = os.path.join(self.context.cmx_config.storage_trade_folder, self.context.cmx_config.storage_trade_file)
        if self.is_live and os.path.exists(self.trade_path):
            self.trade_df = pd.read_csv(
                                        self.trade_path,
                                        index_col = 0,
                                        header = 0,
                                        parse_dates = True
                                       )
        self.trade_df = self.trade_df[self.trade_df.index >= dt.datetime.combine(ts.date(), dt.time(0,0))]

        self.new_trade_df = self.context.cmx_risk.trade_df
        if len(self.trade_df) > 0:
            self.new_trade_df = self.new_trade_df[self.new_trade_df.index > self.trade_df.index[-1]]
        else:
            self.new_trade_df = self.new_trade_df[self.new_trade_df.index >= dt.datetime.combine(ts.date(), dt.time(0,0))]
        if len(self.new_trade_df) == 0:
            return False
        self.trade_df = pd.concat([self.trade_df, self.new_trade_df])
        return True

    def save_trades(self):
        updated = self._update_trades()
        if updated:
            self.trade_df[[
                           'symbol',
                           'side',
                           'price',
                           'amount',
                           'fee',
                           'fee_coin',
                           'position',
                           'cost_basis'
                         ]].to_csv(self.trade_path)

    def update_snapshot(self):
        if self.ts is None:
            return False
        ts = self.ts.replace(tzinfo = None)
        
        self.snapshot_path = os.path.join(self.context.cmx_config.storage_snapshot_folder, self.context.cmx_config.storage_snapshot_file)
        if self.is_live and os.path.exists(self.snapshot_path):
            self.snapshot_df = pd.read_csv(
                                           self.snapshot_path, 
                                           index_col = 0, 
                                           header = 0, 
                                           parse_dates = True
                                          )
    
        self.snapshot_df.loc[ts] = {
                                    'signal'     : self.context.cmx_signal.signal,
                                    'mean'       : self.context.cmx_signal.mean,
                                    'std'        : self.context.cmx_signal.std,
                                    'zscore'     : self.context.cmx_signal.zscore,
                                    'leg_price'  : self.context.cmx_signal.prices.copy(),
                                    'pnl'        : self.context.cmx_risk.pnl,
                                    'net'        : self.context.cmx_risk.net,
                                    'leg_pos'    : self.context.cmx_risk.leg_quote_positions.copy(),
                                    'leg_pnl'    : self.context.cmx_risk.leg_pnls.copy(),
                                    'leg_net'    : self.context.cmx_risk.leg_nets.copy(),
                                    'leg_cost'   : self.context.cmx_risk.leg_costs.copy(),
                                    'leg_max_pos': [self.context.cmx_config.risk_max_notional,self.context.cmx_config.risk_max_notional]
                                   }
        return True
    
    def save_snapshot(self):
        if len(self.snapshot_df) == 0:
            return False
        
        self.snapshot_df[[
                          'signal',
                          'mean',
                          'std',
                          'zscore',
                          'leg_price',
                          'pnl',
                          'net',
                          'leg_pos',
                          'leg_pnl',
                          'leg_net',
                          'leg_cost',
                          'leg_max_pos'
                          ]].to_csv(self.snapshot_path)
        return True

