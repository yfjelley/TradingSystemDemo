


def is_almost_equal(p0, p1, allowed_err):
	# assert allowed_err >= 0, 'allowed_err < 0!'
	if p0 == 0 and p1 == 0:
		return True
	if abs(p0 - p1) < allowed_err:
		return True
	return False

def is_not_larger(p0, p1, allowed_err):
	# assert allowed_err >= 0, 'allowed_err < 0!'
	return p0 - allowed_err <= p1

def is_not_smaller(p0, p1, allowed_err):
	# assert allowed_err >= 0, 'allowed_err < 0!'
	return p0 + allowed_err >= p1