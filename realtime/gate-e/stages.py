"""Sequential benchmark/build ordering; never compile during timing trials."""
import json, subprocess, sys
from statistics import median
from env import ROOT, REPORT, save
from measure import run
from correctness import compare

def build(t,s,p=False,v='current',seconds=2,q=50):
    tag=f'{v}-{t}t-{s}-p{int(p)}-{seconds}s-q{q}'
    if not(REPORT/(tag+'-build.json')).exists():
        with (REPORT/(tag+'-build-console.txt')).open('w') as f:
            r=subprocess.run([sys.executable,str(ROOT/'realtime/gate-e/entry.py'),'build',str(t),s,str(int(p)),v,str(seconds),str(q)],stdout=f,stderr=subprocess.STDOUT)
        r.check_returncode()
    return tag

def trials(tag,cpus):
    out=[]
    for i in range(3):
        path=REPORT/(tag+f'-off-{i}.json')
        out.append(json.loads(path.read_text()) if path.exists() else run(tag,i,cpus))
    return out

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='profile':
        tag=build(1,'looming',True)
        run(tag,0,[6])
    elif mode=='scale':
        reference=None;records=[];winner=None
        for t,cpus in [(1,[6]),(2,[4,6]),(4,[0,2,4,6])]:
            tag=build(t,'looming');rows=trials(tag,cpus)
            if reference is None:reference=rows[0]['label']
            for row in rows:compare(reference,row['label'],exact=t==1)
            pt=build(t,'looming',True)
            pp=REPORT/(pt+'-off-0.json')
            profile=json.loads(pp.read_text()) if pp.exists() else run(pt,0,cpus)
            records.append(dict(threads=t,cpus=cpus,tag=tag,repeats=[x['label'] for x in rows],
                worst_p99_ms=max(x['brain_statistics']['p99_ms'] for x in rows),profile=profile['label']))
            if records[-1]['worst_p99_ms']<=35:
                winner=tag;break
        save(REPORT/'e2-decision.json',dict(records=records,headroom_candidate=winner,
            eight_threads_tested=False,eight_thread_reason='Only permissible if measured4T scaling remains good; no speculative SMT search'))
    elif mode=='cheap':
        assert not json.loads((REPORT/'e2-decision.json').read_text())['headroom_candidate']
        reference='current-1t-looming-p0-2s-q50-off-0'
        records=[]
        # One measured change at a time. No expensive/insignificant monitor work.
        for v in ['clear-fused','zero']:
            tag=build(1,'looming',False,v);rows=trials(tag,[6])
            for row in rows:compare(reference,row['label'],exact=True)
            records.append(dict(variant=v,tag=tag,repeats=[x['label'] for x in rows],
                worst_p99_ms=max(x['brain_statistics']['p99_ms'] for x in rows)))
            save(REPORT/'e3-decision.json',dict(records=records,headroom_candidate=tag if records[-1]['worst_p99_ms']<=35 else None,
                monitor_trial='NOT RUN: SpikeMonitor already record=False and <1% profile; boundary instrumentation also small',
                fusion_qualification='Incoming is scratch storage: zeroed after lif use rather than next start. Final incoming scratch differs; all full neural dynamics states and circuit observations must match exactly.'))
            if records[-1]['worst_p99_ms']<=35:break
    elif mode=='timeline':
        assert not json.loads((REPORT/'e3-decision.json').read_text())['headroom_candidate']
        tag=build(1,'looming',False,'current',20,50);rows=trials(tag,[6])
        for row in rows:compare(rows[0]['label'],row['label'],exact=True)
        save(REPORT/'e4-runs.json',dict(tag=tag,repeats=[x['label'] for x in rows],
            qualification='20s consecutive persistent neural run with2s frozen noise replay to bound RAM; known40-window noise period, not20s independent Gaussian/pipeline certification'))
    elif mode=='planz':
        assert not json.loads((REPORT/'e3-decision.json').read_text())['headroom_candidate']
        initial=[json.loads((REPORT/f'current-1t-looming-p0-2s-q50-off-{i}.json').read_text()) for i in range(3)]
        assert 40<=median(x['brain_statistics']['mean_ms'] for x in initial)<=50
        before=json.loads((REPORT/'e4-runs.json').read_text())
        rows50=[json.loads((REPORT/(n+'.json')).read_text()) for n in before['repeats']]
        tag=build(1,'looming',False,'current',20,100);rows100=trials(tag,[6])
        checks=[]
        for a,b in zip(rows50,rows100):
            equal=all(a['final_state'][k]['sha256']==b['final_state'][k]['sha256'] for k in a['final_state'])
            checks.append(equal)
        assert all(checks), 'Control quantum diagnostic must preserve final neural state'
        costs50=[x['timings']['network_compute']/20000*1000 for x in rows50]
        costs100=[x['timings']['network_compute']/20000*1000 for x in rows100]
        ratios=[a/b for a,b in zip(costs50,costs100)]
        useful=median(ratios)>=1.10 and min(ratios)>=1.05
        save(REPORT/'plan-z.json',dict(classification='100MS QUANTUM: USEFUL ESCAPE OPTION' if useful else '100MS QUANTUM: NO MATERIAL BENEFIT',
            rule='Predeclared conservative material benefit: median pair ratio>=1.10 and every pair>=1.05; sequential timing variance qualified',
            dt_ms=1,production_adopted=False,final_state_exact=checks,q50_repeats=before['repeats'],q100_repeats=[x['label'] for x in rows100],
            q50_network_ms_per_neural_ms=costs50,q100_network_ms_per_neural_ms=costs100,pair_speedups=ratios,
            qualification='Same20s frozen replay and constant strongest input; only control boundary cadence differs. Network timer includes boundary maintenance, no producer/IPC/world. Not production50/100ms pipeline certification.'))
