"""Reproducible API demo; repeatable against an existing seed, with independent review."""
import os
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
base = os.environ.get('DEMO_API_URL', 'http://localhost:8010')


def client(role):
    api = httpx.Client(base_url=base + '/api', timeout=300)
    response = api.post('/auth/login', json={'email': f'{role}@example.test', 'password': os.environ['BOOTSTRAP_PASSWORD']})
    response.raise_for_status()
    api.headers['Authorization'] = f'Bearer {response.json()["access_token"]}'
    return api


def request(api, method, path, body=None):
    response = api.request(method, path, json=body)
    response.raise_for_status()
    return response.json()


def main():
    with client('governance_analyst') as analyst, client('data_owner') as owner, client('reviewer') as reviewer:
        assets = request(analyst, 'GET', '/assets?page_size=100')['items']
        risk = next(a for a in assets if a['name'] == 'customer_risk')
        people = request(analyst, 'GET', '/users')['items']
        owner_id = next(u['id'] for u in people if u['role'] == 'DATA_OWNER')
        # Deliberately reintroduce an ownership gap; historical closed exceptions are retained.
        request(analyst, 'PATCH', f'/assets/{risk["id"]}', {'owner_id': None})
        run = request(analyst, 'POST', '/governance-controls/run', {'run_id': str(uuid4())})
        control = next(c for c in request(analyst,'GET','/governance-controls')['items'] if c['code']=='OWNERSHIP')
        exceptions = request(analyst, 'GET', '/exceptions?page_size=100')['items']
        exception = next(e for e in exceptions if e['data_asset_id']==risk['id'] and e['control_id']==control['id'] and e['status']!='Closed')
        eid = exception['id']
        state = exception['status']
        if state == 'Open':
            request(analyst,'POST',f'/exceptions/{eid}/transition',{'status':'Assigned','assignee_id':owner_id})
            state = 'Assigned'
        if state in {'Assigned', 'Rejected'}:
            request(analyst,'POST',f'/exceptions/{eid}/transition',{'status':'Remediation in Progress','remediation_plan':'Assign the accountable risk data owner and validate ownership control evidence.'})
            state = 'Remediation in Progress'
        request(analyst,'PATCH',f'/assets/{risk["id"]}',{'owner_id':owner_id})
        if state == 'Remediation in Progress':
            evidence = request(owner,'POST','/evidence',{'exception_id':eid,'document_name':'risk-ownership-attestation.pdf','document_type':'Ownership Attestation','local_reference':'private/risk-ownership-attestation.pdf','description':'Risk data office confirms accountable ownership of the customer risk dataset.'})
            request(owner,'POST',f'/exceptions/{eid}/transition',{'status':'Pending Review'})
        else:
            details=request(analyst,'GET',f'/exceptions/{eid}')
            evidence=next(e for e in details['evidence'] if e['status']=='Pending Review')
        request(reviewer,'POST',f'/evidence/{evidence["id"]}/review',{'status':'Approved','notes':'Independently verified the ownership assignment and passing governance control.'})
        closed=request(reviewer,'POST',f'/exceptions/{eid}/transition',{'status':'Closed'})
        final_run=request(analyst,'POST','/governance-controls/run',{})
        print(f'Control run recorded: {run["executions"]} executions; final failures: {final_run["failures"]}')
        print(f'{closed["reference"]}: {closed["status"]}; ownership remediated, evidence independently approved.')


if __name__ == '__main__':
    main()
