import io, json, subprocess, sys, unittest
from env import ROOT, REPORT, sha, save, machine

def files():
    for d in ['braincore','tests','body','ecology','realtime','reports','data/runtime']:
        for p in (ROOT/d).rglob('*'):
            if not p.is_file() or any(x in p.parts for x in ['__pycache__','.godot','tools']):
                continue
            if p.is_relative_to(ROOT/'realtime/gate-e') or p.is_relative_to(REPORT):
                continue
            yield p
    yield from (p for p in ROOT.iterdir() if p.is_file())

if __name__ == '__main__':
    path = REPORT/'preservation-before.json'
    if sys.argv[-1] == 'before':
        assert not path.exists(), 'Do not replace frozen before snapshot'
        save(path, dict(machine=machine(),git_status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
                        files={str(p.relative_to(ROOT)):sha(p) for p in files()}))
    else:
        old=json.loads(path.read_text());changed=[n for n,h in old['files'].items() if not(ROOT/n).is_file() or sha(ROOT/n)!=h]
        sys.path.insert(0,str(ROOT/'body'));stream=io.StringIO()
        suite=unittest.TestSuite([unittest.defaultTestLoader.discover(str(ROOT/'tests')),
            unittest.defaultTestLoader.discover(str(ROOT/'body'),pattern='test_decoder.py',top_level_dir=str(ROOT/'body'))])
        r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        d=dict(success=not changed and r.wasSuccessful() and not r.skipped,checked_files=len(old['files']),
               changed_files=changed,tests=r.testsRun,test_output=stream.getvalue(),machine=machine())
        save(REPORT/'preservation-after.json',d);print(json.dumps(d,indent=2));raise SystemExit(not d['success'])
