"""Fresh native row navigation keeps the origin independent without extra prose."""
import copy,json,unittest
from test_creation_recipes import PROFILE
from creation_page_scope import normalize_creation_page_scope
from studio_contract import apply_changes
from provider_service import ProviderError

def fixture(filtered=True):
    base=PROFILE['baseQuery'];predicate=' | search device_name=$selected_device|s$'if filtered else''
    chart=lambda kind,sid,options:{'type':kind,'dataSources':{'primary':sid},'options':options}
    doc={'title':'Observed readings','description':'','inputs':{},'defaults':{'tokens':{'default':{'selected_device':{'value':'*','future':True}}}},'future':{'keep':True},
         'dataSources':{'summary':{'type':'ds.search','options':{'query':base+' | stats avg(duration) AS mean BY device_name'}},
                        'trend':{'type':'ds.search','future':{'keep':True},'options':{'query':base+predicate+' | timechart bins=100 avg(duration) AS mean','queryParameters':{'earliest':'-24h','latest':'now'}}},
                        'raw':{'type':'ds.search','options':{'query':base+predicate+' | table _time device_name duration'}}},
         'visualizations':{'summary':chart('splunk.table','summary',{'table':'> primary | frameBySeriesNames("device_name", "mean")'}),
                           'overview_trend':chart('splunk.line','trend',{'x':'> primary | seriesByName("_time")','y':'> primary | frameBySeriesNames("mean")'}),
                           'detail_trend':chart('splunk.line','trend',{'x':'> primary | seriesByName("_time")','y':'> primary | frameBySeriesNames("mean")'}),
                           'raw':chart('splunk.table','raw',{'table':'> primary | frameBySeriesNames("_time", "device_name", "duration")'})},
         'layout':{'tabs':{'items':[{'label':'Overview','layoutId':'overview'},{'label':'Device details','layoutId':'details'}]},'globalInputs':[],
                   'layoutDefinitions':{k:{'type':'absolute','options':{'width':1200,'height':800},'structure':[{'item':i,'type':'block','position':{'x':20,'y':n*380,'w':1160,'h':360}}for n,i in enumerate(items)]}for k,items in [('overview',['summary','overview_trend']),('details',['detail_trend','raw'])]}}}
    doc['visualizations']['summary']['eventHandlers']=[{'type':'drilldown.setToken','options':{'fields':['device_name'],'tokens':[{'token':'selected_device','key':'row.device_name.value'},{'token':'constellation_focus','value':'detail_trend'}]}}, {'type':'drilldown.switchToTab','options':{'fields':['device_name'],'tabId':'details'}}]
    for source in doc['dataSources'].values(): source['options'].setdefault('queryParameters', {'earliest':'-24h','latest':'now'})
    return doc

class CreationScopeTests(unittest.TestCase):
    def test_shared_filtered_search_is_isolated_without_a_filter_request(self):
        doc=fixture();before=copy.deepcopy(doc);changes=normalize_creation_page_scope(doc,{},PROFILE,'Click a device to investigate it.');result=apply_changes(doc,changes)
        clone=result['visualizations']['detail_trend']['dataSources']['primary'];self.assertNotEqual(clone,'trend')
        self.assertNotIn('$selected_device',result['dataSources']['trend']['options']['query'])
        self.assertIn('| search device_name=$selected_device|s$ |',result['dataSources'][clone]['options']['query'])
        self.assertEqual(result['dataSources'][clone]['future'],{'keep':True});self.assertEqual(result['dataSources'][clone]['options']['queryParameters'],doc['dataSources']['trend']['options']['queryParameters'])
        self.assertEqual(result['visualizations']['summary'],doc['visualizations']['summary']);self.assertEqual(result['layout'],doc['layout']);self.assertEqual(result['defaults'],doc['defaults']);self.assertEqual(doc,before)
        self.assertEqual(normalize_creation_page_scope(result,{},PROFILE,'Click a device to investigate it.'),[])

    def test_missing_destination_filters_are_compiled_from_native_row_mapping(self):
        doc=fixture(False);result=apply_changes(doc,normalize_creation_page_scope(doc,{},PROFILE,'Investigate a device from its summary row.'))
        for key in ('detail_trend','raw'):
            sid=result['visualizations'][key]['dataSources']['primary'];self.assertIn('| search device_name=$selected_device|s$ |',result['dataSources'][sid]['options']['query'])
        self.assertEqual(result['dataSources']['trend'],doc['dataSources']['trend'])

    def test_unknown_predicates_are_not_stripped_and_failure_is_atomic(self):
        doc=fixture();doc['dataSources']['trend']['options']['query']=PROFILE['baseQuery']+' | where device_name=$selected_device|s$ OR duration>1 | timechart count AS mean';before=copy.deepcopy(doc)
        with self.assertRaisesRegex(ProviderError,'exact pre-aggregation'):normalize_creation_page_scope(doc,{},PROFILE,'Click a device to investigate it.')
        self.assertEqual(doc,before)

    def test_existing_work_explicit_global_selective_and_input_owned_tokens_are_preserved(self):
        doc=fixture()
        self.assertEqual(normalize_creation_page_scope(doc,doc,PROFILE,'Rename its title.'),[])
        for prompt in ('Use a global entity filter.','Filter only one destination chart.','Do not filter detail.'):
            self.assertEqual(normalize_creation_page_scope(doc,{},PROFILE,prompt),[])
        doc['inputs']['selection']={'type':'input.dropdown','options':{'token':'selected_device'}}
        self.assertEqual(normalize_creation_page_scope(doc,{},PROFILE,'Click a device to investigate it.'),[])
        self.assertEqual(normalize_creation_page_scope(fixture(),{},dict(PROFILE,scope={'language':'spl2'}),'Inspect devices.'),[])

if __name__=='__main__':unittest.main()
