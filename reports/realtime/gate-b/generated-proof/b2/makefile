PROGRAM = main

SRCS = code_objects/after_run_neurons_spike_thresholder_codeobject.cpp code_objects/before_run_connections_pre_push_spikes.cpp code_objects/clear_incoming_codeobject.cpp code_objects/connections_pre_codeobject.cpp code_objects/connections_pre_push_spikes.cpp code_objects/connections_synapses_create_array_codeobject.cpp code_objects/lif_update_codeobject.cpp code_objects/neurons_spike_resetter_codeobject.cpp code_objects/neurons_spike_thresholder_codeobject.cpp code_objects/quantum_boundary_codeobject.cpp code_objects/spikes_codeobject.cpp main.cpp network.cpp objects.cpp run.cpp synapses_classes.cpp
H_SRCS = brianlib/clocks.h brianlib/common_math.h brianlib/dynamic_array.h code_objects/after_run_neurons_spike_thresholder_codeobject.h code_objects/before_run_connections_pre_push_spikes.h code_objects/clear_incoming_codeobject.h code_objects/connections_pre_codeobject.h code_objects/connections_pre_push_spikes.h code_objects/connections_synapses_create_array_codeobject.h code_objects/lif_update_codeobject.h code_objects/neurons_spike_resetter_codeobject.h code_objects/neurons_spike_thresholder_codeobject.h code_objects/quantum_boundary_codeobject.h code_objects/spikes_codeobject.h network.h objects.h run.h synapses_classes.h
OBJS = ${SRCS:.cpp=.o}
OBJS := ${OBJS:.c=.o}
OPTIMISATIONS = -I"C:\Users\PC\Documents\Codex\2026-09-13\https-wonju-station-live-tsiba5021-chatgpt\outputs\brain-core\.venv\Library\include" -O3 -march=native -std=c++17
CXXFLAGS = -c -Wno-write-strings $(OPTIMISATIONS) -I.  
LFLAGS =  -L"C:\Users\PC\Documents\Codex\2026-09-13\https-wonju-station-live-tsiba5021-chatgpt\outputs\brain-core\.venv\Library\lib" -ladvapi32 
DEPS = make.deps

all: $(PROGRAM)

.PHONY: all clean

$(PROGRAM): $(OBJS) $(DEPS) makefile
	$(CXX) $(OBJS) -o $(PROGRAM) $(LFLAGS)

clean:
	del *.o /s
	del main.exe $(DEPS)

make.deps: $(SRCS) $(H_SRCS)
	$(CXX) $(CXXFLAGS) -MM $(SRCS) > make.deps
	
ifneq ($(wildcard $(DEPS)), )
include $(DEPS)
endif

%.o : %.cpp makefile
	$(CXX) $(CXXFLAGS) $< -o $@