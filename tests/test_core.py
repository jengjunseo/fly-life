import unittest

import numpy as np
import pandas as pd
from scipy import sparse

from braincore.core import Brain, select, signed_normalized_matrix


def parameters(**updates):
    p = dict(dt_ms=1., tau_m_ms=1., tau_syn_ms=1., threshold=1., reset=0., rest=0.,
             refractory_ms=2., recurrent_gain=2., baseline_current=0., baseline_heterogeneity=0.,
             noise_std=0., activity_tau_ms=50.)
    p.update(updates)
    return p


class CoreTests(unittest.TestCase):
    def test_biological_direction(self):
        # Original records: body_pre=11 -> body_post=22 -> body_post=33.
        ids = np.array([11,22,33])
        pre, post = np.array([11,22]), np.array([22,33])
        w = sparse.coo_matrix(([1.,1.], (np.searchsorted(ids,post),np.searchsorted(ids,pre))), shape=(3,3)).tocsr()
        np.testing.assert_array_equal(w @ [1.,0.,0.], [0.,1.,0.])
        np.testing.assert_array_equal(w @ [0.,1.,0.], [0.,0.,1.])
        # Deterministic simulation proves the first spike is not sent backwards.
        brain = Brain(w, parameters())
        np.testing.assert_array_equal(brain.step([2.,0.,0.]), [1.,0.,0.])
        np.testing.assert_array_equal(brain.step(), [0.,1.,0.])
        np.testing.assert_array_equal(brain.step(), [0.,0.,1.])

    def test_presynaptic_sign_and_normalization(self):
        counts = sparse.csr_matrix([[0,0,0],[3,0,1],[0,5,0]])
        w = signed_normalized_matrix(counts, np.array([1,-1,0],np.float32))
        np.testing.assert_allclose(w @ [1,0,0], [0,1,0])
        np.testing.assert_allclose(w @ [0,1,0], [0,0,-1])
        self.assertEqual(w.dtype, np.float32)
        self.assertEqual(w.nnz, 2)

    def test_refractory_reset_and_negative_current(self):
        brain = Brain(sparse.csr_matrix((1,1)), parameters())
        self.assertEqual(brain.step([2])[0], 1)
        self.assertEqual(brain.v[0], 0)
        self.assertEqual(brain.step([2])[0], 0)
        self.assertEqual(brain.step([2])[0], 0)
        self.assertEqual(brain.step([2])[0], 1)
        brain.step([-2]); brain.step([-2]); brain.step([-2])
        self.assertEqual(brain.spikes[0], 0)
        self.assertLess(brain.v[0], 0)

    def test_external_current_only_selected(self):
        brain = Brain(sparse.csr_matrix((4,4)), parameters())
        external = brain.current([1,3], 2.)
        np.testing.assert_array_equal(external, [0,2,0,2])
        brain.step(external)
        np.testing.assert_array_equal(brain.spikes, [0,1,0,1])
        with self.assertRaises(ValueError): brain.current([-1],2)
        with self.assertRaises(ValueError): brain.step([1])
        with self.assertRaises(ValueError): brain.step([0,0,np.nan,0])

    def test_identity_selector_union(self):
        neurons = pd.DataFrame(dict(bodyId=[11,22,33,44],type=['LC4','MDN','pC1_1a',None]))
        np.testing.assert_array_equal(select(neurons, {'types':['LC4'],'bodyIds':[44],'type_regex':'^pC1'}),[0,2,3])

    def test_seed_and_warmup(self):
        w = sparse.csr_matrix((10,10))
        a, b = [Brain(w,parameters(tau_m_ms=20.,baseline_current=1.2,noise_std=.3),seed=7) for _ in range(2)]
        a.warmup(100); b.warmup(100)
        for _ in range(50): np.testing.assert_array_equal(a.step(),b.step())
        np.testing.assert_array_equal(a.v,b.v)
        self.assertEqual(a.step_count,150)
        with self.assertRaises(ValueError): a.steps_for(1.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
