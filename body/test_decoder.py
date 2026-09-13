import unittest
from decoder import decode


class DecoderTests(unittest.TestCase):
    def setUp(self): self.p=dict(activity_scale_hz=100.,forward_gain=1.,turn_gain=1.)
    def test_left_right_forward(self):
        self.assertEqual(decode(dict(left=100,right=0,forward=0),self.p),dict(forward=0,turn=-1))
        self.assertEqual(decode(dict(left=0,right=100,forward=0),self.p),dict(forward=0,turn=1))
        self.assertEqual(decode(dict(left=0,right=0,forward=50),self.p),dict(forward=.5,turn=0))
    def test_no_activity_no_movement(self):
        self.assertEqual(decode(dict(left=0,right=0,forward=0),self.p),dict(forward=0,turn=0))
    def test_invalid_and_saturation(self):
        with self.assertRaises(ValueError): decode(dict(left=float('nan'),right=0,forward=0),self.p)
        with self.assertRaises(ValueError): decode(dict(left=-1,right=0,forward=0),self.p)
        self.assertEqual(decode(dict(left=0,right=300,forward=300),self.p),dict(forward=1,turn=1))


if __name__=='__main__': unittest.main(verbosity=2)
