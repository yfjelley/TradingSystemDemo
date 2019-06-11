import numpy as np

class multileg_account:
	def __init__(self, context):
		self.context = context
		self.accounts = [leg_account(x) for x in self.context.cmx_config.catalyst_symbols]
		self.positions = [np.nan] * self.context.cmx_config.leg_num
		self.prices = [np.nan] * self.context.cmx_config.leg_num
		self.available_balances = {}
		self.total_balances = {}
		self.portfolio_position = np.nan
		self.portfolio_value = np.nan

	def update(self, data):
		self.available_balances = {}
		self.total_balances = {}
		self.portfolio_value = 0
		for i in range(self.context.cmx_config.leg_num):
			self.accounts[i].update(data)
			self.poitions[i] = self.accounts[i].position
			self.prices[i] = self.accounts[i].price
			self.available_balances.update(self.accounts[i].available_balances)
			self.total_balances.update(self.accounts[i].total_balances)
			self.portfolio_value += self.accounts[i].value
		self.portfolio_position = self.accounts[0].position

class leg_account:
	def __init__(self, asset):
		self.asset = asset
		self.base_currency  = self.asset.symbol.split('_')[0]
		self.quote_currency = self.asset.symbol.split('_')[1]
		self.available_balances = {}
		self.total_balances = {}
		self.value = 0
		self.position = 0
		self.price = np.nan

	def _update_balances(self):
		balances = self.asset.exchange.get_balances()
		
		free_base  = balances[self.base_currency]['free']
		free_quote = balances[self.quote_currency]['free']
		self.available_balances = {self.base_currency: free_base, \
								   self.quote_currency: free_quote}

		total_base  = balances[self.base_currency]['total']
		total_quote = balances[self.quote_currency]['total']
		self.total_balances = {self.base_currency: total_base, \
							   self.quote_currency: total_quote}

	def _update_value(self, data):
		base_pos = self.total_balances[self.base_currency]
		quote_pos = self.total_balances[self.quote_currency]
		price = data.current(self.asset, 'price')
		base_value = base_pos * price
		self.value = base_value + quote_pos
		return self.value

	def update(self, data):
		self._update_balances()
		self.position = self.available_balances[self.base_currency]
		self._update_value(data)

class outright_account:
	def __init__(self, context):
		self.context = context

		self.base_currency  = self.context.symbol_str.split('_')[0]
		self.quote_currency = self.context.symbol_str.split('_')[1]
		
		self.available_balances = {}
		self.total_balances = {}
		self.value = 0
		self.position = 0
		self.price = np.nan

	def _update_balances(self):
		balances = self.context.exchange.get_balances()
		
		free_base  = balances[self.base_currency]['free']
		free_quote = balances[self.quote_currency]['free']
		self.available_balances = {self.base_currency: free_base, \
								   self.quote_currency: free_quote}

		total_base  = balances[self.base_currency]['total']
		total_quote = balances[self.quote_currency]['total']
		self.total_balances = {self.base_currency: total_base, \
							   self.quote_currency: total_quote}

	def _update_value(self, data):
		base_pos = self.total_balances[self.base_currency]
		quote_pos = self.total_balances[self.quote_currency]
		price = data.current(self.context.asset, 'price')
		base_value = base_pos * price
		self.value = base_value + quote_pos
		return self.value

	def update(self, data):
		self._update_balances()
		self.position = self.available_balances[self.base_currency]
		self._update_value(data)
		self.context.cmx_logger.log_acct_info()


