#include <stdlib.h>
#include "objects.h"
#include <csignal>
#include <ctime>
#include <time.h>

#include "run.h"
#include "brianlib/common_math.h"

#include "code_objects/clear_incoming_codeobject.h"
#include "code_objects/clear_incoming_codeobject_1.h"
#include "code_objects/clear_incoming_codeobject_2.h"
#include "code_objects/connections_pre_codeobject.h"
#include "code_objects/connections_pre_codeobject_1.h"
#include "code_objects/connections_pre_codeobject_2.h"
#include "code_objects/connections_pre_push_spikes.h"
#include "code_objects/before_run_connections_pre_push_spikes.h"
#include "code_objects/before_run_connections_pre_push_spikes.h"
#include "code_objects/before_run_connections_pre_push_spikes.h"
#include "code_objects/connections_synapses_create_array_codeobject.h"
#include "code_objects/lif_update_codeobject.h"
#include "code_objects/lif_update_codeobject_1.h"
#include "code_objects/lif_update_codeobject_2.h"
#include "code_objects/neurons_spike_resetter_codeobject.h"
#include "code_objects/neurons_spike_resetter_codeobject_1.h"
#include "code_objects/neurons_spike_resetter_codeobject_2.h"
#include "code_objects/neurons_spike_thresholder_codeobject.h"
#include "code_objects/after_run_neurons_spike_thresholder_codeobject.h"
#include "code_objects/neurons_spike_thresholder_codeobject_1.h"
#include "code_objects/after_run_neurons_spike_thresholder_codeobject_1.h"
#include "code_objects/neurons_spike_thresholder_codeobject_2.h"
#include "code_objects/after_run_neurons_spike_thresholder_codeobject_2.h"
#include "code_objects/spikes_codeobject.h"
#include "code_objects/spikes_codeobject_1.h"
#include "code_objects/spikes_codeobject_2.h"
#include "code_objects/states_codeobject.h"
#include "code_objects/states_codeobject_1.h"
#include "code_objects/states_codeobject_2.h"

#include <chrono>

#include <iostream>
#include <fstream>
#include <string>




void set_from_command_line(const std::vector<std::string> args)
{
    for (const auto& arg : args) {
		// Split into two parts
		size_t equal_sign = arg.find("=");
		auto name = arg.substr(0, equal_sign);
		auto value = arg.substr(equal_sign + 1, arg.length());
		brian::set_variable_by_name(name, value);
	}
}

void _int_handler(int signal_num) {
	if (Network::_globally_running && !Network::_globally_stopped) {
		Network::_globally_stopped = true;
	} else {
		std::signal(signal_num, SIG_DFL);
		std::raise(signal_num);
	}
}

int main(int argc, char **argv)
{
	std::signal(SIGINT, _int_handler);
	std::random_device _rd;
	std::vector<std::string> args(argv + 1, argv + argc);
	if (args.size() >=2 && args[0] == "--results_dir")
	{
		brian::results_dir = args[1];
		#ifdef DEBUG
		std::cout << "Setting results dir to '" << brian::results_dir << "'" << std::endl;
		#endif
		args.erase(args.begin(), args.begin()+2);
	}
        
    auto gate_started = std::chrono::steady_clock::now(); auto gate_run_start = gate_started; bool gate_first = true;

	brian_start();
        

	{
		using namespace brian;

		
                
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.001;
        
                        
                        for(int i=0; i<_num__array_neurons_v; i++)
                        {
                            _array_neurons_v[i] = _static_array__array_neurons_v[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_syn; i++)
                        {
                            _array_neurons_syn[i] = _static_array__array_neurons_syn[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_baseline; i++)
                        {
                            _array_neurons_baseline[i] = _static_array__array_neurons_baseline[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_external; i++)
                        {
                            _array_neurons_external[i] = _static_array__array_neurons_external[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_ref_steps; i++)
                        {
                            _array_neurons_ref_steps[i] = _static_array__array_neurons_ref_steps[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_activity; i++)
                        {
                            _array_neurons_activity[i] = _static_array__array_neurons_activity[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_connections_sources; i++)
                        {
                            _array_connections_sources[i] = _static_array__array_connections_sources[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_connections_targets; i++)
                        {
                            _array_connections_targets[i] = _static_array__array_connections_targets[i];
                        }
                        
        _run_connections_synapses_create_array_codeobject();
        
                        
                        for(int i=0; i<_dynamic_array_connections_w.size(); i++)
                        {
                            _dynamic_array_connections_w[i] = _static_array__dynamic_array_connections_w[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_states__indices; i++)
                        {
                            _array_states__indices[i] = _static_array__array_states__indices[i];
                        }
                        
        
                std::ofstream gate_timing(brian::results_dir + "gate_timing.txt");
                gate_timing.precision(17);
                
        _array_defaultclock_timestep[0] = 0;
        _array_defaultclock_t[0] = 0.0;
        _before_run_connections_pre_push_spikes();
        network.clear();
        network.add(&defaultclock, _run_clear_incoming_codeobject);
        network.add(&defaultclock, _run_connections_pre_push_spikes);
        network.add(&defaultclock, _run_connections_pre_codeobject);
        network.add(&defaultclock, _run_lif_update_codeobject);
        network.add(&defaultclock, _run_neurons_spike_thresholder_codeobject);
        network.add(&defaultclock, _run_spikes_codeobject);
        network.add(&defaultclock, _run_neurons_spike_resetter_codeobject);
        network.add(&defaultclock, _run_states_codeobject);
        
                if (gate_first) {
                    gate_timing << "init " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_started).count() << std::endl;
                    gate_first = false;
                }
                gate_run_start = std::chrono::steady_clock::now();
                
        set_from_command_line(args);
        network.run(0.5, NULL, 10.0);
        
                gate_timing << "run " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_run_start).count() << std::endl;
                
        _after_run_neurons_spike_thresholder_codeobject();
        _array_defaultclock_timestep[0] = 500;
        _array_defaultclock_t[0] = 0.5;
        _before_run_connections_pre_push_spikes();
        network.clear();
        network.add(&defaultclock, _run_clear_incoming_codeobject_1);
        network.add(&defaultclock, _run_connections_pre_push_spikes);
        network.add(&defaultclock, _run_connections_pre_codeobject_1);
        network.add(&defaultclock, _run_lif_update_codeobject_1);
        network.add(&defaultclock, _run_neurons_spike_thresholder_codeobject_1);
        network.add(&defaultclock, _run_spikes_codeobject_1);
        network.add(&defaultclock, _run_neurons_spike_resetter_codeobject_1);
        network.add(&defaultclock, _run_states_codeobject_1);
        
                if (gate_first) {
                    gate_timing << "init " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_started).count() << std::endl;
                    gate_first = false;
                }
                gate_run_start = std::chrono::steady_clock::now();
                
        network.run(10.0, NULL, 10.0);
        
                gate_timing << "run " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_run_start).count() << std::endl;
                
        _after_run_neurons_spike_thresholder_codeobject_1();
        
                        
                        for(int i=0; i<_num__array_neurons_external; i++)
                        {
                            _array_neurons_external[i] = _static_array__array_neurons_external_1[i];
                        }
                        
        _array_defaultclock_timestep[0] = 10500;
        _array_defaultclock_t[0] = 10.5;
        _before_run_connections_pre_push_spikes();
        network.clear();
        network.add(&defaultclock, _run_clear_incoming_codeobject_2);
        network.add(&defaultclock, _run_connections_pre_push_spikes);
        network.add(&defaultclock, _run_connections_pre_codeobject_2);
        network.add(&defaultclock, _run_lif_update_codeobject_2);
        network.add(&defaultclock, _run_neurons_spike_thresholder_codeobject_2);
        network.add(&defaultclock, _run_spikes_codeobject_2);
        network.add(&defaultclock, _run_neurons_spike_resetter_codeobject_2);
        network.add(&defaultclock, _run_states_codeobject_2);
        
                if (gate_first) {
                    gate_timing << "init " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_started).count() << std::endl;
                    gate_first = false;
                }
                gate_run_start = std::chrono::steady_clock::now();
                
        network.run(10.0, NULL, 10.0);
        
                gate_timing << "run " << std::chrono::duration<double>(std::chrono::steady_clock::now()-gate_run_start).count() << std::endl;
                
        _after_run_neurons_spike_thresholder_codeobject_2();
        #ifdef DEBUG
        _debugmsg_connections_pre_codeobject();
        #endif
        
        #ifdef DEBUG
        _debugmsg_spikes_codeobject();
        #endif
        
        #ifdef DEBUG
        _debugmsg_connections_pre_codeobject_1();
        #endif
        
        #ifdef DEBUG
        _debugmsg_spikes_codeobject_1();
        #endif
        
        #ifdef DEBUG
        _debugmsg_connections_pre_codeobject_2();
        #endif
        
        #ifdef DEBUG
        _debugmsg_spikes_codeobject_2();
        #endif

	}
        

	brian_end();
        

	return 0;
}