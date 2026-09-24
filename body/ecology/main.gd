extends "res://main.gd"

# The original apply_neural_frame is the only movement path, inherited unchanged.
# This script displays world state and ACKs actual body pose for next sensory input.
var eco: Dictionary = {}
var meshes: Dictionary = {}
var last_ecology: Dictionary = {}
var life_run := false
var replay_test := false
var ecology_test_stage := 0
var test_duration := 0.0

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--ecology-config="):
			eco = JSON.parse_string(FileAccess.get_file_as_string(arg.trim_prefix("--ecology-config=")))
		if arg == "--life-run": life_run = true
		if arg == "--replay-test": replay_test = true
		if arg.begins_with("--duration="): test_duration = float(arg.trim_prefix("--duration="))
	super._ready()
	box(self,Vector3(float(eco.shade.half_size[0])*2,0.015,float(eco.shade.half_size[2])*2),
		Vector3(float(eco.shade.center[0]),0.015,float(eco.shade.center[2])),Color(0.22,0.38,0.40),false)
	log_row("ecology_start",{"mode":eco.mode,"world_seed":eco.world_seed,"life_run":life_run,"replay_test":replay_test})

func acknowledge_body(packet: Dictionary) -> void:
	send_command("body_snapshot",{"generation":generation,"source_seq":packet.seq,"motor_time_s":packet.motor_time_s,
		"position":[fly.position.x,fly.position.y,fly.position.z],"yaw":fly.rotation.y})

func accept_packet(packet: Dictionary) -> void:
	super.accept_packet(packet)
	if connection == "ready" and packet.has("ecology"):
		last_ecology = packet.ecology
		display_entities(packet.ecology.world.entities)
		if float(packet.dt_s) == 0.0:
			acknowledge_body(packet)

func apply_neural_frame(packet: Dictionary) -> void:
	# HP=0 is an explicitly allowed physiological death stop, not an avoidance rule.
	if float(packet.ecology.world.hp) <= 0.0:
		var stopped := packet.duplicate(true)
		stopped.forward = 0.0
		stopped.turn = 0.0
		super.apply_neural_frame(stopped)
		log_row("death_stop",{"source_seq":packet.seq})
	else:
		super.apply_neural_frame(packet)
	acknowledge_body(packet)
	if life_run and not screenshot_saved and world_time >= 1.0:
		screenshot_saved = true
		capture_ecology.call_deferred()
	if replay_test:
		if ecology_test_stage < 2 and world_time+0.000001 >= test_duration:
			ecology_test_stage += 1
			log_row("ecology_reset_test",{"round":ecology_test_stage})
			send_command("reset")
		elif ecology_test_stage == 2 and world_time+0.000001 >= test_duration:
			ecology_test_stage = 3
			log_row("ecology_ready_for_failure")
			capture_frame.call_deferred()
	elif life_run and test_duration > 0.0 and world_time+0.000001 >= test_duration:
		log_row("life_run_complete")
		capture_and_quit.call_deferred()

func display_entities(entities: Array) -> void:
	var seen := {}
	for entity in entities:
		var ident: String = entity.id
		seen[ident] = true
		if not meshes.has(ident):
			var parent := Node3D.new()
			add_child(parent)
			var color: Color = {"food":Color(0.18,0.65,0.22),"predator":Color(0.65,0.08,0.1),"female":Color(0.7,0.4,0.65),"feces":Color(0.25,0.13,0.07)}[entity.kind]
			var r := float(entity.radius)*2.0
			sphere(parent,Vector3.ZERO,Vector3(r,r,r),color)
			if entity.kind == "female":
				for x in [-0.2,0.2]:
					sphere(parent,Vector3(x,0.08,0.05),Vector3(0.25,0.03,0.3),Color(0.85,0.80,0.90))
			meshes[ident] = parent
		meshes[ident].position = Vector3(float(entity.position[0]),float(entity.position[1]),float(entity.position[2]))
	for ident in meshes.keys():
		if not seen.has(ident):
			meshes[ident].queue_free()
			meshes.erase(ident)

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo: return
	var events := {KEY_F:"food",KEY_P:"predator",KEY_M:"female",KEY_H:"heat",KEY_D:"defecation"}
	if events.has(event.keycode):
		log_row("world_event_key",{"keycode":event.keycode})
		send_command("world_event",{"event":events[event.keycode]})
	else:
		super._unhandled_key_input(event)

func update_hud() -> void:
	if last_ecology.is_empty():
		super.update_hud()
		return
	var w: Dictionary = last_ecology.world
	var activity: Dictionary = state.get("activity_hz",{})
	var wall := float(Time.get_ticks_msec()-started_ms)/1000.0
	var neural := float(state.get("neural_time_s",0.0))
	var currents := ""
	for term in last_ecology.sensory_terms:
		currents += "%s %.2f | " % [term.modality,term.amplitude]
	hud.add_theme_font_size_override("font_size",14)
	hud.text = "MaleCNS ecology | %s | world seed %d | brain seed %d\nBrain %s | FPS %.0f\nWall %.2fs | Neural %.2fs | World %.2fs | %.3fx\nForward %.3f | Left %.2f Hz | Right %.2f Hz | Turn %+.3f\nHP %.1f | Hunger %.2f | Gut %.2f\nLocal %.2f C | Shade %s | Distances %s\n\nCurrent %s\nFdg %.2f Hz | pC1-family %.2f Hz (observation only)\n\nMapping identity VERIFIED | encoder/decoder EXPERIMENTAL\nLC9 FIGURE-MOTION experiment, not escape reconstruction\nTaste CNS SUGAR-SEL PN BYPASS | no guaranteed avoidance\nIngestion / pain / contact pheromone DISABLED_UNRESOLVED\nDefecation PHYSIOLOGY_PLACEHOLDER\n\nF food | P predator | M female | H heat | D placeholder gut load\nR reset | Esc quit | neural debug keys enabled: %s\nOnly completed-body ACK advances world; keyboard-free life run" % [eco.mode,int(eco.world_seed),int(cfg.seed),connection,Engine.get_frames_per_second(),wall,neural,world_time,neural/max(wall,.001),state.get("forward",0),activity.get("left",0),activity.get("right",0),state.get("turn",0),w.hp,w.hunger,w.gut,w.local_temperature_c,str(w.in_shade),JSON.stringify(w.distances),currents,last_ecology.readouts_hz.get("feeding_observation",0),last_ecology.readouts_hz.get("courtship_observation",0),str(debug_enabled)]

func capture_and_quit() -> void:
	await capture_frame()
	shutdown()

func capture_ecology() -> void:
	await RenderingServer.frame_post_draw
	if DisplayServer.get_name() != "headless":
		get_viewport().get_texture().get_image().save_png(logdir.path_join("ecology.png"))
