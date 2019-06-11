import random
import numpy as np
import datetime as dt
import os
import time


def join_path(folder, file):
    if folder is None:
        return file
    if not os.path.exists(folder):
        os.makedirs(folder)
    return os.path.join(folder, file)

def get_log_level(level_str):
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

def get_pickle_file(comics_config):
    file_prefix = get_file_prefix(comics_config)
    file = '{}.pickle'.format(file_prefix)
    return join_path(comics_config['record_path'], file)


def get_file_prefix(comics_config):
    file_prefix = '{}_{}_{}_{}_{}'.format(
                                       comics_config['global_namespace'],
                                       comics_config['global_instance'],
                                       comics_config['global_mode'],
                                       int(time.mktime(dt.datetime.utcnow().timetuple())),
                                       random.randint(1001,10000),
                                       )
    return file_prefix

def round_position(p0, p1):
    if p1 == 0:
        return p0
    return np.floor(p0 / p1) * p1 if p0 > 0 else -(np.floor(-p0 / p1) * p1)