"""Integration checks against downloaded/preprocessed MaleCNS, never a fallback graph."""
import json
import unittest
from pathlib import Path

import numpy as np
from scipy import sparse

from braincore import Brain
from braincore.core import signed_normalized_matrix

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'data/runtime'


@unittest.skipUnless((RUNTIME/'metadata.json').exists(), 'Run preprocess.py to enable real-data integration tests')
class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT/'config.json').read_text())
        cls.brain = Brain.load(RUNTIME,cls.config)
        cls.counts = sparse.load_npz(RUNTIME/'counts.npz')
        cls.meta = json.loads((RUNTIME/'metadata.json').read_text())

    def test_real_dataset_and_identity(self):
        self.assertEqual(self.meta['dataset'],'male-cns:v1.0')
        self.assertEqual(self.brain.n,165122)
        self.assertEqual(self.counts.nnz,self.meta['retained_connection_count'])
        self.assertTrue(self.brain.neurons.bodyId.is_unique)
        self.assertTrue(self.brain.neurons.status.eq('Traced').all())
        for g in ['looming','escape','steering','courtship','giant_fiber']:
            self.assertGreater(len(self.brain.resolve(self.config['groups'][g])),0)

    def test_actual_known_direction_and_signs(self):
        # These selectors are config data, not simulation-code neuron rules.
        src = self.brain.resolve(self.config['groups']['looming'])
        dst = self.brain.resolve(self.config['groups']['giant_fiber'])
        self.assertGreater(self.counts[dst,:][:,src].nnz,0)
        spikes = np.zeros(self.brain.n,np.float32); spikes[src]=1
        current = self.brain.w @ spikes
        self.assertTrue((current[dst]>0).all())
        signs = self.brain.neurons.consensus_nt.map(self.config['sign_policy']['signs']).fillna(0).to_numpy(np.float32)
        expected=signed_normalized_matrix(self.counts,signs)
        self.assertEqual((expected != self.brain.w).nnz,0)
        self.assertGreater(np.count_nonzero(self.brain.w.data<0),0)

    def test_real_stimulus_delivery(self):
        a=Brain.load(RUNTIME,self.config,seed=91)
        b=Brain.load(RUNTIME,self.config,seed=91)
        idx=a.resolve(self.config['groups'][self.config['experiment']['input_group']])
        ext=a.current(idx,self.config['experiment']['stimulus_current'])
        # At initialization these cells do not cross threshold, so the voltage
        # difference must equal Euler dt/tau times external current, only on idx.
        a.step(ext); b.step()
        expected=ext*a.p['dt_ms']/a.p['tau_m_ms']
        np.testing.assert_allclose(a.v-b.v,expected,atol=2e-8,rtol=1e-6)
        np.testing.assert_array_equal(np.flatnonzero(ext),idx)
        self.assertEqual(np.count_nonzero(ext),len(idx))

    def test_pruning_retains_low_degree_identity(self):
        isolated=np.flatnonzero((np.diff(self.counts.indptr)==0)&(self.counts.getnnz(axis=0)==0))
        self.assertEqual(len(isolated),self.meta['disconnected_neuron_count'])
        self.assertGreater(len(isolated),0)
        self.assertTrue(self.brain.neurons.iloc[isolated].bodyId.notna().all())


if __name__=='__main__':
    unittest.main(verbosity=2)
