extends "res://mvp/main.gd"

const R_KEYS = ["MOTOR TEST","CONTROL","PREDATOR","FOOD","FEMALE","HEAT","PREDATOR + HEAT","FOOD RIGHT","HEAT RIGHT"]
const R_NAMES = ["운동 뉴런 자극 · 경로 검사","기본 상태 · 환경 무자극","포식자 접근 · 도약 검사","왼쪽 먹이 · 접근 검사","다른 파리","왼쪽 그늘 · 열 회피 검사","포식자와 가열","오른쪽 먹이 · 접근 검사","오른쪽 그늘 · 열 회피 검사"]
const K_GROUPS = [["DNp09","DNp09","전진 관련 운동 뉴런"],["DNa01","DNa01","회전 관련 운동 뉴런"],["DNa02","DNa02","회전 관련 운동 뉴런"],["lc4","LC4","다가오는 물체 감지"],["lplc2","LPLC2","확대되는 물체 감지"],["GF","GF / DNp01","가설 모델: 신경 신호로 원시 도약"]]
const K_EXTRA = [["figure","LC9 · 물체 움직임"],["food_odor","ORN DM1 / VA2 · 먹이 냄새"],["taste","Sugar SEL PN · 중추 당 자극"],["fly_odor","ORN VA1v / VA1d · 파리 냄새"],["hot","TRN VP2 · 가열"],["cold","TRN VP3 · 냉각"],["feeding_observation","Fdg · 섭식 관찰"],["courtship_observation","pC1 계열 · 구애 회로 관찰"]]
const K_MODALITIES = {"lc4":"접근 감지","lplc2":"확대 감지","figure":"물체 움직임","food_odor":"먹이 냄새","taste":"당 접촉","fly_odor":"파리 냄새","hot":"가열","cold":"냉각"}
const SCIENTIFIC_MODELS = ["sensorimotor","counts","frozen"]
const K_EVENTS = {"RESET":"실험 초기화","HEAT_START":"가열 시작","HEAT_END":"가열 종료","PREDATOR_HIT":"포식자 접촉","DAMAGE":"체력 손실","DEATH":"체력 소진 · 몸체 정지","TEST_GUT_LOAD":"장 내용물 가상 입력","DEFECATION_PENDING":"배설 예약 · 생리 모형","DEFECATE":"배설 · 생리 모형","SHADE_ENTER":"그늘 진입","SHADE_EXIT":"그늘 이탈","TEMPERATURE_SET":"주변 온도 설정","SHADE_CONDITION":"그늘 냉각 변경","EXPERIMENT_CLEARED":"개체와 예정 자극 제거","NEURAL_TEST_FORWARD":"전진 뉴런 자극 시작","NEURAL_TEST_LEFT":"왼쪽 운동 뉴런 자극 시작","NEURAL_TEST_RIGHT":"오른쪽 운동 뉴런 자극 시작","NEURAL_TEST_STOP":"수동 신경 자극 중지","NEURAL_TEST_END":"인위적 신경 자극 종료"}
var diagnosis_label: Label
var test_label: Label
var last_motion_position := Vector3.ZERO
var last_motion_world := 0.0
var measured_speed := 0.0
var low_latency_ready := false
var qa_neural := false
var qa_neural_stage := 0
var qa_neural_generation := -1
var jump_velocity := 0.0
var takeoff_velocity := Vector3.ZERO
var jump_generation := -1
var model_select: OptionButton
var model_apply_button: Button
var tonic_control: SpinBox
var restored_control: CheckBox
var sensory_control: CheckBox
var gf_control: CheckBox
var modality_controls := {}
var measurement_label: Label
var scientific_label: Label
var qa_model := false
var qa_model_stage := 0
var qa_model_generation := -1

func move_body(packet: Dictionary, neural_dt: float) -> void:
	if jump_generation!=generation:jump_velocity=0.;takeoff_velocity=Vector3.ZERO;jump_generation=generation
	if not packet.has("escape_motor"):
		jump_velocity=0.;super.move_body(packet,neural_dt);return
	if float(packet.ecology.world.hp)<=0.:
		fly.velocity=Vector3.ZERO;return
	if float(packet.escape_motor)>0. and fly.position.y<=.225:
		jump_velocity=4.2
		takeoff_velocity=-fly.transform.basis.z*float(packet.get("takeoff_forward_impulse",0.))
		log_row("gf_jump",{"source_seq":packet.seq,"gf_hz":packet.escape_activity_hz,"threshold_hz":packet.escape_threshold_hz})
	fly.rotation.y-=float(packet.turn)*float(packet.get("max_turn_radians_per_neural_second",cfg.body.max_turn_radians_per_neural_second))*neural_dt
	var velocity := -fly.transform.basis.z*float(packet.forward)*float(cfg.body.max_forward_units_per_neural_second)
	if fly.position.y>.221 or jump_velocity>0.:jump_velocity-=9.8*neural_dt
	velocity.y=jump_velocity
	velocity+=takeoff_velocity
	takeoff_velocity*=exp(-.8*neural_dt)
	fly.velocity=velocity
	var collision := fly.move_and_collide(velocity*neural_dt)
	# Enclosed primitive arena: airborne movement cannot land outside its floor.
	var arena_limit: float=float(cfg.arena.half_width)-.29
	if fly.position.y>.5:
		fly.position.x=clampf(fly.position.x,-arena_limit,arena_limit)
		fly.position.z=clampf(fly.position.z,-arena_limit,arena_limit)
	if collision and collision.get_normal().y>.5:jump_velocity=0.;takeoff_velocity=Vector3.ZERO
	if fly.position.y<.22:fly.position.y=.22;jump_velocity=0.;takeoff_velocity=Vector3.ZERO

func _ready() -> void:
	super._ready()
	TranslationServer.set_locale("ko")
	get_window().title="MaleCNS · 한글 신경망 실험실"
	get_window().content_scale_size=Vector2i(1920,1080)
	get_window().content_scale_mode=Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	Engine.physics_ticks_per_second=int(1000.0/float(cfg.packet_neural_ms))
	camera_follow=true
	for arg in OS.get_cmdline_user_args():
		if arg=="--qa-neural":qa_neural=true
		if arg=="--qa-model":qa_model=true

func shutdown() -> void:
	if shutdown_sent:return
	shutdown_sent=true
	log_row("console_health",{"ui_updates":ui_updates,"ui_mean_ms":float(ui_total_us)/maxi(ui_updates,1)/1000.,"ui_max_ms":ui_max_us/1000.,"window_size":[get_window().size.x,get_window().size.y],"viewport_size":[view.size.x,view.size.y] if view else []})
	send_command("shutdown")
	# Keep TCP open and drain pending frames until the brain consumes shutdown
	# and closes its end. Immediate disconnect can discard the command on Windows.
	var deadline := Time.get_ticks_msec()+3000
	while peer.get_status()==StreamPeerTCP.STATUS_CONNECTED and Time.get_ticks_msec()<deadline:
		peer.poll()
		if peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED:break
		var available := peer.get_available_bytes()
		if available>0:peer.get_data(available)
		await get_tree().process_frame
	log_row("quit",{"brain_closed_connection":peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED})
	if log_file:log_file.close();log_file=null
	peer.disconnect_from_host();get_tree().quit()

func capture_frame() -> void:
	if DisplayServer.get_name()=="headless":return
	await super.capture_frame()

func capture_ecology() -> void:
	if DisplayServer.get_name()=="headless":return
	await super.capture_ecology()

func send_command(kind: String, extra: Dictionary = {}) -> void:
	if peer.get_status()==StreamPeerTCP.STATUS_CONNECTED and not low_latency_ready:
		peer.set_no_delay(true)
		low_latency_ready=true
	super.send_command(kind,extra)

func _process(delta: float) -> void:
	pass

func _physics_process(delta: float) -> void:
	if shutdown_sent:return
	if peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED:low_latency_ready=false
	super._process(delta)
	if not shutdown_sent:super._physics_process(delta)

func label(parent: Node, text: String, font_size: int = 20, color: Color = Color("e4e7eb")) -> Label:
	var l := Label.new();l.text=text
	l.add_theme_font_size_override("font_size",font_size);l.add_theme_color_override("font_color",color)
	var font := SystemFont.new();font.font_names=PackedStringArray(["Malgun Gothic","맑은 고딕","Segoe UI"])
	l.add_theme_font_override("font",font);parent.add_child(l);return l

func card(parent: Node, title: String) -> VBoxContainer:
	var panel := PanelContainer.new();var style := skin(Color("19222d"))
	style.content_margin_left=12;style.content_margin_right=12;style.content_margin_top=10;style.content_margin_bottom=10
	panel.add_theme_stylebox_override("panel",style);parent.add_child(panel)
	var col := VBoxContainer.new();col.add_theme_constant_override("separation",7);panel.add_child(col)
	if not title.is_empty():label(col,title,18,Color("9fbdce"))
	return col

func button(parent: Node, text: String, action: Callable, hint: String = "") -> Button:
	var b := Button.new();b.text=text;b.tooltip_text=hint;b.custom_minimum_size.y=38
	b.pressed.connect(action);parent.add_child(b);controls.append(b);return b

func command(kind: String, extra: Dictionary = {}) -> void:
	super.command(kind,extra)
	config_label.text="요청 대기 중 · 진행 중인 뇌 프레임이 끝나면 적용됩니다"

func build_console() -> void:
	var canvas := CanvasLayer.new();add_child(canvas)
	panel_root=Control.new();canvas.add_child(panel_root);panel_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var theme := Theme.new();theme.default_font_size=20
	var font := SystemFont.new();font.font_names=PackedStringArray(["Malgun Gothic","맑은 고딕"]);theme.default_font=font
	for state_name in ["normal","hover","pressed","disabled"]:
		theme.set_stylebox(state_name,"Button",skin(Color("263647") if state_name=="normal" else Color("36536a")))
	panel_root.theme=theme
	var bg := ColorRect.new();bg.color=Color("0e1721");panel_root.add_child(bg);bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var margin := MarginContainer.new();panel_root.add_child(margin);margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+side,16)
	var stack := VBoxContainer.new();stack.add_theme_constant_override("separation",12);margin.add_child(stack)
	var top := HBoxContainer.new();top.custom_minimum_size.y=54;top.add_theme_constant_override("separation",18);stack.add_child(top)
	var brand := VBoxContainer.new();top.add_child(brand);label(brand,"MaleCNS · 신경망 실험실",25);label(brand,"전체 연결망 165,122개 뉴런 · 한글 리마스터",16,Color("8ed4cc"))
	status_label=label(top,"시작 중",20);status_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	clocks_label=label(top,"실제 신경망 준비 중",18)
	button(top,"전체 화면  F11",toggle_fullscreen).set_meta("always",true)
	button(top,"종료",shutdown).set_meta("always",true)
	var middle := HBoxContainer.new();middle.size_flags_vertical=Control.SIZE_EXPAND_FILL;middle.add_theme_constant_override("separation",12);stack.add_child(middle)
	var left_scroll := ScrollContainer.new();left_scroll.custom_minimum_size.x=300;left_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;middle.add_child(left_scroll)
	var left := VBoxContainer.new();left.size_flags_horizontal=Control.SIZE_EXPAND_FILL;left.add_theme_constant_override("separation",10);left_scroll.add_child(left)
	var experiment := card(left,"실험 선택")
	preset_select=OptionButton.new();preset_select.custom_minimum_size.y=38
	for name in R_NAMES:preset_select.add_item(name)
	preset_select.select(R_KEYS.find(eco.mode));experiment.add_child(preset_select)
	button(experiment,"선택한 실험 시작",apply_preset)
	var seeds := VBoxContainer.new();experiment.add_child(seeds)
	var world_col := HBoxContainer.new();seeds.add_child(world_col);label(world_col,"환경 시드",15);world_seed=SpinBox.new();world_seed.max_value=2147483647;world_seed.value=eco.world_seed;world_seed.size_flags_horizontal=Control.SIZE_EXPAND_FILL;world_col.add_child(world_seed)
	var brain_col := HBoxContainer.new();seeds.add_child(brain_col);label(brain_col,"신경망 시드",15);brain_seed=SpinBox.new();brain_seed.max_value=2147483647;brain_seed.value=cfg.seed;brain_seed.size_flags_horizontal=Control.SIZE_EXPAND_FILL;brain_col.add_child(brain_seed)
	config_label=label(experiment,"준비 중",16,Color("9fbdce"));config_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var model_card := card(left,"신경 모델과 대조 조건")
	model_select=OptionButton.new();model_select.add_item("감각·운동 보정 · 새 행동 가설");model_select.add_item("이전 시냅스 수 · 행동 가설");model_select.add_item("기존 v0.1 · 고정 대조 모델");model_card.add_child(model_select)
	model_select.select(SCIENTIFIC_MODELS.find(cfg.get("scientific_model","frozen")))
	label(model_card,"기저 전류 · 모델별 각성 가정 (0~2)",15)
	tonic_control=SpinBox.new();tonic_control.min_value=0.;tonic_control.max_value=2.;tonic_control.step=.05;tonic_control.value=cfg.get("tonic_current",1.5);model_card.add_child(tonic_control)
	restored_control=CheckBox.new();restored_control.text="작은 시냅스까지 복원한 연결망";restored_control.button_pressed=cfg.get("restore_weak",false);model_card.add_child(restored_control)
	model_apply_button=button(model_card,"모델 조건 적용 · 초기화",func():command("model_condition",{"model":SCIENTIFIC_MODELS[model_select.selected],"tonic_current":tonic_control.value,"restore_weak":restored_control.button_pressed}))
	sensory_control=CheckBox.new();sensory_control.text="환경 감각 입력 켜기";sensory_control.button_pressed=eco.sensory.enabled;model_card.add_child(sensory_control)
	sensory_control.toggled.connect(func(on: bool):command("sensory_condition",{"enabled":on}))
	for item in [["vision","시각 입력"],["chemical","냄새·당 감각 입력"],["thermal","온도 감각 입력"]]:
		var modality: String=item[0]
		var check := CheckBox.new();check.text=item[1]+" 켜기";check.button_pressed=eco.sensory.get(modality+"_enabled",true);model_card.add_child(check)
		check.toggled.connect(func(on: bool):command("modality_condition",{"modality":modality,"enabled":on}))
		modality_controls[modality]=check
	gf_control=CheckBox.new();gf_control.text="GF 뉴런 켜기 · 끄면 신경 차단";gf_control.button_pressed=not cfg.get("gf_ablated",false);model_card.add_child(gf_control)
	gf_control.toggled.connect(func(on: bool):command("gf_condition",{"enabled":on}))
	label(model_card,"감각을 끄거나 GF를 차단한 뒤 초기화하여 같은 실험과 비교하세요. 기저 구동은 생물의 실제 각성 회로를 재현하지 않습니다.",15,Color("f0c780")).autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var transport := card(left,"실행")
	var row := HBoxContainer.new();transport.add_child(row)
	button(row,"진행",func():command("resume"));button(row,"정지",func():command("pause"));button(row,"한 프레임",func():command("step"))
	button(transport,"현재 실험 초기화",func():command("reset"))
	label(transport,"스페이스: 진행/정지 · N: 한 프레임 · R: 초기화",14,Color("9fbdce")).autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var test := card(left,"운동 경로 검사 · 인위적 신경 자극")
	label(test,"실제 운동 뉴런에 2초간 전류를 입력합니다. 환경 자극에 의한 자발적 보행과 구분해 보세요.",16,Color("f0c780")).autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	button(test,"전진 뉴런 자극",func():command("neural_test",{"group":"forward"}))
	var turn_row := HBoxContainer.new();test.add_child(turn_row)
	button(turn_row,"왼쪽 뉴런",func():command("neural_test",{"group":"left"}));button(turn_row,"오른쪽 뉴런",func():command("neural_test",{"group":"right"}))
	button(test,"수동 신경 자극 중지",func():command("neural_test",{"group":"stop"}))
	var environment := card(left,"환경 조건")
	for item in [["먹이 추가  F","food"],["포식자 추가  P","predator"],["다른 파리 추가  M","female"],["열 자극  H","heat"]]:
		var kind: String=item[1];button(environment,item[0],func():command("world_event",{"event":kind}))
	label(environment,"주변 온도 (℃)",16)
	temp_control=SpinBox.new();temp_control.min_value=15;temp_control.max_value=40;temp_control.step=.5;temp_control.value=25;environment.add_child(temp_control)
	button(environment,"온도 적용",func():command("temperature",{"celsius":temp_control.value}))
	shade_control=CheckBox.new();shade_control.text="그늘 냉각 켜기";shade_control.button_pressed=true;environment.add_child(shade_control)
	shade_control.toggled.connect(func(on: bool):command("shade",{"enabled":on}))
	button(environment,"개체와 예정 자극 제거",func():command("clear_objects"))
	var center := VBoxContainer.new();center.size_flags_horizontal=Control.SIZE_EXPAND_FILL;center.add_theme_constant_override("separation",8);middle.add_child(center)
	var header := HBoxContainer.new();center.add_child(header)
	var heading := label(header,"실제 신경 출력 → 몸체 → 다음 감각 입력",19);heading.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	button(header,"전체 보기 / 파리 추적",toggle_camera).set_meta("always",true)
	var viewport_container := SubViewportContainer.new();viewport_container.stretch=true;viewport_container.size_flags_vertical=Control.SIZE_EXPAND_FILL;center.add_child(viewport_container)
	view=SubViewport.new();view.size=Vector2i(1100,650);view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport_container.add_child(view)
	world_root=Node3D.new();view.add_child(world_root)
	for child in get_children():
		if child is Node3D:child.reparent(world_root)
	for child in world_root.get_children():
		if child is Camera3D:world_camera=child
		if child is MeshInstance3D and child.mesh is BoxMesh and is_equal_approx(child.mesh.size.y,.015):shade_mesh=child
	world_camera.position=Vector3(3,5,4);world_camera.look_at(Vector3.ZERO);world_camera.size=6
	diagnosis_label=label(center,"움직임 진단 준비 중",20,Color("8ed4cc"));diagnosis_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	test_label=label(center,"",17,Color("f0c780"));test_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	stimulus_label=label(center,"감각 입력 준비 중",16,Color("9fbdce"));stimulus_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	measurement_label=label(center,"실험 수치 준비 중",16,Color("8ed4cc"));measurement_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	label(center,"녹색: 먹이 · 빨강: 포식자 · 보라: 다른 파리 · 청록: 그늘 | 바닥 121.68 단위²",15,Color("9fbdce"))
	var right_scroll := ScrollContainer.new();right_scroll.custom_minimum_size.x=340;right_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;middle.add_child(right_scroll)
	var right := VBoxContainer.new();right.size_flags_horizontal=Control.SIZE_EXPAND_FILL;right.add_theme_constant_override("separation",8);right_scroll.add_child(right)
	label(right,"신경 회로 관찰",22);label(right,"뉴런당 평균 발화율 · 회/초 · 최근 120개 뇌 프레임",14,Color("9fbdce")).autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	for group in K_GROUPS:
		var col := card(right,"");var title := HBoxContainer.new();col.add_child(title)
		var name_label := label(title,group[1],20);name_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		circuit_labels[group[0]]=label(title,"— 회/초",20,Color("8ed4cc"));label(col,group[2],15,Color("9fbdce"))
		var chart := Spark.new();chart.custom_minimum_size.y=30;col.add_child(chart);charts[group[0]]=chart
	var tabs := TabContainer.new();tabs.custom_minimum_size.y=300;right.add_child(tabs)
	var extra := VBoxContainer.new();extra.name="다른 회로";tabs.add_child(extra)
	for group in K_EXTRA:extra_labels[group[0]]=label(extra,group[1]+"  —",15)
	var evidence := VBoxContainer.new();evidence.name="해석과 한계";tabs.add_child(evidence)
	scientific_label=label(evidence,"신경 세포 정체성과 연결: 확인됨\n행동 가설 모델은 기존 인증 모델과 다릅니다.\n기저 구동·감각 부호화·도약은 모형 가정입니다.\n먹이 접근·그늘 선택은 검증을 통과해야 합니다.\n원시 도약은 비행·방향성 도피의 완성본이 아닙니다.\n섭식·구애·신경 통증: 미검증\n장·배설·체력: 단순 모형\n그래프는 회로별 자동 축척입니다.",16,Color("f0c780"));scientific_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var bottom := HBoxContainer.new();bottom.custom_minimum_size.y=190;bottom.add_theme_constant_override("separation",12);stack.add_child(bottom)
	var physiology := card(bottom,"몸체와 생리 상태");physiology.get_parent().custom_minimum_size.x=310
	physiology_label=label(physiology,"준비 중",18);motor_label=label(physiology,"운동 출력 준비 중",16)
	var health := card(bottom,"뇌 프레임 동기화와 성능");health.get_parent().custom_minimum_size.x=430
	health_label=label(health,"실제 처리 시간 측정 중",17)
	var events := card(bottom,"완료된 환경 시간 · 사건 기록");events.get_parent().size_flags_horizontal=Control.SIZE_EXPAND_FILL
	event_text=RichTextLabel.new();event_text.size_flags_vertical=Control.SIZE_EXPAND_FILL;event_text.scroll_following=true;event_text.add_theme_font_size_override("normal_font_size",17);events.add_child(event_text)

func apply_preset() -> void:
	command("preset",{"preset":R_KEYS[preset_select.selected],"world_seed":int(world_seed.value),"brain_seed":int(brain_seed.value)})
	command("resume")

func accept_packet(packet: Dictionary) -> void:
	var previous := observer_generation
	super.accept_packet(packet)
	if packet.has("console") and previous!=observer_generation:
		preset_select.select(R_KEYS.find(console_state.preset));last_motion_world=0.;last_motion_position=Vector3.ZERO;measured_speed=0.
		model_select.select(SCIENTIFIC_MODELS.find(console_state.get("scientific_model","frozen")))
		tonic_control.value=console_state.get("count_tonic_setting",1.5)
		restored_control.set_pressed_no_signal(console_state.get("restored_weak_connections",false))

func event_name(key: String) -> String:
	if key=="MODEL_CONDITION":return "신경 모델 조건 변경"
	if key=="SENSORY_CONDITION":return "감각 입력 대조 조건 변경"
	if key=="GF_CONDITION":return "GF 신경 차단 조건 변경"
	if key=="MODALITY_CONDITION":return "감각별 입력 대조 조건 변경"
	if K_EVENTS.has(key):return K_EVENTS[key]
	if key.ends_with(" ACTIVITY RISE"):
		var circuit := key.trim_suffix(" ACTIVITY RISE")
		return str(K_MODALITIES.get(circuit,circuit))+" 회로 활동 증가"
	for suffix in ["_SPAWN","_DESPAWN","_CONTACT","_INGEST"]:
		if key.ends_with(suffix):
			var object_name: String={"FOOD":"먹이","PREDATOR":"포식자","FEMALE":"다른 파리","FECES":"배설물"}.get(key.trim_suffix(suffix),"개체")
			return object_name+str({"_SPAWN":" 생성","_DESPAWN":" 제거","_CONTACT":" 접촉","_INGEST":" 섭취"}[suffix])
	return "환경 사건"

func update_hud() -> void:
	if not panel_root:return
	var now := Time.get_ticks_msec()
	if now<ui_next_ms:return
	ui_next_ms=now+100
	var started := Time.get_ticks_usec();var ready := connection in ["ready","paused"]
	for b in controls:b.disabled=not ready and not b.get_meta("always",false)
	var wall := float(now-generation_started_ms)/1000.
	var phase: String={"ready":"진행 중","paused":"정지","starting":"신경망 불러오는 중","warming_up":"신경망 초기 안정화 중","disconnected / error":"연결 대기","not running":"대기"}.get(connection,"연결 상태 확인 중")
	if connection=="error" or connection.begins_with("error:"):phase="신경망 또는 통신 오류 · 실행 기록 확인"
	if connection=="ready" and now-last_rx_ms>3000:phase="뇌 계산 대기 · 몸체 정지 유지"
	var preset_index := R_KEYS.find(str(console_state.get("preset",eco.mode)))
	status_label.text=phase+" · "+(R_NAMES[preset_index] if preset_index>=0 else "실험")
	clocks_label.text="환경 %.2f초 · 신경 %.2f초\n실제 경과 %.1f초" % [world_time,state.get("neural_time_s",0),wall]
	if console_state.is_empty():return
	if pending_command_id in state.get("acknowledged_commands",[]):pending_command_id=""
	var experimental: bool=console_state.get("scientific_model","frozen")!="frozen"
	if pending_command_id.is_empty():config_label.text=("2초 기준 상태 → 장시간 행동 관찰" if experimental else "0.5초 기준 상태 → 유한 자극 → 회복")+"\n모든 시간은 완료된 뇌시간 기준입니다."
	sensory_control.set_pressed_no_signal(console_state.get("sensory_enabled",true));gf_control.set_pressed_no_signal(console_state.get("gf_enabled",true))
	model_select.disabled=not ready;tonic_control.editable=ready and model_select.selected!=2
	sensory_control.disabled=not ready;gf_control.disabled=not ready
	for modality in modality_controls:
		modality_controls[modality].set_pressed_no_signal(console_state.get("modality_enabled",{}).get(modality,true))
		modality_controls[modality].disabled=not ready or console_state.get("scientific_model")!="sensorimotor"
		modality_controls[modality].tooltip_text="새 감각·운동 가설 모델에서 감각별 대조 시험을 할 수 있습니다."
	restored_control.disabled=not ready or model_select.selected==2 or not console_state.get("restored_available",false)
	restored_control.tooltip_text="연결 복원 준비가 필요합니다" if restored_control.disabled else "약 2,556만 개의 추적 뉴런 간 연결을 보존합니다"
	for idx in [7,8]:preset_select.set_item_disabled(idx,not experimental)
	if shade_mesh:
		shade_mesh.visible=console_state.shade_enabled
		if console_state.has("shade_center"):
			var c: Array=console_state.shade_center;var h: Array=console_state.shade_half_size
			shade_mesh.position=Vector3(float(c[0]),.015,float(c[2]));shade_mesh.mesh.size=Vector3(2.*float(h[0]),.015,2.*float(h[2]))
	var groups: Dictionary=console_state.groups_hz
	for key in circuit_labels:circuit_labels[key].text="%.2f 회/초" % float(groups.get(key,0.))
	for group in K_EXTRA:extra_labels[group[0]].text="%s  %.2f 회/초" % [group[1],float(groups.get(group[0],0.))]
	var perf: Dictionary=console_state.performance;var frame_ms := float(cfg.packet_neural_ms)
	var compute := float(perf.get("compute_ms",0));var total := compute+float(perf.get("integration_before_emit_ms",0))+float(perf.get("previous_body_ack_ms",0))
	var budget := "목표 시간 충족" if total<=frame_ms and total>0 else "실시간 목표 미달 · 완료 결과에 맞춰 진행"
	var backend := "동일 결과 JIT + 희소 스파이크 전달" if console_state.get("backend")=="fast" else "원본 SciPy 대조 계산"
	if experimental:backend="행동 가설 LIF · 시냅스 수 기반 · 기존 모델과 다름"
	if console_state.get("scientific_model")=="sensorimotor":backend="새 가설 · PSI 문헌 보정 / 희소 KC / DNa02 회전"
	health_label.text="뇌 1프레임 %.0f밀리초 (%d개 1밀리초 적분)\n계산 %.1f · 통신/몸체 %.1f밀리초\n중앙값 %.1f · 95백분위 %.1f밀리초\n화면 %d프레임/초 · 처리율 약 %.2f배\n%s\n%s" % [frame_ms,int(frame_ms),compute,maxf(0.,total-compute),perf.get("p50_ms",0),perf.get("p95_ms",0),int(Engine.get_frames_per_second()),frame_ms/maxf(total,.001),budget,backend]
	if perf.is_empty():health_label.text="뇌 1프레임 %.0f밀리초 (%d개 1밀리초 적분)\n첫 완료 프레임의 실제 처리 시간 측정 대기\n화면 %d프레임/초\n%s" % [frame_ms,int(frame_ms),int(Engine.get_frames_per_second()),backend]
	var lines := ""
	for e in console_state.events:
		lines+="[%.2f초] %s" % [float(e.world_time_s),event_name(str(e.event))]
		if e.has("amount"):lines+=" %.1f" % float(e.amount)
		if e.has("hp"):lines+=" → 체력 %.1f" % float(e.hp)
		lines+="\n"
	if lines!=last_event_signature:event_text.text=lines;last_event_signature=lines
	var neural_test: Dictionary=console_state.get("neural_test",{})
	var is_test := bool(neural_test.get("active",false))
	test_label.text="인위적 신경 자극 중 · 운동 뉴런에 전류 3.0 입력 → 실제 스파이크 → 기존 디코더 → 몸체" if is_test else "환경 감각 입력만 사용 중 · 인위적 운동 신경 자극 없음"
	if experimental and not is_test:test_label.text="행동 가설 모델 · 전뇌 기저 전류 %.2f (각성 가정) · 표적을 지정하는 운동 규칙 없음\n먹이 접근·그늘 선택: 아직 미인증 · 감각 %s / GF %s" % [console_state.get("tonic_current",0),"켜짐" if console_state.get("sensory_enabled",true) else "차단","켜짐" if console_state.get("gf_enabled",true) else "차단"]
	if console_state.get("scientific_model")=="sensorimotor" and not is_test:test_label.text="새 행동 가설 · 기저 전류 %.2f / 케니언 세포 최대 0.85 · 감각 %s / GF %s\n물체 접근·도약을 대조 조건과 비교하세요 · 그늘 선택 미해결 · 생물 행동 인증 아님" % [console_state.get("tonic_current",0),"켜짐" if console_state.get("sensory_enabled",true) else "차단","켜짐" if console_state.get("gf_enabled",true) else "차단"]
	if world_time>last_motion_world:
		measured_speed=fly.position.distance_to(last_motion_position)/(world_time-last_motion_world)
		last_motion_world=world_time;last_motion_position=fly.position
	var forward := float(state.get("forward",0));var turn := float(state.get("turn",0))
	if not ready:diagnosis_label.text="신경망 준비 또는 연결 확인 중 · 준비가 끝나면 실제 운동 출력을 표시합니다."
	elif connection=="paused":diagnosis_label.text="정지됨 · 진행 버튼을 누르면 완료된 신경 결과로 몸체가 갱신됩니다."
	elif forward<.0001 and absf(turn)<.0001:diagnosis_label.text="운동 출력 0 · 현재 운동 뉴런이 보행 신호를 내지 않습니다.\n왼쪽 ‘전진 뉴런 자극’으로 신경→몸체 경로를 검사할 수 있습니다."
	else:diagnosis_label.text="운동 신호 전달 중 · 전진 %.3f / 회전 %+.3f · 실제 이동 속도 %.3f 단위/뇌초" % [forward,turn,measured_speed]
	if experimental and ready:diagnosis_label.text+="\nGF 최대 %.2f / 원시 도약 기준 %.2f 회/초" % [state.get("escape_activity_hz",0),state.get("escape_threshold_hz",0)]
	if state.has("steering_difference_hz"):diagnosis_label.text+=" · DNa02 차이 %+.2f 회/초" % float(state.steering_difference_hz)
	if not last_ecology.is_empty():
		var w: Dictionary=last_ecology.world
		physiology_label.text="체력 %.1f · 허기 %.2f\n장 내용물 %.2f · 국소 온도 %.2f℃\n그늘 내부: %s\n환경 시드 %d / 뇌 시드 %d" % [w.hp,w.hunger,w.gut,w.local_temperature_c,"예" if w.in_shade else "아니요",last_ecology.world_seed,console_state.get("brain_seed",cfg.seed)]
		motor_label.text="전진 %.4f · 회전 %+.4f\n섭식 미검증 · 장 상태는 단순 모형" % [forward,turn]
		var currents := "현재 뇌 프레임의 감각 입력: "
		for term in last_ecology.sensory_terms:
			if absf(float(term.amplitude))>.001:
				var side: String={"L":"왼쪽 ","R":"오른쪽 ","U":""}.get(term.get("side","U"),"")
				var modality: String="작은 물체 움직임" if term.modality=="small_object" else K_MODALITIES.get(term.modality,"감각")
				currents+="%s%s %+.3f  " % [side,modality,term.amplitude]
		var source: Variant=last_ecology.get("sensor_source_body_seq")
		var source_text: String="초기 상태" if source==null else "몸체 응답 #%d" % int(source)
		stimulus_label.text=currents+"\n감각 기준: %s · 화면 감각 상태는 최대 한 뇌 프레임 전 입력" % source_text
		var measures: Dictionary=w.get("experiment_measurements",{})
		var food_distance: Variant=w.distances.get("food");var predator_distance: Variant=w.distances.get("predator")
		measurement_label.text="먹이 거리 %s · 포식자 거리 %s · 그늘 체류 %.2f초\n누적 경로 %.2f · 열 노출 %.2f℃·초 · 거리 감소만으로 자율 접근을 입증하지 않습니다." % ["—" if food_distance==null else "%.2f" % float(food_distance),"—" if predator_distance==null else "%.2f" % float(predator_distance),measures.get("shade_seconds",0),measures.get("path_length",0),measures.get("heat_exposure_c_s",0)]
	if camera_follow:
		world_camera.position=fly.position+Vector3(3,5,4);world_camera.look_at(fly.position);world_camera.size=6
	ui_updates+=1;var elapsed := Time.get_ticks_usec()-started;ui_total_us+=elapsed;ui_max_us=maxi(ui_max_us,elapsed)
	if qa_controls or qa_neural or qa_model:qa_driver(now)

func qa_driver(now: int) -> void:
	if qa_model:
		if connection!="ready":return
		if qa_model_stage==0 and world_time>=.2:sensory_control.button_pressed=false;qa_model_stage=1
		elif qa_model_stage==1 and not console_state.get("sensory_enabled",true):gf_control.button_pressed=false;qa_model_stage=2
		elif qa_model_stage==2 and not console_state.get("gf_enabled",true):qa_model_generation=generation;command("reset");qa_model_stage=3
		elif qa_model_stage==3 and generation>qa_model_generation:
			log_row("qa_conditions_persist",{"passed":not console_state.get("sensory_enabled",true) and not console_state.get("gf_enabled",true)})
			qa_model_generation=generation;model_select.select(2);tonic_control.value=0.;restored_control.set_pressed_no_signal(false);model_apply_button.pressed.emit();qa_model_stage=4
		elif qa_model_stage==4 and generation>qa_model_generation and console_state.get("scientific_model")=="frozen":
			log_row("qa_frozen_switch",{"passed":fly.position.distance_to(Vector3(0,.22,0))<.001 and float(state.get("forward",1))==0.})
			qa_model_generation=generation;model_select.select(1);tonic_control.value=1.5;model_apply_button.pressed.emit();qa_model_stage=5
		elif qa_model_stage==5 and generation>qa_model_generation and console_state.get("scientific_model")=="counts":
			log_row("qa_counts_switch",{"passed":not console_state.get("sensory_enabled",true) and not console_state.get("gf_enabled",true) and is_equal_approx(float(console_state.get("tonic_current",0)),1.5)})
			qa_model_stage=6
		elif qa_model_stage==6:
			qa_model_generation=generation;model_select.select(0);tonic_control.value=1.5;model_apply_button.pressed.emit();qa_model_stage=7
		elif qa_model_stage==7 and generation>qa_model_generation and console_state.get("scientific_model")=="sensorimotor":
			modality_controls["vision"].button_pressed=false;qa_model_stage=8
		elif qa_model_stage==8 and not console_state.get("modality_enabled",{}).get("vision",true):
			modality_controls["chemical"].button_pressed=false;qa_model_stage=9
		elif qa_model_stage==9 and not console_state.get("modality_enabled",{}).get("chemical",true):
			modality_controls["thermal"].button_pressed=false;qa_model_stage=10
		elif qa_model_stage==10 and not console_state.get("modality_enabled",{}).get("thermal",true):
			qa_model_generation=generation;command("reset");qa_model_stage=11
		elif qa_model_stage==11 and generation>qa_model_generation:
			var modalities: Dictionary=console_state.get("modality_enabled",{})
			log_row("qa_sensorimotor_conditions_persist",{"passed":not modalities.get("vision",true) and not modalities.get("chemical",true) and not modalities.get("thermal",true) and not console_state.get("sensory_enabled",true) and not console_state.get("gf_enabled",true)})
			qa_model_stage=12
			shutdown()
		return
	if qa_neural:
		if qa_neural_stage==0 and world_time>=.3:
			qa_neural_generation=generation;command("neural_test",{"group":"left"});qa_neural_stage=1
		elif qa_neural_stage==1 and world_time>=.9:command("neural_test",{"group":"right"});qa_neural_stage=2
		elif qa_neural_stage==2 and world_time>=1.5:command("neural_test",{"group":"forward"});qa_neural_stage=3
		elif qa_neural_stage==3 and world_time>=2.1:command("neural_test",{"group":"stop"});qa_neural_stage=4
		elif qa_neural_stage==4 and world_time>=2.7:command("reset");qa_neural_stage=5
		elif qa_neural_stage==5 and generation>qa_neural_generation:
			log_row("qa_reset",{"passed":world_time<=.04 and fly.position.distance_to(Vector3(0,.22,0))<.001});qa_neural_stage=6
		return
	if qa_stage==0 and world_time>=.3:command("pause");qa_stage=1
	elif qa_stage==1 and connection=="paused":qa_world=world_time;qa_at=now;qa_stage=2
	elif qa_stage==2 and now-qa_at>=1200:
		log_row("qa_pause",{"passed":is_equal_approx(world_time,qa_world)});command("step");qa_stage=3
	elif qa_stage==3 and connection=="paused" and world_time>qa_world:
		log_row("qa_step",{"passed":is_equal_approx(world_time-qa_world,float(cfg.packet_neural_ms)/1000.)});command("resume");qa_stage=4
