"""Evidence-scoped typed tools for the app's existing-table detail suggestion."""
import json
from provider_service import ProviderError

OPS = {'search','chart','page','link','button','filter','token'}
INSTRUCTIONS = '''Create the requested detail page using typed actions only. Preserve
the existing table's source, query, columns and placement and every other existing
element. Do not use set/remove or rebuild the source table.
Use search {op,id,pipeline}: pipeline starts with | and appends to dataProfile.baseQuery;
never repeat the base. Use verified source fields and short output aliases.
Use chart {op,id,chartType,title,description,sourceId,x,y}: sourceId is the new search ID;
table x:"",y:[outputColumns]; singlevalue x:"",y:[oneNumericAlias]; axis charts use a
nonempty output x and numeric y fields. Use timechart bins=100 WITHOUT BY for a
filtered detail trend; stats may use BY for tables. Preserve recorded units and
dashboardBrief exclusions; keep independent measurements and unknowns separate.
Use page {op,layoutId,label,purpose,moveItems:false,width:1200,height,items:[
{id,kind:"block",x,y,w,h}]} with NEW IDs and readable nonoverlapping rectangles.
Each items[].id must exactly match a new chart.id, not a wrapper or placeholder.
Leave empty space for Back; its button action places it, so add no placeholder item.
Pick a verified row field from focusedSourceReceipt. Use token {op,name,value:"*"}
and filter {op,sourceId,field,token} on EVERY new detail source. The compiler inserts
safe wildcard filtering before aggregation; do not write token predicates yourself.
Use link {op,sourceId,pageId,targetId:"",field,token}: sourceId is focus.id (the existing
TABLE), pageId is the NEW destination layout ID, field is an actual output column.
Use button {op,id,label,pageId,targetPageId,targetId:"",x,y,w,h:80} on the new page
with targetPageId equal to the existing table's page. Reserve clear space for it.
Return JSON message,changes,suggestions. Give a short completed-result message and
at most one useful next step. Metadata is not event values; do not claim analysis
of unseen rows. On recovery, preserve working staged changes and repair the same
goal using the provided candidate and exact feedback. All validation still applies.'''


def eligible(prompt, document, selected, profile, receipt, attachments):
    table = document.get('visualizations', {}).get(selected, {})
    title = table.get('title')
    if attachments or not profile or not receipt or profile['scope'].get('language','spl') != 'spl' or table.get('type') != 'splunk.table' or not isinstance(title,str): return False
    if any(handler.get('type') in ('drilldown.switchToTab','drilldown.setToken') for handler in table.get('eventHandlers',[])): return False
    source_fields={field['name'] for field in profile.get('fields',[])}
    if receipt.get('status')=='failed' or not any(field.get('name') in source_fields and not field.get('numeric') for field in receipt.get('fields',[])): return False
    pages = [page for page in document.get('layout',{}).get('layoutDefinitions',{}).values() if any(item.get('item')==selected for item in page.get('structure',[]))]
    expected = 'Make ' + json.dumps(title,ensure_ascii=False) + ' open a focused detail page from a table row. Use an actual verified row field for a native token filter, apply that filter to the detail searches, and add return navigation. Keep the current data, time range and standing requirements; preserve the rest of the dashboard.'
    return len(pages)==1 and prompt==expected


def validate_actions(actions, original, selected):
    existing=set(original.get('visualizations',{}))|set(original.get('inputs',{}))
    sources=original.get('dataSources',{});pages=original.get('layout',{}).get('layoutDefinitions',{})
    tokens=original.get('defaults',{}).get('tokens',{}).get('default',{})
    for action in actions:
        op=action.get('op') if isinstance(action,dict) else None
        if op not in OPS: raise ProviderError('This detail-page turn uses typed search/chart/page/filter/token/link/button actions only. Preserve the existing table binding; do not return native set/remove edits.',422,'row_navigation_actions')
        conflict = ('search.id' if op=='search' and action.get('id') in sources else
                    op+'.id' if op in ('chart','button') and action.get('id') in existing else
                    'page.layoutId' if op=='page' and action.get('layoutId') in pages else
                    'filter.sourceId' if op=='filter' and action.get('sourceId') in sources else
                    'token.name' if op=='token' and action.get('name') in tokens else
                    'link.sourceId' if op=='link' and action.get('sourceId')!=selected else
                    'link.pageId' if op=='link' and action.get('pageId') in pages else
                    'button.pageId' if op=='button' and action.get('pageId') in pages else None)
        if conflict:
            guidance = ('link.sourceId must be the selected table '+json.dumps(selected)+'.' if conflict=='link.sourceId' else
                        'button.pageId places Back on the NEW detail page; button.targetPageId is the existing original page.' if conflict=='button.pageId' else
                        conflict+' must refer to new detail work, preserving existing IDs and content.')
            raise ProviderError(guidance+' Keep separate detail searches/charts/page, link the selected table and add return navigation.',422,'row_navigation_focus')


def validate_result(candidate, original, selected):
    old_pages=original.get('layout',{}).get('layoutDefinitions',{})
    pages=candidate.get('layout',{}).get('layoutDefinitions',{})
    origin=next(key for key,page in old_pages.items()if any(item.get('item')==selected for item in page.get('structure',[])))
    table=candidate.get('visualizations',{}).get(selected,{})
    handlers=table.get('eventHandlers',[])
    targets={handler.get('options',{}).get('tabId')for handler in handlers if handler.get('type')=='drilldown.switchToTab'}-set(old_pages)
    tokens={entry.get('token')for handler in handlers if handler.get('type')=='drilldown.setToken'for entry in handler.get('options',{}).get('tokens',[])}
    if not targets or not tokens: raise ProviderError('Create the new detail page and link the selected table row with a verified field/token; a message alone does not complete this request.',422,'row_navigation_missing')
    for target in targets:
        items={entry.get('item')for entry in pages.get(target,{}).get('structure',[])}
        charts=[chart for key,chart in candidate.get('visualizations',{}).items()if key in items]
        filtered=charts and all(any('$'+str(token)+'|s$' in candidate.get('dataSources',{}).get(chart.get('dataSources',{}).get('primary'),{}).get('options',{}).get('query','') for token in tokens) for chart in charts)
        returned=any(key in items and item.get('type')=='input.button' and any(handler.get('type')=='drilldown.switchToTab' and handler.get('options',{}).get('tabId')==origin for handler in item.get('eventHandlers',[]))for key,item in candidate.get('inputs',{}).items())
        if not filtered or not returned: raise ProviderError('Filter every new detail source with the row token and place a return button targeting the original table page.',422,'row_navigation_missing')
    for key,value in original.get('dataSources',{}).items():
        if candidate.get('dataSources',{}).get(key)!=value: raise ProviderError('Preserve every existing source while adding detail searches.',422,'row_navigation_focus')
    for key,value in original.get('visualizations',{}).items():
        after=candidate.get('visualizations',{}).get(key,{})
        if key==selected:
            value={k:v for k,v in value.items()if k!='eventHandlers'};after={k:v for k,v in after.items()if k!='eventHandlers'}
        if after!=value: raise ProviderError('Preserve the existing charts/table projection and add only the selected table navigation.',422,'row_navigation_focus')
    if any(pages.get(key)!=value for key,value in old_pages.items()): raise ProviderError('Preserve existing page geometry while adding the detail page.',422,'row_navigation_focus')
