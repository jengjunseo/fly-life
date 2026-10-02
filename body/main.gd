extends Node3D

# One body-control path: validated completed neural packet -> apply_neural_frame.
# Keyboard and the test driver ONLY enter _unhandled_key_input -> send_command.
var cfg: Dictionary
var peer := StreamPeerTCP.new()
var buffer := ""
var state: Dictionary = {}
var connection := "not running"
var started_ms := Time.get_ticks_msec()
var last_rx_ms := 0
var next_connect_ms := 0
var next_heartbeat_ms := 0
var generation := -1
var last_seq := -1
var command_number := 0
var world_time := 0.0
var expected_motor_time := 0.0
var queued_frames: Array[Dictionary] = []
var fly: CharacterBody3D
var hud: Label
var log_file: FileAccess
var logdir := ""
var debug_enabled := true
var testing := false
var test_clock := 0.0
var test_stage := -1
var test_wait_wall := 0.0
var shutdown_sent := false
var quit_after := 0.0
var screenshot_saved := false
var last_log_ms := 0

func _ready() -> void:
	cfg = JSON.parse_string(FileAccess.get_file_as_string("res://body_config.json"))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--config="):
			cfg = JSON.parse_string(FileAccess.get_file_as_string(arg.trim_prefix("--config=")))
		if arg.begins_with("--logdir="):
			logdir = arg.trim_prefix("--logdir=")
		if arg == "--integration-test":
			testing = true
		if arg.begins_with("--quit-after="):
			quit_after = float(arg.trim_prefix("--quit-after="))
	if logdir.is_empty():
		logdir = ProjectSettings.globalize_path("res://logs/latest")
	DirAccess.make_dir_recursive_absolute(logdir)
	log_file = FileAccess.open(logdir.path_join("godot.jsonl"), FileAccess.WRITE)
	debug_enabled = bool(cfg.debug.enabled)
	build_world()
	get_tree().auto_accept_quit = false
	log_row("start", {"godot_version": Engine.get_version_info(), "debug_enabled": debug_enabled})

func material(color: Color) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.roughness = 0.85
	return result

func box(parent: Node3D, size: Vector3, at: Vector3, color: Color, solid: bool) -> void:
	var mesh := MeshInstance3D.new()
	var shape := BoxMesh.new()
	shape.size = size
	mesh.mesh = shape
	mesh.material_override = material(color)
	mesh.position = at
	parent.add_child(mesh)
	if solid:
		var wall := StaticBody3D.new()
		var collision := CollisionShape3D.new()
		var bounds := BoxShape3D.new()
		bounds.size = size
		collision.shape = bounds
		wall.position = at
		wall.add_child(collision)
		parent.add_child(wall)

func sphere(parent: Node3D, at: Vector3, size: Vector3, color: Color) -> void:
	var mesh := MeshInstance3D.new()
	mesh.mesh = SphereMesh.new()
	mesh.material_override = material(color)
	mesh.position = at
	mesh.scale = size
	parent.add_child(mesh)

func build_world() -> void:
	var env := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color(0.13,0.16,0.19)
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color(0.8,0.85,1.0)
	settings.ambient_light_energy = 0.7
	env.environment = settings
	add_child(env)
	var lamp := DirectionalLight3D.new()
	lamp.rotation_degrees = Vector3(-60,-25,0)
	lamp.light_energy = 1.2
	lamp.shadow_enabled = true
	add_child(lamp)
	var half := float(cfg.arena.half_width)
	box(self,Vector3(half*2,0.2,half*2),Vector3(0,-0.1,0),Color(0.55,0.58,0.60),true)
	for z in [-half,half]:
		box(self,Vector3(half*2+0.3,0.5,0.2),Vector3(0,0.25,z),Color(0.32,0.36,0.40),true)
	for x in [-half,half]:
		box(self,Vector3(0.2,0.5,half*2),Vector3(x,0.25,0),Color(0.32,0.36,0.40),true)
	fly = CharacterBody3D.new()
	fly.name = "Fly"
	fly.position = Vector3(0,0.22,0)
	var collision := CollisionShape3D.new()
	var bounds := SphereShape3D.new()
	bounds.radius = 0.19
	collision.shape = bounds
	fly.add_child(collision)
	add_child(fly)
	sphere(fly,Vector3(0,0,0.12),Vector3(0.22,0.15,0.35),Color(0.20,0.12,0.08))
	sphere(fly,Vector3(0,0,-0.12),Vector3(0.19,0.17,0.23),Color(0.08,0.07,0.06))
	sphere(fly,Vector3(0,0.02,-0.29),Vector3(0.16,0.14,0.15),Color(0.17,0.10,0.07))
	for x in [-0.10,0.10]:
		sphere(fly,Vector3(x,0.05,-0.31),Vector3(0.08,0.08,0.06),Color(0.60,0.12,0.08))
	for x in [-0.28,0.28]:
		sphere(fly,Vector3(x,0.10,0.08),Vector3(0.30,0.025,0.30),Color(0.76,0.80,0.85))
	var camera := Camera3D.new()
	camera.position = Vector3(7,9,10)
	add_child(camera)
	camera.look_at(Vector3.ZERO)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 12.5
	camera.current = true
	var canvas := CanvasLayer.new()
	hud = Label.new()
	hud.position = Vector2(18,15)
	hud.add_theme_font_size_override("font_size",17)
	hud.add_theme_color_override("font_shadow_color",Color.BLACK)
	hud.add_theme_constant_override("shadow_offset_x",1)
	hud.add_theme_constant_override("shadow_offset_y",1)
	canvas.add_child(hud)
	add_child(canvas)

func send_command(kind: String, extra: Dictionary = {}) -> void:
	command_number += 1
	var packet := {"v":1,"kind":kind,"id":"godot-%d" % command_number}
	packet.merge(extra)
	if peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
		peer.put_data((JSON.stringify(packet)+"\n").to_utf8_buffer())
	log_row("command_sent", {"message":packet})

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	log_row("key", {"keycode":event.keycode,"stimulus_path_enabled":debug_enabled})
	match event.keycode:
		KEY_1,KEY_2,KEY_3:
			if debug_enabled:
				var group: String = {KEY_1:"left",KEY_2:"right",KEY_3:"forward"}[event.keycode]
				send_command("stimulus", {"group":group})
		KEY_4:
			send_command("clear")
		KEY_R:
			send_command("reset")
		KEY_ESCAPE:
			shutdown()

func _process(_delta: float) -> void:
	var now := Time.get_ticks_msec()
	peer.poll()
	if peer.get_status() == StreamPeerTCP.STATUS_NONE or peer.get_status() == StreamPeerTCP.STATUS_ERROR:
		if connection != "not running":
			connection = "disconnected / error"
			queued_frames.clear()
			fly.velocity = Vector3.ZERO
		if now >= next_connect_ms:
			peer.disconnect_from_host()
			peer.connect_to_host(str(cfg.host),int(cfg.port))
			connection = "starting" if last_rx_ms == 0 else "disconnected / error"
			next_connect_ms = now+1000
	if peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
		if now >= next_heartbeat_ms:
			send_command("heartbeat")
			next_heartbeat_ms = now+int(float(cfg.heartbeat_seconds)*1000)
		var available := peer.get_available_bytes()
		if available > 0:
			var result := peer.get_data(available)
			if result[0] == OK:
				buffer += result[1].get_string_from_utf8()
		if buffer.length() > 65536:
			protocol_error("oversized buffer")
		while buffer.contains("\n"):
			var end := buffer.find("\n")
			var line := buffer.left(end)
			buffer = buffer.substr(end+1)
			var packet = JSON.parse_string(line)
			if packet is Dictionary:
				accept_packet(packet)
		if last_rx_ms > 0 and now-last_rx_ms > float(cfg.disconnect_seconds)*1000:
			protocol_error("brain timeout")
	if now-last_log_ms >= 500:
		log_row("sample")
		last_log_ms = now
	update_hud()
	if quit_after > 0 and float(now-started_ms)/1000 >= quit_after:
		shutdown()

func protocol_error(reason: String) -> void:
	connection = "error: "+reason
	queued_frames.clear()
	fly.velocity = Vector3.ZERO
	peer.disconnect_from_host()
	log_row("error", {"reason":reason})

func accept_packet(packet: Dictionary) -> void:
	if int(packet.get("v",0)) != 1 or packet.get("kind") != "state":
		protocol_error("protocol version")
		return
	var gen := int(packet.generation)
	var seq := int(packet.seq)
	if seq <= last_seq:
		protocol_error("duplicate/out-of-order state")
		return
	if gen != generation:
		generation = gen
		queued_frames.clear()
		world_time = 0.0
		expected_motor_time = 0.0
		test_clock = 0.0
		# Reset is an initial-condition operation, not a movement/AI control.
		fly.position = Vector3(0,0.22,0)
		fly.rotation = Vector3.ZERO
		fly.velocity = Vector3.ZERO
		log_row("generation_reset")
	elif last_seq >= 0 and seq != last_seq+1:
		protocol_error("missing completed state")
		return
	last_seq = seq
	last_rx_ms = Time.get_ticks_msec()
	state = packet
	connection = str(packet.status)
	var dt := float(packet.dt_s)
	if connection == "ready" and dt > 0:
		if not is_equal_approx(dt,float(cfg.packet_neural_ms)/1000.0) or not is_equal_approx(float(packet.motor_time_s),expected_motor_time+dt):
			protocol_error("neural-time continuity")
			return
		if not is_finite(float(packet.forward)) or not is_finite(float(packet.turn)) or abs(float(packet.turn)) > 1 or float(packet.forward) < 0 or float(packet.forward) > 1:
			protocol_error("invalid neural motor command")
			return
		expected_motor_time = float(packet.motor_time_s)
		queued_frames.append(packet)
	elif connection != "ready":
		queued_frames.clear()
		fly.velocity = Vector3.ZERO
	log_row("packet", {"packet":packet})

func _physics_process(_delta: float) -> void:
	if connection != "ready":
		return
	while not queued_frames.is_empty():
		apply_neural_frame(queued_frames.pop_front())
	if testing:
		integration_driver()

func apply_neural_frame(packet: Dictionary) -> void:
	var neural_dt := float(packet.dt_s)
	move_body(packet,neural_dt)
	world_time += neural_dt
	test_clock = float(packet.motor_time_s)
	log_row("body_commit", {"source_seq":packet.seq,"source_activity_hz":packet.activity_hz,
		"decoder_forward":packet.forward,"decoder_turn":packet.turn,"neural_dt_s":neural_dt,
		"escape_motor":packet.get("escape_motor",0.)})

func move_body(packet: Dictionary, neural_dt: float) -> void:
	var turn_rate := float(packet.turn)*float(cfg.body.max_turn_radians_per_neural_second)
	# Positive decoder turn means RIGHT; Godot positive Y yaw means LEFT.
	fly.rotation.y -= turn_rate*neural_dt
	fly.velocity = -fly.transform.basis.z*float(packet.forward)*float(cfg.body.max_forward_units_per_neural_second)
	fly.move_and_collide(fly.velocity*neural_dt)

func update_hud() -> void:
	var activity: Dictionary = state.get("activity_hz",{})
	var wall := float(Time.get_ticks_msec()-started_ms)/1000
	var neural := float(state.get("neural_time_s",0))
	hud.text = "MaleCNS v1.0 | one primitive body\nBRAIN: %s\n\nWall      %7.2f s\nNeural    %7.2f s (warm-up included)\nWorld     %7.2f s (completed motor time)\nRatio     %7.3fx\nFPS       %7.1f\n\nForward   %7.3f  (DNp09 experimental)\nLeft      %7.2f Hz\nRight     %7.2f Hz\nTurn      %+7.3f (right positive)\nPop       %7.3f Hz/neuron\nStimulus: %s\n\n1 left neural current | 2 right neural current\n3 DNp09 current | 4 clear | R reset | Esc quit\nNo direct keyboard movement; slow neural-time world" % [connection.to_upper(),wall,neural,world_time,neural/max(wall,0.001),Engine.get_frames_per_second(),state.get("forward",0.0),activity.get("left",0.0),activity.get("right",0.0),state.get("turn",0.0),state.get("population_hz",0.0),state.get("stimulus","none")]

func log_row(event: String, extra: Dictionary = {}) -> void:
	if log_file == null:
		return
	var row := {"event":event,"wall_time_s":float(Time.get_ticks_msec()-started_ms)/1000,
		"neural_time_s":state.get("neural_time_s",0),"world_time_s":world_time,
		"generation":generation,"connection":connection,"position":[fly.position.x,fly.position.y,fly.position.z] if fly else [0,0,0],
		"heading_yaw_radians":fly.rotation.y if fly else 0,"fps":Engine.get_frames_per_second()}
	row.merge(extra)
	log_file.store_line(JSON.stringify(row))
	log_file.flush()

func test_key(key: Key) -> void:
	# Same InputEventKey boundary as a real keyboard; never invokes body functions.
	var event := InputEventKey.new()
	event.keycode = key
	event.pressed = true
	Input.parse_input_event(event)
	event = InputEventKey.new()
	event.keycode = key
	event.pressed = false
	Input.parse_input_event(event)

func integration_driver() -> void:
	# Test-only schedule. Commands remain neural-current messages through the real bridge.
	if test_stage == -1 and test_clock >= 0.2:
		test_stage = 0
		log_row("test_left_start")
		test_key(KEY_1)
	elif test_stage == 0 and test_clock >= 0.9:
		test_stage = 1
		log_row("test_right_start")
		test_key(KEY_2)
	elif test_stage == 1 and test_clock >= 1.6:
		test_stage = 2
		log_row("test_forward_start")
		test_key(KEY_3)
	elif test_stage == 2 and test_clock >= 2.3:
		test_stage = 3
		test_wait_wall = float(Time.get_ticks_msec())/1000
		log_row("test_reset_one")
		test_key(KEY_R)
	elif test_stage == 3 and test_clock >= 0.2 and float(Time.get_ticks_msec())/1000-test_wait_wall > 2:
		test_stage = 4
		debug_enabled = false
		log_row("test_disabled_key")
		test_key(KEY_1)
	elif test_stage == 4 and test_clock >= 0.4:
		test_stage = 5
		test_wait_wall = float(Time.get_ticks_msec())/1000
		log_row("test_reset_two")
		test_key(KEY_R)
	elif test_stage == 5 and test_clock >= 0.4 and float(Time.get_ticks_msec())/1000-test_wait_wall > 2:
		test_stage = 6
		debug_enabled = true
		log_row("test_suite_ready_for_disconnect")
	if test_stage >= 2 and not screenshot_saved:
		screenshot_saved = true
		capture_frame.call_deferred()

func capture_frame() -> void:
	await RenderingServer.frame_post_draw
	if DisplayServer.get_name() != "headless":
		get_viewport().get_texture().get_image().save_png(logdir.path_join("arena.png"))

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		shutdown()

func shutdown() -> void:
	if not shutdown_sent:
		shutdown_sent = true
		send_command("shutdown")
		log_row("quit")
		if log_file:
			log_file.close()
	peer.disconnect_from_host()
	get_tree().quit()
