

#include "objects.h"
#include "synapses_classes.h"
#include "brianlib/clocks.h"
#include "brianlib/dynamic_array.h"
#include "brianlib/stdint_compat.h"
#include "network.h"
#include<random>
#include<vector>
#include<iostream>
#include<fstream>
#include<map>
#include<tuple>
#include<cstdlib>
#include<string>

namespace brian {

std::string results_dir = "results/";  // can be overwritten by --results_dir command line arg

// For multhreading, we need one generator for each thread. We also create a distribution for
// each thread, even though this is not strictly necessary for the uniform distribution, as
// the distribution is stateless.
std::vector< RandomGenerator > _random_generators;

//////////////// networks /////////////////
Network network;

void set_variable_from_value(std::string varname, char* var_pointer, size_t size, char value) {
    #ifdef DEBUG
    std::cout << "Setting '" << varname << "' to " << (value == 1 ? "True" : "False") << std::endl;
    #endif
    std::fill(var_pointer, var_pointer+size, value);
}

template<class T> void set_variable_from_value(std::string varname, T* var_pointer, size_t size, T value) {
    #ifdef DEBUG
    std::cout << "Setting '" << varname << "' to " << value << std::endl;
    #endif
    std::fill(var_pointer, var_pointer+size, value);
}

template<class T> void set_variable_from_file(std::string varname, T* var_pointer, size_t data_size, std::string filename) {
    ifstream f;
    streampos size;
    #ifdef DEBUG
    std::cout << "Setting '" << varname << "' from file '" << filename << "'" << std::endl;
    #endif
    f.open(filename, ios::in | ios::binary | ios::ate);
    size = f.tellg();
    if (size != data_size) {
        std::cerr << "Error reading '" << filename << "': file size " << size << " does not match expected size " << data_size << std::endl;
        return;
    }
    f.seekg(0, ios::beg);
    if (f.is_open())
        f.read(reinterpret_cast<char *>(var_pointer), data_size);
    else
        std::cerr << "Could not read '" << filename << "'" << std::endl;
    if (f.fail())
        std::cerr << "Error reading '" << filename << "'" << std::endl;
}

//////////////// set arrays by name ///////
void set_variable_by_name(std::string name, std::string s_value) {
    size_t var_size;
    size_t data_size;
    // C-style or Python-style capitalization is allowed for boolean values
    if (s_value == "true" || s_value == "True")
        s_value = "1";
    else if (s_value == "false" || s_value == "False")
        s_value = "0";
    // non-dynamic arrays
    if (name == "boundary.dummy") {
        var_size = 1;
        data_size = 1*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_boundary_dummy, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_boundary_dummy, data_size, s_value);
        }
        return;
    }
    if (name == "neurons._spikespace") {
        var_size = 165123;
        data_size = 165123*sizeof(int32_t);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<int32_t>(name, _array_neurons__spikespace, var_size, (int32_t)atoi(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons__spikespace, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.activity") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_activity, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_activity, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.baseline") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_baseline, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_baseline, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.eligible") {
        var_size = 165122;
        data_size = 165122*sizeof(int32_t);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<int32_t>(name, _array_neurons_eligible, var_size, (int32_t)atoi(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_eligible, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.external") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_external, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_external, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.incoming") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_incoming, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_incoming, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.noise_sample") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_noise_sample, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_noise_sample, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.ref_steps") {
        var_size = 165122;
        data_size = 165122*sizeof(int32_t);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<int32_t>(name, _array_neurons_ref_steps, var_size, (int32_t)atoi(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_ref_steps, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.syn") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_syn, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_syn, data_size, s_value);
        }
        return;
    }
    if (name == "neurons.v") {
        var_size = 165122;
        data_size = 165122*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, _array_neurons_v, var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, _array_neurons_v, data_size, s_value);
        }
        return;
    }
    // dynamic arrays (1d)
    if (name == "connections.delay") {
        var_size = _dynamic_array_connections_delay.size();
        data_size = var_size*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, &_dynamic_array_connections_delay[0], var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, &_dynamic_array_connections_delay[0], data_size, s_value);
        }
        return;
    }
    if (name == "connections.w") {
        var_size = _dynamic_array_connections_w.size();
        data_size = var_size*sizeof(float);
        if (s_value[0] == '-' || (s_value[0] >= '0' && s_value[0] <= '9')) {
            // set from single value
            set_variable_from_value<float>(name, &_dynamic_array_connections_w[0], var_size, (float)atof(s_value.c_str()));

        } else {
            // set from file
            set_variable_from_file(name, &_dynamic_array_connections_w[0], data_size, s_value);
        }
        return;
    }
    std::cerr << "Cannot set unknown variable '" << name << "'." << std::endl;
    exit(1);
}
//////////////// arrays ///////////////////
float * _array_boundary_dummy;
const int _num__array_boundary_dummy = 1;
int32_t * _array_boundary_i;
const int _num__array_boundary_i = 1;
int32_t * _array_connections_N;
const int _num__array_connections_N = 1;
int32_t * _array_connections_sources;
const int _num__array_connections_sources = 6327564;
int32_t * _array_connections_targets;
const int _num__array_connections_targets = 6327564;
double * _array_defaultclock_dt;
const int _num__array_defaultclock_dt = 1;
double * _array_defaultclock_t;
const int _num__array_defaultclock_t = 1;
int64_t * _array_defaultclock_timestep;
const int _num__array_defaultclock_timestep = 1;
int32_t * _array_neurons__spikespace;
const int _num__array_neurons__spikespace = 165123;
float * _array_neurons_activity;
const int _num__array_neurons_activity = 165122;
float * _array_neurons_baseline;
const int _num__array_neurons_baseline = 165122;
int32_t * _array_neurons_eligible;
const int _num__array_neurons_eligible = 165122;
float * _array_neurons_external;
const int _num__array_neurons_external = 165122;
int32_t * _array_neurons_i;
const int _num__array_neurons_i = 165122;
float * _array_neurons_incoming;
const int _num__array_neurons_incoming = 165122;
float * _array_neurons_noise_sample;
const int _num__array_neurons_noise_sample = 165122;
int32_t * _array_neurons_ref_steps;
const int _num__array_neurons_ref_steps = 165122;
float * _array_neurons_syn;
const int _num__array_neurons_syn = 165122;
float * _array_neurons_v;
const int _num__array_neurons_v = 165122;
int32_t * _array_spikes__source_idx;
const int _num__array_spikes__source_idx = 165122;
int32_t * _array_spikes_count;
const int _num__array_spikes_count = 165122;
int32_t * _array_spikes_N;
const int _num__array_spikes_N = 1;

//////////////// dynamic arrays 1d /////////
std::vector<int32_t> _dynamic_array_connections__synaptic_post;
std::vector<int32_t> _dynamic_array_connections__synaptic_pre;
std::vector<float> _dynamic_array_connections_delay;
std::vector<int32_t> _dynamic_array_connections_N_incoming;
std::vector<int32_t> _dynamic_array_connections_N_outgoing;
std::vector<float> _dynamic_array_connections_w;
std::vector<int32_t> _dynamic_array_spikes_i;
std::vector<double> _dynamic_array_spikes_t;

//////////////// dynamic arrays 2d /////////

/////////////// static arrays /////////////
int32_t * _static_array__array_connections_sources;
const int _num__static_array__array_connections_sources = 6327564;
int32_t * _static_array__array_connections_targets;
const int _num__static_array__array_connections_targets = 6327564;
float * _static_array__array_neurons_activity;
const int _num__static_array__array_neurons_activity = 165122;
float * _static_array__array_neurons_baseline;
const int _num__static_array__array_neurons_baseline = 165122;
int32_t * _static_array__array_neurons_ref_steps;
const int _num__static_array__array_neurons_ref_steps = 165122;
float * _static_array__array_neurons_syn;
const int _num__static_array__array_neurons_syn = 165122;
float * _static_array__array_neurons_v;
const int _num__static_array__array_neurons_v = 165122;
float * _static_array__dynamic_array_connections_w;
const int _num__static_array__dynamic_array_connections_w = 6327564;

//////////////// synapses /////////////////
// connections
SynapticPathway connections_pre(
    _dynamic_array_connections__synaptic_pre,
    0, 165122);

//////////////// clocks ///////////////////
Clock defaultclock;  // attributes will be set in run.cpp

// Profiling information for each code object
}

void _init_arrays()
{
    using namespace brian;

    // Arrays initialized to 0
    _array_boundary_dummy = new float[1];
    
    for(int i=0; i<1; i++) _array_boundary_dummy[i] = 0;

    _array_boundary_i = new int32_t[1];
    
    for(int i=0; i<1; i++) _array_boundary_i[i] = 0;

    _array_connections_N = new int32_t[1];
    
    for(int i=0; i<1; i++) _array_connections_N[i] = 0;

    _array_connections_sources = new int32_t[6327564];
    
    for(int i=0; i<6327564; i++) _array_connections_sources[i] = 0;

    _array_connections_targets = new int32_t[6327564];
    
    for(int i=0; i<6327564; i++) _array_connections_targets[i] = 0;

    _array_defaultclock_dt = new double[1];
    
    for(int i=0; i<1; i++) _array_defaultclock_dt[i] = 0;

    _array_defaultclock_t = new double[1];
    
    for(int i=0; i<1; i++) _array_defaultclock_t[i] = 0;

    _array_defaultclock_timestep = new int64_t[1];
    
    for(int i=0; i<1; i++) _array_defaultclock_timestep[i] = 0;

    _array_neurons__spikespace = new int32_t[165123];
    
    for(int i=0; i<165123; i++) _array_neurons__spikespace[i] = 0;

    _array_neurons_activity = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_activity[i] = 0;

    _array_neurons_baseline = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_baseline[i] = 0;

    _array_neurons_eligible = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_eligible[i] = 0;

    _array_neurons_external = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_external[i] = 0;

    _array_neurons_i = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_i[i] = 0;

    _array_neurons_incoming = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_incoming[i] = 0;

    _array_neurons_noise_sample = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_noise_sample[i] = 0;

    _array_neurons_ref_steps = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_ref_steps[i] = 0;

    _array_neurons_syn = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_syn[i] = 0;

    _array_neurons_v = new float[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_v[i] = 0;

    _array_spikes__source_idx = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_spikes__source_idx[i] = 0;

    _array_spikes_count = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_spikes_count[i] = 0;

    _array_spikes_N = new int32_t[1];
    
    for(int i=0; i<1; i++) _array_spikes_N[i] = 0;


    // Arrays initialized to an "arange"
    _array_boundary_i = new int32_t[1];
    
    for(int i=0; i<1; i++) _array_boundary_i[i] = 0 + i;

    _array_neurons_i = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_neurons_i[i] = 0 + i;

    _array_spikes__source_idx = new int32_t[165122];
    
    for(int i=0; i<165122; i++) _array_spikes__source_idx[i] = 0 + i;


    // static arrays
    _static_array__array_connections_sources = new int32_t[6327564];
    _static_array__array_connections_targets = new int32_t[6327564];
    _static_array__array_neurons_activity = new float[165122];
    _static_array__array_neurons_baseline = new float[165122];
    _static_array__array_neurons_ref_steps = new int32_t[165122];
    _static_array__array_neurons_syn = new float[165122];
    _static_array__array_neurons_v = new float[165122];
    _static_array__dynamic_array_connections_w = new float[6327564];

    // Random number generator states
    std::random_device rd;
    for (int i=0; i<1; i++)
        _random_generators.push_back(RandomGenerator());
}

void _load_arrays()
{
    using namespace brian;

    ifstream f_static_array__array_connections_sources;
    f_static_array__array_connections_sources.open("static_arrays/_static_array__array_connections_sources", ios::in | ios::binary);
    if(f_static_array__array_connections_sources.is_open())
    {
        f_static_array__array_connections_sources.read(reinterpret_cast<char*>(_static_array__array_connections_sources), 6327564*sizeof(int32_t));
    } else
    {
        std::cout << "Error opening static array _static_array__array_connections_sources." << endl;
    }
    ifstream f_static_array__array_connections_targets;
    f_static_array__array_connections_targets.open("static_arrays/_static_array__array_connections_targets", ios::in | ios::binary);
    if(f_static_array__array_connections_targets.is_open())
    {
        f_static_array__array_connections_targets.read(reinterpret_cast<char*>(_static_array__array_connections_targets), 6327564*sizeof(int32_t));
    } else
    {
        std::cout << "Error opening static array _static_array__array_connections_targets." << endl;
    }
    ifstream f_static_array__array_neurons_activity;
    f_static_array__array_neurons_activity.open("static_arrays/_static_array__array_neurons_activity", ios::in | ios::binary);
    if(f_static_array__array_neurons_activity.is_open())
    {
        f_static_array__array_neurons_activity.read(reinterpret_cast<char*>(_static_array__array_neurons_activity), 165122*sizeof(float));
    } else
    {
        std::cout << "Error opening static array _static_array__array_neurons_activity." << endl;
    }
    ifstream f_static_array__array_neurons_baseline;
    f_static_array__array_neurons_baseline.open("static_arrays/_static_array__array_neurons_baseline", ios::in | ios::binary);
    if(f_static_array__array_neurons_baseline.is_open())
    {
        f_static_array__array_neurons_baseline.read(reinterpret_cast<char*>(_static_array__array_neurons_baseline), 165122*sizeof(float));
    } else
    {
        std::cout << "Error opening static array _static_array__array_neurons_baseline." << endl;
    }
    ifstream f_static_array__array_neurons_ref_steps;
    f_static_array__array_neurons_ref_steps.open("static_arrays/_static_array__array_neurons_ref_steps", ios::in | ios::binary);
    if(f_static_array__array_neurons_ref_steps.is_open())
    {
        f_static_array__array_neurons_ref_steps.read(reinterpret_cast<char*>(_static_array__array_neurons_ref_steps), 165122*sizeof(int32_t));
    } else
    {
        std::cout << "Error opening static array _static_array__array_neurons_ref_steps." << endl;
    }
    ifstream f_static_array__array_neurons_syn;
    f_static_array__array_neurons_syn.open("static_arrays/_static_array__array_neurons_syn", ios::in | ios::binary);
    if(f_static_array__array_neurons_syn.is_open())
    {
        f_static_array__array_neurons_syn.read(reinterpret_cast<char*>(_static_array__array_neurons_syn), 165122*sizeof(float));
    } else
    {
        std::cout << "Error opening static array _static_array__array_neurons_syn." << endl;
    }
    ifstream f_static_array__array_neurons_v;
    f_static_array__array_neurons_v.open("static_arrays/_static_array__array_neurons_v", ios::in | ios::binary);
    if(f_static_array__array_neurons_v.is_open())
    {
        f_static_array__array_neurons_v.read(reinterpret_cast<char*>(_static_array__array_neurons_v), 165122*sizeof(float));
    } else
    {
        std::cout << "Error opening static array _static_array__array_neurons_v." << endl;
    }
    ifstream f_static_array__dynamic_array_connections_w;
    f_static_array__dynamic_array_connections_w.open("static_arrays/_static_array__dynamic_array_connections_w", ios::in | ios::binary);
    if(f_static_array__dynamic_array_connections_w.is_open())
    {
        f_static_array__dynamic_array_connections_w.read(reinterpret_cast<char*>(_static_array__dynamic_array_connections_w), 6327564*sizeof(float));
    } else
    {
        std::cout << "Error opening static array _static_array__dynamic_array_connections_w." << endl;
    }
}

void _write_arrays()
{
    using namespace brian;

    ofstream outfile__array_boundary_dummy;
    outfile__array_boundary_dummy.open(results_dir + "_array_boundary_dummy_2652504583", ios::binary | ios::out);
    if(outfile__array_boundary_dummy.is_open())
    {
        outfile__array_boundary_dummy.write(reinterpret_cast<char*>(_array_boundary_dummy), 1*sizeof(_array_boundary_dummy[0]));
        outfile__array_boundary_dummy.close();
    } else
    {
        std::cout << "Error writing output file for _array_boundary_dummy." << endl;
    }
    ofstream outfile__array_boundary_i;
    outfile__array_boundary_i.open(results_dir + "_array_boundary_i_1003826452", ios::binary | ios::out);
    if(outfile__array_boundary_i.is_open())
    {
        outfile__array_boundary_i.write(reinterpret_cast<char*>(_array_boundary_i), 1*sizeof(_array_boundary_i[0]));
        outfile__array_boundary_i.close();
    } else
    {
        std::cout << "Error writing output file for _array_boundary_i." << endl;
    }
    ofstream outfile__array_connections_N;
    outfile__array_connections_N.open(results_dir + "_array_connections_N_2447535006", ios::binary | ios::out);
    if(outfile__array_connections_N.is_open())
    {
        outfile__array_connections_N.write(reinterpret_cast<char*>(_array_connections_N), 1*sizeof(_array_connections_N[0]));
        outfile__array_connections_N.close();
    } else
    {
        std::cout << "Error writing output file for _array_connections_N." << endl;
    }
    ofstream outfile__array_connections_sources;
    outfile__array_connections_sources.open(results_dir + "_array_connections_sources_2750316304", ios::binary | ios::out);
    if(outfile__array_connections_sources.is_open())
    {
        outfile__array_connections_sources.write(reinterpret_cast<char*>(_array_connections_sources), 6327564*sizeof(_array_connections_sources[0]));
        outfile__array_connections_sources.close();
    } else
    {
        std::cout << "Error writing output file for _array_connections_sources." << endl;
    }
    ofstream outfile__array_connections_targets;
    outfile__array_connections_targets.open(results_dir + "_array_connections_targets_3740271857", ios::binary | ios::out);
    if(outfile__array_connections_targets.is_open())
    {
        outfile__array_connections_targets.write(reinterpret_cast<char*>(_array_connections_targets), 6327564*sizeof(_array_connections_targets[0]));
        outfile__array_connections_targets.close();
    } else
    {
        std::cout << "Error writing output file for _array_connections_targets." << endl;
    }
    ofstream outfile__array_defaultclock_dt;
    outfile__array_defaultclock_dt.open(results_dir + "_array_defaultclock_dt_1978099143", ios::binary | ios::out);
    if(outfile__array_defaultclock_dt.is_open())
    {
        outfile__array_defaultclock_dt.write(reinterpret_cast<char*>(_array_defaultclock_dt), 1*sizeof(_array_defaultclock_dt[0]));
        outfile__array_defaultclock_dt.close();
    } else
    {
        std::cout << "Error writing output file for _array_defaultclock_dt." << endl;
    }
    ofstream outfile__array_defaultclock_t;
    outfile__array_defaultclock_t.open(results_dir + "_array_defaultclock_t_2669362164", ios::binary | ios::out);
    if(outfile__array_defaultclock_t.is_open())
    {
        outfile__array_defaultclock_t.write(reinterpret_cast<char*>(_array_defaultclock_t), 1*sizeof(_array_defaultclock_t[0]));
        outfile__array_defaultclock_t.close();
    } else
    {
        std::cout << "Error writing output file for _array_defaultclock_t." << endl;
    }
    ofstream outfile__array_defaultclock_timestep;
    outfile__array_defaultclock_timestep.open(results_dir + "_array_defaultclock_timestep_144223508", ios::binary | ios::out);
    if(outfile__array_defaultclock_timestep.is_open())
    {
        outfile__array_defaultclock_timestep.write(reinterpret_cast<char*>(_array_defaultclock_timestep), 1*sizeof(_array_defaultclock_timestep[0]));
        outfile__array_defaultclock_timestep.close();
    } else
    {
        std::cout << "Error writing output file for _array_defaultclock_timestep." << endl;
    }
    ofstream outfile__array_neurons__spikespace;
    outfile__array_neurons__spikespace.open(results_dir + "_array_neurons__spikespace_3270573894", ios::binary | ios::out);
    if(outfile__array_neurons__spikespace.is_open())
    {
        outfile__array_neurons__spikespace.write(reinterpret_cast<char*>(_array_neurons__spikespace), 165123*sizeof(_array_neurons__spikespace[0]));
        outfile__array_neurons__spikespace.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons__spikespace." << endl;
    }
    ofstream outfile__array_neurons_activity;
    outfile__array_neurons_activity.open(results_dir + "_array_neurons_activity_1624049166", ios::binary | ios::out);
    if(outfile__array_neurons_activity.is_open())
    {
        outfile__array_neurons_activity.write(reinterpret_cast<char*>(_array_neurons_activity), 165122*sizeof(_array_neurons_activity[0]));
        outfile__array_neurons_activity.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_activity." << endl;
    }
    ofstream outfile__array_neurons_baseline;
    outfile__array_neurons_baseline.open(results_dir + "_array_neurons_baseline_983620626", ios::binary | ios::out);
    if(outfile__array_neurons_baseline.is_open())
    {
        outfile__array_neurons_baseline.write(reinterpret_cast<char*>(_array_neurons_baseline), 165122*sizeof(_array_neurons_baseline[0]));
        outfile__array_neurons_baseline.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_baseline." << endl;
    }
    ofstream outfile__array_neurons_eligible;
    outfile__array_neurons_eligible.open(results_dir + "_array_neurons_eligible_2156051207", ios::binary | ios::out);
    if(outfile__array_neurons_eligible.is_open())
    {
        outfile__array_neurons_eligible.write(reinterpret_cast<char*>(_array_neurons_eligible), 165122*sizeof(_array_neurons_eligible[0]));
        outfile__array_neurons_eligible.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_eligible." << endl;
    }
    ofstream outfile__array_neurons_external;
    outfile__array_neurons_external.open(results_dir + "_array_neurons_external_2498473708", ios::binary | ios::out);
    if(outfile__array_neurons_external.is_open())
    {
        outfile__array_neurons_external.write(reinterpret_cast<char*>(_array_neurons_external), 165122*sizeof(_array_neurons_external[0]));
        outfile__array_neurons_external.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_external." << endl;
    }
    ofstream outfile__array_neurons_i;
    outfile__array_neurons_i.open(results_dir + "_array_neurons_i_2509429918", ios::binary | ios::out);
    if(outfile__array_neurons_i.is_open())
    {
        outfile__array_neurons_i.write(reinterpret_cast<char*>(_array_neurons_i), 165122*sizeof(_array_neurons_i[0]));
        outfile__array_neurons_i.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_i." << endl;
    }
    ofstream outfile__array_neurons_incoming;
    outfile__array_neurons_incoming.open(results_dir + "_array_neurons_incoming_2388045022", ios::binary | ios::out);
    if(outfile__array_neurons_incoming.is_open())
    {
        outfile__array_neurons_incoming.write(reinterpret_cast<char*>(_array_neurons_incoming), 165122*sizeof(_array_neurons_incoming[0]));
        outfile__array_neurons_incoming.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_incoming." << endl;
    }
    ofstream outfile__array_neurons_noise_sample;
    outfile__array_neurons_noise_sample.open(results_dir + "_array_neurons_noise_sample_2030006126", ios::binary | ios::out);
    if(outfile__array_neurons_noise_sample.is_open())
    {
        outfile__array_neurons_noise_sample.write(reinterpret_cast<char*>(_array_neurons_noise_sample), 165122*sizeof(_array_neurons_noise_sample[0]));
        outfile__array_neurons_noise_sample.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_noise_sample." << endl;
    }
    ofstream outfile__array_neurons_ref_steps;
    outfile__array_neurons_ref_steps.open(results_dir + "_array_neurons_ref_steps_723731282", ios::binary | ios::out);
    if(outfile__array_neurons_ref_steps.is_open())
    {
        outfile__array_neurons_ref_steps.write(reinterpret_cast<char*>(_array_neurons_ref_steps), 165122*sizeof(_array_neurons_ref_steps[0]));
        outfile__array_neurons_ref_steps.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_ref_steps." << endl;
    }
    ofstream outfile__array_neurons_syn;
    outfile__array_neurons_syn.open(results_dir + "_array_neurons_syn_1681397312", ios::binary | ios::out);
    if(outfile__array_neurons_syn.is_open())
    {
        outfile__array_neurons_syn.write(reinterpret_cast<char*>(_array_neurons_syn), 165122*sizeof(_array_neurons_syn[0]));
        outfile__array_neurons_syn.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_syn." << endl;
    }
    ofstream outfile__array_neurons_v;
    outfile__array_neurons_v.open(results_dir + "_array_neurons_v_412799339", ios::binary | ios::out);
    if(outfile__array_neurons_v.is_open())
    {
        outfile__array_neurons_v.write(reinterpret_cast<char*>(_array_neurons_v), 165122*sizeof(_array_neurons_v[0]));
        outfile__array_neurons_v.close();
    } else
    {
        std::cout << "Error writing output file for _array_neurons_v." << endl;
    }
    ofstream outfile__array_spikes__source_idx;
    outfile__array_spikes__source_idx.open(results_dir + "_array_spikes__source_idx_2303802139", ios::binary | ios::out);
    if(outfile__array_spikes__source_idx.is_open())
    {
        outfile__array_spikes__source_idx.write(reinterpret_cast<char*>(_array_spikes__source_idx), 165122*sizeof(_array_spikes__source_idx[0]));
        outfile__array_spikes__source_idx.close();
    } else
    {
        std::cout << "Error writing output file for _array_spikes__source_idx." << endl;
    }
    ofstream outfile__array_spikes_count;
    outfile__array_spikes_count.open(results_dir + "_array_spikes_count_328618678", ios::binary | ios::out);
    if(outfile__array_spikes_count.is_open())
    {
        outfile__array_spikes_count.write(reinterpret_cast<char*>(_array_spikes_count), 165122*sizeof(_array_spikes_count[0]));
        outfile__array_spikes_count.close();
    } else
    {
        std::cout << "Error writing output file for _array_spikes_count." << endl;
    }
    ofstream outfile__array_spikes_N;
    outfile__array_spikes_N.open(results_dir + "_array_spikes_N_3246544668", ios::binary | ios::out);
    if(outfile__array_spikes_N.is_open())
    {
        outfile__array_spikes_N.write(reinterpret_cast<char*>(_array_spikes_N), 1*sizeof(_array_spikes_N[0]));
        outfile__array_spikes_N.close();
    } else
    {
        std::cout << "Error writing output file for _array_spikes_N." << endl;
    }

    ofstream outfile__dynamic_array_connections__synaptic_post;
    outfile__dynamic_array_connections__synaptic_post.open(results_dir + "_dynamic_array_connections__synaptic_post_2086485232", ios::binary | ios::out);
    if(outfile__dynamic_array_connections__synaptic_post.is_open())
    {
        if (! _dynamic_array_connections__synaptic_post.empty() )
        {
            outfile__dynamic_array_connections__synaptic_post.write(reinterpret_cast<char*>(&_dynamic_array_connections__synaptic_post[0]), _dynamic_array_connections__synaptic_post.size()*sizeof(_dynamic_array_connections__synaptic_post[0]));
            outfile__dynamic_array_connections__synaptic_post.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_connections__synaptic_post." << endl;
    }
    ofstream outfile__dynamic_array_connections__synaptic_pre;
    outfile__dynamic_array_connections__synaptic_pre.open(results_dir + "_dynamic_array_connections__synaptic_pre_2231496401", ios::binary | ios::out);
    if(outfile__dynamic_array_connections__synaptic_pre.is_open())
    {
        if (! _dynamic_array_connections__synaptic_pre.empty() )
        {
            outfile__dynamic_array_connections__synaptic_pre.write(reinterpret_cast<char*>(&_dynamic_array_connections__synaptic_pre[0]), _dynamic_array_connections__synaptic_pre.size()*sizeof(_dynamic_array_connections__synaptic_pre[0]));
            outfile__dynamic_array_connections__synaptic_pre.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_connections__synaptic_pre." << endl;
    }
    ofstream outfile__dynamic_array_connections_delay;
    outfile__dynamic_array_connections_delay.open(results_dir + "_dynamic_array_connections_delay_2796888156", ios::binary | ios::out);
    if(outfile__dynamic_array_connections_delay.is_open())
    {
        if (! _dynamic_array_connections_delay.empty() )
        {
            outfile__dynamic_array_connections_delay.write(reinterpret_cast<char*>(&_dynamic_array_connections_delay[0]), _dynamic_array_connections_delay.size()*sizeof(_dynamic_array_connections_delay[0]));
            outfile__dynamic_array_connections_delay.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_connections_delay." << endl;
    }
    ofstream outfile__dynamic_array_connections_N_incoming;
    outfile__dynamic_array_connections_N_incoming.open(results_dir + "_dynamic_array_connections_N_incoming_3795736167", ios::binary | ios::out);
    if(outfile__dynamic_array_connections_N_incoming.is_open())
    {
        if (! _dynamic_array_connections_N_incoming.empty() )
        {
            outfile__dynamic_array_connections_N_incoming.write(reinterpret_cast<char*>(&_dynamic_array_connections_N_incoming[0]), _dynamic_array_connections_N_incoming.size()*sizeof(_dynamic_array_connections_N_incoming[0]));
            outfile__dynamic_array_connections_N_incoming.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_connections_N_incoming." << endl;
    }
    ofstream outfile__dynamic_array_connections_N_outgoing;
    outfile__dynamic_array_connections_N_outgoing.open(results_dir + "_dynamic_array_connections_N_outgoing_3307349693", ios::binary | ios::out);
    if(outfile__dynamic_array_connections_N_outgoing.is_open())
    {
        if (! _dynamic_array_connections_N_outgoing.empty() )
        {
            outfile__dynamic_array_connections_N_outgoing.write(reinterpret_cast<char*>(&_dynamic_array_connections_N_outgoing[0]), _dynamic_array_connections_N_outgoing.size()*sizeof(_dynamic_array_connections_N_outgoing[0]));
            outfile__dynamic_array_connections_N_outgoing.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_connections_N_outgoing." << endl;
    }
    ofstream outfile__dynamic_array_connections_w;
    outfile__dynamic_array_connections_w.open(results_dir + "_dynamic_array_connections_w_1869503737", ios::binary | ios::out);
    if(outfile__dynamic_array_connections_w.is_open())
    {
        if (! _dynamic_array_connections_w.empty() )
        {
            outfile__dynamic_array_connections_w.write(reinterpret_cast<char*>(&_dynamic_array_connections_w[0]), _dynamic_array_connections_w.size()*sizeof(_dynamic_array_connections_w[0]));
            outfile__dynamic_array_connections_w.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_connections_w." << endl;
    }
    ofstream outfile__dynamic_array_spikes_i;
    outfile__dynamic_array_spikes_i.open(results_dir + "_dynamic_array_spikes_i_2751340298", ios::binary | ios::out);
    if(outfile__dynamic_array_spikes_i.is_open())
    {
        if (! _dynamic_array_spikes_i.empty() )
        {
            outfile__dynamic_array_spikes_i.write(reinterpret_cast<char*>(&_dynamic_array_spikes_i[0]), _dynamic_array_spikes_i.size()*sizeof(_dynamic_array_spikes_i[0]));
            outfile__dynamic_array_spikes_i.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_spikes_i." << endl;
    }
    ofstream outfile__dynamic_array_spikes_t;
    outfile__dynamic_array_spikes_t.open(results_dir + "_dynamic_array_spikes_t_3237508051", ios::binary | ios::out);
    if(outfile__dynamic_array_spikes_t.is_open())
    {
        if (! _dynamic_array_spikes_t.empty() )
        {
            outfile__dynamic_array_spikes_t.write(reinterpret_cast<char*>(&_dynamic_array_spikes_t[0]), _dynamic_array_spikes_t.size()*sizeof(_dynamic_array_spikes_t[0]));
            outfile__dynamic_array_spikes_t.close();
        }
    } else
    {
        std::cout << "Error writing output file for _dynamic_array_spikes_t." << endl;
    }

    // Write last run info to disk
    ofstream outfile_last_run_info;
    outfile_last_run_info.open(results_dir + "last_run_info.txt", ios::out);
    if(outfile_last_run_info.is_open())
    {
        outfile_last_run_info << (Network::_last_run_time) << " " << (Network::_last_run_completed_fraction) << std::endl;
        outfile_last_run_info.close();
    } else
    {
        std::cout << "Error writing last run info to file." << std::endl;
    }
}

void _dealloc_arrays()
{
    using namespace brian;


    // static arrays
    if(_static_array__array_connections_sources!=0)
    {
        delete [] _static_array__array_connections_sources;
        _static_array__array_connections_sources = 0;
    }
    if(_static_array__array_connections_targets!=0)
    {
        delete [] _static_array__array_connections_targets;
        _static_array__array_connections_targets = 0;
    }
    if(_static_array__array_neurons_activity!=0)
    {
        delete [] _static_array__array_neurons_activity;
        _static_array__array_neurons_activity = 0;
    }
    if(_static_array__array_neurons_baseline!=0)
    {
        delete [] _static_array__array_neurons_baseline;
        _static_array__array_neurons_baseline = 0;
    }
    if(_static_array__array_neurons_ref_steps!=0)
    {
        delete [] _static_array__array_neurons_ref_steps;
        _static_array__array_neurons_ref_steps = 0;
    }
    if(_static_array__array_neurons_syn!=0)
    {
        delete [] _static_array__array_neurons_syn;
        _static_array__array_neurons_syn = 0;
    }
    if(_static_array__array_neurons_v!=0)
    {
        delete [] _static_array__array_neurons_v;
        _static_array__array_neurons_v = 0;
    }
    if(_static_array__dynamic_array_connections_w!=0)
    {
        delete [] _static_array__dynamic_array_connections_w;
        _static_array__dynamic_array_connections_w = 0;
    }
}

