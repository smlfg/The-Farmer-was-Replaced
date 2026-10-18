def full_grass_if_till():
	move(East)
	for i in range(get_world_size()):
		harvest()
		plant(Entities.Grass)
		move(North)
		
def full_grass_if_Gras():	
	move(East)
	for i in range(get_world_size()):
		harvest()
		move(North)