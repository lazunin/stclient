def ien(st, sym, n):
	if len(st) < n: return st
	return st[:n] + sym + ien(st[n:], sym, n)

def compulsory_split(st, sym, n):
	lst = st.split(" ")
	lst = [ (x if len(x)<=n else ien(x, sym, n)) for x in lst ]
	return " ".join(lst)