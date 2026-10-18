def 
	move(North)
	for i in range(get_world_size()):
		move(East)
		harvest()
		plant(Entities.Bush)
	if get_pos_x()==0:
		break
		move(North)