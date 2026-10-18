def is_ready():
	return get_entity_type() == Entities.Pumpkin and can_harvest()
	# alternativ: get_entity_type() == Entities.Pumpkin and get_entity_age() >= MAX_AGE

def planted_per_row(y):
	# wie viele Schachfelder hat die Reihe
	return (world + 1)//2 if y % 2 == 0 else world//2

def check_and_harvest_row():
	y = get_pos_y()
	need = planted_per_row(y)
	ready = 0

	# gerade Überflug, keine West-Rückkehr
	for _ in range(world):
		if is_checker():
			if is_ready():
				ready += 1
			else:
				return False          # Reihe noch nicht komplett
		# Schritt in Laufrichtung
		if get_pos_y() % 2 == 0:
			move(East)
		else:
			move(West)

	return ready == need

while True:
	# 1. Feld komplett bepflanzt? -> Harvest Mode
	# Starte links unten
	# ...

	# geradzahlige Überflüge zum Checken
	for row in range(world):
		move(North)
		if check_and_harvest_row():
			# Reihe ist komplett reif -> jetzt erst ernten
			# nochmal drüber und wirklich ernten
			y = get_pos_y()
			for _ in range(world):
				if is_checker() and is_ready():
					harvest()
				if get_pos_y() % 2 == 0:
					move(East)
				else:
					move(West)
			move(East)   # erst jetzt zur nächsten Spalte
		else:
			# nicht komplett -> nur wässern / warten
			pass
			