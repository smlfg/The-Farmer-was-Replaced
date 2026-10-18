world = get_world_size()

def is_checker():
	return (get_pos_x() + get_pos_y()) % 2 == 0

def do_plant_schachbrett():
	if get_entity_type() == Entities.Dead_Pumpkin:
		till()
		till()
		use_item(Items.Water)
		return
	if is_checker():
		if get_ground_type() == Grounds.Grassland:
			till()
			plant(Entities.Pumpkin)

def is_ready():
	return get_entity_type() == Entities.Pumpkin and can_harvest()

def do_check():
	return is_ready()

def planted_in_row(y):
	if y % 2 == 0:
		return (world + 1) // 2
	else:
		return world // 2

def do_check_harvest_lines():
	y = get_pos_y()
	need = planted_in_row(y)
	found = 0
	for i in range(world):
		if is_checker():
			if is_ready():
				found = found + 1
			else:
				return False
		# Schritt in Laufrichtung
		if y % 2 == 0:
			move(East)
		else:
			move(West)
	return found == need
	
def plant_pass():
	for y in range(world):
		move(North)
		for x in range(world):
			do_plant_schachbrett()
			if x < world - 1:
				if y % 2 == 0:
					move(East)
				else:
					move(West)
		# zur nächsten Reihe
		if y % 2 == 0:
			move(East)
		else:
			move(West)
			
			
			
def harvest_pass():
	for y in range(world):
		move(North)
		if do_check_harvest_lines():
			# Reihe komplett reif -> jetzt ernten
			for x in range(world):
				if is_checker() and is_ready():
					harvest()
				if x < world - 1:
					if y % 2 == 0:
						move(East)
					else:
						move(West)
			# zur nächsten Spalte
			move(East)
		else:
			# noch nicht reif, einfach weiter
			pass
			
			
			
while True:
	plant_pass()
	plant(Entities.Pumpkin)
	harvest_pass()
	
