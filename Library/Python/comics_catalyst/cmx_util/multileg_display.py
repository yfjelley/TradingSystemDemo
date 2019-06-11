import datetime as dt
from decimal import Decimal
import numpy as np

class twoleg_display:
    def __init__(self, context):
        self.context = context
        self.refresh_tdelta = context.cmx_config.display_refresh_rate if context.cmx_config.signal_candle_size == '1T' else None
        self._last_update_ts = None

    def run(self):
        if self.context.cmx_config.global_mode == 'backtest' and not self.context.cmx_config.display_show_sim:
            return
        ts = self.context.cmx_signal.ts
        if self._last_update_ts is None or ts - self._last_update_ts >= self.refresh_tdelta:
            signal    = self.context.cmx_signal.signal
            fairs     = self.context.cmx_signal.mean
            std       = self.context.cmx_signal.std
            zscore    = self.context.cmx_signal.zscore
            net       = self.context.cmx_risk.net
            base_pos  = self.context.cmx_risk.leg_positions[0]
            quote_pos = self.context.cmx_risk.leg_quote_positions[0]
            traded    = self.context.cmx_risk.leg_traded_amounts[0]

            signal_str    = '{:.2E}'.format(Decimal(signal))
            fairs_str     = '{:.2E}'.format(Decimal(fairs))
            std_str       = '{:.2E}'.format(Decimal(std))
            zscore_str    = '{:.2E}'.format(Decimal(zscore))
            net_str       = '{:.2E}'.format(Decimal(net))
            base_pos_str  = '{:.2E}'.format(Decimal(base_pos))
            quote_pos_str = '{:.2E}'.format(Decimal(quote_pos))
            traded_str    = '{:.2E}'.format(Decimal(traded))
            
            status    = 'normal'
            if self.context.cmx_risk.trading_status == 'hedge_only':
                status = 'hedge'
            elif self.context.cmx_risk.trading_status == 'exit_nonew':
                status = 'nonew'
            elif self.context.cmx_risk.trading_status == 'exit_passive':
                status = 'exit_psv'
            elif self.context.cmx_risk.trading_status == 'exit_active':
                status = 'exit_act'

            print('\033[1;37;40m{} | {} | {}:{} | {}:{} | {} | {}'.format(
                                                                    self.context.cmx_config.global_context, 
                                                                    self.context.cmx_config.global_mode,
                                                                    self.context.cmx_config.global_exchanges[0],
                                                                    self.context.cmx_config.global_symbols[0],
                                                                    self.context.cmx_config.global_exchanges[1],
                                                                    self.context.cmx_config.global_symbols[1],
                                                                    self.context.cmx_config.risk_max_notional,
                                                                    ts.replace(tzinfo = None)
                                                                    ))
            window_width = 78
            print('-' * window_width)

            print('\033[1;37;40m|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'
                    .format('price','fair','zscore','status','net','qpos','traded'))
            default_str = '\033[1;37;40m|{:<10}|{:<10}|{:<10}'.format(signal_str, fairs_str, zscore_str)
            status_str = '|\033[1;32;40m{:<10}'.format(status) if status == 'normal' else '|\033[1;31;40m{:<10}'.format(status)
            
            if net > 0:
                net_str = '\033[1;37;40m|\033[1;30;102m{:<10}'.format(net_str)
            elif net < 0:
                net_str = '\033[1;37;40m|\033[1;37;41m{:<10}'.format(net_str)
            else:
                net_str = '\033[1;37;40m|{:<10}'.format(net_str)

            if quote_pos > 0:
                pos_str = '\033[1;37;40m|\033[1;36;40m{:<10}'.format(quote_pos_str)
            elif quote_pos < 0:
                pos_str = '\033[1;37;40m|\033[1;35;40m{:<10}'.format(quote_pos_str)
            else:
                pos_str = '\033[1;37;40m|{:<10}'.format(quote_pos_str)
            trd_str = '\033[1;37;40m|{:<10}'.format(traded_str)

            print(default_str + status_str + net_str + pos_str + trd_str + '|')
            
            price_anchor  = '{:.2E}'.format(Decimal(self.context.cmx_signal.prices[0]))
            net_anchor    = '{:.2E}'.format(Decimal(self.context.cmx_risk.leg_nets[0]))
            pos_anchor    = '{:.2E}'.format(Decimal(self.context.cmx_risk.leg_quote_positions[0]))
            traded_anchor = '{:.2E}'.format(Decimal(self.context.cmx_risk.leg_traded_amounts[0]))
            anchor_str    = '\033[1;37;40m|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format(price_anchor,'', '', '',net_anchor,pos_anchor,traded_anchor)
            print(anchor_str)
   
            price_hedge   = '{:.2E}'.format(Decimal(self.context.cmx_signal.prices[1]))
            net_hedge     = '{:.2E}'.format(Decimal(self.context.cmx_risk.leg_nets[1]))
            pos_hedge     = '{:.2E}'.format(Decimal(self.context.cmx_risk.leg_quote_positions[1]))
            traded_hedge  = '{:.2E}'.format(Decimal(self.context.cmx_risk.leg_traded_amounts[1]))
            hedge_str     = '\033[1;37;40m|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format(price_hedge,'', '', '',net_hedge,pos_hedge,traded_hedge)
            print(hedge_str)

            print('-' * window_width)
            self._last_update_ts = ts

    def run_daily(self):
        ts   = self.context.cmx_signal.ts
        if ts is None:
            return

        net  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_net))
        dd   = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_min_net))
        pos  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_position))
        minp = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_min_position))
        maxp = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_max_position))
        trd  = '{:.2E}'.format(Decimal(self.context.cmx_risk.daily_end_leg_trade_amounts[0]))
        
        print('{} | {} | {} | {}:{} | {}:{} | {} | {}'.format(
                                    self.context.cmx_config.global_context, 
                                    self.context.cmx_config.global_instance, 
                                    self.context.cmx_config.global_mode,
                                    self.context.cmx_config.global_exchanges[0],
                                    self.context.cmx_config.global_symbols[0],
                                    self.context.cmx_config.global_exchanges[1],
                                    self.context.cmx_config.global_symbols[1],
                                    self.context.cmx_config.risk_max_notional,
                                    ts.replace(tzinfo = None)
                                                 ))
        print('-' * 67)
        print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format('net','dd','pos','min_pos','max_pos','trd'))
        print('|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|{:<10}|'.format(net,dd,pos,minp,maxp,trd))
        print('-' * 67)
        