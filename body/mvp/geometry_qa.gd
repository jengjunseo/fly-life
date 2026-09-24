extends "res://main.gd"
var result_path := ""
func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--config="):cfg=JSON.parse_string(FileAccess.get_file_as_string(arg.trim_prefix("--config=")))
		if arg.begins_with("--out="):result_path=arg.trim_prefix("--out=")
	build_world()
	await get_tree().physics_frame
	await get_tree().physics_frame
	var space := get_world_3d().direct_space_state
	var expected := float(cfg.arena.half_width)-.1
	var results := []
	var passed := true
	for direction in [Vector3.RIGHT,Vector3.LEFT,Vector3.FORWARD,Vector3.BACK]:
		var query := PhysicsRayQueryParameters3D.create(Vector3(0,.25,0),direction*20+Vector3(0,.25,0))
		query.exclude=[fly.get_rid()]
		var hit := space.intersect_ray(query)
		var ok := not hit.is_empty()
		if ok:ok=absf(Vector2(hit.position.x,hit.position.z).length()-expected)<.0001
		passed=passed and ok
		results.append({"direction":[direction.x,direction.z],"inner_face_distance":Vector2(hit.position.x,hit.position.z).length() if not hit.is_empty() else -1,"passed":ok})
	var probe := PhysicsShapeQueryParameters3D.new();probe.shape=SphereShape3D.new();probe.shape.radius=.19;probe.exclude=[fly.get_rid()]
	probe.transform=Transform3D(Basis.IDENTITY,Vector3(expected-.19-.01,.25,0))
	var inside := space.intersect_shape(probe).is_empty()
	probe.transform=Transform3D(Basis.IDENTITY,Vector3(expected-.19+.01,.25,0))
	var outside := not space.intersect_shape(probe).is_empty()
	passed=passed and inside and outside
	var f := FileAccess.open(result_path,FileAccess.WRITE)
	f.store_string(JSON.stringify({"passed":passed,"wall_rays":results,"fly_sphere_inside_clear":inside,"fly_sphere_boundary_collision":outside,"note":"Separate geometry fixture uses unchanged production build_world; no focal fly motion controller added."},"  "));f.close()
	get_tree().quit(0 if passed else 1)
func _process(_delta: float) -> void:pass
func _physics_process(_delta: float) -> void:pass
