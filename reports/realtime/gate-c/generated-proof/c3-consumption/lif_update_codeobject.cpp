#include "code_objects/lif_update_codeobject.h"
#include "objects.h"
#include "brianlib/common_math.h"
#include "brianlib/stdint_compat.h"
#include<cmath>
#include<ctime>
#include<iostream>
#include<fstream>
#include<climits>
#include "gate_hooks.h"
#include <cstring>

////// SUPPORT CODE ///////
namespace {
        
    template < typename T1, typename T2 > struct _higher_type;
    template < > struct _higher_type<int32_t,int32_t> { typedef int32_t type; };
    template < > struct _higher_type<int32_t,int64_t> { typedef int64_t type; };
    template < > struct _higher_type<int32_t,float> { typedef float type; };
    template < > struct _higher_type<int32_t,double> { typedef double type; };
    template < > struct _higher_type<int32_t,long double> { typedef long double type; };
    template < > struct _higher_type<int64_t,int32_t> { typedef int64_t type; };
    template < > struct _higher_type<int64_t,int64_t> { typedef int64_t type; };
    template < > struct _higher_type<int64_t,float> { typedef float type; };
    template < > struct _higher_type<int64_t,double> { typedef double type; };
    template < > struct _higher_type<int64_t,long double> { typedef long double type; };
    template < > struct _higher_type<float,int32_t> { typedef float type; };
    template < > struct _higher_type<float,int64_t> { typedef float type; };
    template < > struct _higher_type<float,float> { typedef float type; };
    template < > struct _higher_type<float,double> { typedef double type; };
    template < > struct _higher_type<float,long double> { typedef long double type; };
    template < > struct _higher_type<double,int32_t> { typedef double type; };
    template < > struct _higher_type<double,int64_t> { typedef double type; };
    template < > struct _higher_type<double,float> { typedef double type; };
    template < > struct _higher_type<double,double> { typedef double type; };
    template < > struct _higher_type<double,long double> { typedef long double type; };
    template < > struct _higher_type<long double,int32_t> { typedef long double type; };
    template < > struct _higher_type<long double,int64_t> { typedef long double type; };
    template < > struct _higher_type<long double,float> { typedef long double type; };
    template < > struct _higher_type<long double,double> { typedef long double type; };
    template < > struct _higher_type<long double,long double> { typedef long double type; };
    // General template, used for floating point types
    template < typename T1, typename T2 >
    static inline typename _higher_type<T1,T2>::type
    _brian_mod(T1 x, T2 y)
    {
        return x-y*floor(1.0*x/y);
    }
    // Specific implementations for integer types
    // (from Cython, see LICENSE file)
    template <>
    inline int32_t _brian_mod(int32_t x, int32_t y)
    {
        int32_t r = x % y;
        r += ((r != 0) & ((r ^ y) < 0)) * y;
        return r;
    }
    template <>
    inline int64_t _brian_mod(int32_t x, int64_t y)
    {
        int64_t r = x % y;
        r += ((r != 0) & ((r ^ y) < 0)) * y;
        return r;
    }
    template <>
    inline int64_t _brian_mod(int64_t x, int32_t y)
    {
        int64_t r = x % y;
        r += ((r != 0) & ((r ^ y) < 0)) * y;
        return r;
    }
    template <>
    inline int64_t _brian_mod(int64_t x, int64_t y)
    {
        int64_t r = x % y;
        r += ((r != 0) & ((r ^ y) < 0)) * y;
        return r;
    }
    // General implementation, used for floating point types
    template < typename T1, typename T2 >
    static inline typename _higher_type<T1,T2>::type
    _brian_floordiv(T1 x, T2 y)
    {{
        return floor(1.0*x/y);
    }}
    // Specific implementations for integer types
    // (from Cython, see LICENSE file)
    template <>
    inline int32_t _brian_floordiv<int32_t, int32_t>(int32_t a, int32_t b) {
        int32_t q = a / b;
        int32_t r = a - q*b;
        q -= ((r != 0) & ((r ^ b) < 0));
        return q;
    }
    template <>
    inline int64_t _brian_floordiv<int32_t, int64_t>(int32_t a, int64_t b) {
        int64_t q = a / b;
        int64_t r = a - q*b;
        q -= ((r != 0) & ((r ^ b) < 0));
        return q;
    }
    template <>
    inline int64_t _brian_floordiv<int64_t, int>(int64_t a, int32_t b) {
        int64_t q = a / b;
        int64_t r = a - q*b;
        q -= ((r != 0) & ((r ^ b) < 0));
        return q;
    }
    template <>
    inline int64_t _brian_floordiv<int64_t, int64_t>(int64_t a, int64_t b) {
        int64_t q = a / b;
        int64_t r = a - q*b;
        q -= ((r != 0) & ((r ^ b) < 0));
        return q;
    }
    #ifdef _MSC_VER
    #define _brian_pow(x, y) (pow((double)(x), (y)))
    #else
    #define _brian_pow(x, y) (pow((x), (y)))
    #endif

}

////// HASH DEFINES ///////



void _run_lif_update_codeobject()
{
    using namespace brian;


    ///// CONSTANTS ///////////
    const int32_t N = 165122;
const size_t _numactivity = 165122;
const float activity_decay = 0.9801986813545227;
const float alpha = 0.05000000074505806;
const size_t _numbaseline = 165122;
const float decay = 0.8187307715415955;
const size_t _numeligible = 165122;
const size_t _numexternal = 165122;
const float gain = 2.0;
const size_t _numincoming = 165122;
const float noise_amplitude = 0.10000000149011612;
const size_t _numnoise_sample = 165122;
const size_t _numref_steps = 165122;
const float reset_value = 0.0;
const float rest = 0.0;
const size_t _numsyn = 165122;
const size_t _numv = 165122;
    ///// POINTERS ////////////
        
    float* __restrict  _ptr_array_neurons_activity = _array_neurons_activity;
    float* __restrict  _ptr_array_neurons_baseline = _array_neurons_baseline;
    int32_t* __restrict  _ptr_array_neurons_eligible = _array_neurons_eligible;
    float* __restrict  _ptr_array_neurons_external = _array_neurons_external;
    float* __restrict  _ptr_array_neurons_incoming = _array_neurons_incoming;
    float* __restrict  _ptr_array_neurons_noise_sample = _array_neurons_noise_sample;
    int32_t* __restrict  _ptr_array_neurons_ref_steps = _array_neurons_ref_steps;
    float* __restrict  _ptr_array_neurons_syn = _array_neurons_syn;
    float* __restrict  _ptr_array_neurons_v = _array_neurons_v;


    //// MAIN CODE ////////////
    // scalar code
    const size_t _vectorisation_idx = -1;
        


    const int _N = N;
    
    for(int _idx=0; _idx<_N; _idx++)
    {
        // vector code
        const size_t _vectorisation_idx = _idx;
                
        float activity = _ptr_array_neurons_activity[_idx];
        const float baseline = _ptr_array_neurons_baseline[_idx];
        int32_t eligible = _ptr_array_neurons_eligible[_idx];
        const float external = _ptr_array_neurons_external[_idx];
        const float incoming = _ptr_array_neurons_incoming[_idx];
        float noise_sample = _ptr_array_neurons_noise_sample[_idx];
        int32_t ref_steps = _ptr_array_neurons_ref_steps[_idx];
        float syn = _ptr_array_neurons_syn[_idx];
        float v = _ptr_array_neurons_v[_idx];
        syn *= decay;
        syn += gain * incoming;
        eligible = int_(ref_steps == 0);
        ref_steps -= int_(ref_steps > 0);
        float drive = baseline + syn;
        noise_sample *= noise_amplitude;
        drive += noise_sample;
        drive += external;
        v += alpha * (eligible * ((rest + drive) - v));
        v = (eligible * v) + (reset_value * (1 - eligible));
        activity *= activity_decay;
        _ptr_array_neurons_activity[_idx] = activity;
        _ptr_array_neurons_eligible[_idx] = eligible;
        _ptr_array_neurons_noise_sample[_idx] = noise_sample;
        _ptr_array_neurons_ref_steps[_idx] = ref_steps;
        _ptr_array_neurons_syn[_idx] = syn;
        _ptr_array_neurons_v[_idx] = v;

    }

}


