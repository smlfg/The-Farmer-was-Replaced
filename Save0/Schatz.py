
import Boden

def suche():
	if can_move(East):
		move(East)
		Boden.Ernte()
	if can_move(South):
		move(South)
		Boden.Ernte()
	if can_move(West):
		move(West)
		Boden.Ernte()
	if can_move(North):
		move(North)
		Boden.Ernte()
	