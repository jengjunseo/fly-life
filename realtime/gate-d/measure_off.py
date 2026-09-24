"""Matched D1 counterfactual: same exe/input/affinity, producer absent."""
import json
import numpy as np
import psutil
from env import REPORT,save
from contention import run_trial
from producer import Producer,statistics,pin_thread
if __name__=='__main__':
    final=json.loads((REPORT/'d1-final-decision.json').read_text());label=final['selected_configuration'];decision=json.loads((REPORT/(label+'-decision.json')).read_text())
    zero=label.startswith('d1-zero');comparison={};reports=[]
    for scenario in ['baseline','looming']:
        on=[json.loads((REPORT/f'{label}-{scenario}-{i}.json').read_text()) for i in range(3)];off=[]
        for i in range(3):
            r=run_trial('d1-matched-off',decision['threads'],decision['brain_cpus'],decision['worker_cpus'],scenario,i,producer_on=False,zero=zero);off.append(r);reports.append(r)
            print(scenario,i,r['brain_statistics']['p99_ms'],flush=True)
        on_mean=float(np.mean([r['brain_statistics']['mean_ms'] for r in on]));off_mean=float(np.mean([r['brain_statistics']['mean_ms'] for r in off]))
        comparison[scenario]=dict(on_mean_ms=on_mean,off_mean_ms=off_mean,mean_contention_slowdown=on_mean/off_mean,on_repeat_p99_ms=[r['brain_statistics']['p99_ms'] for r in on],off_repeat_p99_ms=[r['brain_statistics']['p99_ms'] for r in off])
    producer_only=[]
    for i in range(3):
        if zero:pin_thread([decision['worker_cpus'][0]])
        p=Producer(20260913,len(decision['worker_cpus']),decision['worker_cpus'],packed=zero)
        for _ in range(10):p.fill()
        times=[p.fill() for _ in range(200)];stats=statistics(times);metadata=p.metadata();p.close()
        producer_only.append(dict(trial=i,statistics=stats,wall_ms=times,metadata=metadata));print('producer only',i,stats,flush=True)
    save(REPORT/'d1-contention-comparison.json',dict(matched_configuration=label,comparison=comparison,producer_only=producer_only,
        measured_python_process_peak_rss_bytes=psutil.Process().memory_info().peak_wset,
        qualification='Same 2s shared noise, scenario/affinity/executable, three on and three off brain runs, warmup0.5s. Producer-only three200-block trials match fixed streams/affinity/packing and warmup10 blocks. CPU/noise-memory contention associated slowdown, not instruction-level causal profiling.'))
