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
GRADER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sys.path.insert(0, str(ROOT / 'splunk/constellation/bin'))
from authoring_actions import compile_actions
from provider_service import ProviderError
from studio_contract import apply_changes, validate_document
from token_service import resolve_query_tokens
from search_service import read_only_query
import row_navigation

SUITE_VERSION = '2'
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


def navigation_fixture(large=False):
    """Authored existing work, including a shared source and an existing route."""
    doc=golden();actions=[]
    for name in ('details','coverage'):
        for suffix,pipeline,kind,y in (
            ('table',SUMMARY,'splunk.table',['device_name','avg_f','avg_rssi','valid_t','valid_wifi']),
            ('count','| stats count AS source_rows','splunk.singlevalue',['source_rows'])):
            key=name+'_'+suffix;sid='summary_source'if name=='coverage'and suffix=='table'else key+'_source'
            if sid!='summary_source':actions.append({'op':'search','id':sid,'pipeline':pipeline})
            actions.append({'op':'chart','id':key,'chartType':kind,'title':name.title()+' '+suffix,'description':'Authored synthetic fixture','sourceId':sid,'x':'','y':y})
        actions.append({'op':'page','layoutId':name,'label':name.title(),'purpose':'Inspect device observations'if name=='details'else'Check measurement coverage','moveItems':False,
                        'width':1200,'height':1000,'items':[{'id':name+'_table','kind':'block','x':20,'y':20,'w':1160,'h':360},
                                                                        {'id':name+'_count','kind':'block','x':20,'y':400,'w':570,'h':360}]})
    actions.append({'op':'route','sourceId':'summary','pageId':'details','field':'device_name','returnLabel':'Back to Overview'})
    profile=copy.deepcopy(PROFILE)
    from measurement_constraints import temperature_constraints
    profile['measurementConstraints']=temperature_constraints(REQUIREMENTS,{'requirements':REQUIREMENTS},profile)
    doc=apply_changes(doc,compile_actions(doc,actions,profile))
    doc['visualizations']['summary']['futureFixture']={'preserve':'synthetic unknown property'}
    if large:
        page_ids=['layout_main','details','coverage','context']
        doc['layout']['tabs']['items'].append({'label':'Additional context','layoutId':'context'})
        doc['layout']['layoutDefinitions']['context']={'type':'absolute','options':{'width':1200,'height':3600},'structure':[]}
        for number in range(27):
            key='context_'+str(number);pid=page_ids[number%4]
            chart=copy.deepcopy(doc['visualizations']['summary']);chart.pop('eventHandlers',None);chart['title']='Authored context '+str(number)
            doc['visualizations'][key]=chart
            page=doc['layout']['layoutDefinitions'][pid]
            bottom=max((item['position']['y']+item['position']['h']for item in page['structure']),default=0)+20
            page['structure'].append({'item':key,'type':'block','position':{'x':20,'y':bottom,'w':1160,'h':360}})
            page['options']['height']=bottom+380
    validate_document(doc)
    return doc


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
    result.append({'id':'create_8','batch':8,'pageLabels':['Overview','Device details','Network summary','Network details'],'navigation':True,'population':True,
        'body':{'prompt':'Build exactly four pages with exactly eight charts for this synthetic fixture. Page names and purposes: Overview summarizes temperature and devices; Device details investigates one selected device; Network summary summarizes Wi-Fi and devices; Network details investigates selected-device Wi-Fi. '
            'Overview: '+summary+' Add an average temperature trend. Device details: an average temperature trend and a single value for valid temperature count. '
            'Network summary: '+summary+' Add an average Wi-Fi RSSI trend. Network details: an average Wi-Fi RSSI trend and a single value for valid Wi-Fi count. '
            'The device_name row of the Overview table must open Device details and filter BOTH its charts. The device_name row of the Network summary table must open Network details and filter BOTH its charts. Add a Back button on EACH detail page to its own source page. '+REQUIREMENTS,
            'revision':0,'definition':blank(),'dataContext':copy.deepcopy(SCOPE),'history':[],'suggestionFormat':'cards'}})
    for large in (False,True):
        existing=navigation_fixture(large)
        common={'revision':0,'definition':existing,'dataContext':copy.deepcopy(SCOPE),'selected':'summary','brief':{'purpose':'Investigate fixture readings','requirements':REQUIREMENTS},'history':[],'suggestionFormat':'cards'}
        result.append({'id':'large_route'if large else'existing_route','navigation':True,'preserveRoute':True,'target':'coverage','origin':'layout_main',
            'body':dict(common,prompt='Retarget only this table\'s existing device_name row drilldown to open Coverage instead of Details. Filter every existing Coverage chart to that row device before aggregation and add a Back to Overview button there. Preserve the source table query, columns and unknown properties; preserve the entire Details page, its filters and return button, and all other charts, sources, page names, positions and standing requirements. Do not add pages or charts. Use a native all-device token default.')})
        if large:
            result.append({'id':'large_format','population':True,'format':True,'body':dict(common,selected='details_table',prompt='Format only this selected summary table: round avg_f and avg_rssi to one decimal and valid_t and valid_wifi to whole numbers. Preserve every column, source aggregation, other element, existing route and page.')})
            result.append({'id':'focused_metric','population':True,'metric':True,'body':dict(common,selected='details_table',prompt='Add max(temperature_f) AS peak_f to only this selected summary table. Preserve its existing columns, the 150 F cutoff, independent Wi-Fi measurements, all other elements and navigation. Change no other element.')})
            result.append({'id':'large_page','page':'coverage','purpose':'Explain valid temperature and Wi-Fi sample counts.','body':dict(common,selected='page:coverage',prompt='Rename only this selected page from Coverage to Data quality. Set its purpose to exactly "Explain valid temperature and Wi-Fi sample counts." Preserve its ID, charts, searches, positions, unknown properties and all incoming/outgoing navigation.')})
    existing=navigation_fixture();back=next(k for k in existing['inputs']if any(h.get('options',{}).get('tabId')=='layout_main'for h in existing['inputs'][k].get('eventHandlers',[])))
    result.append({'id':'existing_button','button':back,'navigation':True,'body':{
        'prompt':'Change only this selected Back button: rename it "Open Coverage" and make it open Coverage instead of Overview. Keep its ID, position and size, existing device filter, all other interactions, searches, charts and pages. Do not add a button.',
        'revision':0,'definition':existing,'dataContext':copy.deepcopy(SCOPE),'selected':back,'history':[],'suggestionFormat':'cards'}})
    return result


def required_checks(case):
    required={'completion','scope','bindings'}
    if case.get('population'):required.add('population')
    if case.get('navigation'):required.add('navigation')
    if case.get('navigation')and not case.get('batch')or case.get('format')or case.get('page')or case.get('metric'):required.add('preservation')
    return required


def score(records):
    """Correctness weights never compensate for a failed critical gate."""
    earned=possible=0;hard=True;completed=first=0
    definitions={case['id']:case for case in cases()}
    for record in records:
        if not isinstance(record,dict) or record.get('case')not in definitions:
            raise ValueError('Unknown benchmark case.')
        checks=record.get('checks',{})
        required=required_checks(definitions[record['case']])
        for key in required:
            value=checks.get(key)is True
            possible+=WEIGHTS[key];earned+=WEIGHTS[key] if value else 0
            if key in CRITICAL and not value: hard=False
        passed=all(checks.get(key)is True for key in required)
        completed+=passed
        first+=passed and record.get('modelCalls')==1
    batches={n:[r for r in records if r.get('case')=='create_'+str(n)]for n in (1,2,4,8)}
    largest=0
    for n in (1,2,4,8):
        if not batches[n] or not all(all(r.get('checks',{}).get(k)is True for k in required_checks(definitions['create_'+str(n)]))for r in batches[n]):break
        largest=n
    return {'weightedScore':round(100*earned/possible,1)if possible else 0,'criticalGatesPassed':bool(records)and hard,
            'completed':completed,'attempted':len(records),'firstResponsePasses':first,'candidateBatchPanels':largest,
            'suiteComplete':set(definitions) <= {r['case']for r in records},
            'productionQualified':False,'strategy':'Keep IDs, scope, row filters, layout and return navigation deterministic; use the model for analytical choices. Treat candidateBatchPanels as a small-sample candidate, not an automatic routing permission.'}


def checked_query(call,doc,source_id,tokens=None):
    source=doc['dataSources'][source_id];query=source['options']['query']
    if source.get('type')!='ds.search' or not query.startswith(BASE+' '):raise ValueError('scope')
    resolved=resolve_query_tokens(query,doc,tokens);read_only_query(resolved,'spl')
    return call('preview',{'query':resolved,'language':'spl','earliest':'-24h'})


def row_routes(doc):
    pages=doc['layout']['layoutDefinitions']
    for key,table in doc['visualizations'].items():
        if table.get('type')!='splunk.table':continue
        handlers=table.get('eventHandlers',[])
        origins=[pid for pid,page in pages.items()if any(item.get('item')==key for item in page.get('structure',[]))]
        for h in handlers:
            if h.get('type')!='drilldown.switchToTab':continue
            fields=h.get('options',{}).get('fields',[])
            for setter in handlers:
                if setter.get('type')!='drilldown.setToken'or setter.get('options',{}).get('fields',[])!=fields:continue
                for field in fields:
                    for token in setter.get('options',{}).get('tokens',[]):
                        if token.get('key')=='row.'+field+'.value':yield key,field,token.get('token'),h['options'].get('tabId'),origins


def navigation_checks(call,case,doc):
    """Independent exact native checks plus concrete pre-aggregate population probes."""
    from measurement_constraints import pipeline_commands
    old=case['body']['definition'];pages=doc['layout']['layoutDefinitions'];routes=list(row_routes(doc))
    if case.get('preserveRoute'):routes=[r for r in routes if r[0]=='summary'and r[3]==case['target']]
    elif case['id']=='row_detail':routes=[r for r in routes if r[0]=='summary'and r[3]not in old['layout']['layoutDefinitions']]
    else:
        labels={t['layoutId']:t['label']for t in doc['layout']['tabs']['items']}
        expected={('Overview','Device details'),('Network summary','Network details')}
        actual={(labels.get(origins[0]),labels.get(target))for _key,_field,_token,target,origins in routes if len(origins)==1}
        if actual!=expected:return False
    if not routes:return False
    probed=set()
    for _key,field,token,target,origins in routes:
        if field!='device_name'or len(origins)!=1 or target==origins[0]or doc.get('defaults',{}).get('tokens',{}).get('default',{}).get(token,{}).get('value')!='*':return False
        items={entry['item']for entry in pages.get(target,{}).get('structure',[])}
        charts=[v for key,v in doc['visualizations'].items()if key in items and v.get('dataSources')]
        if not charts or not any(key in items and item.get('type')=='input.button'and any(h.get('type')=='drilldown.switchToTab'and h.get('options',{}).get('tabId')==origins[0]for h in item.get('eventHandlers',[]))for key,item in doc.get('inputs',{}).items()):return False
        for chart in charts:
            source=doc['dataSources'][chart['dataSources']['primary']];query=source['options']['query'];suffix=query[len(BASE):];commands=[];end=len(suffix)
            for start,_stop,command in pipeline_commands(suffix):
                if re.match(r'(?:stats|timechart|chart|eventstats|streamstats|table|fields|rename)\b',command,re.I):end=start;break
                commands.append(command)
            if 'search device_name=$'+str(token)+'|s$'not in commands:return False
            prefix=BASE+suffix[:end]
            for entity in ('*','fixture_alpha','fixture_beta'):
                probe=resolve_query_tokens(prefix+' | stats count AS probe_rows count(temperature_f) AS probe_t count(wifi_rssi) AS probe_wifi BY device_name',doc,{'default':{token:entity}})
                if probe in probed:continue
                probed.add(probe);read_only_query(probe,'spl');result=call('preview',{'query':probe,'language':'spl','earliest':'-24h'})
                expected={'fixture_alpha':(4,2,4),'fixture_beta':(3,2,3)}
                if entity!='*':expected={entity:expected[entity]}
                rows={row['device_name']:row for row in result['results']}
                # A temperature-only source may legitimately remove excluded
                # readings. Independent Wi-Fi populations are mandatory only
                # for sources that actually calculate a Wi-Fi metric. Both
                # valid temperature samples must survive every fixture probe.
                uses_wifi=bool(re.search(r'\bwifi_rssi\b',suffix[end:]))
                uses_temperature=bool(re.search(r'\btemperature_f\b',suffix[end:]))
                try:
                    if rows.keys()!=expected.keys():return False
                    for key,(total,valid_t,valid_wifi)in expected.items():
                        row=rows[key]
                        if uses_temperature and float(row['probe_t'])!=valid_t:return False
                        if not 1<=float(row['probe_rows'])<=total:return False
                        if not uses_temperature and float(row['probe_rows'])!=total:return False
                        if uses_wifi and (float(row['probe_rows'])!=total or float(row['probe_wifi'])!=valid_wifi):return False
                except (KeyError,ValueError,TypeError):return False
    return True


def preserved_route(old,doc,target):
    """Only route wiring, destination source filters/bindings and Back may change."""
    items={e['item']for e in old['layout']['layoutDefinitions'][target]['structure']}
    if set(old['visualizations'])!=set(doc['visualizations'])or old['layout']['tabs']!=doc['layout']['tabs']:return False
    for key,before in old['visualizations'].items():
        after=copy.deepcopy(doc['visualizations'][key]);expected=copy.deepcopy(before)
        if key=='summary':after.pop('eventHandlers',None);expected.pop('eventHandlers',None)
        if key in items:after['dataSources']=expected.get('dataSources',{})
        if after!=expected:return False
    for key in set(old)|set(doc):
        if key not in ('visualizations','dataSources','inputs','layout','defaults')and old.get(key)!=doc.get(key):return False
    for key,value in old.get('defaults',{}).items():
        if doc.get('defaults',{}).get(key)!=value:return False
    if old.get('defaults',{})!=doc.get('defaults',{}):return False
    if any(doc.get('inputs',{}).get(k)!=v for k,v in old.get('inputs',{}).items()):return False
    for pid,page in old['layout']['layoutDefinitions'].items():
        after=doc['layout']['layoutDefinitions'].get(pid,{})
        if pid!=target:
            if page!=after:return False
        else:
            positions={e['item']:e for e in after.get('structure',[])}
            if any(positions.get(e['item'])!=e for e in page['structure']):return False
            expected=copy.deepcopy(page);expected['structure']=after.get('structure');expected['options']['height']=after.get('options',{}).get('height')
            if expected!=after:return False
    from measurement_constraints import pipeline_commands
    def without_route(query):
        suffix=query[len(BASE):]
        spans=[(start,end)for start,end,command in pipeline_commands(suffix)if re.fullmatch(r'search device_name=\$[A-Za-z_][A-Za-z0-9_]*\|s\$',command)]
        for start,end in reversed(spans):suffix=suffix[:start]+suffix[end:]
        return ' '.join(command for _start,_end,command in pipeline_commands(suffix))
    for key,before in old['dataSources'].items():
        consumers={k for k,v in old['visualizations'].items()if key in v.get('dataSources',{}).values()}
        if consumers-items:
            if doc['dataSources'].get(key)!=before:return False
    for key in items & set(old['visualizations']):
        before=old['dataSources'][old['visualizations'][key]['dataSources']['primary']]
        after=copy.deepcopy(doc['dataSources'][doc['visualizations'][key]['dataSources']['primary']])
        query=after['options']['query'];after['options']['query']=before['options']['query']
        if before!=after or without_route(query)!=without_route(before['options']['query']):return False
    return True


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
    if case.get('batch'):
        labels=[tab['label']for tab in doc['layout']['tabs']['items']]
        checks['completion'] &= len(doc['visualizations'])==case['batch'] and (labels==case['pageLabels']if case.get('pageLabels')else len(labels)==1)
        if case.get('pageLabels'):
            per_page=[sum(entry.get('item')in doc['visualizations']for entry in doc['layout']['layoutDefinitions'][tab['layoutId']]['structure'])for tab in doc['layout']['tabs']['items']]
            checks['completion'] &= per_page==[2,2,2,2]
    if case.get('population'):
        candidates=[r for r in results.values()if {'device_name','avg_f','avg_rssi','valid_t','valid_wifi'} <= {f['name']for f in r['fields']}]
        expected={'fixture_alpha':(91,-42.5,2,4),'fixture_beta':(5,-46,2,3)}
        valid=bool(candidates)
        for result in candidates:
            rows={row['device_name']:row for row in result['results']}
            try:valid &= rows.keys()==expected.keys() and all(all(math.isclose(float(rows[key][field]),value,abs_tol=.00001)for field,value in zip(('avg_f','avg_rssi','valid_t','valid_wifi'),values))for key,values in expected.items())
            except (KeyError,ValueError,TypeError):valid=False
        checks['population']=valid
    if case.get('navigation')and not case.get('button'):
        checks['navigation']=navigation_checks(call,case,doc)
        if case['id']=='row_detail':
            try:row_navigation.validate_result(doc,old,'summary');checks['preservation']=True
            except ProviderError:checks['preservation']=False
        if case.get('preserveRoute'):checks['preservation']=preserved_route(old,doc,case['target'])
    if case.get('button'):
        key=case['button'];item=doc.get('inputs',{}).get(key,{})
        checks['navigation']=item.get('options',{}).get('label')=='Open Coverage'and {h.get('options',{}).get('tabId')for h in item.get('eventHandlers',[])if h.get('type')=='drilldown.switchToTab'}=={'coverage'}
        expected=copy.deepcopy(old);expected['inputs'][key]['options']['label']=item.get('options',{}).get('label');expected['inputs'][key]['eventHandlers']=item.get('eventHandlers')
        checks['preservation']=expected==doc
    if case.get('page'):
        pid=case['page'];before_tabs=old['layout']['tabs']['items'];after_tabs=doc['layout']['tabs']['items']
        matches=[i for i,tab in enumerate(before_tabs)if tab['layoutId']==pid]
        expected=copy.deepcopy(old)
        if len(matches)!=1:checks.update(completion=False,preservation=False)
        else:
            expected['layout']['tabs']['items'][matches[0]]['label']='Data quality'
            checks['completion'] &= after_tabs==expected['layout']['tabs']['items']and reply.get('pagePurposes',{}).get(pid)==case['purpose']
            checks['preservation']=expected==doc
    if case.get('format'):
        sid=old['visualizations'][case['body']['selected']]['dataSources']['primary']
        expected=copy.deepcopy(old);expected['dataSources'][sid]=doc['dataSources'].get(sid)
        checks['preservation']=expected==doc and doc['dataSources'][sid]['options']['query'].startswith(old['dataSources'][sid]['options']['query'])
    if case.get('metric'):
        selected=case['body']['selected'];sid=old['visualizations'][selected]['dataSources']['primary'];result=results.get(sid,{})
        rows={row['device_name']:row for row in result.get('results',[])}
        try:checks['completion'] &= rows.keys()=={'fixture_alpha','fixture_beta'}and float(rows['fixture_alpha']['peak_f'])==150 and float(rows['fixture_beta']['peak_f'])==20 and 'peak_f'in doc['visualizations'][selected]['options'].get('table','')
        except (KeyError,ValueError,TypeError):checks['completion']=False
        expected=copy.deepcopy(old);expected['dataSources'][sid]=doc['dataSources'].get(sid)
        expected['visualizations'][selected]['options']['table']=doc['visualizations'][selected]['options'].get('table')
        checks['preservation']=expected==doc
    return checks


def run_suite(call,repetitions=1,case_ids=None):
    selected=[case for case in cases()if case_ids is None or case['id']in case_ids]
    metadata=call('settings');config={key:metadata.get(key)for key in ('provider','model','baseUrl','connection')}
    fingerprint=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    fixture_hash=hashlib.sha256(json.dumps(cases(),sort_keys=True).encode()).hexdigest();records=[]
    for repeat in range(repetitions):
        for case in selected:
            start=time.monotonic();record={'case':case['id'],'repeat':repeat+1,
                'inputCharts':len(case['body']['definition']['visualizations']),'inputPages':len(case['body']['definition']['layout']['tabs']['items']),
                'inputDefinitionBytes':len(json.dumps(case['body']['definition'],separators=(',',':')).encode())};phase='author'
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
    return {'suiteVersion':SUITE_VERSION,'fixtureSha256':fixture_hash,'graderSha256':GRADER_SHA256,
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
