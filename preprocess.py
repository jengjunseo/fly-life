"""Streaming Feather -> all traced identities + pruned sparse connectivity."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.ipc as ipc
from scipy import sparse

from acquire import FILES, digest
from braincore.core import select, signed_normalized_matrix
from braincore.evidence import Resources, machine, save

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(ROOT / 'config.json'))
    parser.add_argument('--runtime', default=str(ROOT / 'data/runtime'))
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    raw = ROOT / 'data/raw'
    out = Path(args.runtime)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    manifest = json.loads((raw / 'manifest.json').read_text())
    if manifest['dataset'] != config['dataset'] or config['dataset'] != 'male-cns:v1.0':
        raise ValueError('Only verified MaleCNS v1.0 bulk schema is supported')
    for item in manifest['files']:
        if digest(raw / item['file']) != item['sha256']:
            raise ValueError('Raw data checksum mismatch')
    with Resources() as resources:
        annotations = feather.read_table(raw / FILES[0])
        annotation_counts = annotations['status'].to_pandas().value_counts(dropna=False)
        a = annotations.to_pandas()
        a = a[a.status.isin(config['preprocessing']['statuses'])].sort_values('bodyId').reset_index(drop=True)
        nt = feather.read_table(raw / FILES[1])
        nt_schema = str(nt.schema)
        nt_rows = nt.num_rows
        nt = nt.filter(pc.is_in(nt['body'], value_set=pa.array(a.bodyId.to_numpy()))).to_pandas()
        nt = nt.rename(columns={'body': 'bodyId', 'cell_type': 'nt_cell_type'})
        a = a.merge(nt, on='bodyId', how='left', validate='one_to_one')
        a['runtime_index'] = np.arange(len(a), dtype=np.int32)
        ids = a.bodyId.to_numpy()
        resolved = {}
        protected = np.zeros(len(a), bool)
        identity_columns = ['bodyId', 'type', 'instance', 'flywireType', 'hemibrainType', 'mancType',
                            'synonyms', 'status', 'predicted_nt', 'predicted_nt_confidence', 'consensus_nt']
        for name, selector in config['groups'].items():
            idx = select(a, selector)
            records = json.loads(a.iloc[idx][identity_columns].to_json(orient='records'))
            resolved[name] = dict(selector=selector, count=len(idx), neurons=records)
            if name in config['preprocessing']['protected_groups']:
                if not len(idx):
                    raise ValueError(f'Protected group {name} resolves to zero neurons')
                protected[idx] = True
        for name in config['preprocessing']['protected_groups']:
            if name not in resolved:
                raise ValueError(f'Unknown protected group {name}')
        threshold = config['preprocessing']['weight_threshold']
        if threshold < 1:
            raise ValueError('Pruning threshold must be >=1')
        rows, cols, values = [], [], []
        raw_rows = raw_synapses = eligible_rows = eligible_synapses = protected_weak = 0
        threshold_counts = {str(t): 0 for t in [1, 3, 5, 10]}
        # Feather V2 is Arrow IPC; bounded decompression of ~65k-row record batches.
        with pa.memory_map(str(raw / FILES[2]), 'r') as source:
            reader = ipc.open_file(source)
            weight_schema = str(reader.schema)
            if reader.schema.names != ['body_pre', 'body_post', 'weight']:
                raise ValueError('Unexpected bulk connectivity schema')
            for b in range(reader.num_record_batches):
                batch = reader.get_batch(b)
                pre, post, weight = [batch.column(k).to_numpy() for k in range(3)]
                raw_rows += len(weight)
                raw_synapses += int(weight.sum())
                if (weight <= 0).any():
                    raise ValueError('Nonpositive source count')
                src, dst = np.searchsorted(ids, pre), np.searchsorted(ids, post)
                valid = (src < len(ids)) & (dst < len(ids))
                src_clip, dst_clip = np.minimum(src, len(ids)-1), np.minimum(dst, len(ids)-1)
                valid &= (ids[src_clip] == pre) & (ids[dst_clip] == post)
                eligible_rows += int(valid.sum())
                eligible_synapses += int(weight[valid].sum())
                for t in threshold_counts:
                    threshold_counts[t] += int((valid & (weight >= int(t))).sum())
                protect_edge = protected[src_clip] | protected[dst_clip]
                keep = valid & ((weight >= threshold) | protect_edge)
                protected_weak += int((valid & protect_edge & (weight < threshold)).sum())
                rows.append(dst[keep].astype(np.int32))
                cols.append(src[keep].astype(np.int32))
                values.append(weight[keep].astype(np.int32))
                if b % 400 == 0:
                    print(f'batch {b}/{reader.num_record_batches}; eligible edges {eligible_rows:,}', flush=True)
        counts = sparse.coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(cols))),
                                   shape=(len(ids), len(ids)), dtype=np.int32).tocsr()
        counts.sort_indices()
        signs = a[config['sign_policy']['field']].map(config['sign_policy']['signs']).fillna(
            config['sign_policy']['unknown_sign']).to_numpy(dtype=np.float32)
        if not np.isin(signs, [-1, 0, 1]).all():
            raise ValueError('Signs must be -1, 0, or 1')
        w = signed_normalized_matrix(counts, signs)
        sparse.save_npz(out / 'counts.npz', counts)
        sparse.save_npz(out / 'weights.npz', w)
        a.to_parquet(out / 'neurons.parquet', index=False)
        save(out / 'resolved_groups.json', resolved)
        metadata = dict(dataset=config['dataset'], source_download_page='https://male-cns.janelia.org/download/',
            license='CC-BY-4.0', source_manifest=manifest,
            schemas=dict(annotations=str(annotations.schema), neurotransmitters=nt_schema, connectivity=weight_schema),
            annotation_rows=annotations.num_rows, neurotransmitter_rows=nt_rows,
            source_status_counts={str(k):int(v) for k,v in annotation_counts.items()},
            source_connection_rows=raw_rows, source_synapse_count=raw_synapses,
            eligible_traced_connection_rows=eligible_rows, eligible_traced_synapse_count=eligible_synapses,
            neuron_count=len(a), retained_connection_count=counts.nnz,
            retained_synapse_count=int(counts.sum()), effective_nonzero_connection_count=w.nnz,
            threshold_comparison_unprotected=threshold_counts,
            protected_neuron_count=int(protected.sum()), protected_weak_connections=protected_weak,
            disconnected_neuron_count=int(((np.diff(counts.indptr)==0) &
                (np.asarray(counts.getnnz(axis=0))==0)).sum()),
            neurotransmitter_counts={str(k):int(v) for k,v in a.consensus_nt.value_counts(dropna=False).items()},
            matrix_orientation='W[target, source]; input = W @ previous_step_spikes',
            preprocessing=config['preprocessing'], groups=config['groups'], sign_policy=config['sign_policy'],
            model_assumptions=[
                'Only annotated status Traced endpoints retained; glia, orphan, unassigned segments excluded.',
                'All selected neurons retained regardless of degree; all positive edges incident to protected neurons retained.',
                'Presynaptic consensus_nt sign: ACh +1; GABA, glutamate, histamine -1; modulatory/unclear 0.',
                'Glutamate can be excitatory (especially motor/NMJ); no receptor-specific inference is possible here.',
                'Zero-sign edges remain in counts.npz but do not transmit in weights.npz.',
                'Absolute incoming normalization and arbitrary unit LIF currents are model assumptions, not measured biophysics.',
                'One-step uniform transmission delay; no gap junctions, plasticity or receptor dynamics.'
            ], model_default=config['model'], machine=machine(),
            artifact_sha256={name:digest(out/name) for name in ['counts.npz','weights.npz','neurons.parquet','resolved_groups.json']})
    metadata['resources'] = resources.report()
    metadata['total_preprocessing_wall_seconds'] = time.perf_counter() - started
    save(out / 'metadata.json', metadata)
    print(json.dumps({k:metadata[k] for k in ['dataset','neuron_count','retained_connection_count',
        'effective_nonzero_connection_count','protected_weak_connections','resources']}, indent=2), flush=True)

if __name__ == '__main__':
    main()
