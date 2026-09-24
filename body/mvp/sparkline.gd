extends Control
var samples: Array[float] = []
var accent := Color("79b8aa")
func push(value: float) -> void:
	samples.append(value)
	if samples.size() > 120: samples.pop_front()
	queue_redraw()
func _draw() -> void:
	draw_line(Vector2(0,size.y-1),Vector2(size.x,size.y-1),Color("343a40"),1)
	if samples.size()<2:return
	var peak := maxf(1.,samples.max())
	var points := PackedVector2Array()
	for i in range(samples.size()):
		points.append(Vector2(float(i)/119.0*size.x,size.y-3-samples[i]/peak*(size.y-6)))
	draw_polyline(points,accent,2,true)
