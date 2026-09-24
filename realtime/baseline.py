"""Byte snapshot of ALL preexisting sources/reports/runtime; never rewrites old reports."""
import io
import json
import sys
import unittest
from common import ROOT, REPORT, sha, save, machine


def files():
    for folder in ('braincore', 'tests', 'body', 'ecology', 'reports', 'data/runtime'):
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or 'tools' in p.parts:
                continue
            if p.is_relative_to(REPORT) or p.suffix == '.pyc':
                continue
            yield p
    for p in ROOT.iterdir():
        if p.is_file():
            yield p


if __name__ == '__main__':
    if sys.argv[-1] == 'snapshot':
        save(REPORT/'baseline-before.json', dict(machine=machine(),
             files={str(p.relative_to(ROOT)): sha(p) for p in files()}))
    else:
        before = json.loads((REPORT/'baseline-before.json').read_text())['files']
        changed = [name for name, digest in before.items() if not (ROOT/name).is_file() or sha(ROOT/name) != digest]
        sys.path.insert(0, str(ROOT/'body'))
        suite = unittest.TestSuite([unittest.defaultTestLoader.discover(str(ROOT/'tests')),
            unittest.defaultTestLoader.discover(str(ROOT/'body'), pattern='test_decoder.py', top_level_dir=str(ROOT/'body'))])
        stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        report=dict(success=not changed and result.wasSuccessful() and not result.skipped,
            checked_files=len(before), changed_files=changed, tests=result.testsRun, output=stream.getvalue())
        save(REPORT/'baseline-after.json',report);print(json.dumps(report,indent=2))
        raise SystemExit(not report['success'])
