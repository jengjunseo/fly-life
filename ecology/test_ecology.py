"""New reports only. Unit rules plus real annotation/current/topology integration."""
import copy
import io
import json
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parent;CORE=ROOT.parent;sys.path.insert(0,str(CORE))
from braincore import Brain
from braincore.evidence import save
from model import World,load_config,distance
from sensory import Encoder,amplitudes


class Rules(unittest.TestCase):
    def setUp(self):self.cfg=load_config(ROOT/'config.json','certification')
    def test_seed_schedule_and_replay_unit(self):
        a,b=World(self.cfg),World(self.cfg)
        self.assertEqual(a.initial_schedule,b.initial_schedule)
        for _ in range(60):
            a.advance(.05,[0.,.22,0.],0.);b.advance(.05,[0.,.22,0.],0.)
            self.assertEqual(a.snapshot(),b.snapshot());self.assertEqual(a.events,b.events)
    def test_world_time_no_wall_or_render_unit(self):
        world=World(self.cfg);before=world.snapshot()
        for _ in range(50):world.snapshot()
        self.assertEqual(before,world.snapshot());world.advance(.05,[0.,.22,0.],0.)
        self.assertEqual(world.time,.05)
        with self.assertRaises(ValueError):world.advance(1.,[0.,.22,0.],0.)
    def test_food_no_collision_ingestion_unit(self):
        w=World(self.cfg);w.advance(0.,[0.,.22,0.],0.,500.)
        h,g=w.hunger,w.gut;w.advance(.05,[0.,.22,0.],0.,500.)
        self.assertGreater(w.hunger,h);self.assertLess(w.gut,g)
        self.assertFalse(any(e['event']=='FOOD_INGEST' for e in w.events))
        self.assertEqual(w.sensor['contact_sugar'],1.);self.assertEqual(w.sensor['food_odor'],1.)
    def test_conditional_gate_rule_unit_not_live_certificate(self):
        # Counterfactual only: production ingestion stays DISABLED.
        cfg=copy.deepcopy(self.cfg);cfg['food']['ingestion_enabled']=True
        w=World(cfg);w.advance(0.,[0.,.22,0.],0.,0.)
        w.advance(.05,[0.,.22,0.],0.,19.)
        self.assertFalse(any(e['event']=='FOOD_INGEST' for e in w.events))
        w.advance(.05,[0.,.22,0.],0.,21.)
        self.assertTrue(any(e['event']=='FOOD_INGEST' for e in w.events))
        other=World(cfg);other.advance(.05,[3.,.22,3.],0.,500.)
        self.assertFalse(any(e['event']=='FOOD_INGEST' for e in other.events))
    def test_damage_death_and_defecation_placeholder_unit(self):
        cfg=copy.deepcopy(self.cfg);cfg['initial_hp']=12.
        w=World(cfg)
        for _ in range(50):w.advance(.05,[0.,.22,0.],0.)
        self.assertEqual(w.hp,0.);self.assertEqual(sum(e['event']=='DEATH' for e in w.events),1)
        feces=[e for e in w.events if e['event']=='DEFECATE']
        self.assertTrue(feces);self.assertEqual(feces[0]['classification'],'PHYSIOLOGY_PLACEHOLDER')
        self.assertFalse(any('PAIN_CURRENT'==e['event'] for e in w.events))
    def test_loom_geometry_not_distance_switch_unit(self):
        w=World(self.cfg);rows=[]
        for _ in range(16):
            w.advance(.05,[0.,.22,0.],0.);fig=[f for f in w.sensor['figures'] if f['contrast']==1.]
            if fig:rows.append(fig[0])
        self.assertEqual(rows[0]['positive_expansion_deg_s'],0.)
        self.assertGreater(rows[-1]['angular_size_deg'],rows[1]['angular_size_deg'])
        self.assertGreater(rows[-1]['positive_expansion_deg_s'],0.)
        raw=copy.deepcopy(w.sensor)
        for f in raw['figures']:f['positive_expansion_deg_s']=0.;f['angular_motion_deg_s']=0.
        amp=amplitudes(raw,self.cfg['sensory']);self.assertEqual(amp['lc4'],0.);self.assertEqual(amp['lplc2'],0.);self.assertEqual(amp['figure'],0.)
    def test_sensor_boundary_has_no_target_direction_or_internal_state_unit(self):
        w=World(self.cfg)
        self.assertEqual(set(w.sensor),{'figures','food_odor','contact_sugar','fly_odor','contact_cuticle','temperature_c','temperature_change_c_s'})
        source=(ROOT/'sensory.py').read_text()
        self.assertNotIn('forward_gain',source);self.assertNotIn('max_turn',source)
    def test_interactive_seeded_non_perframe_schedule_unit(self):
        cfg=load_config(ROOT/'config.json');w=World(cfg)
        self.assertGreater(len(w.schedule),100)
        self.assertTrue(all(e['at_s']>0 for e in w.schedule));self.assertTrue(any(e.get('wander') for e in w.schedule))


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain=Brain.load(CORE/'data/runtime',json.loads((CORE/'config.json').read_text()));cls.cfg=load_config(ROOT/'config.json','certification')
        cls.encoder=Encoder(cls.brain,cls.cfg['sensory'])
    def test_actual_sensory_current_excludes_motor_and_readout_integration(self):
        w=World(self.cfg)
        for _ in range(16):w.advance(.05,[0.,.22,0.],0.)
        cur,terms=self.encoder.encode(w.sensor)
        allowed=np.concatenate([self.encoder.indices[t['modality']] for t in terms])
        self.assertTrue(np.isin(np.flatnonzero(cur),allowed).all());self.assertTrue(np.isfinite(cur).all())
        motor=self.brain.resolve(dict(types=['DNa01','DNa02','DNp09','DNp01','GNG588'],type_regex='^pC1'))
        self.assertFalse(cur[motor].any())
        self.assertGreater(cur[self.encoder.indices['lc4']].max(),0.)
        self.assertGreater(cur[self.encoder.indices['food_odor']].max(),0.)
        self.assertGreater(cur[self.encoder.indices['fly_odor']].max(),0.)
    def test_actual_hot_shade_current_comparison_initial_conditions_only_integration(self):
        # Relocation is test setup only; no shade-directed behavior implemented.
        w=World(self.cfg);w.time=.7;w.heat_start=.3
        hot,_=w.local_temperature([0.,.22,0.]);shade,_=w.local_temperature([2.,.22,1.8])
        raw=copy.deepcopy(w.sensor);raw['temperature_change_c_s']=0.
        raw['temperature_c']=hot;a,terms=self.encoder.encode(raw)
        raw['temperature_c']=shade;b,_=self.encoder.encode(raw)
        self.assertAlmostEqual(hot-shade,6.)
        self.assertGreater(float(a[self.encoder.indices['hot']].mean()),float(b[self.encoder.indices['hot']].mean()))
        save(CORE/'reports/ecology/thermal-integration.json',dict(level='INTEGRATION_INITIAL_CONDITIONS_NOT_BEHAVIOR',hot_c=hot,shade_c=shade,
            hot_current=float(a[self.encoder.indices['hot']].mean()),shade_current=float(b[self.encoder.indices['hot']].mean()),hot_bodyIds=self.brain.neurons.iloc[self.encoder.indices['hot']].bodyId.tolist(),shade_direction_input=False))
    def test_actual_ecology_current_enters_lif_selected_voltage_integration(self):
        a=Brain.load(CORE/'data/runtime',json.loads((CORE/'config.json').read_text()),seed=91)
        b=Brain.load(CORE/'data/runtime',json.loads((CORE/'config.json').read_text()),seed=91)
        world=World(self.cfg)
        for _ in range(16):world.advance(.05,[0.,.22,0.],0.)
        current,_=self.encoder.encode(world.sensor)
        a.step(current);b.step()
        np.testing.assert_allclose(a.v-b.v,current*a.p['dt_ms']/a.p['tau_m_ms'],atol=2e-8,rtol=1e-6)
        self.assertEqual(a.n,165122)
    def test_alias_and_actual_topology_integration(self):
        e=self.encoder;brain=self.brain;c=sparse.load_npz(CORE/'data/runtime/counts.npz');dn=brain.resolve(dict(types=['DNp09']))
        contacts=int(c[dn][:,e.indices['figure']].sum())
        self.assertGreater(contacts,0)
        self.assertEqual(brain.neurons.iloc[e.indices['feeding_observation']].bodyId.tolist(),[12617,14321])
        # Preserve negative evidence: topology is not a functional feeding gate.
        f=e.indices['feeding_observation'];taste=e.indices['taste']
        save(CORE/'reports/ecology/topology.json',dict(level='INTEGRATION_ACTUAL_MATRIX',figure_LC9_to_DNp09_contacts=contacts,
            targets=[dict(bodyId=int(brain.neurons.iloc[idx].bodyId),LC9_contacts=int(c[idx,e.indices['figure']].sum()),
                LC9_signed_normalized_weight=float(brain.w[idx,e.indices['figure']].sum()),LC4_LPLC2_contacts=int(c[idx,np.concatenate([e.indices['lc4'],e.indices['lplc2']])].sum())) for idx in dn],
            Sugar_SEL_PN_to_Fdg_contacts=int(c[f][:,taste].sum()),Fdg_aliases=e.evidence()['feeding_observation'],ingestion_enabled=False))


if __name__=='__main__':
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    save(CORE/'reports/ecology/tests.json',dict(success=result.wasSuccessful(),tests_run=result.testsRun,skipped=len(result.skipped),output=stream.getvalue()))
    print(stream.getvalue());raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
