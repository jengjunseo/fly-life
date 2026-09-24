# Data attribution

This project derives its neural identity table and sparse graph from **MaleCNS
v1.0**, distributed by the FlyEM/HHMI Janelia, Cambridge, MRC LMB and Google
Research collaborators under **Creative Commons Attribution 4.0 International**.

Official dataset: https://male-cns.janelia.org/download/
License: https://creativecommons.org/licenses/by/4.0/

Original release filenames, URLs, bytes and pinned SHA-256 are retained verbatim
in `data/raw/manifest.json`. The runtime is a **modified/derived** representation:
Traced-neuron selection; configured synapse-count pruning with protected groups;
presynaptic NT sign policy; absolute incoming normalization; CSR matrix order
`[target, source]`. Full policies and provenance are in `config.json` and
`data/runtime/metadata.json`; the unchanged detailed brain-core report remains in
`docs/BRAIN_CORE.md`. These transformations are our engineering assumptions and
do not imply endorsement or biological validation by the data creators.

The frozen runtime files are included for reproducibility. The substantially
larger raw Feather files are not redistributed in Git and can be downloaded with
`acquire.py`, whose SHA checks must not be bypassed. No anatomical meshes or
neuron images are included in the primitive virtual-world rendering.
