import numpy as np
from collections import deque
import logging


class sma:
    def __init__(self, window, minsd = -1, need_full_window = True):
        self.window = window
        self.minsd  = minsd
        self.need_full_window = need_full_window
        self.buffer = deque()
        self._mean  = np.nan
        self._mean2 = np.nan
        self._var   = np.nan
        self._std   = np.nan
        self._signal= np.nan
        self._ts    = None

    def update(self, data, ts = None):
        if data is None or np.isnan(data):
            return False
        if len(self.buffer) < self.window:
            if len(self.buffer) == 0:
                self._mean  = data
                self._mean2 = data * data
                self._signal  = data
                self._ts    = ts
                self.buffer.append(data)
                return True
            else:
                self._mean  = (self._mean * len(self.buffer) + data) / (len(self.buffer) + 1)
                self._mean2 = (self._mean2 * len(self.buffer) + data * data) / (len(self.buffer) + 1)
        else:
            head = self.buffer.popleft()
            self._mean  = (self._mean * self.window + data - head) / self.window
            self._mean2 = (self._mean2 * self.window + data * data - head * head) / self.window
        self._var  = self._mean2 - self._mean * self._mean
        self._std  = np.sqrt(self._var) if self._var >= 0 else np.nan
        self._std  = max(self.minsd, self._std)
        self._signal = data
        self._ts   = ts
        self.buffer.append(data)
        return True

    def flush(self, data_series):
        local_data = data_series.iloc[-self.window:]
        self.__init__(self.window, self.minsd, self.need_full_window)
        for i in range(len(local_data)):
            ts = local_data.index[i]
            data = local_data[i]
            self.update(data, ts)

    @property
    def mean(self):
        if len(self.buffer) < self.window and self.need_full_window:
            return np.nan
        return self._mean
    
    @property
    def std(self):
        if len(self.buffer) < self.window and self.need_full_window:
            return np.nan
        return self._std

    @property
    def zscore(self):
        if len(self.buffer) < self.window and self.need_full_window:
            return np.nan
        return (self._signal - self._mean) / self._std

    @property
    def ts(self):
        return self._ts

    @property
    def signal(self):
        return self._signal

# my_sma = sma(3)
# my_sma.update(1)
# print(my_sma.get_mean(), my_sma.mean)
# print(my_sma.get_std(), my_sma.std)
# my_sma.update(2)
# print(my_sma.get_mean(), my_sma.mean)
# print(my_sma.get_std(), my_sma.std)
# my_sma.update(3)
# print(my_sma.get_mean(), my_sma.mean)
# print(my_sma.get_std(), my_sma.std)
# my_sma.update(4)
# print(my_sma.get_mean(), my_sma.mean)
# print(my_sma.get_std(), my_sma.std)
# my_sma.update(14)
# print(my_sma.get_mean(), my_sma.mean)
# print(my_sma.get_std(), my_sma.std)