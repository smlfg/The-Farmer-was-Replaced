def saat():
		if get_ground_type() == Grounds.Grassland:
			till()
		plant(Entities.Pumpkin)

def check():
	if get_entity_type() == Entities.Dead_Pumpkin:
		till()
		till()
		use_item(Items.Water)
		use_item(Items.Fertilizer)
		plant(Entities.Pumpkin)
			
		return True

while True:
	if can_harvest():
		harvest()

	for k in range(get_world_size()):
		move(East)
		for i in range(get_world_size()):
			move(North)
			saat()
	
		for i in range(get_world_size()):
			check()
			move(West)
		for i in range(get_world_size()):
			check()
			move(North)
		move(East)

	

		