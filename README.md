# TradingSystemDemo

## Introduction
This repo demonstrates a crypto trading system built on top of [Catalyst](https://enigma.co/catalyst/), [CryptoCompare](https://min-api.cryptocompare.com/), and [CCXT](https://github.com/ccxt/ccxt). This is a simplified version of my trading system. Performance is not guaranteed.

## Features
- **Backtesting**: supports backtesting using OHLCV data at any time frame;
- **Live Trading**: supports live trading across 100+ crypto exchanges;
- **Third Party Data**: digests news, social media posts, coins fundamental data;
- **EOD Reports**: EOD, monthly, and quarterly reporting system;
- **Alerts**: send out alerts (text msg and email) based on PnL, positions, or disconnection. 

---

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [System Diagram](#system-diagram)
- [Github Repo](#github-repo)
- [GCP Server](#gcp-server)
- [UI on Linux](#ui-on-linux)
- [Trading on Binance](#trading-on-binance)

---

## Installation
- Python: [Conda Installation Documentation](http://conda.pydata.org/docs/download.html)
- Catalyst: [Catalyst Installation](https://enigma.co/catalyst/install.html)
- CCXT: [CCXT Installation](https://github.com/ccxt/ccxt#install)
- Python library: `pip install -r requirements.txt`

## System Diagram
![trading_system_diagram](https://github.com/FWangTrading/TradingSystemDemo/blob/master/img/trading_system_diagram.png)

## Github Repo
- The repo is a proprietary asset of Superluminance Investment. The following screenshots are for demonstrating purpose only.
![git_repo_comics_project](https://github.com/FWangTrading/TradingSystemDemo/blob/master/img/project_git.png)

## GCP Server
### Trading System runs on GCP computer engine

![gcp_com_eng](https://github.com/FWangTrading/TradingSystemDemo/blob/master/img/gcp_com_eng.png)

### UI on Linux (tmux)

![xman_gcp](https://github.com/FWangTrading/TradingSystemDemo/blob/master/img/ui_on_linux.gif)

## Trading on Binance
![binance_order](https://github.com/FWangTrading/TradingSystemDemo/blob/master/img/binance_order.gif)
