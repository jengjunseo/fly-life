"""Run the complete real-data sanity suite with Python socket connections denied."""
import json
import sys

from braincore.evidence import save
from run import ROOT, sanity

attempts=[]

def deny_network(event,args):
    if event in ['socket.connect','socket.getaddrinfo']:
        attempts.append(event)
        raise RuntimeError('Offline verification: network connection forbidden')

sys.addaudithook(deny_network)
config=json.loads((ROOT/'config.json').read_text())
sanity(ROOT/'data/runtime',config,ROOT/'reports/sanity')
save(ROOT/'reports/offline.json',dict(real_dataset='male-cns:v1.0',
    python_socket_connect_and_dns_audit_guard=True,network_attempts=len(attempts),
    entire_sanity_suite_passed=True,
    limitation='Python socket audit guard, not physical disconnection of the entire machine.'))
print('Offline verification passed: no DNS/socket connection attempts',flush=True)
