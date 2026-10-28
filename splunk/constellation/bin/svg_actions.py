"""Bind an existing SVG asset without model-authored nested JSON encoding."""
import copy
import json
import re
from provider_service import ProviderError

ACTION = {'type':'object','properties':{
    'op':{'type':'string','enum':['bindSvg']},
    'id':{'type':'string','description':'Exact existing SVG visualization ID.'},
    'sourceId':{'type':'string'},
    'areaField':{'type':'string','description':'Exact output field matching the supplied path IDs.'},
    'valueField':{'type':'string','description':'Exact numeric output field.'},
    'title':{'type':'string','maxLength':200,'description':'Requested title; empty preserves the existing title.'},
    'selectionToken':{'type':'string','maxLength':149,'description':'Explicit area.click token; empty preserves existing handlers.'}},
    'required':['op','id','sourceId','areaField','valueField','title','selectionToken'],'additionalProperties':False}


def compile_binding(action, document):
    if set(action) != set(ACTION['required']): raise ProviderError('Use the complete bindSvg action.')
    for key in ('id','sourceId','areaField','valueField'):
        if not isinstance(action[key],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,199}',action[key]):
            raise ProviderError('Use exact simple IDs and output fields for bindSvg; advanced bindings retain native edits.')
    token, title = action['selectionToken'], action['title']
    if not isinstance(title,str) or len(title)>200 or not isinstance(token,str) or token and not re.fullmatch(r'[A-Za-z_]\w{0,148}',token):
        raise ProviderError('Use a concise SVG title and plain selection token.')
    item=copy.deepcopy(document.get('visualizations',{}).get(action['id'],{}))
    if item.get('type')!='splunk.choropleth.svg' or not item.get('options',{}).get('svg'):
        raise ProviderError('bindSvg requires an existing SVG map and its exact asset reference.')
    options=item['options'];item.setdefault('dataSources',{})['primary']=action['sourceId']
    for channel,field in (('areaIds','areaField'),('areaValues','valueField')):
        options[channel]='> primary | seriesByName('+json.dumps(action[field])+')'
    if 'areaColors' not in options:
        context=item.setdefault('context',{});name='constellationAreaGradient'
        while name in context: name+='_'  # Never overwrite an imported context entry.
        context[name]={'colors':['#B5C7E3','#355C9C']};options['areaColors']='> areaValues | gradient('+name+')'
    if title: item['title']=title
    if token:
        found=False
        for handler in item.get('eventHandlers',[]):
            if handler.get('type')!='drilldown.setToken' or 'area.click' not in handler.get('options',{}).get('events',[]):continue
            for target in handler['options'].get('tokens',[]):
                if target.get('token')==token:
                    target.pop('value',None);target['key']='name';found=True
        if not found:item.setdefault('eventHandlers',[]).append({'type':'drilldown.setToken','options':{'events':['area.click'],'tokens':[{'token':token,'key':'name'}]}})
    return {'op':'set','path':'/visualizations/'+action['id'],'value':json.dumps(item)}
