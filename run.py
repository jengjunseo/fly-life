"""Brain-only runtime, controlled named-neuron sanity test, and CPU benchmark."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy import sparse

from acquire import digest
from braincore import Brain
from braincore.evidence import Resources, machine, save

ROOT = Path(__file__).parent


def topology(runtime, config, brain, out):
    counts = sparse.load_npz(runtime / 'counts.npz')
    sources = brain.resolve(config['groups'][config['experiment']['input_group']])
    direct_counts = np.asarray(counts[:,sources].sum(axis=1)).ravel()
    downstream = np.flatnonzero(direct_counts > 0)
    downstream = np.setdiff1d(downstream, sources)
    named = {}
    for name in config['experiment']['observe_groups']:
        targets = brain.resolve(config['groups'][name])
        sub = counts[targets,:][:,sources].tocoo()
        records = []
        for row, col, weight in zip(sub.row, sub.col, sub.data):
            a, b = brain.neurons.iloc[sources[col]], brain.neurons.iloc[targets[row]]
            records.append(dict(body_pre=int(a.bodyId),type_pre=a['type'],body_post=int(b.bodyId),
                                type_post=b['type'],weight=int(weight),presynaptic_consensus_nt=a.consensus_nt))
        named[name] = dict(source_to_group_edges=len(records),synapses=sum(x['weight'] for x in records),edges=records)
    save(out / 'circuit_topology.json',dict(input_group=config['experiment']['input_group'],
        input_bodyIds=brain.neurons.iloc[sources].bodyId.tolist(),
        direct_downstream_count=len(downstream), named_connections=named,
        statement='Directed retained MaleCNS anatomy only; this is not a prediction of escape behaviour.'))
    return sources, downstream


def phase(brain, name, duration, groups, bin_steps, external=None, spike_hash=None):
    counts = np.zeros(brain.n,np.int64)
    voltage_sum = {g:0. for g in groups}
    syn_sum = {g:0. for g in groups}
    bins = []
    steps = brain.steps_for(duration)
    if steps == 0:
        raise ValueError('Experiment phases must be nonempty')
    bin_spikes = 0
    max_fraction = 0.
    for k in range(steps):
        spikes = brain.step(external)
        if spike_hash is not None:
            spike_hash.update(spikes.tobytes())
        counts += spikes.astype(np.int64)
        total = int(spikes.sum())
        bin_spikes += total
        max_fraction = max(max_fraction,total/brain.n)
        for g,idx in groups.items():
            if len(idx):
                voltage_sum[g] += float(brain.v[idx].mean())
                syn_sum[g] += float(brain.syn[idx].mean())
        if (k+1) % bin_steps == 0 or k+1 == steps:
            actual_steps = bin_steps if (k+1) % bin_steps == 0 else (k+1) % bin_steps
            bins.append(dict(end_ms=(k+1)*brain.p['dt_ms'],spikes=bin_spikes,
                             mean_hz=bin_spikes/brain.n/(actual_steps*brain.p['dt_ms']/1000)))
            bin_spikes = 0
    rates = counts/(duration/1000)
    group_stats = {}
    for g,idx in groups.items():
        group_stats[g] = dict(neurons=len(idx),total_spikes=int(counts[idx].sum()),
            mean_hz=float(rates[idx].mean()) if len(idx) else None,
            active_neurons=int(np.count_nonzero(counts[idx])),
            mean_voltage=voltage_sum[g]/steps if len(idx) else None,
            mean_synaptic_current=syn_sum[g]/steps if len(idx) else None,
            final_activity_hz=float(brain.read_activity(idx)['activity_hz'].mean()) if len(idx) else None)
    stats = dict(phase=name,duration_ms=duration,total_spikes=int(counts.sum()),
        mean_population_hz=float(rates.mean()),active_neurons=int(np.count_nonzero(counts)),
        max_neuron_hz=float(rates.max()),max_simultaneous_spiking_fraction=max_fraction,
        bins=bins,groups=group_stats,finite_state=bool(np.isfinite(brain.v).all() and np.isfinite(brain.syn).all()))
    print(f'{name}: {stats["total_spikes"]:,} spikes; {stats["mean_population_hz"]:.4f} Hz/neuron; '
          f'{stats["active_neurons"]:,} active',flush=True)
    return stats,counts


def trial(runtime, config, label, sources, downstream, out):
    with Resources() as resources:
        brain = Brain.load(runtime,config)
        if label == 'ablated':
            # A controlled diagnostic, not a replacement connectome: cut input outputs only.
            mask = np.ones(brain.n,np.float32)
            mask[sources] = 0
            brain.w = brain.w.multiply(mask[None,:]).tocsr()
            brain.w.eliminate_zeros()
        groups = {g:brain.resolve(config['groups'][g]) for g in config['experiment']['observe_groups']}
        groups['direct_downstream'] = downstream
        exp = config['experiment']
        external = brain.current(sources,exp['stimulus_current'])
        if not np.array_equal(np.flatnonzero(external),sources):
            raise AssertionError('Current target mismatch')
        bin_steps = brain.steps_for(exp['bin_ms'])
        if not bin_steps: raise ValueError('bin_ms must be >= one step')
        report = {}
        spike_hash = hashlib.sha256()
        count_arrays = {}
        start = time.perf_counter()
        for name,duration in [('warmup',exp['warmup_ms']),('baseline',exp['baseline_ms']),
                              ('stimulus',exp['stimulus_ms']),('recovery',exp['recovery_ms'])]:
            inject = external if name == 'stimulus' and label != 'control' else None
            stats,counts = phase(brain,name,duration,groups,bin_steps,inject,spike_hash)
            report[name] = stats
            count_arrays[name] = counts
        simulation_wall = time.perf_counter()-start
        report['spike_sequence_sha256'] = spike_hash.hexdigest()
        report['external_current_evidence'] = dict(amplitude=exp['stimulus_current'],
            nonzero_indices=sources.tolist(),bodyIds=brain.neurons.iloc[sources].bodyId.tolist(),
            unselected_external_current_is_zero=True,
            integrated_external_current_per_selected_neuron=exp['stimulus_current']*exp['stimulus_ms'] if label!='control' else 0,
            note='Arbitrary current units times ms; baseline drive is separate from external current.')
        report['simulation_wall_seconds'] = simulation_wall
        np.savez_compressed(out / f'{label}_spike_counts.npz',**count_arrays)
    report['resources'] = resources.report()
    save(out / f'{label}.json',report)
    return report,count_arrays


def sanity(runtime,config,out):
    out.mkdir(parents=True,exist_ok=True)
    brain = Brain.load(runtime,config)
    sources,downstream = topology(runtime,config,brain,out)
    if not len(sources) or not len(downstream):
        raise AssertionError('Real named inputs and downstream anatomy required')
    del brain
    results = {}
    arrays = {}
    for label in ['control','stimulated','ablated','replay']:
        results[label],arrays[label] = trial(runtime,config,label,sources,downstream,out)
    replay_equal = results['replay']['spike_sequence_sha256']==results['stimulated']['spike_sequence_sha256']
    baseline_equal = np.array_equal(arrays['control']['baseline'],arrays['stimulated']['baseline'])
    differences = {}
    for group in results['stimulated']['stimulus']['groups']:
        s = results['stimulated']['stimulus']['groups'][group]
        c = results['control']['stimulus']['groups'][group]
        a = results['ablated']['stimulus']['groups'][group]
        differences[group] = dict(stimulated_hz=s['mean_hz'],control_hz=c['mean_hz'],ablated_hz=a['mean_hz'],
            stimulus_minus_control_hz=s['mean_hz']-c['mean_hz'] if s['neurons'] else None,
            stimulated_minus_ablated_synaptic_current=s['mean_synaptic_current']-a['mean_synaptic_current'] if s['neurons'] else None)
    # Engineering usability criteria, explicitly not physiological validation.
    steady = [results['stimulated'][g] for g in ['baseline','stimulus','recovery']]
    stable = all(s['finite_state'] and s['total_spikes']>0 and s['mean_population_hz']<100 and
                 s['max_simultaneous_spiking_fraction']<0.25 and all(b['spikes']>0 for b in s['bins']) for s in steady)
    propagated = differences['direct_downstream']['stimulated_minus_ablated_synaptic_current']>0
    changed = differences['direct_downstream']['stimulus_minus_control_hz']>0
    summary = dict(dataset=config['dataset'],config=config,machine=machine(),
        runtime_metadata_sha256=digest(runtime/'metadata.json'),
        retained_neurons=json.loads((runtime/'metadata.json').read_text())['neuron_count'],
        real_input_count=len(sources),real_direct_downstream_count=len(downstream),
        replay_identical_spike_sequence=replay_equal,paired_baselines_identical=baseline_equal,
        operating_regime_usable=stable,
        usability_criteria='Every post-warmup bin nonzero; finite state; mean population <100Hz; simultaneous spiking <25%. Engineering guardrails, not physiological targets.',
        downstream_synaptic_propagation=propagated,downstream_spike_rate_increase=changed,
        paired_differences=differences,
        stimulus_baseline_difference_hz=results['stimulated']['stimulus']['mean_population_hz']-results['stimulated']['baseline']['mean_population_hz'],
        trials={label:dict(spike_sequence_sha256=r['spike_sequence_sha256'],resources=r['resources']) for label,r in results.items()})
    save(out/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['replay_identical_spike_sequence','paired_baselines_identical',
        'operating_regime_usable','downstream_synaptic_propagation','downstream_spike_rate_increase','paired_differences']},indent=2),flush=True)
    if not (stable and propagated and changed and replay_equal and baseline_equal):
        raise SystemExit('Sanity evidence incomplete; inspect results rather than claim completion')


def benchmark(runtime,config,out,duration=None):
    params = config['benchmark']
    neural_ms = duration if duration is not None else params['duration_ms']
    with Resources() as resources:
        load_start = time.perf_counter()
        brain = Brain.load(runtime,config)
        load_wall = time.perf_counter()-load_start
        brain.warmup(params['warmup_ms'])
        start = time.perf_counter()
        total = 0
        bins = []
        bin_spikes = 0
        count = brain.steps_for(neural_ms)
        bin_steps = max(1,brain.steps_for(100))
        for k in range(count):
            spikes = int(brain.step().sum())
            total += spikes
            bin_spikes += spikes
            if (k+1)%bin_steps==0 or k+1==count:
                bins.append(dict(end_ms=(k+1)*brain.p['dt_ms'],spikes=bin_spikes))
                bin_spikes=0
            if (k+1)%1000==0:
                print(f'benchmark {k+1}/{count} steps',flush=True)
        wall = time.perf_counter()-start
        report = dict(dataset=config['dataset'],machine=machine(),model=config['model'],seed=brain.seed,
            runtime_metadata_sha256=digest(runtime/'metadata.json'),neuron_count=brain.n,
            retained_connection_count=json.loads((runtime/'metadata.json').read_text())['retained_connection_count'],
            effective_nonzero_connections=brain.w.nnz,neural_simulated_seconds=neural_ms/1000,
            simulation_wall_seconds=wall,neural_seconds_per_wall_second=neural_ms/1000/wall,
            wall_seconds_per_neural_second=wall/(neural_ms/1000),warmup_ms=params['warmup_ms'],load_wall_seconds=load_wall,
            total_spikes=total,mean_population_hz=total/brain.n/(neural_ms/1000),bins=bins,
            finite_state=bool(np.isfinite(brain.v).all() and np.isfinite(brain.syn).all()),
            sparse_bytes=brain.w.data.nbytes+brain.w.indices.nbytes+brain.w.indptr.nbytes)
    report['resources'] = resources.report()
    save(out,report)
    print(json.dumps(report,indent=2),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command',choices=['simulate','sanity','benchmark'])
    parser.add_argument('--config',default=str(ROOT/'config.json'))
    parser.add_argument('--runtime',default=str(ROOT/'data/runtime'))
    parser.add_argument('--out')
    parser.add_argument('--duration-ms',type=float)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    runtime = Path(args.runtime)
    if args.command=='sanity':
        sanity(runtime,config,Path(args.out) if args.out else ROOT/'reports/sanity')
    elif args.command=='benchmark':
        benchmark(runtime,config,Path(args.out) if args.out else ROOT/'reports/benchmark.json',args.duration_ms)
    else:
        out = Path(args.out) if args.out else ROOT/'reports/simulate'
        out.mkdir(parents=True,exist_ok=True)
        brain = Brain.load(runtime,config)
        sources,downstream=topology(runtime,config,brain,out)
        del brain
        trial(runtime,config,'stimulated',sources,downstream,out)

if __name__ == '__main__':
    main()
