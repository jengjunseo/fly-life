"""Read-only anatomical audit of literature thermal/escape candidate pathways."""
import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='reports/behavior-retry/pathway-audit.json');a=parser.parse_args()
    n=pd.read_parquet(ROOT/'data/runtime/neurons.parquet')
    cfg=json.loads((ROOT/'config.json').read_text())
    patterns=dict(warm_TRN='^TRN_VP2$',cool_TRN='^TRN_VP3[ab]$',warm_PN='^VP2.*PN$',
        cool_PN='^VP3.*PN$',TLHON_I='^LHPV2g',LHPV2a='^LHPV2a',LHAD1='^LHAD1(?:[^0-9]|$)',
        PVLP076='^PVLP076$',AVLP053='^AVLP053$',DNp06='^DNp06$',GF='^DNp01$',
        LC10a='^LC10a$',DNa02='^DNa02$',PSI='^PSI$',DLM='^DLMn',TTM='^TTMn')
    groups={k:np.flatnonzero((n.type.fillna('').str.match(v)|n.hemibrainType.fillna('').str.match(v)).to_numpy()) for k,v in patterns.items()}
    signs=n.consensus_nt.map(cfg['sign_policy']['signs']).fillna(0).to_numpy()
    report=dict(source='https://pmc.ncbi.nlm.nih.gov/articles/PMC10624821/',
        limitation='Candidate groups selected by explicit type/hemibrainType annotations. Connection counts do not establish motor direction or effective neural dynamics.',
        groups={k:json.loads(n.iloc[idx][['bodyId','type','hemibrainType','somaSide','rootSide','consensus_nt']].to_json(orient='records')) for k,idx in groups.items()},graphs={})
    for name,folder in [('pruned','runtime'),('restored','behavior')]:
        counts=sparse.load_npz(ROOT/f'data/{folder}/counts.npz')
        edges=[]
        for source,pre in groups.items():
            for target,post in groups.items():
                sub=counts[post][:,pre];total=int(sub.sum())
                if total:edges.append(dict(source=source,target=target,synapses=total,
                    positive_synapses=float(sub.multiply((signs[pre]>0)[None,:]).sum()),
                    negative_synapses=float(sub.multiply((signs[pre]<0)[None,:]).sum()),
                    zero_sign_synapses=float(sub.multiply((signs[pre]==0)[None,:]).sum())))
        report['graphs'][name]=dict(connections=int(counts.nnz),edges=edges)
    out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:len(v) for k,v in groups.items()}))

if __name__=='__main__':main()
