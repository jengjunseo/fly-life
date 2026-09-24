#include <stdlib.h>
#include "objects.h"
#include <csignal>
#include <ctime>
#include <time.h>

#include "run.h"
#include "brianlib/common_math.h"

#include "code_objects/clear_incoming_codeobject.h"
#include "code_objects/connections_pre_codeobject.h"
#include "code_objects/connections_pre_push_spikes.h"
#include "code_objects/before_run_connections_pre_push_spikes.h"
#include "code_objects/connections_synapses_create_array_codeobject.h"
#include "code_objects/lif_update_codeobject.h"
#include "code_objects/neurons_spike_resetter_codeobject.h"
#include "code_objects/neurons_spike_thresholder_codeobject.h"
#include "code_objects/after_run_neurons_spike_thresholder_codeobject.h"
#include "code_objects/quantum_boundary_codeobject.h"
#include "code_objects/spikes_codeobject.h"

#include "gate_hooks.h"

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
        
    gate_b::begun = gate_b::GateClock::now();

	brian_start();
        

	{
		using namespace brian;

		
                
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.001;
        for (int _i=0; _i<1; _i++)
            brian::_random_generators[_i].seed(20260913L + _i);
        
                        
                        for(int i=0; i<_num__array_neurons_baseline; i++)
                        {
                            _array_neurons_baseline[i] = _static_array__array_neurons_baseline[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_v; i++)
                        {
                            _array_neurons_v[i] = _static_array__array_neurons_v[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_syn; i++)
                        {
                            _array_neurons_syn[i] = _static_array__array_neurons_syn[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_ref_steps; i++)
                        {
                            _array_neurons_ref_steps[i] = _static_array__array_neurons_ref_steps[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_activity; i++)
                        {
                            _array_neurons_activity[i] = _static_array__array_neurons_activity[i];
                        }
                        
        
                        
                        for(int i=0; i<_num__array_neurons_external; i++)
                        {
                            _array_neurons_external[i] = 0;
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
                        
        
                gate_b::windows_file.open(brian::results_dir+"windows.txt");gate_b::windows_file.precision(17);
                gate_b::timing_file.open(brian::results_dir+"timing.txt");gate_b::timing_file.precision(17);
                gate_b::input.resize(352800);gate_b::pool.resize(882);
                {std::ifstream f("C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/work/brian2-gate-c/c2-native-1t-cpp/stimulus.bin",std::ios::binary);f.read(reinterpret_cast<char*>(gate_b::input.data()),1411200);if(!f)throw std::runtime_error("input read");}
                {std::ifstream f("C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/work/brian2-gate-c/c2-native-1t-cpp/pool.bin",std::ios::binary);f.read(reinterpret_cast<char*>(gate_b::pool.data()),3528);if(!f)throw std::runtime_error("pool read");}
                for(int j=0;j<882;++j)brian::_array_neurons_external[gate_b::pool[j]]=gate_b::input[j];
                
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
        network.add(&defaultclock, _run_quantum_boundary_codeobject);
        
                gate_b::timing_file << "init " << std::chrono::duration<double>(gate_b::GateClock::now()-gate_b::begun).count() << std::endl;
                gate_b::window_start = gate_b::GateClock::now();
                auto simulation_started = gate_b::window_start;
                
        set_from_command_line(args);
        network.run(20.0, NULL, 10.0);
        
                gate_b::timing_file << "network_compute " << std::chrono::duration<double>(gate_b::GateClock::now()-simulation_started).count() << std::endl;
                gate_b::timing_file << "windows_compute " << gate_b::wall_sum*.001 << std::endl;
                
        _after_run_neurons_spike_thresholder_codeobject();
        #ifdef DEBUG
        _debugmsg_connections_pre_codeobject();
        #endif
        
        #ifdef DEBUG
        _debugmsg_spikes_codeobject();
        #endif

	}
        
    gate_b::output_start = gate_b::GateClock::now();

	brian_end();
        
    gate_b::timing_file << "brian_output " << std::chrono::duration<double>(gate_b::GateClock::now()-gate_b::output_start).count() << std::endl;

	return 0;
}