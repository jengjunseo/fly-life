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
from behavior.sensorimotor import SensorimotorWorld,SensorimotorEncoder,SteeringReadout
from behavior.model import load_connectivity

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

class SensorimotorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.brain=Brain.load(ROOT/'data/runtime',CFG)

    def world(self):return SensorimotorWorld(configure('CONTROL',42,8))

    def test_food_has_primitive_visual_features_without_identity(self):
        w=self.world();w.spawn(dict(kind='food',position=[-1.,.22,-1.]))
        raw=w.sense(.02);self.assertEqual(len(raw['figures']),1)
        for forbidden in ['kind','id','bodyId','position','target','desired_turn']:self.assertNotIn(forbidden,raw['figures'][0])
        self.assertGreater(raw['figures'][0]['angular_size_deg'],0)

    def test_self_motion_removed_from_looming_but_not_retinal_object_motion(self):
        w=self.world();w.spawn(dict(kind='food',position=[0.,.22,-2.]))
        w.sense(.02);w.fly=[0.,.22,-.2]
        f=w.sense(.02)['figures'][0]
        self.assertGreater(f['positive_expansion_deg_s'],0)
        self.assertEqual(f['compensated_expansion_deg_s'],0)
        self.assertGreater(f['angular_motion_deg_s'],0)

    def test_real_approach_is_not_removed_by_compensation(self):
        w=self.world();w.spawn(dict(kind='predator',position=[0.,.3,-2.]))
        w.sense(.02);next(iter(w.entities.values()))['position'][2]= -1.8
        self.assertGreater(w.sense(.02)['figures'][0]['compensated_expansion_deg_s'],0)

    def test_modality_ablation_preserves_other_inputs_and_never_drives_motor(self):
        w=self.world();w.spawn(dict(kind='food',position=[-1.,.22,-1.]));raw=w.sense(.02)
        raw['figures'][0]['angular_motion_deg_s']=30.
        e=SensorimotorEncoder(self.brain,w.cfg['sensory']);all_current,_=e.encode(raw)
        self.assertGreater(float(all_current[e.indices['small_object']].sum()),0)
        self.assertGreater(float(all_current[e.indices['food_odor']].sum()),0)
        e.params['vision_enabled']=False;chemical,_=e.encode(raw)
        np.testing.assert_array_equal(chemical[e.indices['small_object']],0.)
        np.testing.assert_array_equal(chemical[e.indices['food_odor']],all_current[e.indices['food_odor']])
        e.params['vision_enabled']=True;e.params['chemical_enabled']=False;visual,_=e.encode(raw)
        np.testing.assert_array_equal(visual[e.indices['food_odor']],0.)
        np.testing.assert_array_equal(visual[e.indices['small_object']],all_current[e.indices['small_object']])
        motor=self.brain.resolve(dict(types=['DNa02','DNp09','DNp01','DNp06']))
        np.testing.assert_array_equal(all_current[motor],0.)

    def test_signed_cooling_and_global_disable(self):
        w=self.world();raw=w.sense(.02);e=SensorimotorEncoder(self.brain,w.cfg['sensory'])
        for side,rate in [('L',1.),('R',-1.)]:raw['bilateral'][side]['temperature_change_c_s']=rate
        current,_=e.encode(raw)
        self.assertLess(float(current[e.sides['cold']['L']].mean()),0.)
        self.assertGreater(float(current[e.sides['cold']['R']].mean()),0.)
        e.params['thermal_enabled']=False;current,_=e.encode(raw)
        for name in ['hot','cold']:np.testing.assert_array_equal(current[e.indices[name]],0.)
        e.params['enabled']=False;current,terms=e.encode(raw)
        np.testing.assert_array_equal(current,0.)
        self.assertTrue(all(t['amplitude']==0 for t in terms))

    def test_steering_uses_spikes_only_and_zero_warmup_bias(self):
        b=self.brain;old=b.activity.copy();step=b.step_count
        try:
            r=SteeringReadout(b);b.activity[:]=0.;b.step_count=300
            b.activity[r.sides['R']]=20.;r.observe(b,True)
            for _ in range(300):r.observe(b,False)
            self.assertEqual(r.decode(6.)['turn'],0.)
            b.activity[r.sides['R']]=40.
            for _ in range(300):r.observe(b,False)
            self.assertGreater(r.decode(6.)['turn'],0.)
            b.activity[r.sides['R']]=0.
            for _ in range(1000):r.observe(b,False)
            self.assertLess(r.decode(6.)['turn'],0.)
        finally:b.activity[:]=old;b.step_count=step

    def test_psi_override_adds_only_annotated_psi_output(self):
        base,neurons,old=load_connectivity(CFG)
        new,_,evidence=load_connectivity(CFG,psi_literature=True)
        psi=np.flatnonzero(neurons.type.eq('PSI').to_numpy())
        self.assertEqual(old['literature_sign_overrides'],[])
        self.assertEqual(set(evidence['literature_sign_overrides'][0]['bodyIds']),{802401,903327})
        changed=(new-base).tocoo()
        self.assertGreater(changed.nnz,0);self.assertTrue(np.isin(changed.col,psi).all())
        self.assertTrue(neurons.iloc[psi].consensus_nt.eq('unclear').all())

    def test_steering_calibration_excludes_initial_transient(self):
        b=self.brain;old=b.activity.copy();step=b.step_count
        try:
            r=SteeringReadout(b,warmup_ms=2000.)
            b.activity[:]=0.;b.activity[r.sides['R']]=100.;b.step_count=500
            r.observe(b,True);self.assertEqual(r.count,0)
            b.activity[r.sides['R']]=10.;b.step_count=1500
            r.observe(b,True);self.assertEqual(r.bias,10.)
            b.activity[r.sides['R']]=20.;b.step_count=2000
            r.observe(b,True);self.assertEqual(r.bias,15.)
        finally:b.activity[:]=old;b.step_count=step

    def test_evidence_can_repeat_without_mutating_shared_mapping(self):
        w=self.world();e=SensorimotorEncoder(self.brain,w.cfg['sensory'])
        self.assertEqual(e.evidence(),e.evidence())
        old=BilateralEncoder(self.brain,w.cfg['sensory']).evidence()
        self.assertNotIn('small_object',old)

if __name__=='__main__':unittest.main()
