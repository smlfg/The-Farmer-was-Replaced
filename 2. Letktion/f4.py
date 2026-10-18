clear()

field1=False
field2=False
field3=False
field4=False

def check_pumpkin_state():
	if get_entity_type()==Entities.Dead_Pumpkin:
		till()
		till()
def check_land_state():
	if get_ground_type()==Grounds.Grassland:
		till()
def ready_harvest():
	if can_harvest()==True:
		return True
		
def seed_pumpkin():
	if get_entity_type()!=Entities.Pumpkin:
		check_pumpkin_state()
		use_item(Items.Water)
		check_land_state()
		plant(Entities.pumpkin)

def mega_pumpkin():	
	field1=False
	field2=False
	field3=False
	field4=False
	while field1==False:
		seed_pumpkin()
		check_pumpkin_state()
		if ready_harvest():
			field1=True
			move(North)
	while field2==False:
		seed_pumpkin()
		check_pumpkin_state()
		if ready_harvest()==True:
			field2=True
			move(East)
	while field3==False:
		seed_pumpkin()
		check_pumpkin_state()
		if ready_harvest()==True:
			field3=True
			move(South)
	while field4==False:
		seed_pumpkin()
		check_pumpkin_state()
		if ready_harvest()==True:
			field4=True
			move(West)
	harvest()

def moving_cycle():
	for i in range(3):
		seed_pumpkin()
		move(North)
	seed_pumpkin()
	move(East)
	for i in range(3):
		seed_pumpkin()
		move(South)
	seed_pumpkin()
	move(East)
	
	seed_pumpkin()
	move(West)
	mega_pumpkin()
		
while True:
	moving_cycle()

			

		
