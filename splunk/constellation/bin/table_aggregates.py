"""Exact named numeric aggregate additions on an inspected ordinary table.

Ambiguous subjects, complex searches and mixed requests retain model authoring.
The returned native edits still pass the normal caller-scoped validation loop.
"""
import copy
import hashlib
import json
import re
from measurement_constraints import pipeline_commands, mask_command
from planning_sources import simple_stats
from search_scope import scoped_suffix

FUNCTIONS={'minimum':'min','maximum':'max','average':'avg','mean':'avg','sum':'sum'}


def exact_table_aggregates(prompt, selected, document, profile, receipt, attachments):
    if attachments or not profile or not receipt or receipt.get('status')=='failed' or profile.get('scope',{}).get('language','spl')!='spl':return None
    if not re.search(r'\b(?:for|to) only this selected table\b|\bchange no other element\b',prompt,re.I):return None
    if re.search(r'\b(?:rename|reorder|sort|format|round|colou?r|resize|move|remove|delete|retarget|navigate|link|limit)\b',prompt,re.I):return None
    op=r'(?:minimum|maximum|average|mean|sum)';field=r'[A-Za-z_][A-Za-z0-9_]*'
    match=re.search(r'\b(?:add|include)\s+('+op+r'(?:\s*(?:,|and)\s*'+op+r')*)\s+([A-Za-z_][A-Za-z0-9_ ]{0,80}?)\s+columns?\s+(?:named|called)\s+('+field+r'(?:\s*,\s*'+field+r')*(?:\s*,?\s+and\s+'+field+r')?)\s*(?=[.;\n]|$|\balongside\b|\bwhile\b|\bwithout\b)',prompt,re.I)
    if not match:return None
    prefix=prompt[:match.start()].strip(' ,.:;\n')
    if prefix and not re.fullmatch(r'(?:for|to) only this selected table',prefix,re.I):return None
    tail=prompt[match.end():].strip()
    tail=re.sub(r'^alongside (?:its|the) existing (?:summary )?columns\s*','',tail,flags=re.I)
    clauses=[part.strip()for part in re.split(r'[.;\n]',tail)if part.strip()]
    if any(not re.match(r'(?:Keep|Preserve|Exclude)\b',part,re.I)for part in clauses):return None
    if re.search(r'\b(?:add|include|create|convert|change|replace|also|instead|except)\b',tail,re.I):return None
    functions=[FUNCTIONS[word.lower()]for word in re.findall(op,match[1],re.I)]
    aliases=re.split(r'\s*,\s*(?:and\s+)?|\s+and\s+',match[3],flags=re.I)
    if not 1<=len(aliases)<=4 or len(aliases)!=len(functions)or len(set(aliases))!=len(aliases):return None
    table=document.get('visualizations',{}).get(selected,{})
    if table.get('type')!='splunk.table'or set(table.get('dataSources',{}))!={'primary'}:return None
    sid=table['dataSources']['primary'];source=document.get('dataSources',{}).get(sid,{})
    if source.get('type')!='ds.search'or receipt.get('table')!=selected or receipt.get('source')!=sid:return None
    query=source.get('options',{}).get('query','');suffix=scoped_suffix(query,profile)
    if suffix is None or any(re.search(r'\b'+re.escape(alias)+r'\b',query)for alias in aliases):return None
    if any(mask_command(rule)not in query for rule in profile.get('measurementConstraints',[])):return None
    normalized='| '+query.strip().lstrip('| ').strip();commands=pipeline_commands(normalized)
    stats=[(i,start,end,command)for i,(start,end,command)in enumerate(commands)if re.match(r'(?i)stats\b',command)]
    if len(stats)!=1:return None
    index,start,end,command=stats[0];parsed=simple_stats('| '+command)
    if not parsed:return None
    known={f['name']for f in profile.get('fields',[])if f.get('numeric')is True}
    used={m['field']for m in parsed['metrics']if m['field']in known}
    subject=match[2].strip().lower();words=set(re.findall(r'[a-z0-9]+',subject))-{'the','of','field','values','value','readings','reading','stored','recorded'}
    candidates=[name for name in used if name.lower()==subject]
    if not candidates:candidates=[name for name in used if words and words<=set(re.findall(r'[a-z0-9]+',name.lower()))]
    if len(candidates)!=1:return None
    input_field=candidates[0]
    # Preserve post-aggregation calculations/order and extend only a literal
    # terminal projection. Other frame-changing commands need general editing.
    projections=[]
    for j,(a,b,c)in enumerate(commands[index+1:],index+1):
        if re.match(r'(?i)(?:eval|sort|head)\b',c):continue
        if j==len(commands)-1 and re.fullmatch(r'(?i)(?:fields|table)\s+'+field+r'(?:\s+'+field+r')*',c):projections.append((a,b,c));continue
        return None
    extra=' '.join(fn+'('+input_field+') AS '+alias for fn,alias in zip(functions,aliases))
    group=re.search(r'(?i)\bBY\s+[A-Za-z_][A-Za-z0-9_]*\s*$',command)
    replacement=command[:group.start()].rstrip()+' '+extra+' '+command[group.start():]if group else command+' '+extra
    edits=[(start,end,normalized[start:end].replace(command,replacement,1))]
    for a,b,c in projections:edits.append((a,b,normalized[a:b].replace(c,c+' '+' '.join(aliases),1)))
    for a,b,text in sorted(edits,reverse=True):normalized=normalized[:a]+text+normalized[b:]
    updated=copy.deepcopy(source);updated['options']['query']=normalized if query.lstrip().startswith('|')else normalized[2:]
    shared=(any(key!=selected and sid in item.get('dataSources',{}).values()for key,item in document.get('visualizations',{}).items())
            or any(sid in item.get('dataSources',{}).values()for item in document.get('inputs',{}).values())
            or any(item.get('options',{}).get('extend',item.get('extend'))==sid for item in document.get('dataSources',{}).values()))
    escape=lambda value:value.replace('~','~0').replace('/','~1');target=sid;changes=[]
    if shared:
        base='table_calc_'+hashlib.sha256((selected+sid+updated['options']['query']).encode()).hexdigest()[:20];target=base;n=2
        while target in document['dataSources']:target=base+'_'+str(n);n+=1
        changes.append({'op':'set','path':'/visualizations/'+escape(selected)+'/dataSources/primary','value':json.dumps(target)})
    changes.insert(0,{'op':'set','path':'/dataSources/'+escape(target),'value':json.dumps(updated)})
    return {'message':'Added '+', '.join(aliases)+' using the selected table’s existing '+input_field+' data.','changes':changes,'suggestions':[]}
