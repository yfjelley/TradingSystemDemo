import os
import logging
import datetime as dt
import time
import numpy as np
import pandas as pd
from catalyst.api import (record, symbol, set_commission, set_slippage)
# import random
import json


if os.path.exists('c:'):
    ROOT_DISK = 'c:'  
elif os.path.exists('/Users/fw/Trading/projects/avengers'):
    ROOT_DISK = '/Users/fw/Trading/projects/avengers'
else:
    ROOT_DISK = '/home/frankwang_trading'

class multileg_config:
    def __init__(self, json_file):
        self.ts = None
        self.json_file = json_file
        self.json_data = self._read_json()
                
        self.global_context   = self.json_data['global']['context']
        self.global_instance  = self.json_data['global']['instance']
        self.global_mode      = self.json_data['global']['mode']
        self.global_exchanges = self.json_data['global']['exchanges']
        self.global_symbols   = self.json_data['global']['symbols']
        self.global_leg_num   = len(self.global_symbols)

        self.catalyst_exchanges = None
        self.catalyst_assets    = []

        self.sim_maker_fee_pct = self.json_data['simulation']['maker_fee_pct']
        self.sim_taker_fee_pct = self.json_data['simulation']['taker_fee_pct']
        self.sim_slippage_pct  = self.json_data['simulation']['slippage_pct']

        self._config_last_modify_ts = os.path.getmtime(self.json_file)

        self.signal_window             = self.json_data['signal']['window']
        self.signal_update_rate        = dt.timedelta(minutes = self.json_data['signal']['update_rate'])
        self.signal_minsd              = self.json_data['signal']['minsd']
        self.signal_candle_size        = self.json_data['signal']['candle_size']
        self.signal_hist_bar_limit     = self.json_data['signal']['hist_bar_limit']
        self.signal_wait_for_full_hist = self.json_data['signal']['wait_for_full_hist']
        self.signal_bid_ask_diffs      = self.json_data['signal']['bid_ask_diffs']

        self.invent_profit_margin        = self.json_data['invent']['profit_margin']
        self.invent_e0                   = self.json_data['invent']['e0']
        self.invent_en                   = self.json_data['invent']['en']
        self.invent_share_per_level      = self.json_data['invent']['share_per_level']
        self.invent_ignore_partial_fills = self.json_data['invent']['ignore_partial_fills']
        self.invent_min_shares           = self.json_data['invent']['min_shares']
        self.invent_ticksizes            = self.json_data['invent']['ticksizes']
        self.invent_bid_ask_offsets      = self.json_data['invent']['bid_ask_offsets']
        self.invent_hedge_rates          = self.json_data['invent']['hedge_rates']
        self.invent_init_hedge_levels    = self.json_data['invent']['init_hedge_levels']

        self.risk_start_dt        = None
        if self.json_data['risk']['start_ts']:
            self.risk_start_dt    = pd.to_datetime(self.json_data['risk']['start_ts'], utc = True) 
        self.risk_end_dt          = None
        if self.json_data['risk']['end_ts']:
            self.risk_end_dt      = pd.to_datetime(self.json_data['risk']['end_ts'], utc = True)
        self.risk_max_notional    = self._round_position(self.json_data['risk']['max_notional'], self.invent_share_per_level)
        self.risk_min_notional    = self._round_position(self.json_data['risk']['min_notional'], self.invent_share_per_level)
        self.risk_max_positions   = self.json_data['risk']['max_positions'] # TODO round position by spn
        self.risk_min_positions   = self.json_data['risk']['min_positions']
        self.risk_quote_currency  = self.json_data['risk']['quote_currency']
        self.risk_max_delta       = self.json_data['risk']['max_delta']
        self.risk_exit_nonew_dt   = pd.to_datetime(self.json_data['risk']['exit_nonew_ts'], utc = True)
        self.risk_exit_passive_dt = pd.to_datetime(self.json_data['risk']['exit_passive_ts'], utc = True)
        self.risk_exit_active_dt  = pd.to_datetime(self.json_data['risk']['exit_active_ts'], utc = True)

        self.invent_n = int((self.risk_max_notional - self.risk_min_notional) / self.invent_share_per_level / 2)
        
        self.display_refresh_rate = dt.timedelta(minutes = self.json_data['display']['refresh_rate'])
        self.display_show_sim     = self.json_data['display']['show_sim']
        self.display_plot         = self.json_data['display']['plot']

        self.storage_refresh_rate     = dt.timedelta(minutes = self.json_data['storage']['refresh_rate'])
        self.storage_log_folder       = '{}/comics_data/{}/log'.format(ROOT_DISK, self.global_context)
        self.storage_log_level        = self.json_data['storage']['log_level'].upper()
        self.storage_record_folder    = '{}/comics_data/{}/record'.format(ROOT_DISK, self.global_context)
        self.storage_trade_folder     = '{}/comics_data/{}/trade'.format(ROOT_DISK, self.global_context)
        self.storage_snapshot_folder  = '{}/comics_data/{}/snapshot'.format(ROOT_DISK, self.global_context)
        self.storage_perf_stat_folder = '{}/comics_data/{}/perf_stat'.format(ROOT_DISK, self.global_context)
        self.storage_plot_folder      = '{}/comics_data/{}/plot'.format(ROOT_DISK, self.global_context)

        if self.storage_log_folder and not os.path.exists(self.storage_log_folder):
            os.makedirs(self.storage_log_folder)
        if self.storage_record_folder and not os.path.exists(self.storage_record_folder):
            os.makedirs(self.storage_record_folder)
        if self.storage_trade_folder and not os.path.exists(self.storage_trade_folder):
            os.makedirs(self.storage_trade_folder)
        if self.storage_snapshot_folder and not os.path.exists(self.storage_snapshot_folder):
            os.makedirs(self.storage_snapshot_folder)
        if self.storage_perf_stat_folder and not os.path.exists(self.storage_perf_stat_folder):
            os.makedirs(self.storage_perf_stat_folder)
        if self.storage_plot_folder and not os.path.exists(self.storage_plot_folder):
            os.makedirs(self.storage_plot_folder)

        self.storage_log_file       = None
        self.storage_record_file    = '{}_{}_{}.pickle'.format(self.global_context, self.global_instance, self.global_mode)
        self.storage_trade_file     = None
        self.storage_snapshot_file  = None
        self.storage_perf_stat_file = 'pnl.stat.csv'
        self.storage_plot_file      = None

    def _round_position(self, p0, p1):
        if p1 == 0:
            return p0
        return np.floor(p0 / p1) * p1 if p0 > 0 else -(np.floor(-p0 / p1) * p1)

    def _read_json(self):
        if not os.path.exists(self.json_file):
            return None
        with open(self.json_file) as f:
            data = json.load(f)
        return data

    def _generate_file_prefix(self, eod):
        file_prefix = '{}_{}_{}_{}'.format(
                                           self.global_context,
                                           self.global_instance,
                                           self.global_mode,
                                           eod
                                          )
        return file_prefix

    def _get_log_level(self, level_str):
        if level_str.upper() == 'CRITICAL':
            return logging.CRITICAL
        if level_str.upper() == 'ERROR':
            return logging.ERROR
        if level_str.upper() == 'WARNING':
            return logging.WARNING
        if level_str.upper() == 'INFO':
            return logging.INFO
        if level_str.upper() == 'DEBUG':
            return logging.DEBUG
        return logging.NOTSE

    def reload_config(self):
        if self.global_mode == 'backtest':
            return False

        config_mtime = os.path.getmtime(self.json_file)
        if config_mtime != self._config_last_modify_ts:
            self._config_last_modify_ts = config_mtime

            self.json_data = self._read_json()
            if not self.json_data:
                return False
            
            self.ts = None
            self.global_context   = self.json_data['global']['context']
            self.global_instance  = self.json_data['global']['instance']
            self.global_mode      = self.json_data['global']['mode']
            self.global_exchanges = self.json_data['global']['exchanges']
            self.global_symbols   = self.json_data['global']['symbols']
            self.global_leg_num   = len(self.global_symbols)

            self.catalyst_exchanges = [self.context.exchanges[self.global_exchanges[i]] for i in range(self.global_leg_num)]
            self.catalyst_assets    = [symbol(self.global_symbols[i], self.global_exchanges[i]) for i in range(self.global_leg_num)]

            self.sim_maker_fee_pct = self.json_data['simulation']['maker_fee_pct']
            self.sim_taker_fee_pct = self.json_data['simulation']['taker_fee_pct']
            self.sim_slippage_pct  = self.json_data['simulation']['slippage_pct']

            self._config_last_modify_ts = os.path.getmtime(self.json_file)

            self.signal_window             = self.json_data['signal']['window']
            self.signal_update_rate        = dt.timedelta(minutes = self.json_data['signal']['update_rate'])
            self.signal_minsd              = self.json_data['signal']['minsd']
            self.signal_candle_size        = self.json_data['signal']['candle_size']
            self.signal_hist_bar_limit     = self.json_data['signal']['hist_bar_limit']
            self.signal_wait_for_full_hist = self.json_data['signal']['wait_for_full_hist']
            self.signal_bid_ask_diffs      = self.json_data['signal']['bid_ask_diffs']

            self.invent_profit_margin        = self.json_data['invent']['profit_margin']
            self.invent_e0                   = self.json_data['invent']['e0']
            self.invent_en                   = self.json_data['invent']['en']
            self.invent_share_per_level      = self.json_data['invent']['share_per_level']
            self.invent_ignore_partial_fills = self.json_data['invent']['ignore_partial_fills']
            self.invent_min_shares           = self.json_data['invent']['min_shares']
            self.invent_ticksizes            = self.json_data['invent']['ticksizes']
            self.invent_bid_ask_offsets      = self.json_data['invent']['bid_ask_offsets']
            self.invent_hedge_rates          = self.json_data['invent']['hedge_rates']
            self.invent_init_hedge_levels    = self.json_data['invent']['init_hedge_levels']

            self.risk_start_dt        = None
            if self.json_data['risk']['start_ts']:
                self.risk_start_dt    = pd.to_datetime(self.json_data['risk']['start_ts'], utc = True) 
            self.risk_end_dt          = None
            if self.json_data['risk']['end_ts']:
                self.risk_end_dt      = pd.to_datetime(self.json_data['risk']['end_ts'], utc = True)
            self.risk_max_notional    = self._round_position(self.json_data['risk']['max_notional'], self.invent_share_per_level)
            self.risk_min_notional    = self._round_position(self.json_data['risk']['min_notional'], self.invent_share_per_level)
            self.risk_max_positions   = self.json_data['risk']['max_positions'] # TODO round position by spn
            self.risk_min_positions   = self.json_data['risk']['min_positions']
            self.risk_quote_currency  = self.json_data['risk']['quote_currency']
            self.risk_max_delta       = self.json_data['risk']['max_delta']
            self.risk_exit_nonew_dt   = pd.to_datetime(self.json_data['risk']['exit_nonew_ts'], utc = True)
            self.risk_exit_passive_dt = pd.to_datetime(self.json_data['risk']['exit_passive_ts'], utc = True)
            self.risk_exit_active_dt  = pd.to_datetime(self.json_data['risk']['exit_active_ts'], utc = True)

            self.invent_n = int((self.risk_max_notional - self.risk_min_notional) / self.invent_share_per_level / 2)
            
            self.display_refresh_rate = dt.timedelta(minutes = self.json_data['display']['refresh_rate'])
            self.display_show_sim     = self.json_data['display']['show_sim']
            self.display_plot         = self.json_data['display']['plot']

            self.storage_refresh_rate     = dt.timedelta(minutes = self.json_data['storage']['refresh_rate'])
            self.storage_log_folder       = '{}/comics_data/{}/log'.format(ROOT_DISK, self.global_context)
            self.storage_log_level        = self.json_data['storage']['log_level'].upper()
            self.storage_record_folder    = '{}/comics_data/{}/record'.format(ROOT_DISK, self.global_context)
            self.storage_trade_folder     = '{}/comics_data/{}/trade'.format(ROOT_DISK, self.global_context)
            self.storage_snapshot_folder  = '{}/comics_data/{}/snapshot'.format(ROOT_DISK, self.global_context)
            self.storage_perf_stat_folder = '{}/comics_data/{}/perf_stat'.format(ROOT_DISK, self.global_context)
            self.storage_plot_folder      = '{}/comics_data/{}/plot'.format(ROOT_DISK, self.global_context)

            if self.storage_log_folder and not os.path.exists(self.storage_log_folder):
                os.makedirs(self.storage_log_folder)
            if self.storage_record_folder and not os.path.exists(self.storage_record_folder):
                os.makedirs(self.storage_record_folder)
            if self.storage_trade_folder and not os.path.exists(self.storage_trade_folder):
                os.makedirs(self.storage_trade_folder)
            if self.storage_snapshot_folder and not os.path.exists(self.storage_snapshot_folder):
                os.makedirs(self.storage_snapshot_folder)
            if self.storage_perf_stat_folder and not os.path.exists(self.storage_perf_stat_folder):
                os.makedirs(self.storage_perf_stat_folder)
            if self.storage_plot_folder and not os.path.exists(self.storage_plot_folder):
                os.makedirs(self.storage_plot_folder)
            logging.info('[multileg_config] reloaded config.')
            return True
        return False

    def update_ts(self, ts, context):
        self.catalyst_exchanges = [context.exchanges[self.global_exchanges[i]] for i in range(self.global_leg_num)]
        self.catalyst_assets = [symbol(self.global_symbols[i], self.global_exchanges[i]) for i in range(self.global_leg_num)]
        if not ts:
            return False
        if not self.ts or self.ts.date() != ts.date():
            self.ts = ts
            eod = self.ts.date()
            file_prefix = self._generate_file_prefix(eod)
            self.storage_log_file         = '{}.comics.log'.format(file_prefix)
            self.storage_trade_file       = '{}.trade.csv'.format(file_prefix)
            self.storage_snapshot_file    = '{}.snapshot.csv'.format(file_prefix)
            self.storage_plot_file        = '{}.png'.format(file_prefix)
            
            logging.basicConfig(
                                filename = os.path.join(self.storage_log_folder, self.storage_log_file),\
                                format   = '%(asctime)s - %(levelname)s - %(message)s', 
                                level    = self._get_log_level(self.storage_log_level)
                               )
            logging.info('[multileg_config] updated eod to {}'.format(eod))
            if self.global_mode != 'live':
                set_commission(maker = self.sim_maker_fee_pct, taker = self.sim_taker_fee_pct)
                set_slippage(slippage = self.sim_slippage_pct)
            return True
        return False
        
