import pandas as pd

context = 'sample'
if os.path.exists('c:'):
    root_disk = 'c:'  
elif os.path.exists('/Users/fw/Trading/projects/xman'):
    root_disk = '/Users/fw/Trading/projects/xman'
else:
    root_disk = '/home/frankwang_trading'

cmx_config = {
            'global_namespace': context,
            'global_instance': 'xman-live-c1',
            'global_mode': 'paper', # 'live', 'paper', 'backtest'
            'global_bootstrap': False,

            'sim_maker_fee_pct': 0.001,
            'sim_taker_fee_pct': 0.001,
            'sim_slippage_pct': 0,

            'time_start': None,
            'time_end' : None,
            # 'time_start': pd.to_datetime('2018-7-1', utc=True),
            # 'time_end': pd.to_datetime('2018-7-12', utc=True),

            'exchange': 'binance',
            'symbol' : 'tusd_usdt',

            'risk_max_notional': 0,
            'risk_max_pos' : 160,
            'risk_max_long_pos': 160,
            'risk_max_short_pos': -160, # short_pos <= 0
            'risk_quote_currency': 'usdt',
            # 'risk_init_position': 0,
            # 'risk_init_cost_basis': 0,

            'signal_window': 60 * 24 * 7,
            'signal_update_rate': 60, 
            'signal_minsd': 0.002,
            'signal_ref_price' : 1.0013,
            'signal_candle_size' : '1T',
            'signal_hist_rate_limit': 1000,
            'signal_wait_for_full_hist': True,

            'invent_pm' : 1.5,
            'invent_e0' : 0.5,
            'invent_en' : 4,
            'invent_spn' : 20,
            'invent_ignore_partial_fill_value': 0.1,
            'invent_min_share': 20,
            'invent_ticksize': 1e-4,

            'exit_nonew_dt'  : pd.to_datetime('2019-8-4 17:00:00', utc = True),
            'exit_passive_dt': pd.to_datetime('2019-8-4 17:00:00', utc = True),
            'exit_active_dt' : pd.to_datetime('2019-8-4 17:00:00', utc = True),
            # 'exit_signal_shift': 1e-4,
            # 'exit_shift_interval': dt.timedelta(minutes = 1),

            'record_path': '{}/comics_data/{}/record'.format(root_disk, context),
            'trade_path' : '{}/comics_data/{}/trade'.format(root_disk, context),
            'snapshot_path': '{}/comics_data/{}/snapshot'.format(root_disk, context),
            'perf_stat_path': '{}/comics_data/{}/perf_stat'.format(root_disk, context),
            'record_pickle': None,
            'record_rate': 1,

            'display_refresh_rate': 1,
            'display_plot': True,
            'display_sim': False,

            'plot_fig': True,
            'plot_path': '{}/comics_data/{}/plot'.format(root_disk, context),
            }


cmx_pair_config = {
                        'global_namespace': context,
                        'global_instance' : 827001,
                        'global_mode'     : 'backtest', # 'live', 'paper', 'backtest'
                        'global_bootstrap': False,

                        'sim_maker_fee_pct': 0.001,
                        'sim_taker_fee_pct': 0.001,
                        'sim_slippage_pct' : 0.0005,

                        # 'time_start': None,
                        # 'time_end' : None,
                        'time_start': pd.to_datetime('2018-7-2', utc=True),
                        'time_end'  : pd.to_datetime('2018-8-1', utc=True),

                        'exchanges': ['binance', 'binance'],
                        'symbols'  : ['dash_btc', 'eth_btc'],
                        'betas'    : [1, -1],
                        'bridge_currency': 'btc',

                        'risk_max_amount'        : 20,
                        'risk_max_long_position' : 20,
                        'risk_max_short_position': -20, # short_pos <= 0
                        'risk_quote_currency'    : 'btc',
                        'risk_deltas'            : [1, 1],
                        'risk_init_positions'    : [0, 0],

                        'signal_long_window'  : 60 * 24,
                        'signal_short_windows': [1, 1],
                        'signal_update_rate'  : 1, 
                        'signal_minsd'        : 0.005,
                        'signal_reset_rate'   : 1440 * 70,
                        'signal_reset_ror_thresholds' : [0.1, 0.1],
                        'signal_betas'        : [1, -1],
                        'signal_candle_size'  : '1T',
                        'signal_hist_rate_limit': 1000,

                        'invent_pm'    : 1,
                        'invent_e0'    : 1,
                        'invent_en'    : 5,
                        'invent_spn'   : 2,
                        'invent_min_shares'   : [0.05, 0.03],
                        'invent_price_offsets': [1, 5e-6],
                        'invent_ignore_partial_fill_shares': [5e-4, 3e-4],
                        'invent_ticksizes': [1e-6, 1e-6],

                        'log_path': '{}/comics_data/{}/log'.format(root_disk, context),
                        'log_level': 'WARNING'.upper(), #CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSE

                        'record_path': '{}/comics_data/{}/record'.format(root_disk, context),
                        'record_pickle': None,
                        'record_rate': 60,

                        'display_refresh_rate': 1,
                        'display_plot': True,
                        'display_sim': False,

                        'plot_fig': True,
                        'plot_path': '{}/comics_data/{}/plot'.format(root_disk, context),
                         }

