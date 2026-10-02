"""New regression report; prior certificates and reports are never overwritten."""
import io
import argparse
import unittest
from mvp.test_all import ROOT,module
from braincore.evidence import save

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='reports/behavior/tests.json');args=parser.parse_args()
    modules=[module(ROOT/path,name) for path,name in [
        ('tests/test_core.py','core_regression'),('tests/test_real.py','real_regression'),
        ('body/test_decoder.py','decoder_regression'),('ecology/test_ecology.py','ecology_regression'),
        ('mvp/test_mvp.py','mvp_regression'),('remaster/tests.py','remaster_regression'),
        ('behavior/tests.py','behavior_tests')]]
    destination=ROOT/args.out
    modules[3].save=lambda path,data:save(destination.parent/'regression-artifacts'/path.name,data)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report=dict(passed=result.wasSuccessful() and not result.skipped,tests=result.testsRun,
                skipped=len(result.skipped),output=stream.getvalue())
    save(destination,report)
    print(stream.getvalue());raise SystemExit(not report['passed'])

if __name__=='__main__':main()
