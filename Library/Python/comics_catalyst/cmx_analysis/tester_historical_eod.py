import datetime as dt
from eod import outright_eod



# context = 'sway'
# symbol = 'omg_eth'
exchange = 'binance'
start_date = dt.date(2018, 8, 31)
end_date = dt.date(2018, 11, 2)

binance_context_map = {
					   'changeling': 'dash_eth', \
					   'cyclops': 'xmr_eth', \
					   'havok': 'xem_eth', \
					   'sway': 'omg_eth',\
					   }
for context, symbol in binance_context_map.items():
	print(context, symbol)			   
	eod = start_date
	while eod <= end_date:
		print(eod)
		algo_log_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/live_algo/comics_data'
		exch_log_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/exchanges/{}'.format(exchange)
		oe = outright_eod(context, exchange, symbol, eod, algo_log_folder, exch_log_folder)
		oe.update()

		agg_df_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
		live_df_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/live_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
		sim_df_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/sim_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
		exch_df_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
		fig_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/plot/{0}_eod_{1}.png'.format(context, eod)
		oe.save_live_df(live_df_saveto)
		oe.save_sim_df(sim_df_saveto)
		oe.save_exch_df(exch_df_saveto)
		oe.save_agg_df(agg_df_saveto)
		oe.plot(fig_saveto)

		live_summary_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/live_eod/{0}/csv/{0}_live_summary.csv'.format(context)
		sim_summary_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/sim_eod/{0}/csv/{0}_sim_summary.csv'.format(context)
		exch_summary_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{0}/csv/{0}_exch_summary.csv'.format(context)
		agg_summary_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/csv/{0}_agg_summary.csv'.format(context)
		oe.save_live_summary(live_summary_saveto)
		oe.save_sim_summary(sim_summary_saveto)
		oe.save_exch_summary(exch_summary_saveto)
		oe.save_agg_summary(agg_summary_saveto)
		eod += dt.timedelta(days = 1)