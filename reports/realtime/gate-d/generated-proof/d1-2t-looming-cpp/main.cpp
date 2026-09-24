#include <stdlib.h>
#include "objects.h"
#include <csignal>
#include <ctime>
#include <time.h>
#include <omp.h>
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
#include "code_objects/shared_noise_reader_codeobject.h"
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

		omp_set_dynamic(0);
omp_set_num_threads(2);
                
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.0001;
        _array_defaultclock_dt[0] = 0.001;
        for (int _i=0; _i<2; _i++)
            brian::_random_generators[_i].seed(20260913L + _i);
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_neurons_baseline; i++)
                        {
                            _array_neurons_baseline[i] = _static_array__array_neurons_baseline[i];
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_neurons_v; i++)
                        {
                            _array_neurons_v[i] = _static_array__array_neurons_v[i];
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_neurons_syn; i++)
                        {
                            _array_neurons_syn[i] = _static_array__array_neurons_syn[i];
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_neurons_ref_steps; i++)
                        {
                            _array_neurons_ref_steps[i] = _static_array__array_neurons_ref_steps[i];
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_neurons_activity; i++)
                        {
                            _array_neurons_activity[i] = _static_array__array_neurons_activity[i];
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_neurons_external; i++)
                        {
                            _array_neurons_external[i] = 0;
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_connections_sources; i++)
                        {
                            _array_connections_sources[i] = _static_array__array_connections_sources[i];
                        }
                        
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_num__array_connections_targets; i++)
                        {
                            _array_connections_targets[i] = _static_array__array_connections_targets[i];
                        }
                        
        _run_connections_synapses_create_array_codeobject();
        
                        #pragma omp for schedule(static)
                        for(int i=0; i<_dynamic_array_connections_w.size(); i++)
                        {
                            _dynamic_array_connections_w[i] = _static_array__dynamic_array_connections_w[i];
                        }
                        
        
                gate_b::windows_file.open(brian::results_dir+"windows.txt");gate_b::windows_file.precision(17);
                gate_b::timing_file.open(brian::results_dir+"timing.txt");gate_b::timing_file.precision(17);
                gate_b::input.resize(35280);gate_b::pool.resize(882);
                {std::ifstream f("C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/work/brian2-gate-d/d1-2t-looming-cpp/stimulus.bin",std::ios::binary);f.read(reinterpret_cast<char*>(gate_b::input.data()),141120);if(!f)throw std::runtime_error("input read");}
                {std::ifstream f("C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/work/brian2-gate-d/d1-2t-looming-cpp/pool.bin",std::ios::binary);f.read(reinterpret_cast<char*>(gate_b::pool.data()),3528);if(!f)throw std::runtime_error("pool read");}
                for(int j=0;j<882;++j)brian::_array_neurons_external[gate_b::pool[j]]=gate_b::input[j];
                gate_b::noise_file.open("C:/Users/PC/Documents/Codex/2026-09-13/https-wonju-station-live-tsiba5021-chatgpt/work/brian2-gate-b/noise-b0-float32.bin",std::ios::binary);
        gate_d_noise.resize(2000LL*165122);
        gate_b::noise_file.read(reinterpret_cast<char*>(gate_d_noise.data()),2000LL*165122*4);
        if(!gate_b::noise_file)throw std::runtime_error("Tape preload");gate_b::noise_file.close();
        _array_defaultclock_timestep[0] = 0;
        _array_defaultclock_t[0] = 0.0;
        _before_run_connections_pre_push_spikes();
        network.clear();
        network.add(&defaultclock, _run_clear_incoming_codeobject);
        network.add(&defaultclock, _run_shared_noise_reader_codeobject);
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
                
        
        {std::ofstream f(brian::results_dir+"ready");f<<GetCurrentProcessId();}
        while(GetFileAttributesA((brian::results_dir+"go").c_str())==INVALID_FILE_ATTRIBUTES)Sleep(1);
        {DWORD_PTR processmask,systemmask;GetProcessAffinityMask(GetCurrentProcess(),&processmask,&systemmask);
        std::ofstream f(brian::results_dir+"affinity");f<<processmask;}
        {std::ofstream f(brian::results_dir+"compute-start");f.precision(17);f<<gate_d_qpc();}
        gate_b::window_start=gate_b::GateClock::now();simulation_started=gate_b::window_start;
        
        set_from_command_line(args);
        network.run(2.0, NULL, 10.0);
        
                gate_b::timing_file << "network_compute " << std::chrono::duration<double>(gate_b::GateClock::now()-simulation_started).count() << std::endl;
                gate_b::timing_file << "windows_compute " << gate_b::wall_sum*.001 << std::endl;
                
        {std::ofstream f(brian::results_dir+"compute-done");f.precision(17);f<<gate_d_qpc();}
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