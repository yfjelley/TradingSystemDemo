import os
import datetime as dt
import numpy as np
import pandas as pd
# import matplotlib
# matplotlib.use('agg')
import matplotlib.pyplot as plt
import plot_live_outright as plo
import get_live_outright_summary as glos
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
import sys
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_crypto_compare'))
import hist_data
from trade_converter import single_product_trade_converter as sptc


# outright_instance_eod functions:
# 1. mark_trade_by_snapshot
# 2. mark_trade_by_cc
# 3. compare_snapshot_trade
# 4. summarize

class outright_instance_eod:
    # for backtest / paper / live instance
    def __init__(self, context, instance, exchange, symbol, eod, log_folder, t0 = None, tn = None, init_pos = None, init_cost_basis = None):
        self.context = context
        self.instance = instance
        self.exchange = exchange
        self.symbol = symbol
        sym_info = self._format_symbol(symbol)
        self.base_coin = sym_info['base']
        self.quote_coin = sym_info['quote']
        self.eod = eod
        if t0 is not None and t0.date() == eod:
            self.t0 = t0
        else:
            self.t0 = dt.datetime.combine(self.eod, dt.time(0,0))
        if tn is not None and tn.date() == eod:
            self.tn = tn
        else:
            self.tn = dt.datetime.combine(self.eod, dt.time(23,59,59))
        self.init_pos = init_pos
        self.init_cost_basis = init_cost_basis
        self.log_folder = log_folder
        self.trade_folder = os.path.join(log_folder, 'trade')
        self.snapshot_folder = os.path.join(log_folder, 'snapshot')
        self.trade_file = self._get_file(self.trade_folder, [context, instance, '{}.trade.csv'.format(eod)])
        self.snapshot_file = self._get_file(self.snapshot_folder, [context, instance, '{}.snapshot.csv'.format(eod)])
        self.trade_df = self._read_csv(self.trade_folder, self.trade_file)
        self.snapshot_df = self._read_csv(self.snapshot_folder, self.snapshot_file)
        self.snapshot_df = self._handle_snapshot_reboot()
        self.trade_by_snapshot_df = None
        self.trade_by_cc_df = None
        self.max_size = np.nan
        if self.snapshot_df is not None and 'max_pos' in self.snapshot_df.columns:
            self.max_size = self.snapshot_df['max_pos'][-1] 
        self.close_price = np.nan
        self.max_value = np.nan
        self.base_coin = None
        self.quote_coin = None

    def _format_symbol(self, symbol):
        if '/' in symbol:
            coin_list = symbol.split('/')
        elif '.' in symbol:
            coin_list = symbol.split('.')
        elif '_' in symbol:
            coin_list = symbol.split('_')
        elif '-' in symbol:
            coin_list = symbol.split('-')
        else:
            return {
                    'binance'  : symbol.upper(), 
                    'dot'      : symbol.lower(), 
                    'underline': symbol.lower(), 
                    'base'     : symbol, 
                    'quote'    : symbol
                    }
        binance_symbol = '{}{}'.format(coin_list[0].upper(), coin_list[1].upper())
        dot_symbol     = '{}.{}'.format(coin_list[0].lower(), coin_list[1].lower())
        under_symbol   = '{}_{}'.format(coin_list[0].lower(), coin_list[1].lower())
        return {
                'binance'  : binance_symbol, 
                'dot'      : dot_symbol, 
                'underline': under_symbol,
                'base'     : coin_list[0].lower(), 
                'quote'    : coin_list[1].lower()
                }

    def _read_csv(self, folder, file):
        if folder is None or file is None:
            return None
        pathfile = os.path.join(folder, file)
        if not os.path.exists(pathfile):
            return None
        df = pd.read_csv(pathfile, header = 0, index_col = 0, parse_dates = True)
        df = df[(df.index >= self.t0) & (df.index <= self.tn)]
        return df

    def _get_file(self, folder, keywords):
        tarf = None
        for f in os.listdir(folder):
            found = True
            for kw in keywords:
                if str(kw) not in f:
                    found = False
                    break
            if found:
                tarf = f
                break
        return tarf

    def _get_init_stats(self):
        #try:
        #   t0 = self.trade_df.dropna().index[0]
        #except:
        t0 = self.t0
        if self.snapshot_df is None:
            return None
        tmp_snap_df = self.snapshot_df[self.snapshot_df.index <= t0][['position', 'cost_basis']].dropna()
        if len(tmp_snap_df) == 0:
            # this is a day that algo starts late:
            pos = self.snapshot_df['position'][0]
            cost_basis = self.snapshot_df['cost_basis'][0]
        else:            
            pos = self.init_pos if self.init_pos else tmp_snap_df['position'][-1]
            cost_basis = self.init_cost_basis if self.init_cost_basis else tmp_snap_df['cost_basis'][-1]
        return{'position': pos, 'cost_basis': cost_basis}

    def _handle_snapshot_reboot(self):
        if self.snapshot_df is None or len(self.snapshot_df) == 0:
            return self.snapshot_df
        reboot_df = self.snapshot_df[
                                     (self.snapshot_df['position'] == 0) & 
                                     (self.snapshot_df['pnl'] == 0) & 
                                     (self.snapshot_df['cost_basis'] == 0)
                                     ]
        if len(reboot_df) == 0:
            return self.snapshot_df

        # init_pnl = self.snapshot_df['pnl'][0]
        # init_cost_basis = self.snapshot_df['cost_basis'][0]
        reboot_ts_list = [reboot_df.index[0]]
        for i in range(1, len(reboot_df)):
            cur_ts = reboot_df.index[i]
            pre_ts = reboot_df.index[i-1]
            if cur_ts - pre_ts > dt.timedelta(minutes = 1):
                reboot_ts_list.append(cur_ts)

        for ts in reboot_ts_list:
            row_index = self.snapshot_df.index.get_loc(ts)
            init_pnl = self.snapshot_df['pnl'][row_index - 1]
            self.snapshot_df.iloc[row_index:][['pnl']] += init_pnl
        return self.snapshot_df

    def mark_trade_by_snapshot(self):
        if self.snapshot_df is None:
            return None
        init_stats = self._get_init_stats()
        if init_stats is None:
            return None

        trd_converter = sptc(
                             self.exchange,
                             self.symbol,
                             init_stats['position'], 
                             init_stats['cost_basis'], 
                             self.trade_df
                            )
        self.trade_by_snapshot_df = trd_converter.convert_by_minute(self.t0, self.tn, self.snapshot_df[['signal']])
        self.base_coin = trd_converter.base_coin
        self.quote_coin = trd_converter.quote_coin
        if self.trade_by_snapshot_df is not None:
            self.close_price = self.trade_by_snapshot_df['mkt_price'][-1]
            self.max_value = self.max_size * self.close_price
        return self.trade_by_snapshot_df

    def mark_trade_by_cc(self):
        init_stats = self._get_init_stats()
        if init_stats is None:
            return None
        trd_converter = sptc(
                             self.exchange,
                             self.symbol,
                             init_stats['position'], 
                             init_stats['cost_basis'], 
                             self.trade_df
                            )
        self.trade_by_cc_df = trd_converter.convert_by_minute(self.t0, self.tn)
        self.base_coin = trd_converter.base_coin
        self.quote_coin = trd_converter.quote_coin
        if self.trade_by_cc_df is not None:
            self.close_price = self.trade_by_cc_df['mkt_price'][-1]
            self.max_value = self.max_size * self.close_price
        return self.trade_by_cc_df
    
    def validate_trade_snapshot(self, fig_saveto = None):
        converted_trade_df = self.mark_trade_by_snapshot()
        if converted_trade_df is None:
            return None
        trade_net_ser = converted_trade_df['pnl'] - converted_trade_df['fee']
        trade_pos = converted_trade_df['position'][-1]

        if fig_saveto:
            plt.figure(figsize = (8,6))
            plt.subplot(2,2,1)
            plt.plot(converted_trade_df.index, converted_trade_df['position'])

            plt.subplot(2,2,2)
            plt.plot(self.snapshot_df.index, self.snapshot_df['position'])

            plt.subplot(2,2,3)
            plt.plot(converted_trade_df.index, trade_net_ser)

            plt.subplot(2,2,4)
            plt.plot(self.snapshot_df.index, self.snapshot_df['pnl'])

            plt.grid()
            plt.tight_layout()
            plt.savefig(fig_saveto, dpi = 300)
            plt.close
        return {
                'trade_net': trade_net_ser[-1] - trade_net_ser[0], 
                'snapshot_net': self.snapshot_df['pnl'][-1] - self.snapshot_df['pnl'][0],
                'trade_pos': trade_pos,
                'snapshot_pos': self.snapshot_df['position'][-1]
                }

# context = 'changeling'
# exchange = 'binance'
# symbol = 'dash_eth'
# eod = dt.date(2018,11,8)
# # dn = dt.date(2018,11,4)
# log_folder = '/Users/fw/Trading/projects/xman/comics_data/{}'.format(context)
# oie = outright_instance_eod(context, exchange, symbol, eod, log_folder)
# # print(oie.snapshot_df)
# # oie.snapshot_df.to_csv('tmp.csv')
# # trade_snap_df = oie.mark_trade_by_snapshot()
# trade_snap_df = oie.mark_trade_by_cc()
# trade_snap_df.to_csv('tmp2.csv')

class outright_exchange_eod:
    def __init__(self, context, exchange, symbol, eod, log_folder, t0 = None, tn = None, init_pos = None, init_cost_basis = None):
        self.context = context
        self.exchange = exchange
        self.symbol = symbol
        self.eod = eod
        self.log_folder = log_folder
        self.exchange_file = '{}_trade_history.csv'.format(exchange)
        self.exchange_df = self._read_csv(log_folder, self.exchange_file)
        if t0 is not None and t0.date() == eod:
            self.t0 = t0
        else:
            self.t0 = dt.datetime.combine(self.eod, dt.time(0,0))
        if tn is not None and tn.date() == eod:
            self.tn = tn
        else:
            self.tn = dt.datetime.combine(self.eod, dt.time(23,59,59))
        self.init_pos = init_pos
        self.init_cost_basis = init_cost_basis
        self.trade_by_price_df = None
        self.trade_df = self.exchange_df[(self.exchange_df.index >= self.t0) & (self.exchange_df.index <= self.tn)]
        self.close_price = np.nan
        self.base_coin = None
        self.quote_coin = None

    def _read_csv(self, folder, file):
        if folder is None or file is None:
            return None
        if not os.path.exists(os.path.join(folder, file)):
            return None
        df = pd.read_csv(os.path.join(folder, file), header = 0, index_col = 0, parse_dates = True)
        df = df[df['ticker'] == self.symbol]
        return df

    def get_init_stats(self, ignore_pct = 0.01):
        if self.exchange_df is None:
            init_pos = self.init_pos
            init_cost_basis = self.init_cost_basis
            return {'position': self.init_pos, 'cost_basis': self.init_cost_basis}

        if self.init_pos and self.init_cost_basis:
            return {'position': self.init_pos, 'cost_basis': self.init_cost_basis}

        pre_df = self.exchange_df[self.exchange_df.index < self.t0]
        init_pos = self.init_pos if self.init_pos else pre_df['amount'].sum()
        if init_pos == 0:
            init_cost_basis = np.nan
        else:
            if self.init_cost_basis:
                init_cost_basis = self.init_cost_basis
            else:
                ignore_pos = init_pos * ignore_pct
                agg_pos = init_pos
                i0 = 0
                for i in range(len(pre_df))[::-1]:
                    agg_pos -= pre_df['amount'][i]
                    if init_pos > 0 and agg_pos <= ignore_pos:
                        i0 = i
                        break
                    elif init_pos < 0 and agg_pos >= -ignore_pos:
                        i0 = i
                        break
                init_cost_basis = pre_df['price'][i0]
                for i in range(i0, len(pre_df)):
                    amount = pre_df['amount'][i]
                    price = pre_df['price'][i]
                    if amount * agg_pos > 0:
                        init_cost_basis = (init_cost_basis * agg_pos + amount * price) / (agg_pos + amount)
                    elif abs(amount) > abs(agg_pos):
                        init_cost_basis = price
                    agg_pos += amount
                    
                # if agg_pos != init_pos:
                #   print('ERROR: agg_pos != init_pos')
        return {'position': init_pos, 'cost_basis': init_cost_basis}

    def get_init_stats_v2(self):
        # This is for validation purpose only
        df = sptc(self.exchange, self.symbol, 0, 0, self.exchange_df).convert_by_hour(dt.datetime(2018,7,21), self.t0 - dt.timedelta(seconds = 1e-3))
        return {'position': df['position'][-1], 'cost_basis': df['cost_basis'][-1]}

    def mark_trade(self, price_df = None):
        if self.exchange_df is None:
            return None
        init_stats = self.get_init_stats()
        if init_stats is None:
            return None

        trd_converter = sptc(
                             self.exchange,
                             self.symbol,
                             init_stats['position'],
                             init_stats['cost_basis'],
                             self.exchange_df
                            )
        self.trade_by_price_df = trd_converter.convert_by_minute(self.t0, self.tn)
        self.base_coin = trd_converter.base_coin
        self.quote_coin = trd_converter.quote_coin
        if self.trade_by_price_df is not None:
            self.close_price = self.trade_by_price_df['mkt_price'][-1]
        return self.trade_by_price_df

# context = 'changeling'
# symbol = 'dash_eth'
# exchange = 'binance'
# eod = dt.date(2018,11,8)
# log_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/exchanges/{}'.format(exchange)
# oee = outright_exchange_eod(context,exchange,symbol,eod,log_folder)
# # print(oee.get_init_stats())
# # print(oee.get_init_stats_v2())
# df = oee.mark_trade()
# df.to_csv('tmp.csv')
# print(df)

class outright_eod:
    # combine live / sim / exchange
    def __init__(self, context, instance, exchange, symbol, eod, algo_log_folder, exch_log_folder, t0 = None, tn = None, init_pos = None, init_cost_basis = None):
        self.context = context
        self.instance = instance
        self.exchange = exchange
        self.symbol = symbol
        self.eod = eod
        self.algo_log_folder = algo_log_folder
        self.exch_log_folder = exch_log_folder
        self.live_eod = outright_instance_eod(
                                                context,
                                                instance,
                                                exchange,
                                                symbol,
                                                eod,
                                                os.path.join(algo_log_folder, context),
                                                t0 = t0,
                                                tn = tn,
                                                init_pos = init_pos,
                                                init_cost_basis = init_cost_basis
                                              )
        self.sim_eod = outright_instance_eod(
                                             context,
                                             instance,
                                             exchange,
                                             symbol,
                                             eod,
                                             os.path.join(algo_log_folder, '{}-sim'.format(context)),
                                             t0 = t0,
                                             tn = tn,
                                             init_pos = init_pos,
                                             init_cost_basis = init_cost_basis
                                            )
        self.exch_eod = outright_exchange_eod(
                                              context,
                                              exchange,
                                              symbol,
                                              eod,
                                              exch_log_folder,
                                              t0 = t0,
                                              tn = tn,
                                              init_pos = init_pos,
                                              init_cost_basis = init_cost_basis
                                             )
        self.live_df = None
        self.sim_df  = None
        self.exch_df = None
        self.agg_df = None
        self.live_summary = None
        self.sim_summary = None
        self.exch_summary = None
        self.agg_summary = None

    def mark_trade_by_cc(self):
        self.live_df = self.live_eod.mark_trade_by_cc()
        self.sim_df  = self.sim_eod.mark_trade_by_cc()
        self.exch_df = self.exch_eod.mark_trade()

    def mark_trade_by_snapshot(self):
        self.live_df = self.live_eod.mark_trade_by_snapshot()
        self.sim_df  = self.sim_eod.mark_trade_by_snapshot()
        self.exch_df = self.exch_eod.mark_trade(self.sim_df['mkt_price'])

    def aggregate_df(self, saveto = None):
        self.agg_df = pd.DataFrame()
        if self.live_df is not None:
            tmp_df = self.live_df[['mkt_price', 'pnl', 'position', 'fee', 'realized', 'unrealized']].copy()
            tmp_df.columns = ['live_{}'.format(x) for x in tmp_df.columns]
            self.agg_df = pd.concat([self.agg_df, tmp_df], axis = 1)
        if self.sim_df is not None:
            tmp_df = self.sim_df[['mkt_price', 'pnl', 'position', 'fee', 'realized', 'unrealized']].copy()
            tmp_df.columns = ['sim_{}'.format(x) for x in tmp_df.columns]
            self.agg_df = pd.concat([self.agg_df, tmp_df], axis = 1)
        if self.exch_df is not None:
            tmp_df = self.exch_df[['mkt_price', 'pnl', 'position', 'fee', 'realized', 'unrealized']].copy()
            tmp_df.columns = ['exch_{}'.format(x) for x in tmp_df.columns]
            self.agg_df = pd.concat([self.agg_df, tmp_df], axis = 1)
        self.agg_df.fillna(method = 'ffill', inplace = True)
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            self.agg_df.to_csv(saveto)
        return self.agg_df

    def _save_df(self, df, saveto):
        if not saveto:
            return
        if df is None:
            return

        folder = os.path.dirname(saveto)
        if not os.path.exists(folder):
            os.makedirs(folder)
        df.to_csv(saveto)

    def save_live_df(self, saveto):
        self._save_df(self.live_df, saveto)

    def save_sim_df(self, saveto):
        self._save_df(self.sim_df, saveto)

    def save_exch_df(self, saveto):
        self._save_df(self.exch_df, saveto)

    def save_agg_df(self, saveto):
        self._save_df(self.agg_df, saveto)

    def _get_summary(self, time_df, trade_df):
        features = ['position', 'net', 'fee', 'traded', 'realized', 'unrealized']
        # realized is net fee, unrealized is gross.

        if time_df is None:
            return pd.Series([None] * len(features), index = features)
        
        pos = time_df['position'][-1]
        pos = 0 if np.isnan(pos) else pos
        fee = time_df['fee'][-1]
        fee = 0 if np.isnan(fee) else fee
        net = time_df['pnl'][-1] - time_df['pnl'][0] - fee
        net = 0 if np.isnan(net) else net
        traded = trade_df['amount'].abs().sum() if trade_df is not None else 0
        realized = time_df['realized'][-1] - fee
        realized = 0 if np.isnan(realized) else realized
        unrealized = time_df['unrealized'][-1] - time_df['unrealized'][0]
        unrealized = 0 if np.isnan(unrealized) else unrealized
        return pd.Series([pos, net, fee, traded, realized, unrealized], index = features)

    def get_summary(self):
        self.live_summary = self._get_summary(self.live_df, self.live_eod.trade_df)
        self.live_summary.index = ['live_{}'.format(x) for x in self.live_summary.index]
        self.live_summary.name = self.eod
        self.sim_summary = self._get_summary(self.sim_df, self.sim_eod.trade_df)
        self.sim_summary.index = ['sim_{}'.format(x) for x in self.sim_summary.index]
        self.sim_summary.name = self.eod
        self.exch_summary = self._get_summary(self.exch_df, self.exch_eod.trade_df)
        self.exch_summary.index = ['exch_{}'.format(x) for x in self.exch_summary.index]
        self.exch_summary.name = self.eod
        self.agg_summary = pd.concat([self.live_summary, self.sim_summary, self.exch_summary])
        self.agg_summary['price']     = self.exch_eod.close_price
        self.agg_summary['max_size']  = self.live_eod.max_size
        self.agg_summary['max_value'] = self.agg_summary['price'] * self.agg_summary['max_size']
        self.agg_summary['coin'] = self.exch_eod.quote_coin
        self.agg_summary.name = self.eod

    def _save_summary(self, summary_to_add, saveto):
        if not saveto:
            return
        if os.path.exists(saveto):
            df = pd.read_csv(saveto, header = 0, index_col = 0, parse_dates = True)
            df.index = df.index.map(pd.Timestamp.date)
            df.loc[self.eod] = summary_to_add
            df.sort_index(ascending = True, inplace = True)
        else:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            df = pd.DataFrame([summary_to_add], index = [self.eod])
        df.to_csv(saveto)
        return df

    def save_live_summary(self, saveto):
        self._save_summary(self.live_summary, saveto)
        return self.live_summary

    def save_sim_summary(self, saveto):
        self._save_summary(self.sim_summary, saveto)
        return self.sim_summary

    def save_exch_summary(self, saveto):
        self._save_summary(self.exch_summary, saveto)
        return self.exch_summary

    def save_agg_summary(self, saveto):
        self._save_summary(self.agg_summary, saveto)
        return self.agg_summary
            
    def update(self):
        self.mark_trade_by_cc()
        self.aggregate_df()
        self.get_summary()

    def update_by_snapshot(self):
        self.mark_trade_by_snapshot()
        self.aggregate_df()
        self.get_summary()
    
    def plot(self, saveto = None):
        min_net = max_net = 0
        min_pos = max_pos = 0
        
        plot_live = self.live_df is not None and len(self.live_df[['pnl', 'fee']].dropna()) > 0
        if plot_live:
            new_min_pos = self.live_df['position'].dropna().min()
            new_max_pos = self.live_df['position'].dropna().max()
            live_df = self.live_df[['pnl', 'fee']].dropna()
            new_min_net = np.min(live_df['pnl'] - live_df['fee'] - live_df['pnl'][0])
            new_max_net = np.max(live_df['pnl'] - live_df['fee'] - live_df['pnl'][0])
            if min_pos > new_min_pos:
                min_pos = new_min_pos
            if max_pos < new_max_pos:
                max_pos = new_max_pos
            if min_net > new_min_net:
                min_net = new_min_net
            if max_net < new_max_net:
                max_net = new_max_net

        plot_sim = self.sim_df is not None and len(self.sim_df[['pnl', 'fee']].dropna()) > 0
        if plot_sim:
            new_min_pos = self.sim_df['position'].dropna().min()
            new_max_pos = self.sim_df['position'].dropna().max()
            sim_df = self.sim_df[['pnl', 'fee']].dropna()
            new_min_net = np.min(sim_df['pnl'] - sim_df['fee'] - sim_df['pnl'][0])
            new_max_net = np.max(sim_df['pnl'] - sim_df['fee'] - sim_df['pnl'][0])
            if min_pos > new_min_pos:
                min_pos = new_min_pos
            if max_pos < new_max_pos:
                max_pos = new_max_pos
            if min_net > new_min_net:
                min_net = new_min_net
            if max_net < new_max_net:
                max_net = new_max_net

        plot_exch = self.exch_df is not None and len(self.exch_df[['pnl', 'fee']].dropna()) > 0 
        if plot_exch:
            new_min_pos = self.exch_df['position'].dropna().min()
            new_max_pos = self.exch_df['position'].dropna().max()
            exch_df = self.exch_df[['pnl', 'fee']].dropna()
            new_min_net = np.min(exch_df['pnl'] - exch_df['fee'] - exch_df['pnl'][0])
            new_max_net = np.max(exch_df['pnl'] - exch_df['fee'] - exch_df['pnl'][0])
            if min_pos > new_min_pos:
                min_pos = new_min_pos
            if max_pos < new_max_pos:
                max_pos = new_max_pos
            if min_net > new_min_net:
                min_net = new_min_net
            if max_net < new_max_net:
                max_net = new_max_net

        plt.figure(figsize = (9,9))
        if plot_live:
            plt.subplot(3,3,1)
            plt.title('{}_live'.format(self.context))
            plt.plot(self.live_df.index, self.live_df['mkt_price'])
            plt.ylabel('mkt_price')
            plt.xticks(rotation = 45)
            plt.grid()

            plt.subplot(3,3,4)
            plt.plot(self.live_df.index, self.live_df['position'])
            plt.ylabel('position')
            plt.ylim([min_pos, max_pos])
            plt.xticks(rotation = 45)
            plt.grid()
            
            plt.subplot(3,3,7)
            # plt.plot(self.live_df.index, self.live_df['pnl'] - self.live_df['fee'])
            plt.plot(live_df.index, live_df['pnl'] - live_df['fee'] - live_df['pnl'][0])
            plt.ylabel('net')
            plt.ylim([min_net, max_net])
            plt.xticks(rotation = 45)
            plt.grid()
        
        if plot_sim:
            plt.subplot(3,3,2)
            plt.title('{}_sim'.format(self.context))
            plt.plot(self.sim_df.index, self.sim_df['mkt_price'])
            plt.ylabel('mkt_price')
            plt.xticks(rotation = 45)
            plt.grid()

            plt.subplot(3,3,5)
            plt.plot(self.sim_df.index, self.sim_df['position'])
            plt.ylabel('position')
            plt.ylim([min_pos, max_pos])
            plt.xticks(rotation = 45)
            plt.grid()

            plt.subplot(3,3,8)
            # plt.plot(self.sim_df.index, self.sim_df['pnl'] - self.sim_df['fee'])
            plt.plot(sim_df.index, sim_df['pnl'] - sim_df['fee'] - sim_df['pnl'][0])
            plt.ylabel('net')
            plt.ylim([min_net, max_net])
            plt.xticks(rotation = 45)
            plt.grid()

        if plot_exch:
            plt.subplot(3,3,3)
            plt.title('{}_exch'.format(self.context))
            plt.plot(self.exch_df.index, self.exch_df['mkt_price'])
            plt.ylabel('mkt_price')
            plt.xticks(rotation = 45)
            plt.grid()

            plt.subplot(3,3,6)
            plt.plot(self.exch_df.index, self.exch_df['position'])
            plt.ylim([min_pos, max_pos])
            plt.ylabel('position')
            plt.xticks(rotation = 45)
            plt.grid()

            plt.subplot(3,3,9)
            # plt.plot(self.exch_df.index, self.exch_df['pnl'] - self.exch_df['fee'])
            plt.plot(exch_df.index, exch_df['pnl'] - exch_df['fee'] - exch_df['pnl'][0])
            plt.ylabel('net')
            plt.ylim([min_net, max_net])
            plt.xticks(rotation = 45)
            plt.grid()

        plt.tight_layout()
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            plt.savefig(saveto, dpi = 300)
        plt.close()
        return
