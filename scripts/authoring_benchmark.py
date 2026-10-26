#!/usr/bin/env python3
"""Versioned synthetic task checks through an installed app, with no stored secrets.

Offline score aggregation is pure Python. --live uses the caller's existing Splunk
session and selected provider; it never changes providers, credentials or settings.
Full replies, queries, hosts, headers and result rows are never written to reports.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, HTTPSHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'splunk/constellation/bin'))
from authoring_actions import compile_actions
from provider_service import ProviderError
from studio_contract import apply_changes, validate_document
from token_service import resolve_query_tokens
from search_service import read_only_query
import row_navigation

SUITE_VERSION = '1'
WEIGHTS = {'completion':10,'scope':20,'population':25,'navigation':20,'preservation':15,'bindings':10}
CRITICAL = frozenset(WEIGHTS)
BASE = ('| makeresults count=7 | streamstats count AS ordinal '
        '| eval device_name=if(ordinal<=4,"fixture_alpha","fixture_beta"), '
        'temperature_f=case(ordinal=1,32,ordinal=2,151,ordinal=3,150,ordinal=5,-10,ordinal=6,160,ordinal=7,20), '
        'wifi_rssi=-40-ordinal, _time=now()-ordinal*60 | fields _time device_name temperature_f wifi_rssi')
SCOPE = {'query':BASE,'language':'spl','earliest':'-24h','fieldDefinitions':{
    'temperature_f':{'unit':'°F'},'wifi_rssi':{'unit':'dBm'}}}
PROFILE = {'baseQuery':BASE,'scope':SCOPE,'fields':[{'name':'_time'},{'name':'device_name'},{'name':'temperature_f','numeric':True},{'name':'wifi_rssi','numeric':True}]}
SUMMARY = '| stats avg(temperature_f) AS avg_f avg(wifi_rssi) AS avg_rssi count(temperature_f) AS valid_t count(wifi_rssi) AS valid_wifi BY device_name'
REQUIREMENTS = 'temperature_f is recorded in Fahrenheit. wifi_rssi is recorded in dBm. Exclude readings over 150 F from every temperature calculation while retaining Wi-Fi measurements independently. Missing measurements are unknown, never zero.'


def blank():
    return {'title':'New dashboard','description':'','visualizations':{},'dataSources':{},'inputs':{},'defaults':{},'expressions':{},
            'layout':{'globalInputs':[],'tabs':{'items':[{'label':'Overview','layoutId':'layout_main'}]},
                      'layoutDefinitions':{'layout_main':{'type':'absolute','options':{'width':1200,'height':800},'structure':[]}}}}


def golden():
    actions=[{'op':'search','id':'summary_source','pipeline':SUMMARY},
             {'op':'chart','id':'summary','chartType':'splunk.table','title':'Readings by device','description':'Synthetic fixture',
              'sourceId':'summary_source','x':'','y':['device_name','avg_f','avg_rssi','valid_t','valid_wifi']},
             {'op':'page','layoutId':'layout_main','label':'Overview','purpose':'Summarize fixture readings','moveItems':False,
              'width':1200,'height':800,'items':[{'id':'summary','kind':'block','x':20,'y':20,'w':1160,'h':360}]}]
    # Use the real exclusion compiler, but verify output against independent
    # numeric fixture answers below; compiled syntax is not itself the oracle.
    profile=copy.deepcopy(PROFILE);profile['measurementConstraints']=[{'field':'temperature_f','maximum':150,'unit':'°F'}]
    from measurement_constraints import temperature_constraints
    profile['measurementConstraints']=temperature_constraints(REQUIREMENTS,{'purpose':'','requirements':REQUIREMENTS},profile)
    return apply_changes(blank(),compile_actions(blank(),actions,profile))


def cases():
    plans=[(1,'Show one device summary table with device_name, avg(temperature_f) AS avg_f, avg(wifi_rssi) AS avg_rssi, count(temperature_f) AS valid_t and count(wifi_rssi) AS valid_wifi.'),
           (2,'Show that device summary table plus an average temperature trend.'),
           (4,'Show that device summary table, an average temperature trend, a Wi-Fi RSSI trend and a single value for the valid temperature count.')]
    summary=plans[0][1]
    result=[]
    for count,goal in plans:
        result.append({'id':'create_'+str(count),'batch':count,'body':{'prompt':'Create a one-page synthetic fixture dashboard with exactly '+str(count)+' panels. '+(goal if count==1 else summary+' '+goal)+' '+REQUIREMENTS,
            'revision':0,'definition':blank(),'dataContext':copy.deepcopy(SCOPE),'history':[],'suggestionFormat':'cards'},'population':True})
    doc=golden()
    prompt='Make "Readings by device" open a focused detail page from a table row. Use an actual verified row field for a native token filter, apply that filter to the detail searches, and add return navigation. Keep the current data, time range and standing requirements; preserve the rest of the dashboard.'
    common={'revision':0,'definition':doc,'dataContext':copy.deepcopy(SCOPE),'selected':'summary','brief':{'purpose':'Investigate fixture readings','requirements':REQUIREMENTS},'history':[],'suggestionFormat':'cards'}
    result.extend([{'id':'row_detail','body':dict(common,prompt=prompt),'navigation':True},
                   {'id':'focused_format','body':dict(common,prompt='Format only this selected summary table: round avg_f and avg_rssi to one decimal and valid_t and valid_wifi to whole numbers. Preserve every column, source aggregation, other element and page.'),'population':True,'format':True}])
    return result


def score(records):
    """Correctness weights never compensate for a failed critical gate."""
    earned=possible=0;hard=True;completed=first=0
    for record in records:
        if not isinstance(record,dict) or record.get('case')not in ('create_1','create_2','create_4','row_detail','focused_format'):
            raise ValueError('Unknown benchmark case.')
        checks=record.get('checks',{})
        required={'completion','scope','bindings'}
        if record.get('case')in ('create_1','create_2','create_4','focused_format'):required.add('population')
        if record.get('case')=='row_detail':required.update(('navigation','preservation'))
        if record.get('case')=='focused_format':required.add('preservation')
        for key in required:
            value=checks.get(key)is True
            possible+=WEIGHTS[key];earned+=WEIGHTS[key] if value else 0
            if key in CRITICAL and not value: hard=False
        passed=all(checks.get(key)is True for key in required)
        completed+=passed
        first+=passed and record.get('modelCalls')==1
    batches={n:[r for r in records if r.get('case')=='create_'+str(n)]for n in (1,2,4)}
    largest=0
    for n in (1,2,4):
        if not batches[n] or not all(all(r.get('checks',{}).get(k)is True for k in ('completion','scope','population','bindings'))for r in batches[n]):break
        largest=n
    return {'weightedScore':round(100*earned/possible,1)if possible else 0,'criticalGatesPassed':bool(records)and hard,
            'completed':completed,'attempted':len(records),'firstResponsePasses':first,'candidateBatchPanels':largest,
            'suiteComplete':{'create_1','create_2','create_4','row_detail','focused_format'} <= {r['case']for r in records},
            'productionQualified':False,'strategy':'Keep IDs, scope, row filters, layout and return navigation deterministic; use the model for analytical choices. Treat candidateBatchPanels as a small-sample candidate, not an automatic routing permission.'}


def checked_query(call,doc,source_id,tokens=None):
    source=doc['dataSources'][source_id];query=source['options']['query']
    if source.get('type')!='ds.search' or not query.startswith(BASE+' '):raise ValueError('scope')
    resolved=resolve_query_tokens(query,doc,tokens);read_only_query(resolved,'spl')
    return call('preview',{'query':resolved,'language':'spl','earliest':'-24h'})


def grade(call,case,reply):
    old=case['body']['definition'];doc=apply_changes(old,reply['changes']);validate_document(doc)
    checks={'completion':bool(reply['changes']),'scope':all(v.get('type')=='ds.search' and v.get('options',{}).get('query','').startswith(BASE+' ') and v['options'].get('queryParameters')=={'earliest':'-24h','latest':'now'}for v in doc.get('dataSources',{}).values())}
    results={key:checked_query(call,doc,key)for key in doc.get('dataSources',{})}
    bindings=True
    for viz in doc['visualizations'].values():
        fields={f['name']for f in results[viz['dataSources']['primary']]['fields']}
        for channel in ('x','y','table','majorValue'):
            for args in re.findall(r'(?:seriesByName|frameBySeriesNames)\(([^)]*)\)',str(viz.get('options',{}).get(channel,''))):
                try:bindings &= set(json.loads('['+args+']')) <= fields
                except ValueError:bindings=False
    checks['bindings']=bindings
    if case.get('batch'):checks['completion'] &= len(doc['visualizations'])==case['batch'] and len(doc['layout']['tabs']['items'])==1
    if case.get('population'):
        candidates=[r for r in results.values()if {'device_name','avg_f','avg_rssi','valid_t','valid_wifi'} <= {f['name']for f in r['fields']}]
        expected={'fixture_alpha':(91,-42.5,2,4),'fixture_beta':(5,-46,2,3)}
        valid=False
        for result in candidates:
            rows={row['device_name']:row for row in result['results']}
            try:valid=rows.keys()==expected.keys() and all(all(math.isclose(float(rows[key][field]),value,abs_tol=.00001)for field,value in zip(('avg_f','avg_rssi','valid_t','valid_wifi'),values))for key,values in expected.items())
            except (KeyError,ValueError,TypeError):valid=False
            if valid:break
        checks['population']=valid
    if case.get('navigation'):
        try:row_navigation.validate_result(doc,old,'summary');checks.update(navigation=True,preservation=True)
        except ProviderError:checks.update(navigation=False,preservation=False)
        # Exercise concrete non-default filters as well as the native all-values
        # default; results stay local and reports retain only Boolean outcomes.
        table=doc['visualizations']['summary'];tokens=[t['token']for h in table.get('eventHandlers',[])if h['type']=='drilldown.setToken'for t in h['options']['tokens']if t.get('key')=='row.device_name.value']
        new_sources=set(doc['dataSources'])-set(old['dataSources'])
        for token in tokens:
            for entity in ('fixture_alpha','fixture_beta'):
                for source in new_sources:
                    result=checked_query(call,doc,source,{'default':{token:entity}})
                    checks['navigation'] &= bool(result['results']) and all(row.get('device_name',entity)==entity for row in result['results'])
        checks['navigation'] &= bool(tokens and new_sources)
    if case.get('format'):
        expected=copy.deepcopy(old);expected['dataSources']['summary_source']=doc['dataSources'].get('summary_source')
        checks['preservation']=expected==doc and doc['dataSources']['summary_source']['options']['query'].startswith(old['dataSources']['summary_source']['options']['query'])
    return checks


def run_suite(call,repetitions=1,case_ids=None):
    selected=[case for case in cases()if case_ids is None or case['id']in case_ids]
    metadata=call('settings');config={key:metadata.get(key)for key in ('provider','model','baseUrl','connection')}
    fingerprint=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    fixture_hash=hashlib.sha256(json.dumps(cases(),sort_keys=True).encode()).hexdigest();records=[]
    for repeat in range(repetitions):
        for case in selected:
            start=time.monotonic();record={'case':case['id'],'repeat':repeat+1};phase='author'
            try:
                reply=call('author',copy.deepcopy(case['body']))
                recovery=reply.get('recovery',{});record.update(modelCalls=recovery.get('modelCalls'),searchChecks=recovery.get('queryChecks'),authoringSeconds=recovery.get('seconds'))
                phase='grading';record['checks']=grade(call,case,reply)
            except Exception as error:
                record.update(checks={'completion':False},failure=type(error).__name__,failurePhase=phase)
                if isinstance(error,HTTPError):
                    try:
                        payload=json.load(error);recovery=payload.get('recovery',{});record.update(modelCalls=recovery.get('modelCalls'),searchChecks=recovery.get('queryChecks'),authoringSeconds=recovery.get('seconds'))
                    except Exception:pass
                    finally:error.close()
            record['totalSeconds']=round(time.monotonic()-start,2);records.append(record)
            print(json.dumps(record),flush=True)
    return {'suiteVersion':SUITE_VERSION,'fixtureSha256':fixture_hash,'graderSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'connectionFingerprint':fingerprint,'records':records,'assessment':score(records)}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise URLError('Redirect refused')


class InstalledClient:
    def __init__(self):
        origin=os.environ.get('SPLUNK_MANAGEMENT_URL','');parsed=urlsplit(origin)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
            raise ValueError('Set an HTTPS SPLUNK_MANAGEMENT_URL origin without credentials or a path.')
        key=os.environ.get('SPLUNK_SESSION_KEY','')
        if not key or any(c in key for c in '\r\n'):raise ValueError('Set the existing caller SPLUNK_SESSION_KEY securely in the environment.')
        self.origin=origin.rstrip('/');self.authorization='Splunk '+key
        self.opener=build_opener(NoRedirect,HTTPSHandler(context=ssl.create_default_context(cafile=os.environ.get('SPLUNK_CA_CERT_PATH')or None)))
    def wire(self,action,body=None):
        part='control/'if action=='run'else'v1/'
        req=Request(self.origin+'/servicesNS/-/constellation/constellation/'+part+action+'?output_mode=json',
                    data=json.dumps(body).encode()if body is not None else None,
                    headers={'Authorization':self.authorization,'Content-Type':'application/json','Accept':'application/json'})
        with self.opener.open(req,timeout=240)as response:return json.load(response)
    def __call__(self,action,body=None):
        if action!='author':return self.wire(action,body)
        handle=self.wire('run',{'action':'start'})['handle']
        try:
            try:reply=self.wire('author',dict(body,runHandle=handle))
            except (URLError,TimeoutError):
                cached=self.wire('run',{'action':'result','handle':handle})
                if not cached.get('available'):raise
                reply=cached['reply']
            self.wire('run',{'action':'ack','handle':handle});return reply
        finally:
            try:self.wire('run',{'action':'cancel','handle':handle})
            except Exception:pass


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true',help='Send the fixed synthetic suite through the selected provider; may incur charges.')
    parser.add_argument('--score',type=Path,help='Aggregate existing metadata-only benchmark records offline.')
    parser.add_argument('--output',type=Path,default=ROOT/'.local/benchmarks/assessment.json');parser.add_argument('--repetitions',type=int,choices=range(1,6),default=1)
    args=parser.parse_args()
    if args.live==bool(args.score):parser.error('Choose either --live or --score.')
    output=args.output.resolve()
    if not output.is_relative_to((ROOT/'.local').resolve()):parser.error('Keep raw benchmark reports inside ignored .local; publish only reviewed summaries.')
    output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    try:
        report=run_suite(InstalledClient(),args.repetitions)if args.live else {'assessment':score(json.loads(args.score.read_text())['records'])}
        fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w')as handle:json.dump(report,handle,indent=2)
        print(json.dumps(report['assessment']))
    except Exception as error:print(json.dumps({'failed':True,'category':type(error).__name__}));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
