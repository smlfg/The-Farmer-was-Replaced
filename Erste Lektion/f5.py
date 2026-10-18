def water_mid():
	x = get_pos_x()
	y = get_pos_y()
	z = get_world_size()
	
	if z // x  == 1 and y // y == 1:
		use_item(Items.Water)