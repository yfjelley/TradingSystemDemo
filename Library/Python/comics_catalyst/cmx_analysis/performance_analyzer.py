import pandas as pd
import datetime as dt
import os 
import numpy as np
import matplotlib.pyplot as plt
from eod import outright_instance_eod

def read_eod_csv(infile):
    if not infile:
        return None
    if not os.path.exists(infile):
        return None
    df = pd.read_csv(infile, header = 0, index_col = 0, parse_dates = True)
    df.index = df.index.map(pd.Timestamp.date)
    return df

class context_performance:
    def __init__(self, context, infile = None):
        self.context = context
        self.infile = infile
        if infile is None:
            self.infile = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/csv/{0}_agg_summary.csv'.format(context)
        self.df = read_eod_csv(self.infile)
        self.exch_pnl_df = None
        self.live_pnl_df = None
        self.sim_pnl_df  = None

    def _drop_column_prefix(self, columns):
        column_keywords = []
        for i in columns:
            if i in ['max_size', 'max_value']:
                column_keywords.append(i)
            else:
                kwstr = i.split('_')
                if len(kwstr) == 1:
                    column_keywords.append(kwstr[0])
                elif len(kwstr) != 2:
                    column_keywords.append('_'.join(kwstr[1:]))
                else:
                    column_keywords.append(kwstr[1])
        return column_keywords

    def _calculate_performance(self, df, d0 = None, dn = None):
        if df is None or len(df) == 0:
            return None
        new_columns = self._drop_column_prefix(df.columns)
        if len(set(new_columns)) != len(df.columns):
            return None
        df_copy = df.copy()
        df_copy.columns = new_columns
        if 'realized' not in df_copy.columns or \
           'unrealized' not in df_copy.columns or \
           'net' not in df_copy.columns:
           return None

        if d0 is not None:
            df_copy = df_copy[df_copy.index >= d0]
        if dn is not None:
            df_copy = df_copy[df_copy.index <= dn]

        # net = df_copy['net']
        notional = df_copy['max_value']
        notional.fillna(method = 'ffill', inplace = True)
                
        net = df_copy['net']
        fee = df_copy['fee']
        pnl = net + fee
        ror = net / df_copy['max_value']

        agg_net = net.cumsum()
        agg_fee = fee.cumsum()
        agg_pnl = pnl.cumsum()
        agg_ror = ror.cumsum()

        agg_df = pd.concat([net, fee, pnl, agg_net, agg_fee, agg_pnl, agg_ror, notional], axis = 1)
        agg_df.columns = ['net', 'fee', 'pnl', 'agg_net', 'agg_fee', 'agg_pnl', 'return', 'notional']
        
        daycount = len(net)
        sharpe = np.nan
        if np.std(net) != 0:
            sharpe = np.mean(net) / np.std(net)
        winrate = np.nan
        if daycount != 0:
            winrate = len(net[net >= 0]) / daycount
        total_net = agg_net[-1]
        total_fee = agg_fee[-1]
        total_gross = total_net + total_fee
        total_return = agg_ror[-1]
        return {
                'day': daycount,
                'pnl': total_gross,
                'net': total_net,
                'fee': total_fee,
                'winrate': winrate,
                'sharpe': sharpe,
                'notional': notional[-1],
                'return': total_return,
                'df': agg_df
                }

    def calculate_exchange_performance(self, d0 = None, dn = None):
        if self.df is None:
            return None 

        exch_columns = [x for x in self.df.columns if 'live' not in x and 'sim' not in x]
        if len(exch_columns) == 0:
            return None
        perf = self._calculate_performance(self.df[exch_columns], d0, dn)
        return perf

    def calculate_live_performance(self, d0 = None, dn = None):
        live_columns = [x for x in self.df if 'exch' not in x and 'sim' not in x]
        if len(live_columns) == 0:
            return None
        perf = self._calculate_performance(self.df[live_columns], d0, dn)
        return perf

    def calculate_sim_performance(self, d0 = None, dn = None):
        sim_columns = [x for x in self.df if 'live' not in x and 'exch' not in x]
        if len(sim_columns) == 0:
            return None
        perf = self._calculate_performance(self.df[sim_columns], d0, dn)
        return perf

# cp = context_performance('changeling')
# # print(cp.df)
# perf = cp.calculate_exchange_performance(dt.date(2018,8,2), dt.date(2018,11,1))
# print(perf)
# # perf['df'].plot()
# # plt.show()

class portfolio_performance:
    def __init__(self, contexts, logfolder = None):
        self.logfolder = logfolder
        if logfolder is None:
            self.logfolder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod'
        self.contexts = contexts
        self.ctx_perfs = []
        for c in contexts:
            infile = os.path.join(self.logfolder, '{0}/csv/{0}_agg_summary.csv'.format(c))
            self.ctx_perfs.append(context_performance(c, infile))
        self.live_perf_df = pd.DataFrame(columns = ['day', 'pnl', 'net', 'fee', 'winrate', 'sharpe', 'notional', 'return'], index = contexts)
        self.sim_perf_df  = pd.DataFrame(columns = ['day', 'pnl', 'net', 'fee', 'winrate', 'sharpe', 'notional', 'return'], index = contexts)
        self.exch_perf_df = pd.DataFrame(columns = ['day', 'pnl', 'net', 'fee', 'winrate', 'sharpe', 'notional', 'return'], index = contexts)
        self.live_net_df = pd.DataFrame()
        self.live_pnl_df = pd.DataFrame()
        self.live_fee_df = pd.DataFrame()
        self.live_agg_net_df = pd.DataFrame()
        self.live_agg_fee_df = pd.DataFrame()
        self.live_agg_pnl_df = pd.DataFrame()
        self.live_agg_return = pd.DataFrame()
        self.sim_pnl_df  = pd.DataFrame()
        self.sim_net_df  = pd.DataFrame()
        self.sim_fee_df  = pd.DataFrame()
        self.sim_agg_net_df = pd.DataFrame()
        self.sim_agg_fee_df = pd.DataFrame()
        self.sim_agg_pnl_df = pd.DataFrame()
        self.sim_agg_return = pd.DataFrame()
        self.exch_pnl_df = pd.DataFrame()
        self.exch_net_df = pd.DataFrame()
        self.exch_fee_df = pd.DataFrame()
        self.exch_agg_net_df = pd.DataFrame()
        self.exch_agg_fee_df = pd.DataFrame()
        self.exch_agg_pnl_df = pd.DataFrame()
        self.exch_agg_return = pd.DataFrame()

    def _aggregate_performance(self, context_df_dict):
        pnl_df = pd.DataFrame()
        net_df = pd.DataFrame()
        fee_df = pd.DataFrame()
        agg_pnl_df = pd.DataFrame()
        agg_net_df = pd.DataFrame()
        agg_fee_df = pd.DataFrame()
        agg_return = pd.DataFrame()
        agg_notional = pd.DataFrame()
        contexts = []
        for context, df in context_df_dict.items():
            contexts.append(context)
            pnl_df = pd.concat([pnl_df, df['pnl']], axis = 1)
            net_df = pd.concat([net_df, df['net']], axis = 1)
            fee_df = pd.concat([fee_df, df['fee']], axis = 1)
            agg_pnl_df = pd.concat([agg_pnl_df, df['agg_pnl']], axis = 1)
            agg_net_df = pd.concat([agg_net_df, df['agg_net']], axis = 1)
            agg_fee_df = pd.concat([agg_fee_df, df['agg_fee']], axis = 1)
            agg_return = pd.concat([agg_return, df['return']], axis = 1)
            agg_notional = pd.concat([agg_notional, df['notional']], axis = 1)
        pnl_df.columns = contexts
        net_df.columns = contexts
        fee_df.columns = contexts
        agg_pnl_df.columns = contexts
        agg_net_df.columns = contexts
        agg_fee_df.columns = contexts
        agg_return.columns = contexts
        agg_notional.columns = contexts
        pnl_df['portfolio'] = pnl_df.sum(axis = 1)
        net_df['portfolio'] = net_df.sum(axis = 1)
        fee_df['portfolio'] = fee_df.sum(axis = 1)
        agg_pnl_df['portfolio'] = agg_pnl_df.sum(axis = 1)
        agg_net_df['portfolio'] = agg_net_df.sum(axis = 1)
        agg_fee_df['portfolio'] = agg_fee_df.sum(axis = 1)
        agg_notional['portfolio'] = agg_notional.sum(axis = 1)
        # agg_return['portfolio'] = agg_return.sum(axis = 1)
        agg_return['portfolio'] = agg_net_df['portfolio'] / agg_notional['portfolio']
        pnl_df.fillna(0, inplace = True)
        net_df.fillna(0, inplace = True)
        fee_df.fillna(0, inplace = True)
        agg_pnl_df.fillna(method = 'ffill', inplace = True)
        agg_net_df.fillna(method = 'ffill', inplace = True)
        agg_fee_df.fillna(method = 'ffill', inplace = True)
        agg_return.fillna(method = 'ffill', inplace = True)

        day = len(net_df)
        pnl = agg_pnl_df['portfolio'][-1]
        net = agg_net_df['portfolio'][-1]
        fee = agg_fee_df['portfolio'][-1]
        winrate = len(net_df[net_df['portfolio'] >= 0]) / day if day > 0 else np.nan
        net_std = np.std(net_df['portfolio'])
        sharpe = np.mean(net_df['portfolio']) / net_std if net_std > 0 else np.nan
        ror = agg_return['portfolio'][-1]
        port_perf = {
                     'day': day,
                     'pnl': pnl,
                     'net': net,
                     'fee': fee,
                     'winrate': winrate,
                     'sharpe': sharpe,
                     'notional': agg_notional['portfolio'][-1],
                     'return': ror
                    }

        return{
               'pnl_df': pnl_df,
               'net_df': net_df,
               'fee_df': fee_df,
               'agg_pnl_df': agg_pnl_df,
               'agg_net_df': agg_net_df,
               'agg_fee_df': agg_fee_df,
               'agg_notional': agg_notional,
               'agg_return': agg_return,
               'portfolio_perf': port_perf
              }

    def calculate_live_performance(self, d0 = None, dn = None):
        context_df_dict = {}
        for cp in self.ctx_perfs:
            perf = cp.calculate_live_performance(d0, dn)
            df = perf.pop('df')
            self.live_perf_df.loc[cp.context] = perf
            context_df_dict[cp.context] = df

        agg_perf = self._aggregate_performance(context_df_dict)
        self.live_pnl_df = agg_perf['pnl_df']
        self.live_net_df = agg_perf['net_df']
        self.live_fee_df = agg_perf['fee_df']
        self.live_agg_pnl_df = agg_perf['agg_pnl_df']
        self.live_agg_net_df = agg_perf['agg_net_df']
        self.live_agg_fee_df = agg_perf['agg_fee_df']
        self.live_agg_return = agg_perf['agg_return']
        self.live_perf_df.loc['portfolio'] = agg_perf['portfolio_perf']

    def calculate_sim_performance(self, d0 = None, dn = None):
        context_df_dict = {}
        for cp in self.ctx_perfs:
            perf = cp.calculate_sim_performance(d0, dn)
            df = perf.pop('df')
            self.sim_perf_df.loc[cp.context] = perf
            context_df_dict[cp.context] = df

        agg_perf = self._aggregate_performance(context_df_dict)
        self.sim_pnl_df = agg_perf['pnl_df']
        self.sim_net_df = agg_perf['net_df']
        self.sim_fee_df = agg_perf['fee_df']
        self.sim_agg_pnl_df = agg_perf['agg_pnl_df']
        self.sim_agg_net_df = agg_perf['agg_net_df']
        self.sim_agg_fee_df = agg_perf['agg_fee_df']
        self.sim_agg_return = agg_perf['agg_return']
        self.sim_perf_df.loc['portfolio'] = agg_perf['portfolio_perf']

    def calculate_exchange_performance(self, d0 = None, dn = None):
        context_df_dict = {}
        for cp in self.ctx_perfs:
            perf = cp.calculate_exchange_performance(d0, dn)
            df = perf.pop('df')
            self.exch_perf_df.loc[cp.context] = perf
            context_df_dict[cp.context] = df

        agg_perf = self._aggregate_performance(context_df_dict)
        self.exch_pnl_df = agg_perf['pnl_df']
        self.exch_net_df = agg_perf['net_df']
        self.exch_fee_df = agg_perf['fee_df']
        self.exch_agg_pnl_df = agg_perf['agg_pnl_df']
        self.exch_agg_net_df = agg_perf['agg_net_df']
        self.exch_agg_fee_df = agg_perf['agg_fee_df']
        self.exch_agg_return = agg_perf['agg_return']
        self.exch_perf_df.loc['portfolio'] = agg_perf['portfolio_perf']

    def calculate_performance(self, d0 = None, dn = None):
        self.calculate_live_performance(d0, dn)
        self.calculate_sim_performance(d0, dn)
        self.calculate_exchange_performance(d0, dn)
        return {'live': self.live_perf_df, 'sim': self.sim_perf_df, 'exch': self.exch_perf_df}

    def plot_live(self, saveto = None):
        contexts = self.contexts + ['portfolio']
        plt.figure(figsize = (6, len(contexts) * 2))
        ncol = 2
        # nrow = int(np.ceil(len(contexts) / 2))
        nrow = len(contexts)
        for i, c in enumerate(contexts):
            plt.subplot(nrow, ncol, 2 * i + 1)
            plt.title('{} live pnl'.format(c))
            plt.plot(self.live_agg_net_df.index, self.live_agg_net_df[c], 'g')
            plt.plot(self.live_agg_pnl_df.index, self.live_agg_pnl_df[c], 'b--')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()

            plt.subplot(nrow, ncol, 2 * i + 2)
            plt.title('{} live return'.format(c))
            plt.plot(self.live_agg_return.index, self.live_agg_return[c], 'g')
            plt.xticks(rotation = 45)
            plt.ylabel('return')
            plt.grid()
        
        plt.tight_layout()
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            plt.savefig(saveto, dpi = 300)
            plt.close()
        else:
            plt.show()

    def plot_sim(self, saveto = None):
        contexts = self.contexts + ['portfolio']
        plt.figure(figsize = (6,len(contexts) * 2))
        ncol = 2
        # nrow = int(np.ceil(len(contexts) / 2))
        nrow = len(contexts)
        for i, c in enumerate(contexts):
            plt.subplot(nrow, ncol, 2 * i + 1)
            plt.title('{} sim pnl'.format(c))
            plt.plot(self.sim_agg_net_df.index, self.sim_agg_net_df[c], 'g')
            plt.plot(self.sim_agg_pnl_df.index, self.sim_agg_pnl_df[c], 'b--')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()

            plt.subplot(nrow, ncol, 2 * i + 2)
            plt.title('{} sim return'.format(c))
            plt.plot(self.sim_agg_return.index, self.sim_agg_return[c], 'g')
            plt.xticks(rotation = 45)
            plt.ylabel('return')
            plt.grid()

        plt.tight_layout()
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            plt.savefig(saveto, dpi = 300)
            plt.close()
        else:
            plt.show()

    def plot_exchange(self, saveto = None):
        contexts = self.contexts + ['portfolio']
        plt.figure(figsize = (6,len(contexts) * 2))
        ncol = 2
        # nrow = int(np.ceil(len(contexts) / 2))
        nrow = len(contexts)
        for i, c in enumerate(contexts):
            plt.subplot(nrow, ncol, 2 * i + 1)
            plt.title('{} exch pnl'.format(c))
            plt.plot(self.exch_agg_net_df.index, self.exch_agg_net_df[c], 'g')
            plt.plot(self.exch_agg_pnl_df.index, self.exch_agg_pnl_df[c], 'b--')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()

            plt.subplot(nrow, ncol, 2 * i + 2)
            plt.title('{} exch return'.format(c))
            plt.plot(self.exch_agg_return.index, self.exch_agg_return[c], 'g')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()

        plt.tight_layout()
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            plt.savefig(saveto, dpi = 300)
            plt.close()
        else:
            plt.show()

    def plot_live_sim(self, saveto = None):
        contexts = self.contexts + ['portfolio']
        plt.figure(figsize = (6,len(contexts) * 2))
        ncol = 2
        # nrow = int(np.ceil(len(contexts) / 2))
        nrow = len(contexts)
        for i, c in enumerate(contexts):
            plt.subplot(nrow, ncol, 2 * i + 1)
            plt.title('{} live & sim net pnl'.format(c))
            plt.plot(self.live_agg_net_df.index, self.live_agg_net_df[c], 'g')
            plt.plot(self.sim_agg_net_df.index, self.sim_agg_net_df[c], 'b--')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()

            plt.subplot(nrow, ncol, 2 * i + 2)
            plt.title('{} live - sim net pnl'.format(c))
            plt.plot(self.live_agg_net_df.index, self.live_agg_net_df[c] - self.sim_agg_net_df[c], 'r')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()
        
        plt.tight_layout()
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            plt.savefig(saveto, dpi = 300)
            plt.close()
        else:
            plt.show()

    def plot_live_exch(self, saveto = None):
        contexts = self.contexts + ['portfolio']
        plt.figure(figsize = (6,len(contexts) * 2))
        ncol = 2
        # nrow = int(np.ceil(len(contexts) / 2))
        nrow = len(contexts)
        for i, c in enumerate(contexts):
            plt.subplot(nrow, ncol, 2 * i + 1)
            plt.title('{} live & exch net pnl'.format(c))
            plt.plot(self.live_agg_net_df.index, self.live_agg_net_df[c], 'g')
            plt.plot(self.exch_agg_net_df.index, self.exch_agg_net_df[c], 'b--')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()

            plt.subplot(nrow, ncol, 2 * i + 2)
            plt.title('{} live - exch net pnl'.format(c))
            plt.plot(self.live_agg_net_df.index, self.live_agg_net_df[c] - self.exch_agg_net_df[c], 'r')
            plt.xticks(rotation = 45)
            plt.ylabel('eth')
            plt.grid()
        
        plt.tight_layout()
        if saveto:
            folder = os.path.dirname(saveto)
            if not os.path.exists(folder):
                os.makedirs(folder)
            plt.savefig(saveto, dpi = 300)
            plt.close()
        else:
            plt.show()


# pp = portfolio_performance(['changeling', 'cyclops', 'havok', 'sway'])
# perf = pp.calculate_performance()
# for k,v in perf.items():
#   print(k)
#   print(v)
# pp.plot_live('/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/weekly/live.png')
# pp.plot_sim('/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/weekly/sim.png')
# pp.plot_exchange('/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/weekly/exch.png')

class context_backtest_performance:
    def __init__(self, exchange, context, instance, symbol, folder = None):
        self.exchange = exchange
        self.context = context
        self.instance = instance
        self.symbol = symbol
        self.folder = folder
        if folder is None:
            self.folder = os.path.join('/Users/fw/Trading/projects/xman/comics_data', context)
        self.trade_folder = os.path.join(self.folder, 'trade')
        self.snapshot_folder = os.path.join(self.folder, 'snapshot')
        self.daily_df = pd.DataFrame(columns = ['pnl', 'net', 'fee', 'traded', 'notional', 'price'])

    def _get_daily(self, d0, dn):
        if not os.path.exists(self.snapshot_folder):
            return None
        if not os.path.exists(self.trade_folder):
            return None

        eod = d0
        while eod <= dn:
            oie = outright_instance_eod(self.context, self.instance, self.exchange, self.symbol, eod, self.folder)
            df = oie.mark_trade_by_snapshot()
            if df is None:
                eod += dt.timedelta(days = 1)
                continue
            df_snapshot = oie.snapshot_df
            if df_snapshot is None:
                eod += dt.timedelta(days = 1)
                continue
            df_trade = oie.trade_df
            
            pnl = df_snapshot['pnl'][-1]
            fee = df['fee'][-1]
            net = pnl - fee
            size = df_snapshot['max_pos'][-1]
            price = df_snapshot['signal'][-1]
            notional = size * price
            traded = df_trade['amount'].abs().sum() if df_trade is not None else 0
            self.daily_df.loc[eod] = {
                                      'pnl': pnl,
                                      'net': net,
                                      'fee': fee,
                                      'traded': traded,
                                      'notional': notional,
                                      'price': price
                                     }
            eod += dt.timedelta(days = 1)
        return self.daily_df


# exchange = 'binance'
# context = 'changeling-sim'
# symbol = 'dash_eth'
# cbp = context_backtest_performance(exchange, context, symbol)
# d0 = dt.date(2018,11,10)
# dn = dt.date(2018,11,16)
# df = cbp._get_daily(d0, dn)
# print(df)

