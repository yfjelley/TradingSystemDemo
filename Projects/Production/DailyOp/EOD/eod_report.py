import os
import sys
if 'Projects' in os.getcwd():
    cmx_rootpath = os.getcwd().split('Projects')[0]
else:
    cmx_rootpath = os.getcwd().split('Library')[0]
sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/cmx_analysis'))
from eod import outright_eod
from performance_analyzer import portfolio_performance
import datetime as dt
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart


def format_float(x):
    if abs(x) < 1:
        return '{0:.3f}'.format(x)
    if abs(x) < 10:
        return '{0:.2f}'.format(x)
    if abs(x) < 100:
        return '{0:.1f}'.format(x)
    return '{0:.0f}'.format(x)

if __name__ == '__main__':
    eod = dt.datetime.utcnow().date() - dt.timedelta(days = 1)
    summary_df = None
    figfiles = []
    context_map = {
                   'nightcrawler': ['binance', 'tusd_usdt'], 
                  }

    algo_log_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/live_algo/comics_data'
    instance = 'xman-live-c1'
    for context, exch_symbol in context_map.items():
        exchange = exch_symbol[0]
        symbol = exch_symbol[1]
        print('create eod report for {}:{} on {}'.format(context, symbol, eod))
        exch_log_folder = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/exchanges/{}'.format(exchange)
        oe = outright_eod(context, instance, exchange, symbol, eod, algo_log_folder, exch_log_folder)
        oe.update()
        agg_df_saveto  = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
        live_df_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/live_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
        sim_df_saveto  = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/sim_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
        exch_df_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{0}/csv/{0}_eod_{1}.csv'.format(context, eod)
        fig_saveto     = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/plot/{0}_eod_{1}.png'.format(context, eod)
        oe.save_live_df(live_df_saveto)
        oe.save_sim_df(sim_df_saveto)
        oe.save_exch_df(exch_df_saveto)
        oe.save_agg_df(agg_df_saveto)
        oe.plot(fig_saveto)
        live_summary_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/live_eod/{0}/csv/{0}_live_summary.csv'.format(context)
        sim_summary_saveto  = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/sim_eod/{0}/csv/{0}_sim_summary.csv'.format(context)
        exch_summary_saveto = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/exchange_eod/{0}/csv/{0}_exch_summary.csv'.format(context)
        agg_summary_saveto  = '/Volumes/Tamedog_2T/AirPort_Work/Trading/projects/AirPort_Xman/data/production/eod/aggregate_eod/{0}/csv/{0}_agg_summary.csv'.format(context)
        live_summary = oe.save_live_summary(live_summary_saveto)
        sim_summary  = oe.save_sim_summary(sim_summary_saveto)
        exch_summary = oe.save_exch_summary(exch_summary_saveto)
        agg_summary  = oe.save_agg_summary(agg_summary_saveto)
        if summary_df is None:
            summary_df = pd.DataFrame([agg_summary[['live_net', 'sim_net', 'exch_net', 'live_position', 'sim_position', 'exch_position']]], index = [context])
        else:
            summary_df.loc[context] = agg_summary[['live_net', 'sim_net', 'exch_net', 'live_position', 'sim_position', 'exch_position']]
        figfiles.append(fig_saveto)
    summary_df.sort_index(inplace = True)

    pp = portfolio_performance(list(context_map.keys()))
    perf_dfs = pp.calculate_performance(eod, eod)
    summary_df.loc['portfolio', ['live_net', 'sim_net', 'exch_net']] = [perf_dfs[x].loc['portfolio', 'net'] for x in ['live', 'sim', 'exch']]
    summary_str_df = summary_df.applymap(format_float)

    # send email:
    from_email = 'frankwang.alert@gmail.com'
    to_emails  = [from_email]
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(from_email, 'xrzfetasfecmqebj')
    msg = MIMEMultipart()
    msg['subject'] = '[Xman] eod report: {}'.format(eod)
    msg['From'] = from_email
    msg['To']   = ','.join(to_emails)
    msg.attach(MIMEText(summary_str_df.to_html(), 'html'))
    for f in figfiles:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=os.path.basename(f)
            )
        part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(f)
        msg.attach(part)
    server.sendmail(from_email, from_email, msg.as_string())
    server.quit()
