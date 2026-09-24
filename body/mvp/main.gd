extends "res://ecology/main.gd"

const Spark = preload("res://mvp/sparkline.gd")
const PRESETS = ["CONTROL","PREDATOR","FOOD","FEMALE","HEAT","PREDATOR + HEAT"]
const GROUPS = [["lc4","LC4","Looming input"],["lplc2","LPLC2","Expansion-gated size"],["GF","GF / DNp01","Downstream • no escape decoder"],["DNa01","DNa01","Experimental steering readout"],["DNa02","DNa02","Experimental steering readout"],["DNp09","DNp09","Experimental forward readout"]]
const EXTRA_GROUPS = [["figure","LC9"],["food_odor","ORN DM1"],["taste","Sugar SEL PN · CNS bypass"],["fly_odor","ORN VA1v / VA1d"],["hot","TRN VP2 · heat"],["cold","TRN VP3 · cooling"],["feeding_observation","Fdg · gate UNRESOLVED"],["courtship_observation","pC1 family · observation"]]
var panel_root: Control
var view: SubViewport
var world_root: Node3D
var world_camera: Camera3D
var status_label: Label
var clocks_label: Label
var health_label: Label
var physiology_label: Label
var motor_label: Label
var config_label: Label
var stimulus_label: Label
var event_text: RichTextLabel
var preset_select: OptionButton
var world_seed: SpinBox
var brain_seed: SpinBox
var temp_control: SpinBox
var shade_control: CheckBox
var circuit_labels: Dictionary = {}
var charts: Dictionary = {}
var extra_labels: Dictionary = {}
var ui_next_ms := 0
var observer_seq := -1
var observer_generation := -1
var ui_total_us := 0
var ui_updates := 0
var ui_max_us := 0
var last_event_signature := ""
var console_state: Dictionary = {}
var controls: Array[BaseButton] = []
var qa_controls := false
var qa_stage := 0
var qa_at := 0
var qa_world := 0.0
var camera_follow := false
var pending_command_id := ""
var generation_started_ms := 0
var shade_mesh: MeshInstance3D

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--qa-controls":qa_controls=true
	super._ready()
	hud.hide()
	get_window().title = "MaleCNS • Experiment Console • MVP v0.1"
	get_window().content_scale_size = Vector2i.ZERO
	Engine.max_fps=60
	build_console()
	log_row("console_display",{"window_size":[get_window().size.x,get_window().size.y],"screen_size":[DisplayServer.screen_get_size().x,DisplayServer.screen_get_size().y],"mode":DisplayServer.window_get_mode(),"viewport_size":[view.size.x,view.size.y]})

func skin(color: Color, border: Color = Color("343a40")) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color=color;s.border_color=border
	s.set_border_width_all(1);s.set_corner_radius_all(8)
	s.content_margin_left=18;s.content_margin_right=18;s.content_margin_top=14;s.content_margin_bottom=14
	return s

func label(parent: Node, text: String, font_size: int = 23, color: Color = Color("e4e7eb")) -> Label:
	var l := Label.new();l.text=text
	l.add_theme_font_size_override("font_size",font_size);l.add_theme_color_override("font_color",color)
	if font_size>=24:
		var mono := SystemFont.new();mono.font_names=PackedStringArray(["Consolas"]);l.add_theme_font_override("font",mono)
	parent.add_child(l);return l

func card(parent: Node, title: String) -> VBoxContainer:
	var panel := PanelContainer.new();panel.add_theme_stylebox_override("panel",skin(Color("191e24")))
	parent.add_child(panel)
	var col := VBoxContainer.new();col.add_theme_constant_override("separation",12);panel.add_child(col)
	if not title.is_empty():label(col,title,21,Color("9ba7b5"))
	return col

func button(parent: Node, text: String, action: Callable, hint: String = "") -> Button:
	var b := Button.new();b.text=text;b.tooltip_text=hint;b.custom_minimum_size.y=54
	b.pressed.connect(action);parent.add_child(b);controls.append(b);return b

func command(kind: String, extra: Dictionary = {}) -> void:
	send_command(kind,extra)
	pending_command_id="godot-%d" % command_number
	config_label.text="Command queued • applies at completed quantum boundary"

func build_console() -> void:
	var canvas := CanvasLayer.new();add_child(canvas)
	panel_root=Control.new();canvas.add_child(panel_root);panel_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var theme := Theme.new();theme.default_font_size=23
	var font := SystemFont.new();font.font_names=PackedStringArray(["Segoe UI"]);theme.default_font=font
	theme.set_stylebox("normal","Button",skin(Color("242b33")))
	theme.set_stylebox("hover","Button",skin(Color("34443f"),Color("79b8aa")))
	theme.set_stylebox("pressed","Button",skin(Color("3c5b51")))
	theme.set_stylebox("disabled","Button",skin(Color("1c2026")))
	theme.set_color("font_color","Button",Color("e4e7eb"));panel_root.theme=theme
	var bg := ColorRect.new();bg.color=Color("11151a");panel_root.add_child(bg);bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var margin := MarginContainer.new();panel_root.add_child(margin);margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+side,22)
	var stack := VBoxContainer.new();stack.add_theme_constant_override("separation",16);margin.add_child(stack)
	var top := HBoxContainer.new();top.custom_minimum_size.y=75;top.add_theme_constant_override("separation",40);stack.add_child(top)
	var branding := VBoxContainer.new();top.add_child(branding)
	label(branding,"MALECNS  /  VIRTUAL FLY",27)
	label(branding,"MVP v0.1   •   CONNECTOME EXPERIMENT CONSOLE",17,Color("79b8aa"))
	status_label=label(top,"STARTING",23);status_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	clocks_label=label(top,"Loading the full neural network…",23)
	button(top,"Fullscreen  F11",toggle_fullscreen)
	button(top,"Exit",shutdown)
	var middle := HBoxContainer.new();middle.size_flags_vertical=Control.SIZE_EXPAND_FILL;middle.add_theme_constant_override("separation",16);stack.add_child(middle)
	var left_scroll := ScrollContainer.new();left_scroll.custom_minimum_size.x=440;left_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;middle.add_child(left_scroll)
	var left := VBoxContainer.new();left.size_flags_horizontal=Control.SIZE_EXPAND_FILL;left.add_theme_constant_override("separation",16);left_scroll.add_child(left)
	var experiment := card(left,"01  EXPERIMENT")
	preset_select=OptionButton.new();preset_select.custom_minimum_size.y=54
	for name in PRESETS:preset_select.add_item(name)
	preset_select.select(PRESETS.find(eco.mode));experiment.add_child(preset_select)
	label(experiment,"World seed",19,Color("9ba7b5"));world_seed=SpinBox.new();world_seed.max_value=2147483647;world_seed.value=eco.world_seed;experiment.add_child(world_seed)
	label(experiment,"Brain seed",19,Color("9ba7b5"));brain_seed=SpinBox.new();brain_seed.max_value=2147483647;brain_seed.value=cfg.seed;experiment.add_child(brain_seed)
	button(experiment,"Apply preset + reset",apply_preset,"Restarts the actual brain RNG and world from these seeds.")
	config_label=label(experiment,"0.5 s baseline → stimulus → recovery",19,Color("9ba7b5"));config_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var transport := card(left,"02  EXECUTION")
	var row := HBoxContainer.new();transport.add_child(row)
	button(row,"Run",func():command("resume"));button(row,"Pause",func():command("pause"));button(row,"Step",func():command("step"),"Complete exactly one 50 ms quantum, then remain paused.")
	button(transport,"Reset current preset",func():command("reset"))
	label(transport,"Space pause/run  •  N step  •  R reset",18,Color("9ba7b5"))
	var environment := card(left,"03  WORLD CONDITIONS")
	for item in [["Spawn food  F","food"],["Spawn predator  P","predator"],["Spawn female  M","female"],["Heat pulse  H","heat"]]:
		var kind: String=item[1]
		button(environment,item[0],func():command("world_event",{"event":kind}))
	label(environment,"Ambient temperature · °C",19,Color("9ba7b5"))
	temp_control=SpinBox.new();temp_control.min_value=15;temp_control.max_value=40;temp_control.step=.5;temp_control.value=25;environment.add_child(temp_control)
	button(environment,"Set temperature",func():command("temperature",{"celsius":temp_control.value}))
	shade_control=CheckBox.new();shade_control.text="Shade cooling enabled";shade_control.button_pressed=true;environment.add_child(shade_control)
	shade_control.toggled.connect(func(on: bool):command("shade",{"enabled":on}))
	button(environment,"Clear objects + pending stimuli",func():command("clear_objects"))
	var truth := card(left,"SCIENTIFIC BOUNDARY")
	for text in ["VERIFIED · MaleCNS identities","EXPERIMENTAL · encoding / motor","UNRESOLVED · ingestion / courtship","DISABLED · neural pain / contact cue","PLACEHOLDER · gut / defecation"]:
		var badge_panel := PanelContainer.new()
		var badge_style := skin(Color("242823"));badge_style.content_margin_top=4;badge_style.content_margin_bottom=4
		badge_panel.add_theme_stylebox_override("panel",badge_style);truth.add_child(badge_panel)
		var l := label(badge_panel,text,17,Color("c5bc99"));l.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	label(truth,"No body-steering controls.\nActivity does not imply behavior.",19,Color("9ba7b5"))
	var center := VBoxContainer.new();center.size_flags_horizontal=Control.SIZE_EXPAND_FILL;center.add_theme_constant_override("separation",12);middle.add_child(center)
	var world_header := HBoxContainer.new();center.add_child(world_header)
	var heading := label(world_header,"LIVE WORLD  /  one neural body",22);heading.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	button(world_header,"Overview / follow",toggle_camera)
	var viewport_container := SubViewportContainer.new();viewport_container.stretch=true;viewport_container.size_flags_vertical=Control.SIZE_EXPAND_FILL;center.add_child(viewport_container)
	view=SubViewport.new();view.size=Vector2i(2400,1500);view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport_container.add_child(view)
	world_root=Node3D.new();view.add_child(world_root)
	for child in get_children():
		if child is Node3D:child.reparent(world_root)
	for child in world_root.get_children():
		if child is Camera3D:world_camera=child
		if child is MeshInstance3D and child.mesh is BoxMesh and is_equal_approx(child.mesh.size.y,.015):shade_mesh=child
	world_camera.position=Vector3(8,12,10);world_camera.look_at(Vector3.ZERO);world_camera.size=14.2
	var legend := label(center,"● FOOD    ● PREDATOR    ● FEMALE    ▰ SHADE     |     121.68 units² interior · 2.000×",20,Color("9ba7b5"))
	legend.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
	stimulus_label=label(center,"Sensory features appear after neural warm-up.",20);stimulus_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var right_scroll := ScrollContainer.new();right_scroll.custom_minimum_size.x=530;right_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;middle.add_child(right_scroll)
	var right := VBoxContainer.new();right.size_flags_horizontal=Control.SIZE_EXPAND_FILL;right.add_theme_constant_override("separation",12);right_scroll.add_child(right)
	label(right,"BRAIN OBSERVER",24)
	label(right,"Mean EMA Hz / group • 50 ms neural samples",18,Color("9ba7b5"))
	for group in GROUPS:
		var col := card(right,"")
		var title := HBoxContainer.new();col.add_child(title)
		var name_label := label(title,group[1],24);name_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		circuit_labels[group[0]]=label(title,"— Hz",25,Color("79b8aa"))
		var badge := label(col,"VERIFIED IDENTITY  ·  EXPERIMENTAL FUNCTION",15,Color("c5bc99"))
		badge.tooltip_text="Actual MaleCNS annotation membership is verified. Encoding, downstream interpretation and motor decoding remain experimental."
		label(col,group[2],18,Color("9ba7b5"))
		var chart := Spark.new();chart.custom_minimum_size.y=44;col.add_child(chart);charts[group[0]]=chart
	var tabs := TabContainer.new();tabs.custom_minimum_size.y=330;right.add_child(tabs)
	var extra := VBoxContainer.new();extra.name="Other circuits";tabs.add_child(extra)
	for group in EXTRA_GROUPS:extra_labels[group[0]]=label(extra,group[1]+"  — Hz",19)
	var evidence := VBoxContainer.new();evidence.name="Interpretation";tabs.add_child(evidence)
	var info := label(evidence,"Identities: VERIFIED\nEncoding: EXPERIMENTAL\nGF response is not an escape motor.\nLC9 → DNp09 interpretation: EXPERIMENTAL\nFood ingestion: UNRESOLVED\nFemale odor is not sex-specific.\npC1 is a family, not an exact P1 alias.\nCharts autoscale; 120 neural samples.",19,Color("c5bc99"));info.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var bottom := HBoxContainer.new();bottom.custom_minimum_size.y=310;bottom.add_theme_constant_override("separation",16);stack.add_child(bottom)
	var physiology := card(bottom,"BODY / PHYSIOLOGY");physiology.get_parent().custom_minimum_size.x=560
	physiology_label=label(physiology,"Waiting for completed neural state",24)
	motor_label=label(physiology,"Motor outputs derive only from neural activity.",20,Color("9ba7b5"))
	var health := card(bottom,"PERFORMANCE HEALTH");health.get_parent().custom_minimum_size.x=660
	health_label=label(health,"Measuring actual reference backend…",22)
	label(health,"50 ms neural quantum • slow motion is shown honestly",18,Color("9ba7b5"))
	var events := card(bottom,"CAUSAL EVENT TIMELINE  /  completed world seconds");events.get_parent().size_flags_horizontal=Control.SIZE_EXPAND_FILL
	event_text=RichTextLabel.new();event_text.size_flags_vertical=Control.SIZE_EXPAND_FILL;event_text.scroll_following=true;event_text.add_theme_font_size_override("normal_font_size",21);events.add_child(event_text)

func apply_preset() -> void:
	command("preset",{"preset":PRESETS[preset_select.selected],"world_seed":int(world_seed.value),"brain_seed":int(brain_seed.value)})

func toggle_fullscreen() -> void:
	var fullscreen := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if fullscreen else DisplayServer.WINDOW_MODE_FULLSCREEN)
	if fullscreen:DisplayServer.window_set_size(Vector2i(1920,1080))
	log_row("fullscreen_toggle",{"mode":DisplayServer.window_get_mode()})

func toggle_camera() -> void:
	camera_follow=not camera_follow
	if not camera_follow:
		world_camera.position=Vector3(8,12,10);world_camera.look_at(Vector3.ZERO);world_camera.size=14.2

func display_entities(entities: Array) -> void:
	super.display_entities(entities)
	if world_root:
		for mesh in meshes.values():
			if mesh.get_parent()!=world_root:mesh.reparent(world_root)

func accept_packet(packet: Dictionary) -> void:
	super.accept_packet(packet)
	if packet.has("console"):
		console_state=packet.console
		if packet.has("ecology"):
			last_ecology=packet.ecology
			if connection=="paused":display_entities(packet.ecology.world.entities)
		if generation!=observer_generation:
			observer_generation=generation;generation_started_ms=Time.get_ticks_msec()
			world_seed.value=packet.ecology.world_seed;brain_seed.value=console_state.brain_seed
			preset_select.select(PRESETS.find(console_state.preset))
			temp_control.value=console_state.ambient_setting
			shade_control.set_pressed_no_signal(console_state.shade_enabled)
			for chart in charts.values():chart.samples.clear();chart.queue_redraw()
		if float(packet.dt_s)>0 and int(packet.seq)!=observer_seq:
			observer_seq=int(packet.seq)
			for key in charts:charts[key].push(float(console_state.groups_hz.get(key,0.)))

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:return
	match event.keycode:
		KEY_F11:toggle_fullscreen()
		KEY_SPACE:command("resume" if console_state.get("paused",false) else "pause")
		KEY_N:command("step")
		KEY_ESCAPE:
			if DisplayServer.window_get_mode()==DisplayServer.WINDOW_MODE_FULLSCREEN:toggle_fullscreen()
			else:shutdown()
		KEY_D:pass
		_:super._unhandled_key_input(event)

func update_hud() -> void:
	if not panel_root:return
	var now := Time.get_ticks_msec()
	if now<ui_next_ms:return
	ui_next_ms=now+100
	var started := Time.get_ticks_usec()
	var ready := connection in ["ready","paused"]
	for b in controls:
		if b.text not in ["Exit","Fullscreen  F11","Overview / follow"]:b.disabled=not ready
	var wall := float(now-generation_started_ms)/1000.
	var display_status := connection.to_upper()
	if connection=="ready" and now-last_rx_ms>3000:display_status="WAITING FOR BRAIN · BODY HELD"
	status_label.text="%s  /  %s" % [display_status,console_state.get("preset",eco.mode)]
	clocks_label.text="WORLD %.2f s   NEURAL %.2f s   WALL %.1f s" % [world_time,state.get("neural_time_s",0),wall]
	if not console_state.is_empty():
		if pending_command_id in state.get("acknowledged_commands",[]):pending_command_id=""
		if pending_command_id.is_empty():
			var phase := "BASELINE" if world_time<.5 else ("STIMULUS / OBSERVE" if world_time<3. else "RECOVERY / FREE OBSERVATION")
			config_label.text=phase+"\nFixed onset 0.50 s · no background schedule"
		if shade_mesh:shade_mesh.visible=console_state.shade_enabled
		var groups: Dictionary=console_state.groups_hz
		for key in circuit_labels:circuit_labels[key].text="%.2f Hz" % float(groups.get(key,0.))
		for group in EXTRA_GROUPS:extra_labels[group[0]].text="%s   %.2f Hz" % [group[1],float(groups.get(group[0],0.))]
		var perf: Dictionary=console_state.performance
		health_label.text="Compute  %.1f ms   /  50 ms neural\np50  %.1f     p95  %.1f     p99  %.1f ms\nFPS  %.0f     Neural / wall  %.3f×\nReference SciPy · dt 1 ms · PCG64 noise" % [perf.get("compute_ms",0),perf.get("p50_ms",0),perf.get("p95_ms",0),perf.get("p99_ms",0),Engine.get_frames_per_second(),float(state.get("neural_time_s",0))/maxf(wall,.001)]
		var lines := ""
		for e in console_state.events:
			lines+="[%6.2f]  %s" % [float(e.world_time_s),str(e.event).replace("_"," ")]
			if e.has("amount"):lines+="  %.1f" % float(e.amount)
			if e.has("hp"):lines+="  → HP %.1f" % float(e.hp)
			lines+="\n"
		if lines!=last_event_signature:event_text.text=lines;last_event_signature=lines
	if not last_ecology.is_empty():
		var w: Dictionary=last_ecology.world
		physiology_label.text="HP  %.1f      HUNGER  %.2f      GUT  %.2f\nLOCAL  %.2f °C     SHADE  %s\nWORLD SEED %d  /  BRAIN SEED %d" % [w.hp,w.hunger,w.gut,w.local_temperature_c,str(w.in_shade),last_ecology.world_seed,console_state.get("brain_seed",cfg.seed)]
		motor_label.text="FORWARD %.4f   TURN %+.4f\nIngestion disabled · gut model is a placeholder" % [state.get("forward",0),state.get("turn",0)]
		var currents := "LAST QUANTUM INPUT  /  "
		for term in last_ecology.sensory_terms:
			if float(term.amplitude)>.001:currents+="%s %.2f   " % [term.modality,term.amplitude]
		stimulus_label.text=currents+"\nSource body ACK %s • displayed world is input snapshot (≤1 quantum lag)" % str(last_ecology.get("sensor_source_body_seq","—"))
	if camera_follow:
		world_camera.position=fly.position+Vector3(3,5,4);world_camera.look_at(fly.position);world_camera.size=6
	ui_updates+=1
	var elapsed := Time.get_ticks_usec()-started
	ui_total_us+=elapsed;ui_max_us=maxi(ui_max_us,elapsed)
	if qa_controls:qa_driver(now)

func qa_driver(now: int) -> void:
	if qa_stage==0 and world_time>=.3:
		command("pause");qa_stage=1
	elif qa_stage==1 and connection=="paused":
		qa_world=world_time;qa_at=now;qa_stage=2
	elif qa_stage==2 and now-qa_at>=1200:
		log_row("qa_pause",{"passed":is_equal_approx(world_time,qa_world)})
		command("step");qa_stage=3
	elif qa_stage==3 and connection=="paused" and world_time>qa_world:
		log_row("qa_step",{"passed":is_equal_approx(world_time-qa_world,.05)})
		command("resume");qa_stage=4

func shutdown() -> void:
	if not shutdown_sent:
		log_row("console_health",{"ui_updates":ui_updates,"render_process_ms":Performance.get_monitor(Performance.TIME_PROCESS)*1000.,"physics_process_ms":Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)*1000.,"ui_mean_ms":float(ui_total_us)/maxi(ui_updates,1)/1000.,"ui_max_ms":ui_max_us/1000.,"window_size":[get_window().size.x,get_window().size.y],"mode":DisplayServer.window_get_mode(),"viewport_size":[view.size.x,view.size.y] if view else [],"qa_stage":qa_stage})
	super.shutdown()
