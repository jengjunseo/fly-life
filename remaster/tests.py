import copy
import json
import unittest
import numpy as np
from scipy import sparse
from braincore.core import Brain
from remaster.fastbrain import FastBrain
from remaster.runtime import EfficientEncoder
from remaster.presets import configure
from ecology.model import World
from ecology.sensory import Encoder
from core_regression import parameters
from mvp.test_all import ROOT

class RemasterTests(unittest.TestCase):
    def test_signed_delivery_refractory_noise_and_reset_equivalence(self):
        weights=sparse.csr_matrix([[0,.3,-.4],[.6,0,.1],[-.2,.2,0]],dtype=np.float32)
        for noise in [0.,.1]:
            p=parameters(tau_m_ms=5.,rest=.2,reset=.1,noise_std=noise,baseline_current=.3)
            a,b=Brain(weights,p,seed=91),FastBrain(weights,p,seed=91)
            for i in range(100):
                current=None if i<10 else np.array([2.,-1.,.7],np.float32)
                a.step(current);b.step(current)
                for field in ['v','syn','spikes','refractory','activity','baseline']:
                    np.testing.assert_array_equal(getattr(a,field),getattr(b,field))
                self.assertEqual(a.rng.bit_generator.state,b.rng.bit_generator.state)

    def test_invalid_inputs_fail_before_advancing(self):
        b=FastBrain(sparse.csr_matrix((3,3)),parameters())
        for current in [[1.], [1.,np.nan,0.], [np.inf,0.,0.]]:
            with self.assertRaises(ValueError):b.step(current)
            self.assertEqual(b.step_count,0)

    def test_frame_resolution_retains_original_timestep(self):
        cfg=json.loads((ROOT/'config.json').read_text())
        b=FastBrain(sparse.csr_matrix((3,3)),cfg['model'])
        for frame in [10,20,50]:self.assertEqual(b.steps_for(frame),frame)
        self.assertEqual(b.p['dt_ms'],1.)
        with self.assertRaises(ValueError):b.steps_for(16.6667)

    def test_sensor_current_and_evidence_exactly_match(self):
        cfg=json.loads((ROOT/'config.json').read_text())
        brain=Brain.load(ROOT/'data/runtime',cfg)
        eco=configure('PREDATOR + HEAT');world=World(eco)
        a,b=Encoder(brain,eco['sensory']),EfficientEncoder(brain,eco['sensory'])
        for i in range(70):
            world.advance(.02,[0.,.22,0.],i*.01)
            raw=copy.deepcopy(world.sensor)
            raw.update(food_odor=(i%10)/10.,fly_odor=(i%7)/7.,contact_sugar=float(i%2))
            original,terms=a.encode(raw);fast,fast_terms=b.encode(raw)
            np.testing.assert_array_equal(original,fast);self.assertEqual(terms,fast_terms)

    def test_motor_test_has_no_scripted_ecology(self):
        c=configure('MOTOR TEST')
        self.assertEqual(World(c).initial_schedule,World(configure('CONTROL')).initial_schedule)
        self.assertFalse(c['food']['ingestion_enabled'])
        self.assertFalse(c['sensory']['pain_enabled'])
