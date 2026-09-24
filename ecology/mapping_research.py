"""Persist actual annotation candidates and negative debts without guessing IDs."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from braincore.evidence import save

if __name__=='__main__':
    n=pd.read_parquet(ROOT/'data/runtime/neurons.parquet');c=sparse.load_npz(ROOT/'data/runtime/counts.npz');w=sparse.load_npz(ROOT/'data/runtime/weights.npz')
    fields=['bodyId','type','instance','somaSide','superclass','class','subclass','receptorType','synonyms','consensus_nt']
    def records(mask):return json.loads(n.loc[mask,fields].to_json(orient='records'))
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    ppk=n.receptorType.fillna('').str.contains('ppk23|ppk29',regex=True)
    gn=n['class'].eq('gustatory');pain=n.type.fillna('').str.contains('nocicept|pain',case=False,regex=True)|n.synonyms.fillna('').str.contains('nocicept|pain',case=False,regex=True)
    loom=np.flatnonzero(n.type.isin(['LC4','LPLC2']));motor=np.flatnonzero(n.type.isin(['DNa01','DNa02','DNp09']))
    drive=np.asarray(w[:,loom].sum(axis=1)).ravel();paths=[]
    for t in motor:
        product=w.getrow(t).toarray().ravel()*drive;best=np.argsort(product)[-5:][::-1]
        paths.append(dict(target=int(n.iloc[t].bodyId),type=n.iloc[t].type,direct_loom_contacts=int(c[t,loom].sum()),
            two_hop_positive_products=[dict(bodyId=int(n.iloc[k].bodyId),type=None if pd.isna(n.iloc[k].type) else n.iloc[k].type,
                product=float(product[k]),loom_to_intermediate_normalized_weight=float(drive[k]),intermediate_to_motor_weight=float(w[t,k])) for k in best if product[k]>0]))
    taste=np.flatnonzero(n.type.eq('GNG540'));gust=np.flatnonzero(gn)
    report=dict(dataset='male-cns:v1.0',runtime_metadata_sha256=sha(ROOT/'data/runtime/metadata.json'),
        neurons_sha256=sha(ROOT/'data/runtime/neurons.parquet'),core_config_sha256=sha(ROOT/'config.json'),
        actual_sugar_aliases=records(n.synonyms.fillna('').str.contains('Sugar SEL',regex=False)),actual_Fdg_aliases=records(n.synonyms.fillna('').str.contains('Fdg',regex=False)),
        actual_thermo_afferents=records(n['class'].eq('thermosensory')),putative_contact_receptors=records(ppk),
        gustatory_type_counts=json.loads(n.loc[gn].groupby(['type','receptorType'],dropna=False).size().rename('members').reset_index().to_json(orient='records')),
        pain_name_candidates=records(pain),Sugar_SEL_PN_incoming_gustatory_contacts=int(c[taste][:,gust].sum()),
        loom_to_existing_motor_topology=paths,
        interpretation=dict(taste='Sugar SEL PN alias is actual; CNS bypass, peripheral sweet-GRN subclass unresolved; no claim of second-order order.',
            NT_discrepancy='Yao & Scott sugar SEL literature describes serotonin; actual preserved GNG540 consensus_nt=acetylcholine. No sign-policy override.',
            contact='putative_ppk23 is not verified female-specific receptive identity; neural contact mapping disabled.',
            pain='A mechanosensory annotation alone is not a verified nociceptive modality; neural pain disabled.',
            feeding='Actual Fdg alias found; no live activation/functional gate certificate, ingestion disabled.',
            visual='Two-hop topology is not functional propagation proof; LC4/LPLC2-only negative response scouts retained. LC9 is distinct experimental figure-motion input.'),
        primary_sources=['https://www.sciencedirect.com/science/article/pii/S0960982219301381','https://pubmed.ncbi.nlm.nih.gov/25972183/',
            'https://pubmed.ncbi.nlm.nih.gov/19396157/','https://pmc.ncbi.nlm.nih.gov/articles/PMC4911275/',
            'https://elifesciences.org/articles/66018','https://www.sciencedirect.com/science/article/pii/S0960982220308447',
            'https://www.sciencedirect.com/science/article/pii/S089662732101045X','https://elifesciences.org/articles/79887'])
    save(ROOT/'reports/ecology/research/mapping-research.json',report);print(json.dumps(dict(gustatory_neurons=int(gn.sum()),putative_ppk23=int(ppk.sum()),pain_named_candidates=int(pain.sum()),Sugar_SEL_PN_incoming_gustatory_contacts=report['Sugar_SEL_PN_incoming_gustatory_contacts']),indent=2))
