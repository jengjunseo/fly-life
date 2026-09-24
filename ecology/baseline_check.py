"""Re-run existing test suites without overwriting their original certificates."""
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'body'))
from braincore.evidence import save

if __name__=='__main__':
    suite=unittest.TestSuite([unittest.defaultTestLoader.discover(str(ROOT/'tests')),
        unittest.defaultTestLoader.discover(str(ROOT/'body'),pattern='test_decoder.py',top_level_dir=str(ROOT/'body'))])
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    # All pre-ecology tracked files must be byte-identical to f289a74, including old reports.
    files=subprocess.check_output(['git','ls-tree','-r','--name-only','f289a74'],cwd=ROOT,text=True).splitlines()
    changed=[];eol_only=[]
    for name in files:
        old=subprocess.check_output(['git','show','f289a74:'+name],cwd=ROOT)
        current=(ROOT/name).read_bytes()
        if current!=old:
            if current.replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n'):
                eol_only.append(dict(path=name,working_tree_bytes=len(current),git_object_bytes=len(old),note='Inherited CRLF working-tree console logs vs LF Git objects; not rewritten by ecology'))
            else:changed.append(name)
    report=dict(success=result.wasSuccessful() and not result.skipped and not changed,tests_run=result.testsRun,
        skipped=len(result.skipped),baseline_commit='f289a74',preexisting_files_checked=len(files),changed_baseline_files=changed,
        inherited_eol_only_differences=eol_only,output=stream.getvalue())
    save(ROOT/'reports/ecology/baseline.json',report);print(json.dumps(report,indent=2));raise SystemExit(0 if report['success'] else 1)
