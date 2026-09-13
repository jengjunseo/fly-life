"""Resolve literature candidates from real released fields; never invent aliases."""
from pathlib import Path

import pyarrow.feather as feather

from acquire import FILES, digest
from braincore.evidence import save

ROOT=Path(__file__).parent
path=ROOT/'data/raw'/FILES[0]
a=feather.read_table(path).to_pandas()
fields=['type','flywireType','hemibrainType','mancType']
cols=['bodyId','type','instance','flywireType','hemibrainType','mancType','synonyms','status','statusLabel']
results={}
for candidate in ['LC4','LPLC2','MDN','DNa01','DNa02','P1','pC1']:
    mask=a[fields].eq(candidate).any(axis=1)
    results[candidate]=dict(exact_field_matches=int(mask.sum()),
        neurons=__import__('json').loads(a.loc[mask,cols].to_json(orient='records')))
mask=a.type.fillna('').str.match('^pC1')
results['pC1_family']=dict(type_prefix='pC1',count=int(mask.sum()),
    types=a.loc[mask,'type'].value_counts().to_dict(),
    neurons=__import__('json').loads(a.loc[mask,cols].to_json(orient='records')))
save(ROOT/'reports/annotation_investigation.json',dict(dataset='male-cns:v1.0',annotation_sha256=digest(path),
    searched_fields=fields,results=results,
    limitations=['P1/pC1 exact-field absence does not imply biological absence.',
        'pC1 prefix selection is a broad annotation family, not a claim all subtypes have the same function.',
        'food/temperature/pain config entries are intentionally empty; no unverified neuron IDs assigned.']))
print({k:v.get('exact_field_matches',v.get('count')) for k,v in results.items()})
