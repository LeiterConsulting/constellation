"""Compile an exact selected-chart literal token request without inventing events.

Compound/dynamic requests retain model authoring. Every resulting change still
passes the ordinary native, search, compatibility and atomic acceptance checks.
"""
import copy
import json
import re
from native_intent import ALIASES
from studio_inventory import INVENTORY
from studio_features import supports_event


def exact_event_set(prompt, selected, document, attachments):
    if attachments:return None
    match=re.fullmatch(r'\s*For only the selected ([A-Za-z -]{1,80}),\s*add a native ([A-Za-z][A-Za-z0-9_.-]{0,80}) interaction that sets the token ([A-Za-z_][A-Za-z0-9_]{0,149}) to the literal string ("[^"\\\n]{0,200}"|[A-Za-z0-9_.-]{1,200})\.\s*(.*)',prompt,re.I|re.S)
    if not match:return None
    label,event,token,value,tail=match.groups();item=document.get('visualizations',{}).get(selected,{})
    kind=item.get('type');alias=ALIASES.get(kind)
    if label.lower()not in ('chart','visualization')and (not alias or not re.fullmatch(alias,label,re.I)):return None
    if not any(supports_event(pattern,event)for pattern in INVENTORY['visualizations'].get(kind,{}).get('events',[])):return None
    # Accept only this optional exact event-filter instruction and preservation
    # clauses. Negations, changes and exceptions retain the model path.
    tail=re.sub(r'^Use options\.events to constrain it to '+re.escape(event)+r'\.\s*','',tail,flags=re.I)
    clauses=[clause.strip()for clause in re.split(r'[.!?]',tail)if clause.strip()]
    if any(not re.match(r'(?:Preserve|Keep)\b',clause,re.I)for clause in clauses)or re.search(r'\b(?:add|create|remove|delete|replace|filter|rename|move|resize|convert|except|unless|but|also|instead|not|change)\b',tail,re.I):return None
    if value.startswith('"'):value=value[1:-1]
    if '$' in value or token in ('__proto__','constructor','prototype'):return None
    handlers=copy.deepcopy(item.get('eventHandlers',[]))
    if not isinstance(handlers,list):return None
    handler={'type':'drilldown.setToken','options':{'events':[event],'tokens':[{'token':token,'value':value}]}}
    if handler not in handlers:handlers.append(handler)
    return {'message':'Updated the selected chart’s '+event+' interaction.','suggestions':[],
        'changes':[]if handlers==item.get('eventHandlers',[])else[{'op':'set','path':'/visualizations/'+selected.replace('~','~0').replace('/','~1')+'/eventHandlers','value':json.dumps(handlers)}]}
