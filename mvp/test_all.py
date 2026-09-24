"""Run original suites, redirecting test-generated reports to a new evidence folder."""
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in [ROOT,ROOT/'body',ROOT/'ecology']:sys.path.insert(0,str(p))
from braincore.evidence import save

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

if __name__=='__main__':
    modules=[module(ROOT/'tests/test_core.py','core_regression'),module(ROOT/'tests/test_real.py','real_regression'),
             module(ROOT/'body/test_decoder.py','decoder_regression'),module(ROOT/'ecology/test_ecology.py','ecology_regression'),
             module(ROOT/'mvp/test_mvp.py','mvp_regression')]
    modules[3].save=lambda path,data:save(ROOT/'reports/mvp/regression-artifacts'/Path(path).name,data)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report=dict(passed=r.wasSuccessful() and not r.skipped,tests=r.testsRun,skipped=len(r.skipped),output=stream.getvalue())
    save(ROOT/'reports/mvp/tests.json',report);print(stream.getvalue());raise SystemExit(not report['passed'])
