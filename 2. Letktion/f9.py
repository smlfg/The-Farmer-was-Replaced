world = get_world_size()

def is_checker():
	return (get_pos_x() + get_pos_y()) % 2 == 0

def maintain():
	if get_entity_type() == Entities.Dead_Pumpkin:
		till()
		till()
		use_item(Items.Water)
	if is_checker() and get_ground_type() == Grounds.Grassland:
		till()
		plant(Entities.Pumpkin)

def plant_all():
	# Schlangenlinie, genau wie du es hattest
	for y in range(world):
		move(North)
		# Richtung je nach Reihe
		step = East if y % 2 == 0 else West
		for x in range(world):
			maintain()
			if x < world - 1:
				move(step)
		move(East)   # zur nächsten Reihe
		