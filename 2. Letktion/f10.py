def is_ready():
	e = get_entity_type()
	# Ripe Pumpkin / can_harvest() je nach API
	return e == Entities.Pumpkin and can_harvest()  # oder get_entity_age() >= MAX_AGE

def harvest_cell():
	if is_ready():
		harvest()
		return True
	return False

def maintain_cell():
	if get_entity_type() == Entities.Dead_Pumpkin:
		till()
		till()
		use_item(Items.Water)
	if get_ground_type() == Grounds.Grassland:
		till()
		plant(Entities.Pumpkin)
		

world = get_world_size()
total = world * world

def scan_field():
	ready = 0
	for i in range(world):
		move(North)
		if get_pos_y() % 2 == 0:
			if is_ready():
				ready += 1
			else:
				maintain_cell()
		else:
			move(East)
			if is_ready():
				ready += 1
			else:
				maintain_cell()
			move(West)
		move(East)
	return ready

def harvest_field():
	for i in range(world):
		move(North)
		if get_pos_y() % 2 == 0:
			harvest_cell()
		else:
			move(East)
			harvest_cell()
			move(West)
		move(East)

while True:
	ready = scan_field()
	if ready == total:
		# erst wenn wirklich jedes Feld reif ist -> Bonus sicher
		harvest_field()
		# neu anpflanzen
		for i in range(world):
			move(North)
			if get_pos_y() % 2 == 0:
				maintain_cell()
			else:
				move(East)
				maintain_cell()
				move(West)
			move(East)
	else:
		# noch nicht komplett -> nur pflegen / wässern
		pass
		