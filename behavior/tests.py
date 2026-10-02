import json
import unittest
import tempfile
import shutil
from pathlib import Path
import numpy as np
from scipy import sparse
from braincore.core import Brain
from behavior.model import CountBrain,parameters
from behavior.world import ExperimentWorld
from behavior.sensory import BilateralEncoder
from behavior.readout import EscapeReadout
from behavior.presets import configure
from behavior.run_assays import rows

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config.json').read_text())

class BehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain=Brain.load(ROOT/'data/runtime',CFG)

    def world(self, name='CONTROL'):
        return ExperimentWorld(configure(name,42,8))

    def test_food_antennae_mirror(self):
        a,b=self.world(),self.world()
        a.spawn(dict(kind='food',position=[-1.,.22,-1.]))
        b.spawn(dict(kind='food',position=[1.,.22,-1.]))
        x,y=a.sense(0.)['bilateral'],b.sense(0.)['bilateral']
        self.assertGreater(x['L']['food_odor'],x['R']['food_odor'])
        self.assertAlmostEqual(x['L']['food_odor'],y['R']['food_odor'])
        self.assertAlmostEqual(x['R']['food_odor'],y['L']['food_odor'])

    def test_thermal_mirror_and_outside_gradient(self):
        a,b=self.world('HEAT'),self.world('HEAT RIGHT')
        a.cfg['ambient_c']=b.cfg['ambient_c']=34.
        x,y=a.sense(0.)['bilateral'],b.sense(0.)['bilateral']
        self.assertLess(x['L']['temperature_c'],x['R']['temperature_c'])
        self.assertAlmostEqual(x['L']['temperature_c'],y['R']['temperature_c'])
        self.assertFalse(a.in_shade)
        self.assertLess(x['L']['temperature_c'],34.)

    def test_antennal_rotation_uses_body_yaw(self):
        w=self.world();w.yaw=np.pi/2
        left,right=w.antennae()['L'],w.antennae()['R']
        self.assertLess(left[0],w.fly[0]);self.assertGreater(left[2],right[2])

    def test_odor_encoder_retains_laterality(self):
        w=self.world();w.spawn(dict(kind='food',position=[-1.,.22,-1.]))
        e=BilateralEncoder(self.brain,w.cfg['sensory']);current,terms=e.encode(w.sense(0.))
        left=current[e.sides['food_odor']['L']];right=current[e.sides['food_odor']['R']]
        self.assertGreater(float(left.mean()),float(right.mean()))
        self.assertEqual(len(e.indices['food_odor']),157)
        self.assertTrue(all(t['side'] in ['L','R','U'] for t in terms))

    def test_visual_hemisphere_does_not_stimulate_motor(self):
        w=self.world();raw=w.sense(0.)
        raw['figures']=[dict(angular_size_deg=60.,positive_expansion_deg_s=60.,
                            bearing_radians=-np.pi/2,angular_motion_deg_s=60.,contrast=1.)]
        e=BilateralEncoder(self.brain,w.cfg['sensory']);current,_=e.encode(raw)
        self.assertGreater(current[e.sides['lc4']['L']].mean(),0.)
        self.assertEqual(float(current[e.sides['lc4']['R']].max()),0.)
        motor=self.brain.resolve(dict(types=['DNp09','DNa01','DNa02','DNp01','GNG588']))
        np.testing.assert_array_equal(current[motor],0.)

    def test_sensory_ablation_is_zero(self):
        w=self.world('FOOD');w.cfg['sensory']['enabled']=False
        w.spawn(dict(kind='food',position=[0.,.22,0.]))
        e=BilateralEncoder(self.brain,w.cfg['sensory']);current,terms=e.encode(w.sense(0.))
        self.assertEqual(np.count_nonzero(current),0)
        self.assertTrue(all(t['amplitude']==0 for t in terms))

    def test_encoder_evidence_lists_actual_va2(self):
        e=BilateralEncoder(self.brain,self.world().cfg['sensory']);v=e.evidence()['food_odor']
        self.assertIn('ORN_VA2',{m['type'] for m in v['members']})
        self.assertEqual(sum(len(ids) for ids in v['bilateral_bodyIds'].values()),157)

    def test_no_entity_identity_or_target_in_sensor(self):
        raw=self.world('PREDATOR').sense(0.)
        self.assertNotIn('target',raw);self.assertNotIn('position',raw);self.assertNotIn('entities',raw)
        for side in raw['bilateral'].values():self.assertNotIn('direction',side)

    def test_count_spike_reset_and_silencing(self):
        p=parameters(CFG,0.);p.update(noise_std=0.,recurrent_gain=1.)
        b=CountBrain(sparse.csr_matrix([[0.,0.],[100.,0.]]),p)
        b.step(np.array([30.,0.]));self.assertEqual(b.spikes[0],1.)
        b.step();self.assertEqual(b.spikes[1],1.);self.assertEqual(b.syn[1],0.)
        b.silenced=np.array([0,1])
        for _ in range(10):b.step(np.array([30.,30.]));np.testing.assert_array_equal(b.spikes,0.)
        np.testing.assert_array_equal(b.activity,0.)

    def test_no_tonic_or_input_no_motion_source(self):
        p=parameters(CFG,0.);p['noise_std']=0.
        b=CountBrain(sparse.csr_matrix([[0.,3.],[3.,0.]]),p)
        for _ in range(100):b.step()
        np.testing.assert_array_equal(b.activity,0.)

    def test_invalid_tonic_rejected(self):
        for value in [-1.,3.,float('nan')]:
            with self.assertRaises(ValueError):parameters(CFG,value)

    def test_escape_uses_only_gf_neural_state_and_time(self):
        b=self.brain;old=b.activity.copy();step=b.step_count
        try:
            b.activity[:]=0.;r=EscapeReadout(b)
            self.assertEqual(r.decode(b)['escape_motor'],0.)
            b.activity[r.indices]=100.;self.assertEqual(r.decode(b)['escape_motor'],1.)
            self.assertEqual(r.decode(b)['escape_motor'],0.)
            b.step_count+=600;self.assertEqual(r.decode(b)['escape_motor'],1.)
            r.enabled=False;b.step_count+=600;self.assertEqual(r.decode(b)['escape_motor'],0.)
        finally:b.activity[:]=old;b.step_count=step

    def test_presets_have_observation_time_and_mirror(self):
        a,b=configure('FOOD',42,8),configure('FOOD RIGHT',42,8)
        self.assertEqual(a['initial_events'][0]['at_s'],2.)
        self.assertEqual(a['initial_events'][0]['position'][0],-b['initial_events'][0]['position'][0])
        self.assertGreaterEqual(a['food']['lifetime_s'],30.)
        self.assertEqual(a['horizon_s'],0.)

    def test_world_measurements_only_completed_body_time(self):
        w=self.world();w.advance(.02,[1.,.22,0.],0.)
        m=w.snapshot()['experiment_measurements']
        self.assertAlmostEqual(m['path_length'],1.)
        self.assertAlmostEqual(w.time,.02)
        w.sense(0.);self.assertAlmostEqual(w.time,.02)

    def test_archived_world_trace_reads_without_local_original(self):
        source=ROOT/'reports/behavior/assays/control/world.jsonl'
        expected=rows(source)
        with tempfile.TemporaryDirectory(prefix='braincore-archive-') as folder:
            target=Path(folder)/'world.jsonl'
            shutil.copyfile(str(source)+'.gz',str(target)+'.gz')
            self.assertFalse(target.exists())
            self.assertEqual(rows(target),expected)

if __name__=='__main__':unittest.main()
