extends "res://mvp/main.gd"

const R_KEYS = ["MOTOR TEST","CONTROL","PREDATOR","FOOD","FEMALE","HEAT","PREDATOR + HEAT"]
const R_NAMES = ["운동 뉴런 자극 · 경로 검사","기본 상태 · 무자극","포식자 접근","먹이 냄새와 접촉","다른 파리","가열과 냉각","포식자와 가열"]
const K_GROUPS = [["DNp09","DNp09","전진 관련 운동 뉴런"],["DNa01","DNa01","회전 관련 운동 뉴런"],["DNa02","DNa02","회전 관련 운동 뉴런"],["lc4","LC4","다가오는 물체 감지"],["lplc2","LPLC2","확대되는 물체 감지"],["GF","GF / DNp01","하류 회로 · 도피 동작 연결은 미검증"]]
const K_EXTRA = [["figure","LC9 · 물체 움직임"],["food_odor","ORN DM1 · 먹이 냄새"],["taste","Sugar SEL PN · 중추 당 자극"],["fly_odor","ORN VA1v / VA1d · 파리 냄새"],["hot","TRN VP2 · 가열"],["cold","TRN VP3 · 냉각"],["feeding_observation","Fdg · 섭식 관찰"],["courtship_observation","pC1 계열 · 구애 회로 관찰"]]
const K_MODALITIES = {"lc4":"접근 감지","lplc2":"확대 감지","figure":"물체 움직임","food_odor":"먹이 냄새","taste":"당 접촉","fly_odor":"파리 냄새","hot":"가열","cold":"냉각"}
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

func shutdown() -> void:
	if shutdown_sent:return
	super.shutdown()
	log_file=null

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
	label(evidence,"신경 세포 정체성과 연결: 확인됨\n감각 부호화와 운동 해석: 실험적\nGF 반응만으로 도피를 뜻하지 않습니다.\n먹이 섭취·구애·자발적 회피: 미검증\n신경 통증·암컷 특이 접촉 입력: 비활성\n장·배설·체력 변화: 단순 환경/생리 모형\n운동 경로 검사는 인위적 신경 자극입니다.\n그래프는 회로별 자동 축척입니다.",16,Color("f0c780")).autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
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

func event_name(key: String) -> String:
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
	if pending_command_id.is_empty():config_label.text="0.5초 기준 상태 → 유한 자극 → 회복\n모든 시간은 실제 완료된 뇌시간 기준입니다."
	if shade_mesh:shade_mesh.visible=console_state.shade_enabled
	var groups: Dictionary=console_state.groups_hz
	for key in circuit_labels:circuit_labels[key].text="%.2f 회/초" % float(groups.get(key,0.))
	for group in K_EXTRA:extra_labels[group[0]].text="%s  %.2f 회/초" % [group[1],float(groups.get(group[0],0.))]
	var perf: Dictionary=console_state.performance;var frame_ms := float(cfg.packet_neural_ms)
	var compute := float(perf.get("compute_ms",0));var total := compute+float(perf.get("integration_before_emit_ms",0))+float(perf.get("previous_body_ack_ms",0))
	var budget := "목표 시간 충족" if total<=frame_ms and total>0 else "실시간 목표 미달 · 완료 결과에 맞춰 진행"
	var backend := "동일 결과 JIT + 희소 스파이크 전달" if console_state.get("backend")=="fast" else "원본 SciPy 대조 계산"
	health_label.text="뇌 1프레임 %.0f밀리초 (%d개 1밀리초 적분)\n계산 %.1f · 통신/몸체 %.1f밀리초\n중앙값 %.1f · 95백분위 %.1f밀리초\n화면 %d프레임/초 · 처리율 약 %.2f배\n%s\n%s" % [frame_ms,int(frame_ms),compute,maxf(0.,total-compute),perf.get("p50_ms",0),perf.get("p95_ms",0),int(Engine.get_frames_per_second()),frame_ms/maxf(total,.001),budget,backend]
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
	if world_time>last_motion_world:
		measured_speed=fly.position.distance_to(last_motion_position)/(world_time-last_motion_world)
		last_motion_world=world_time;last_motion_position=fly.position
	var forward := float(state.get("forward",0));var turn := float(state.get("turn",0))
	if connection=="paused":diagnosis_label.text="정지됨 · 진행 버튼을 누르면 완료된 신경 결과로 몸체가 갱신됩니다."
	elif forward<.0001 and absf(turn)<.0001:diagnosis_label.text="운동 출력 0 · 현재 운동 뉴런이 보행 신호를 내지 않습니다.\n왼쪽 ‘전진 뉴런 자극’으로 신경→몸체 경로를 검사할 수 있습니다."
	else:diagnosis_label.text="운동 신호 전달 중 · 전진 %.3f / 회전 %+.3f · 실제 이동 속도 %.3f 단위/뇌초" % [forward,turn,measured_speed]
	if not last_ecology.is_empty():
		var w: Dictionary=last_ecology.world
		physiology_label.text="체력 %.1f · 허기 %.2f\n장 내용물 %.2f · 체온 %.2f℃\n그늘 내부: %s\n환경 시드 %d / 뇌 시드 %d" % [w.hp,w.hunger,w.gut,w.local_temperature_c,"예" if w.in_shade else "아니요",last_ecology.world_seed,console_state.get("brain_seed",cfg.seed)]
		motor_label.text="전진 %.4f · 회전 %+.4f\n섭식 미검증 · 장 상태는 단순 모형" % [forward,turn]
		var currents := "현재 뇌 프레임의 감각 입력: "
		for term in last_ecology.sensory_terms:
			if float(term.amplitude)>.001:currents+="%s %.2f  " % [K_MODALITIES.get(term.modality,"감각"),term.amplitude]
		stimulus_label.text=currents+"\n실제 몸체 응답 #%s로 계산 · 화면 감각 상태는 최대 한 뇌 프레임 전 입력" % str(last_ecology.get("sensor_source_body_seq","—"))
	if camera_follow:
		world_camera.position=fly.position+Vector3(3,5,4);world_camera.look_at(fly.position);world_camera.size=6
	ui_updates+=1;var elapsed := Time.get_ticks_usec()-started;ui_total_us+=elapsed;ui_max_us=maxi(ui_max_us,elapsed)
	if qa_controls or qa_neural:qa_driver(now)

func qa_driver(now: int) -> void:
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
