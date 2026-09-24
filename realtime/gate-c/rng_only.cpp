// C1/C2: exact extracted Brian2 RandomGenerator, no neuron/synapse computation.
#include "native_rng.h"
#include <omp.h>
#include <chrono>
#include <vector>
#include <iostream>
#include <iomanip>
#include <cstdlib>
int main(int argc,char**argv) {
    const int threads=std::atoi(argv[1]),n=165122,steps=1000;
    omp_set_dynamic(0);omp_set_num_threads(threads);
    std::vector<RandomGenerator> rng(threads);
    for(int t=0;t<threads;++t)rng[t].seed(20260913+t);
    std::vector<float> output(n);
    auto generate=[&](int count) {
        for(int s=0;s<count;++s) {
            #pragma omp parallel for schedule(static)
            for(int i=0;i<n;++i)output[i]=static_cast<float>(rng[omp_get_thread_num()].randn());
        }
    };
    auto warm=std::chrono::steady_clock::now();generate(50);
    double warm_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-warm).count();
    int actual=0;
    #pragma omp parallel
    {
        #pragma omp single
        actual=omp_get_num_threads();
    }
    std::cout<<std::setprecision(17);
    for(int trial=0;trial<2;++trial) {
        auto start=std::chrono::steady_clock::now();generate(steps);
        double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        double checksum=0;for(float x:output)checksum+=x;
        std::cout<<threads<<" "<<actual<<" "<<trial<<" "<<(long long)n*steps<<" "<<wall<<" "<<warm_seconds<<" "<<checksum<<"\n";
    }
}
