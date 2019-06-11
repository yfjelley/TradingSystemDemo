#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 30 12:58:15 2018

@author: fw
"""
import os
import json
import numpy as np
import datetime as dt

def read_json(json_file):
    if not os.path.exists(json_file):
        return None

    with open(json_file) as f:
        data = json.load(f)
    return data

# json_file = '/Users/fw/Trading/projects/xman/configuration/changeling_config.json'
class outright_context_config:
    def __init__(self, context, config_folder = None):
        self._context = context.lower()
        self._config_folder = config_folder if config_folder else '/Users/fw/Trading/projects/xman/configuration'
        self._config_json = os.path.join(self._config_folder, '{}_config.json'.format(self._context))
        self._json_data = read_json(self._config_json)

        self._exchange = None
        self._symbol = None

        self._log_root_folder = self._get_log_root_folder()
        self._log_perf_folder = None

        self._risk_max_position = np.nan
        self._risk_min_position = np.nan

        self._alert_refresh_rate = dt.timedelta(seconds = 50)
        self._alert_email_recipients = ["frankwang.alert@gmail.com"]
        self._alert_connect_ts_delays = []
        self._alert_live_pnls = []
        self._alert_live_sim_pnl_diffs = []
        self._alert_live_sim_position_abs_diffs = []
        self._alert_live_sim_position_pct_diffs = []

    def update(self):
        self._json_data = read_json(self._config_json)

    @property
    def context(self):
        try:
            jcontext = self._json_data['context'].lower()
            if self._context != jcontext:
                raise Exception('context mismatch! class {} vs json {}'.format(self._context, jcontext))
        except:
            print('WARNING! missing context in {}_config.json'.format(self._context))
        return self._context

    @property
    def exchange(self):
        try:
            self._exchange = self._json_data['exchange'].lower()
        except:
            print('WARNING! missing exchange in {}_config.json'.format(self._context))
        return self._exchange

    @property
    def symbol(self):
        try:
            self._symbol = self._json_data['symbol'].lower()
        except:
            print('WARNING! missing symbol in {}_config.json'.format(self._context))
        return self._symbol

    def _get_log_root_folder(self):
        if os.path.exists('c:'):
            root_folder = 'c:'  
        elif os.path.exists('/Users/fw/Trading/projects/xman'):
            root_folder = '/Users/fw/Trading/projects/xman'
        else:
            root_folder = '/home/frankwang_trading'
        return root_folder

    @property
    def log_root_folder(self):
        return self._log_root_folder

    @property
    def log_perf_folder(self):
        self._log_perf_folder = '{}/comics_data/{}/perf_stat'.format(self._log_root_folder, self.context)
        return self._log_perf_folder

    @property
    def alert_connect_ts_dalays(self):
        try:
            self._alert_connect_ts_delays = [dt.timedelta(minutes = int(x)) for  x in self._json_data['alert']['connection']['ts_delay_in_minute']]
        except:
            self._alert_connect_ts_delays = []
        return self._alert_connect_ts_delays

    @property
    def risk_max_position(self):
        try:
            self._risk_max_position = self._json_data['risk']['max_position']
        except:
            print('[WARNING] failed to get max_position for {}'.format(self._context))
        return self._risk_max_position

    @property
    def risk_min_position(self):
        try:
            self._risk_min_position = self._json_data['risk']['min_position']
        except:
            print('[WARNING] failed to get min_position for {}'.format(self._context))
        return self._risk_min_position

    @property
    def alert_refresh_rate(self):
        try:
            refresh_in_second = self._json_data['alert']['refresh_in_second']
            self._alert_refresh_rate = dt.timedelta(seconds = refresh_in_second)
        except:
            pass
        return self._alert_refresh_rate

    @property
    def alert_email_recipients(self):
        try:
            self._alert_email_recipients = self._json_data['alert']['email_recipients']
        except:
            pass
        return self._alert_email_recipients

    @property
    def alert_live_pnls(self):
        try:
            self._alert_live_pnls = self._json_data['alert']['pnl']['live']
        except:
            self._alert_live_pnls = []
        return self._alert_live_pnls

    @property
    def alert_live_sim_pnl_diffs(self):
        try:
            self._alert_live_sim_pnl_diffs = self._json_data['alert']['pnl']['live_sim']
        except:
            self._alert_live_sim_pnl_diffs = []
        return self._alert_live_sim_pnl_diffs

    @property
    def alert_live_sim_position_abs_diffs(self):
        try:
            self._alert_live_sim_position_abs_diffs = self._json_data['alert']['position']['live_sim_abs']
        except:
            self._alert_live_sim_position_abs_diffs = []
        return self._alert_live_sim_position_abs_diffs

    @property
    def alert_live_sim_position_pct_diffs(self):
        try:
            self._alert_live_sim_position_pct_diffs = self._json_data['alert']['position']['live_sim_pct']
        except:
            self._alert_live_sim_position_pct_diffs = []
        return self._alert_live_sim_position_pct_diffs


# changeling_config = outright_config('changeling', '/Users/fw/Trading/projects/xman/configuration')
# print(changeling_config.context)
# print(changeling_config.exchange)
# print(changeling_config.symbol)
# print(changeling_config.alert_live_pnl)
# print(changeling_config.alert_live_sim_pnl_diff)
# print(changeling_config.alert_live_sim_position_diff_abs)
# print(changeling_config.alert_live_sim_position_diff_pct)

class outright_portfolio_config:
    def __init__(self, config_folder):
        self._config_folder = config_folder
        self._context_configs = []
        self._context_map = {}
        self._contexts = []
        self._exchanges = []
        self._symbols = []

    @property
    def context_configs(self):
        if len(self._context_configs) > 0:
            return self._context_configs
        for f in os.listdir(self._config_folder):
            if '_config.json' in f:
                ctx = f.split('_')[0]
                config = outright_context_config(ctx, self._config_folder)
                self._context_configs.append(config)
        return self._context_configs

    @property
    def context_map(self):
        if len(self._context_map) > 0:
            return self._context_map
        configs = self.context_configs
        for cfg in configs:
            ctx = cfg.context
            exch = cfg.exchange
            sym = cfg.symbol
            self._context_map[ctx] = [exch, sym]
        return self._context_map

    @property
    def contexts(self):
        cmap = self.context_map
        self._contexts = list(cmap.keys())
        return self._contexts

    @property
    def exchanges(self):
        cmap = self.context_map
        self._exchanges = []
        for k,v in cmap.items():
            self._exchanges.append(v[0])
        return self._exchanges

    @property
    def symbols(self):
        cmap = self.context_map
        self._symbols = []
        for k,v in cmap.items():
            self._symbols.append(v[1])
        return self._symbols

# opc = outright_portfolio_config('/Users/fw/Trading/projects/xman/configuration')
# print(opc.context_map)
# print(opc.contexts)
# print(opc.exchanges)
# print(opc.symbols)


