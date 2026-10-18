
def is_checker():
	return (get_pos_x() + get_pos_y()) % 2 == 0

def do_checker():
	if get_entity_type() == Entities.Dead_Pumpkin:
		till()
		till()
		use_item(Items.Water)
	if is_checker() and get_ground_type() == Grounds.Grassland:
		till()
		plant(Entities.Pumpkin)

world = get_world_size()

def plant_pass():
	for i in range(world):
		move(North)
		if get_pos_y() % 2 == 0:          # gerade Reihe -> nach Osten
			do_checker()
		else:                             # ungerade Reihe -> nach Osten, dann zurück
			move(East)
			do_checker()
			move(West)
		move(East)
		