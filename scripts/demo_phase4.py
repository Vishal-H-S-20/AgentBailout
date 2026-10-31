"""Live HTTP comparison demo. Does not call paid providers unless you explicitly select them."""
import argparse
import time
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8003')
parser.add_argument('--template',choices=['research','coding','document'],default='coding')
parser.add_argument('--scenario',default='crash')
args=parser.parse_args()
with httpx.Client(base_url=args.url,timeout=10) as client:
    start=time.monotonic()
    response=client.post('/comparisons',json={'prompt':'Create a text normalization utility',
        'workflow_id':'template-'+args.template,'failure':{'scenario':args.scenario,'stage_index':1}})
    response.raise_for_status()
    comparison_id=response.json()['id']
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        response=client.get('/comparisons/'+comparison_id)
        response.raise_for_status()
        result=response.json()
        if all(result[key]['execution_seconds'] is not None for key in ['baseline','protected']):
            break
        time.sleep(.1)
    else:
        raise RuntimeError('Comparison did not finish within 30 seconds')
    print('Comparison:',comparison_id)
    for key in ['baseline','protected']:
        run=result[key]
        assert run['ledger']['balanced'] and run['ledger']['settled']
        print(key,run['status'],'seconds=',round(run['execution_seconds'],3),
              'recovery_attempts=',run['recovery_attempts'],'API cost=',run['api_cost'],
              'simulated refund=',run['ledger']['balances']['client_refund'])
    print('Protected minus baseline seconds:',round(result['time_difference_seconds'],3))
    print('Observed wall clock seconds:',round(time.monotonic()-start,3))
    print(result['note'])
