"""Persist exact unit/integration evidence as a JSON artifact."""
import io
import unittest
from pathlib import Path

from braincore.evidence import machine, save

ROOT=Path(__file__).parent
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
report=dict(machine=machine(),tests_run=result.testsRun,success=result.wasSuccessful(),
            skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),
            output=stream.getvalue())
save(ROOT/'reports/tests.json',report)
print(stream.getvalue())
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
