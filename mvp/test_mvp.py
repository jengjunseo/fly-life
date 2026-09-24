import io
import json
import math
import unittest
from mvp.presets import configure,PRESETS,NEW_HALF,area_evidence
from ecology.model import World
from mvp.bridge import ConsoleRuntime

class MvpTests(unittest.TestCase):
    def test_area_and_spawn_geometry(self):
        self.assertAlmostEqual(area_evidence()['ratio'],2.,places=14)
        for preset in PRESETS:
            w=World(configure(preset));w.advance(.05,[0.,.22,0.],0.)
            for event in w.schedule:
                if event['kind']!='heat':
                    r=w.cfg[event['kind']]['radius']
                    for k in (0,2):self.assertLess(abs(event['position'][k])+r,NEW_HALF-.1)
            shade=w.cfg['shade']
            for k in (0,2):self.assertLess(abs(shade['center'][k])+shade['half_size'][k],NEW_HALF-.1)
    def test_all_presets_and_seed_replay(self):
        for preset in PRESETS:
            a,b=World(configure(preset)),World(configure(preset))
            self.assertTrue(all(e['at_s']==.5 for e in a.schedule))
            for _ in range(70):
                a.advance(.05,[0.,.22,0.],0.);b.advance(.05,[0.,.22,0.],0.)
                self.assertEqual(a.snapshot(),b.snapshot())
            self.assertEqual(a.gut,0.)
            self.assertFalse(a.cfg['food']['ingestion_enabled'])
    def test_world_changes_are_queued_until_boundary(self):
        runtime=ConsoleRuntime.__new__(ConsoleRuntime)
        runtime.world=World(configure('CONTROL'));runtime.pending_actions=[]
        runtime.handle(dict(v=1,id='test-1',kind='world_event',event='food'))
        self.assertEqual(len(runtime.world.entities),0)
        self.assertEqual(len(runtime.pending_actions),1)
        runtime.handle(dict(v=1,id='test-2',kind='pause'))
        self.assertEqual([a['kind'] for a in runtime.pending_actions],['world_event','pause'])
    def test_no_hidden_biology_or_background_schedule(self):
        for preset in PRESETS:
            c=configure(preset)
            self.assertFalse(c['sensory']['pain_enabled']);self.assertFalse(c['sensory']['female_contact_enabled'])
            self.assertFalse(c['debug_neural_keys']);self.assertEqual(c['horizon_s'],0)
        with self.assertRaises(ValueError):configure('scripted-escape')
