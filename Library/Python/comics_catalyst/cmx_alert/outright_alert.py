import os
import numpy as np
import pandas as pd
import datetime as dt
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
import sendgrid
from sendgrid.helpers.mail import *
import time

# import sys
# if 'Projects' in os.getcwd():
#     cmx_rootpath = os.getcwd().split('Projects')[0]
# else:
#     cmx_rootpath = os.getcwd().split('Library')[0]
# sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst'))
# sys.path.append(os.path.join(cmx_rootpath, 'Library/Python/comics_catalyst/*'))
from cmx_config.json_configuration import (outright_context_config, outright_portfolio_config)



class context_alert:
    def __init__(self, config = None, context = None, config_folder = None):
        if config:
            self._json_config = config
        elif context:
            self._json_config = outright_context_config(context, config_folder)
        else:
            raise Exception('[cmx_alert] config and context are both None')

        self._context = self._json_config.context
        self._exchange = self._json_config.exchange
        self._symbol = self._json_config.symbol

        self._refresh_rate = self._json_config.alert_refresh_rate
        self._last_refresh_ts = None
        self._email_recipients = self._json_config.alert_email_recipients

        self._log_root_folder = self._json_config.log_root_folder
        self._live_perf_stat_folder = self._json_config.log_perf_folder
        self._sim_perf_stat_folder = '{}/comics_data/{}-sim/perf_stat'.format(self._log_root_folder, self._context)

        self._max_position = self._json_config.risk_max_position
        self._price = np.nan

        self._alert_connect_ts_delays = self._json_config.alert_connect_ts_dalays
        self._connect_delay_level = 0

        self._live_net = 0
        self._sim_net = 0
        self._alert_pnl_values = self._json_config.alert_live_pnls
        self._alert_pnl_level = 0
        self._live_sim_pnl_diffs = self._json_config.alert_live_sim_pnl_diffs
        self._live_sim_pnl_diff_level = 0

        self._live_pos = 0
        self._sim_pos = 0
        self._alert_live_sim_pos_abs_diffs = self._json_config.alert_live_sim_position_abs_diffs
        self._alert_live_sim_pos_pct_diffs = self._json_config.alert_live_sim_position_pct_diffs
        self._live_sim_pos_diff_level = 0

    def _reset_levels(self):
        self._connect_delay_level = 0
        self._alert_pnl_level = 0
        self._live_sim_pnl_diff_level = 0
        self._live_sim_pnl_diff_level = 0

    def update(self):
        utcnow = dt.datetime.utcnow()
        if not self._last_refresh_ts or utcnow - self._last_refresh_ts >= self._refresh_rate:
            self._json_config.update()
            if self._last_refresh_ts and utcnow.date() != self._last_refresh_ts.date():
                self._reset_levels()
            if os.path.exists(os.path.join(self._live_perf_stat_folder, 'pnl.stat.csv')):
                live_perf_df = pd.read_csv(os.path.join(self._live_perf_stat_folder, 'pnl.stat.csv'), header = 0, index_col = 0, parse_dates = True)
                self._live_net = live_perf_df['net'][0]
                self._live_pos = live_perf_df['position'][0]
                self._price = live_perf_df['price'][0]
                last_ts = live_perf_df.index[0]
            else:
                live_perf_df = None
                self._live_net = np.nan
                self._live_pos = np.nan
                self._price = np.nan
                last_ts = None
                # self.email_disconnect_alert(utcnow, last_ts)
                return False
            
            if os.path.exists(os.path.join(self._sim_perf_stat_folder, 'pnl.stat.csv')):
                sim_perf_df = pd.read_csv(os.path.join(self._sim_perf_stat_folder, 'pnl.stat.csv'), header = 0, index_col = 0, parse_dates = True)
                self._sim_net = sim_perf_df['net'][0]
                self._sim_pos = sim_perf_df['position'][0]
                if np.isnan(self._price):
                    self._price = sim_perf_df['price'][0]
            else:
                sim_perf_df = None
                self._sim_net = np.nan
                self._sim_pos = np.nan
            
            if self._alert_connect_ts_delays and utcnow - last_ts > self._alert_connect_ts_delays[self._connect_delay_level]:
                self.email_disconnect_alert(utcnow, last_ts)
                self._connect_delay_level += 1 if self._connect_delay_level < len(self._alert_connect_ts_delays) - 1 else 0
                self._last_refresh_ts = utcnow
                return True # no need to check pnl or position when disconnected

            if self._alert_pnl_values and self._live_net <= self._alert_pnl_values[self._alert_pnl_level]:
                self.email_pnl_alert(utcnow, self._alert_pnl_values[self._alert_pnl_level])
                self._alert_pnl_level+= 1 if self._alert_pnl_level< len(self._alert_pnl_values) - 1 else 0

            live_sim_net_diff = self._live_net - self._sim_net
            if self._live_sim_pnl_diffs and live_sim_net_diff <= -1 * abs(self._live_sim_pnl_diffs[self._live_sim_pnl_diff_level]):
                self.email_pnl_mismatch_alert(utcnow, live_sim_net_diff, self._live_sim_pnl_diffs[self._live_sim_pnl_diff_level])
                self._live_sim_pnl_diff_level += 1 if self._live_sim_pnl_diff_level < len(self._live_sim_pnl_diffs) - 1 else 0

            live_sim_pos_diff = self._live_pos - self._sim_pos
            if self._alert_live_sim_pos_abs_diffs:
                # abs position has higher priority than percentage
                if abs(live_sim_pos_diff) >= self._alert_live_sim_pos_abs_diffs[self._live_sim_pos_diff_level]:
                    self.email_position_abs_mismatch_alert(utcnow, live_sim_pos_diff, self._alert_live_sim_pos_abs_diffs[self._live_sim_pos_diff_level])
                    self._live_sim_pos_diff_level += 1 if self._live_sim_pos_diff_level < len(self._alert_live_sim_pos_abs_diffs) - 1 else 0
            else:
                if abs(live_sim_pos_diff) / self._max_position >= self._alert_live_sim_pos_pct_diffs[self._live_sim_pos_diff_level]:
                    self.email_position_pct_mismatch_alert(utcnow, live_sim_pos_diff / self._max_position, self._alert_live_sim_pos_pct_diffs[self._live_sim_pos_diff_level])
                    self._live_sim_pos_diff_level += 1 if self._live_sim_pos_diff_level < len(self._alert_live_sim_pos_pct_diffs) - 1 else 0  

            self._last_refresh_ts = utcnow
            return True
        return False

    @property
    def live_net(self):
        return self._live_net
    @property
    def sim_net(self):
        return self._sim_net
    @property
    def live_position(self):
        return self._live_pos
    @property
    def sim_position(self):
        return self._sim_pos
    @property
    def price(self):
        return self._price
    @property
    def symbol(self):
        return self._symbol

    def _send_email(self, to_addrs, subject, body):
        # from_addr = 'frankwang.alert@gmail.com'
        # server = smtplib.SMTP('smtp.gmail.com', 587)
        # server.ehlo()
        # server.starttls()
        # server.login(from_addr, 'lxcprckoblifrmmj')
        # msg = MIMEMultipart()
        # msg['subject'] = subject
        # msg['From'] = from_addr
        # msg['To']   = ','.join(to_addrs)
        # msg.attach(MIMEText(body, 'plain'))
        # server.sendmail(from_addr, to_addrs, msg.as_string())
        # server.quit()
        sg = sendgrid.SendGridAPIClient(apikey= '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')
        from_email = Email("frankwang.alert@gmail.com")
        to_email_list = [Email(x) for x in to_addrs]
        content = Content("text/plain", body)
        for to_email in to_email_list:
            mail = Mail(from_email, subject, to_email, content)
            response = sg.client.mail.send.post(request_body=mail.get())

    def email_disconnect_alert(self, ts, last_ts):
        subject = '[xman][alert][{}] DISCONNECTED'.format(self._context)
        body = 'now = {} | last_ts = {}'.format(ts, last_ts)
        self._send_email(self._email_recipients, subject, body)

    def email_pnl_alert(self, ts, alert_net):
        subject = '[xman][alert][{}] net pnl {:.3f} < {:.3f}'.format(self._context, self._live_net, alert_net)
        body = '{}: {} net pnl {} < {}'.format(ts, self._context, self._live_net, alert_net)
        self._send_email(self._email_recipients, subject, body)

    def email_pnl_mismatch_alert(self, ts, net_diff, alert_diff):
        subject = '[xman][alert][{}] net diff {:.4f} < {:.4f}'.format(self._context, net_diff, -1 * abs(alert_diff))
        body = '{}: {}\n live net: {}\n sim net: {}\n diff {} < {}'.format(ts, self._context, self._live_net, self._sim_net, net_diff, -abs(alert_diff))
        self._send_email(self._email_recipients, subject, body)

    def email_position_abs_mismatch_alert(self, ts, pos_diff, alert_diff):
        subject = '[xman][alert][{}] position abs diff {:.3f} < {:.3f}'.format(self._context, pos_diff, alert_diff)
        body = '{}: {}\n live position: {}\n sim position: {}\n diff {} > {}'.format(ts, self._context, self._live_pos, self._sim_pos, abs(pos_diff), abs(alert_diff))
        self._send_email(self._email_recipients, subject, body)

    def email_position_pct_mismatch_alert(self, ts, pos_diff, alert_diff):
        subject = '[xman][alert][{}] position pct diff {:.1f}% < {:.1f}%'.format(self._context, pos_diff * 100, alert_diff * 100)
        body = '{}: {}\n live position: {}\n sim position: {}\n max position: {}\n diff {} > {}'.format(ts, self._context, self._live_pos, self._sim_pos, self._max_position, abs(pos_diff), abs(alert_diff))
        self._send_email(self._email_recipients, subject, body)

# changeling_alert = context_alert(context = 'changeling')
# while 1:
#     changeling_alert.update()
#     print(changeling_alert.live_net)
#     print(changeling_alert.sim_net)
#     print(changeling_alert.live_position)
#     print(changeling_alert.sim_position)
#     print(changeling_alert.price)
#     print(changeling_alert.symbol)
#     print('...............')
#     time.sleep(30)

def format_float(x):
    if not isinstance(x, int) and not isinstance(x, float):
        return x
    if abs(x) < 1:
        return '{0:.3f}'.format(x)
    if abs(x) < 10:
        return '{0:.2f}'.format(x)
    if abs(x) < 100:
        return '{0:.1f}'.format(x)
    return '{0:.0f}'.format(x)

class portfolio_alert:
    def __init__(self, config_folder):
        self.portfolio_config = outright_portfolio_config(config_folder)
        self.context_configs = self.portfolio_config.context_configs
        self.contexts = self.portfolio_config.contexts
        self.context_alerts = {}
        for cc in self.context_configs:
            self.context_alerts[cc.context] = context_alert(config = cc)
        self.portfolio_perf_df = pd.DataFrame(columns = ['net', 'position', 'price', 'symbol'], index = self.contexts)
        # self._last_update_ts = None
        self._refresh_rate = dt.timedelta(seconds = 10)

    def update(self):
        for ctx, alt in self.context_alerts.items():
            updated = alt.update()
            if updated:
                self.portfolio_perf_df.loc[ctx] = [alt.live_net, alt.live_position, alt.price, alt.symbol]

    def display(self):
        print(self.portfolio_perf_df.dropna().applymap(format_float).sort_values(by = ['symbol', 'position']))

    def run(self):
        while 1:
            # utcnow = dt.datetime.utcnow()
            # if self._last_update_ts is None or utcnow - self._last_update_ts >= self._refresh_rate:
            self.update()
            self.display()
            time.sleep(self._refresh_rate.total_seconds())

# pa = portfolio_alert('/Users/fw/Trading/projects/xman/configuration')
# pa.run()

