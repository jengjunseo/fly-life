#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <cstring>
#pragma once

        #include "objects.h"
        #include <chrono>
        #include <fstream>
        #include <cmath>
        #include <stdexcept>
        namespace gate_b {
            typedef std::chrono::steady_clock GateClock;
            inline GateClock::time_point begun, window_start, output_start;
            inline std::ofstream windows_file, timing_file;
            inline std::ifstream noise_file;
            inline long long step=0, quantum_spikes=0, max_sync=0;
            inline bool finite=true;
            inline double wall_sum=0;
            inline long long previous_population=0;
            inline std::vector<float> input;
            inline std::vector<int> pool;
            inline const int group_LC4[] = {1899,2195,2642,4517,4635,5622,5630,6078,6239,6334,6455,6645,6648,6709,6733,6835,6897,6953,6995,7008,7184,7243,7294,7419,7474,7661,7693,7732,8436,8573,8683,8689,8765,8906,9051,9105,9342,9442,9477,9567,9595,9611,9691,9810,9856,9908,9948,9955,10112,10123,10181,10239,10261,10281,10621,10700,10908,11057,11181,11579,11651,11718,11755,11764,11872,11959,11982,12133,12489,12616,12981,13142,14089,14552,15901,16015,16088,17077,17110,17496,17540,17583,17631,18103,18440,18725,19115,19151,19157,19262,20296,20762,22273,22646,22961,24701,25125,58525,61306,76056,81169,84241,124366,124611,124803,125804,126065,126347,126603,127209,127696,127859,128103,128167,128286,128446,128838,128990,129279,131094,131714,132142,132821,133906,134326,135381};
inline const int group_LPLC2[] = {1398,2228,2932,3475,3509,3755,3817,4134,5341,6460,6894,6900,7105,7106,7203,7297,7905,8113,8141,8148,8238,8339,8408,8425,8688,8724,8743,8901,8940,8951,9013,9133,9184,9233,9251,9305,9329,9382,9386,9505,9561,9607,9708,9758,9802,10018,10251,10265,10304,10480,10604,10666,10704,10753,10785,11080,11111,11118,11383,11491,12000,12093,12220,12266,12302,12371,12568,12607,12779,12842,12915,12953,13041,13174,13206,13383,13418,13587,13684,13749,13788,13800,13817,13842,14010,14023,14034,14078,14081,14134,14331,14583,14806,14828,14926,15108,15270,15364,15659,15701,15763,15851,15984,16059,16244,16251,16279,16409,16899,17015,17141,17295,17323,17382,17411,17474,17661,17761,17809,17864,17914,17986,18015,18066,18203,18468,18804,18806,18840,18990,19112,19380,19731,19754,19964,19973,20217,20415,20804,20911,20997,21006,21036,21259,21499,21577,21627,21861,21890,22107,22130,22674,22977,23020,23159,23203,24563,24726,25000,25543,26501,27551,27580,27808,35821,40409,72181,75763,84331,84607,96091,98970,125901,126640,127313,127314,127725,128287,129460,129601,130815,131512,133321,134717,135809};
inline const int group_GF[] = {0,6};
inline const int group_DNp09[] = {725,1087};
inline double peak_LC4=0, sum_LC4=0;
inline double peak_LPLC2=0, sum_LPLC2=0;
inline double peak_GF=0, sum_GF=0;
inline double peak_DNp09=0, sum_DNp09=0;
        }
        inline double gate_tick() {
            using namespace gate_b;
            ++step;
            long long sync=brian::_array_neurons__spikespace[165122];
            quantum_spikes+=sync;if(sync>max_sync)max_sync=sync;
            {double ema=0;for(int i:group_LC4)ema+=brian::_array_neurons_activity[i];ema/=126;
            sum_LC4+=ema;if(ema>peak_LC4)peak_LC4=ema;}
{double ema=0;for(int i:group_LPLC2)ema+=brian::_array_neurons_activity[i];ema/=185;
            sum_LPLC2+=ema;if(ema>peak_LPLC2)peak_LPLC2=ema;}
{double ema=0;for(int i:group_GF)ema+=brian::_array_neurons_activity[i];ema/=2;
            sum_GF+=ema;if(ema>peak_GF)peak_GF=ema;}
{double ema=0;for(int i:group_DNp09)ema+=brian::_array_neurons_activity[i];ema/=2;
            sum_DNp09+=ema;if(ema>peak_DNp09)peak_DNp09=ema;}

            if(step % 50 != 0) return 0;
            auto finish=GateClock::now();
            double ms=std::chrono::duration<double,std::milli>(finish-window_start).count();wall_sum+=ms;
            long long cumulative=0, active=0;
            for(int i=0;i<165122;++i) {
                cumulative+=brian::_array_spikes_count[i];active+=brian::_array_spikes_count[i]>0;
                finite=finite && std::isfinite(brian::_array_neurons_v[i]) && std::isfinite(brian::_array_neurons_syn[i]);
            }
            windows_file << step/50-1 << " " << (step-50)*.001 << " " << step*.001 << " " << ms << " " << quantum_spikes << " " << cumulative << " " << active << " " << max_sync << " " << finite;
            
            {long long count=0,active_group=0;double ema=0;
            for(int i:group_LC4){count+=brian::_array_spikes_count[i];active_group+=brian::_array_spikes_count[i]>0;ema+=brian::_array_neurons_activity[i];}
            windows_file << " " << count << " " << ema/126 << " " << active_group << " " << peak_LC4 << " " << sum_LC4/50;
            peak_LC4=0;sum_LC4=0;}
        
            {long long count=0,active_group=0;double ema=0;
            for(int i:group_LPLC2){count+=brian::_array_spikes_count[i];active_group+=brian::_array_spikes_count[i]>0;ema+=brian::_array_neurons_activity[i];}
            windows_file << " " << count << " " << ema/185 << " " << active_group << " " << peak_LPLC2 << " " << sum_LPLC2/50;
            peak_LPLC2=0;sum_LPLC2=0;}
        
            {long long count=0,active_group=0;double ema=0;
            for(int i:group_GF){count+=brian::_array_spikes_count[i];active_group+=brian::_array_spikes_count[i]>0;ema+=brian::_array_neurons_activity[i];}
            windows_file << " " << count << " " << ema/2 << " " << active_group << " " << peak_GF << " " << sum_GF/50;
            peak_GF=0;sum_GF=0;}
        
            {long long count=0,active_group=0;double ema=0;
            for(int i:group_DNp09){count+=brian::_array_spikes_count[i];active_group+=brian::_array_spikes_count[i]>0;ema+=brian::_array_neurons_activity[i];}
            windows_file << " " << count << " " << ema/2 << " " << active_group << " " << peak_DNp09 << " " << sum_DNp09/50;
            peak_DNp09=0;sum_DNp09=0;}
        
            windows_file << std::endl;
            quantum_spikes=0;
            if(step/50 < 40) {
                for(int j=0;j<882;++j)brian::_array_neurons_external[pool[j]]=input[(step/50)*882+j];
            }
            // Boundary statistics/output/input maintenance excluded from EACH compute timer;
            // whole Network.run timer also reported, including maintenance.
            window_start=GateClock::now();
            return 0;
        }
        inline std::vector<float> gate_d_noise;
inline float* gate_d_owned_noise=nullptr;
inline long long gate_d_step=0;
inline double gate_noise_read() {
    if(gate_d_step>=2000)throw std::runtime_error("Nonperiodic shared noise exhausted");
    brian::_array_neurons_noise_sample=gate_d_noise.data()+gate_d_step*165122LL;
    ++gate_d_step;return 0;
}
inline double gate_d_qpc() {LARGE_INTEGER c,f;QueryPerformanceCounter(&c);QueryPerformanceFrequency(&f);return double(c.QuadPart)/f.QuadPart;}

        