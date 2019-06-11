import psutil

def get_cpu_pct():
	return psutil.cpu_percent()

def get_ram_pct():
	return psutil.virtual_memory().percent