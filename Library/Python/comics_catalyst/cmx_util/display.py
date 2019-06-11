import datetime as dt
from decimal import Decimal
import cmx_util.system_monitor as cmx_sys
import numpy as np

class base_display:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = dt.timedelta(minutes = self.context.display_refresh_rate)
        self._last_update_ts = None

    def run(self):
        if self.context.global_mode == 'backtest' and not self.context.display_sim:
            return
        ts = self.context.cmx_signal.ts
        if self._last_update_ts is None or ts - self._last_update_ts >= self.refresh_tdelta:
            price  = '{:.2E}'.format(Decimal(self.context.cmx_signal.price))            
            
            print('\033[1;37;40m{} | {} | {} | {} | {}'.format(
                                                                    self.context.global_namespace, 
                                                                    self.context.global_mode,
                                                                    self.context.exchange_str,
                                                                    self.context.symbol_str,
                                                                    ts.replace(tzinfo = None)
                                                                    ))
            window_width = 78
            print('-' * window_width)

            print('|{:<10}|'.format('price'))
            default_str = '|{:<10}|'.format(price)

            print(default_str)
            print('-' * window_width)
            # print('CPU: {}% | RAM: {}%'.format(cpu_pct, ram_pct))
            self._last_update_ts = ts

    def run_daily(self):
        pass

class multileg_display:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = dt.timedelta(minutes = self.context.cmx_config.display_refresh_rate) \
                              if self.context.cmx_config.signal_candle_size == '1T' else None
        self._last_update_ts = None

    def run(self):
        if self.context.cmx_config.mode == 'backtest' and not self.context.cmx_config.display_sim:
            return
        ts = self.context.cmx_signal.ts
        if self._last_update_ts is None or ts - self._last_update_ts >= self.refresh_tdelta:
            signal  = '{:.2E}'.format(Decimal(self.context.cmx_signal.signal))
            mean    = '{:.2E}'.format(Decimal(self.context.cmx_signal.mean))
            std     = '{:.2E}'.format(Decimal(self.context.cmx_signal.std))
            zscore  = '{:.2E}'.format(Decimal(self.context.cmx_signal.zscore))
            pnl           = '{:.2E}'.format(Decimal(self.context.cmx_risk.pnl))
            anchor_pos    = '{:.2E}'.format(Decimal(self.context.cmx_risk.positions[0]))
            anchor_amount = '{:.2E}'.format(Decimal(self.context.cmx_risk.amounts[0]))
            traded        = '{:.2E}'.format(Decimal(float(np.sum(self.context.cmx_invent.trade_amounts))))

            cpu_pct = cmx_sys.get_cpu_pct()
            ram_pct = cmx_sys.get_ram_pct()
            
            print('{} | {} | {} | {} | {}'.format(
                                                self.context.cmx_config.namespace, 
                                                self.context.cmx_config.instance, 
                                                self.context.cmx_config.mode,
                                                self.context.cmx_config.risk_max_position,
                                                ts
                                                 ))
            window_len = 89
            print('-' * window_len)

            print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'
                    .format('pnl','pos','amount','signal','mean','std','zscore',''))
            print('|' + '-' * (window_len - 2) + '|')
            print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'
                    .format(pnl,anchor_pos,anchor_amount,signal,mean,std,zscore,''))
            print('|' + '-' * (window_len - 2) + '|')
            print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'
                    .format('symbol','exchange','buy','sell','ratio','pos','unhedged','traded'))
            for i in range(self.context.cmx_config.leg_num):
                print('|' + '-' * (window_len - 2) + '|')
                print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'
                      .format(
                              self.context.cmx_config.str_symbols[i],
                              self.context.cmx_config.str_exchanges[i],
                              self.context.cmx_invent.buy_flags[i],
                              self.context.cmx_invent.sell_flags[i],
                              '{:.2E}'.format(Decimal(self.context.cmx_signal.share_ratios[i])),
                              '{:.2E}'.format(Decimal(self.context.cmx_risk.positions[i])),
                              '{:.2E}'.format(Decimal(self.context.cmx_invent.unhedged_positions[i])),
                              '{:.2E}'.format(Decimal(self.context.cmx_invent.trade_positions[i]))
                              ))
            print('-' * window_len)
            print('CPU: {}% | RAM: {}%'.format(cpu_pct, ram_pct))
            self._last_update_ts = ts

    def run_daily(self):
        ts   = self.context.cmx_risk.ts
        if ts is None:
            return

        pnl  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_pnl))
        dd   = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_min_pnl))
        pos  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_positions[0]))
        minp = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_min_positions[0]))
        maxp = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_max_positions[0]))
        trd  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_trade_positions[0]))
        
        cpu_pct = cmx_sys.get_cpu_pct()
        ram_pct = cmx_sys.get_ram_pct()
        print('{} | {} | {} | {} | {}'.format(
                                    self.context.cmx_config.namespace, 
                                    self.context.cmx_config.instance, 
                                    self.context.cmx_config.mode,
                                    self.context.cmx_config.risk_max_position,
                                    ts.floor('1D')
                                                 ))
        print('-' * 67)
        print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format('pnl','dd','pos','min_pos','max_pos','trd'))
        print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format(pnl,dd,pos,minp,maxp,trd))
        print('-' * 67)
        print('CPU: {} | RAM: {}'.format(cpu_pct, ram_pct))

class outright_display:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = dt.timedelta(minutes = context.display_refresh_rate) if context.signal_candle_size == '1T' else None
        self._last_update_ts = None

    def run(self):
        if self.context.global_mode == 'backtest' and not self.context.display_sim:
            return
        ts = self.context.cmx_signal.ts
        if self._last_update_ts is None or ts - self._last_update_ts >= self.refresh_tdelta:
            price  = '{:.2E}'.format(Decimal(self.context.cmx_signal.price))
            fairp  = '{:.2E}'.format(Decimal(self.context.cmx_signal.fair_price))
            std    = '{:.2E}'.format(Decimal(self.context.cmx_signal.std))
            zscore = '{:.2E}'.format(Decimal(self.context.cmx_signal.zscore))
            net       = '{:.2E}'.format(Decimal(self.context.cmx_risk.net))
            base_pos  = '{:.2E}'.format(Decimal(self.context.cmx_risk.base_pos))
            quote_pos = '{:.2E}'.format(Decimal(self.context.cmx_risk.quote_pos))
            traded = '{:.2E}'.format(Decimal(self.context.cmx_risk.traded))
            status = 'normal'
            if self.context.cmx_risk.trading_status == 'exit_nonew':
                status = 'nonew'
            elif self.context.cmx_risk.trading_status == 'exit_passive':
                status = 'exit_psv'
            elif self.context.cmx_risk.trading_status == 'exit_active':
                status = 'exit_act'

            # cpu_pct = cmx_sys.get_cpu_pct()
            # ram_pct = cmx_sys.get_ram_pct()
            
            print('\033[1;37;40m{} | {} | {} | {} | {} | {}'.format(
                                                                    self.context.global_namespace, 
                                                                    self.context.global_mode,
                                                                    self.context.exchange_str,
                                                                    self.context.symbol_str,
                                                                    self.context.risk_max_position,
                                                                    ts.replace(tzinfo = None)
                                                                    ))
            window_width = 78
            print('-' * window_width)

            print('\033[1;37;40m|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'
                    .format('price','fair','zscore','status','net','bpos','traded'))
            default_str = '\033[1;37;40m|{:<10}|{:<10}|{:<10}'.format(price,fairp,zscore)
            status_str = '|\033[1;32;40m{:<10}'.format(status) if status == 'normal' else '|\033[1;31;40m{:<10}'.format(status)
            
            if self.context.cmx_risk.net > 0:
                net_str = '\033[1;37;40m|\033[1;30;102m{:<10}'.format(net)
            elif self.context.cmx_risk.net < 0:
                net_str = '\033[1;37;40m|\033[1;37;41m{:<10}'.format(net)
            else:
                net_str = '\033[1;37;40m|{:<10}'.format(net)

            if self.context.cmx_risk.base_pos > 0:
                pos_str = '\033[1;37;40m|\033[1;36;40m{:<10}'.format(base_pos)
            elif self.context.cmx_risk.base_pos < 0:
                pos_str = '\033[1;37;40m|\033[1;35;40m{:<10}'.format(base_pos)
            else:
                pos_str = '\033[1;37;40m|{:<10}'.format(base_pos)
            trd_str = '\033[1;37;40m|{:<10}'.format(traded)

            print(default_str + status_str + net_str + pos_str + trd_str + '|')
            print('-' * window_width)
            # print('CPU: {}% | RAM: {}%'.format(cpu_pct, ram_pct))
            self._last_update_ts = ts

    def run_daily(self):
        ts   = self.context.cmx_risk.ts
        if ts is None:
            return

        net  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_net))
        dd   = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_min_net))
        pos  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_position))
        minp = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_min_position))
        maxp = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_max_position))
        trd  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_traded))
        
        cpu_pct = cmx_sys.get_cpu_pct()
        ram_pct = cmx_sys.get_ram_pct()
        print('{} | {} | {} | {} | {} | {} | {}'.format(
                                    self.context.global_namespace, 
                                    self.context.global_instance, 
                                    self.context.global_mode,
                                    self.context.exchange_str,
                                    self.context.symbol_str,
                                    self.context.risk_max_position,
                                    ts.floor('1D')
                                                 ))
        print('-' * 67)
        print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format('net','dd','pos','min_pos','max_pos','trd'))
        print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format(net,dd,pos,minp,maxp,trd))
        print('-' * 67)
        print('CPU: {} | RAM: {}'.format(cpu_pct, ram_pct))