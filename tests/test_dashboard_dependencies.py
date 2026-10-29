"""Synthetic dependency metadata; no lookup data or credentials are transported."""
import sys,copy,unittest,base64,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from dashboard_dependencies import DashboardDependencies
from native_media import NativeMedia
from native_shapes import validate_shape
from provider_service import ProviderError
from svg_actions import compile_binding
from authoring_intent import validate_page_intent
from test_drafts_and_data import blank
SVG='<svg xmlns="http://www.w3.org/2000/svg"><path id="north" d="M0 0h10v10z"/></svg>'
URI='data:image/svg+xml;base64,'+base64.b64encode(SVG.encode()).decode()
class Runtime:
    user='fixture_author'
    def __init__(self):self.paths=[];self.query='search index="fixture" | stats count';self.available=True
    def datasets(self):return {'indexes':[{'name':'fixture'}]}
    def request(self,path,method='GET',fields=None,optional=False):
        assert method=='GET' and fields is None;self.paths.append(path)
        if 'storage/collections/data' in path:return {'dataURI':URI}
        return {'entry':[{'name':'Report','acl':{'app':'search'},'content':{'search':self.query,'dispatch.earliest_time':'-7d','dispatch.latest_time':'now'}}]} if self.available and path.endswith('/saved/searches/Report') else {'entry':[]}
class DependencyTests(unittest.TestCase):
    def report_doc(self):
        doc=blank()['definition'];doc['dataSources']={'r':{'type':'ds.savedSearch','future':'keep','options':{'app':'search','ref':'Report'}}};return doc
    def test_report_receipt_and_explicit_search_copy_preserve_query_times_and_unrelated_work(self):
        runtime=Runtime();service=DashboardDependencies(runtime);doc=self.report_doc();before=copy.deepcopy(doc)
        kept=service.operation({'action':'export','definition':doc});self.assertEqual(kept['definition'],doc);self.assertTrue(any(x['kind']=='report'and x['fingerprint']for x in kept['dependencies']))
        copied=service.operation({'action':'export','definition':doc,'includeReports':True});source=copied['definition']['dataSources']['r'];self.assertEqual(source['type'],'ds.search');self.assertEqual(source['future'],'keep');self.assertEqual(source['options']['query'],runtime.query);self.assertEqual(source['options']['queryParameters']['earliest'],'-7d');self.assertTrue(copied['notes']);self.assertEqual(doc,before)
        runtime.query+=' | head 1';checked=service.operation({'action':'check','definition':doc,'dependencies':kept['dependencies']});self.assertTrue(checked['blocked'])
    def test_unreadable_reports_and_missing_dependencies_are_actionable(self):
        runtime=Runtime();runtime.available=False;service=DashboardDependencies(runtime);result=service.operation({'action':'check','definition':self.report_doc()});self.assertTrue(result['blocked'])
        doc=blank()['definition'];doc['dataSources']={'s':{'type':'ds.search','options':{'query':'search index="absent" | lookup unavailable.csv key'}}};result=service.operation({'action':'check','definition':doc});self.assertEqual({x['kind']for x in result['dependencies']if x['status']=='missing'},{'index','lookup'})
    def test_quoted_search_text_is_not_an_index_dependency(self):
        doc=blank()['definition'];doc['dataSources']={'s':{'type':'ds.search','options':{'query':'search index="fixture" message="note index=absent" | stats count'}}};result=DashboardDependencies(Runtime()).operation({'action':'check','definition':doc});self.assertEqual([x['name']for x in result['dependencies']],['fixture']);self.assertFalse(result['blocked'])
    def test_parameterized_macro_resolves_exact_arity_and_missing_definition_blocks(self):
        runtime=Runtime();doc=blank()['definition'];doc['dataSources']={'s':{'type':'ds.search','options':{'query':'search index="fixture" | `custom(a,if(b,c,d))`'}}}
        result=DashboardDependencies(runtime).operation({'action':'check','definition':doc})
        self.assertTrue(result['blocked']);self.assertEqual(next(x for x in result['dependencies'] if x['kind']=='macro')['status'],'missing')
        self.assertTrue(any(path.endswith('/conf-macros/custom%282%29') for path in runtime.paths))
    def test_does_not_embed_unsafe_or_advanced_report_searches(self):
        runtime=Runtime();runtime.query='| sendemail to="example@example.com"'
        with self.assertRaises(ProviderError):DashboardDependencies(runtime).operation({'action':'export','definition':self.report_doc(),'includeReports':True})
        with self.assertRaises(ProviderError):DashboardDependencies(runtime).operation({'action':'export','definition':self.report_doc(),'includeReports':True,'includeKnowledge':True})
        runtime.query='search index=fixture | stats count';doc=self.report_doc();doc['dataSources']['r']['options']['future']='keep'
        with self.assertRaises(ProviderError):DashboardDependencies(runtime).operation({'action':'export','definition':doc,'includeReports':True})
class NativeMediaTests(unittest.TestCase):
    def test_unbound_svg_scaffold_does_not_leave_an_extra_overview_page(self):
        previous=blank()['definition'];previous['visualizations']={'map':{'type':'splunk.choropleth.svg','options':{'svg':'splunk-enterprise-kvstore://fixture'}}}
        candidate=copy.deepcopy(previous);candidate['layout']['tabs']={'items':[{'label':'Overview','layoutId':'layout_main'},{'label':'Ranges','layoutId':'layout_ranges'}]}
        with self.assertRaisesRegex(ProviderError,'existing scaffold page'):
            validate_page_intent('Build exactly one page named Ranges.','',candidate,previous,{'kind':'dashboard'})
        candidate['layout']['tabs']['items']=[{'label':'Ranges','layoutId':'layout_main'}]
        validate_page_intent('Build exactly one page named Ranges.','',candidate,previous,{'kind':'dashboard'})
    def test_typed_svg_binding_preserves_asset_properties_and_unrelated_handlers(self):
        item={'type':'splunk.choropleth.svg','title':'Original','options':{'svg':'splunk-enterprise-kvstore://fixture','future':17},'context':{'constellationAreaGradient':{'future':True}},'eventHandlers':[{'type':'drilldown.setToken','options':{'events':['area.click'],'tokens':[{'token':'selected_area','value':'old'},{'token':'unrelated','value':'keep'}]}}]}
        document={'visualizations':{'map':item}};before=copy.deepcopy(document);action=dict(op='bindSvg',id='map',sourceId='new_source',areaField='area_id',valueField='readings',title='',selectionToken='selected_area')
        result=json.loads(compile_binding(action,document)['value']);self.assertEqual(result['options']['svg'],item['options']['svg']);self.assertEqual(result['options']['future'],17);self.assertEqual(result['title'],'Original');self.assertEqual(result['context']['constellationAreaGradient'],{'future':True});self.assertEqual(result['eventHandlers'][0]['options']['tokens'],[{'token':'selected_area','key':'name'},{'token':'unrelated','value':'keep'}]);self.assertEqual(document,before)
        result['options']['areaColors']='> existingColor';document['visualizations']['map']=result
        self.assertEqual(json.loads(compile_binding(action,document)['value'])['options']['areaColors'],'> existingColor')
    def test_typed_svg_binding_requires_existing_asset_and_plain_fields(self):
        action=dict(op='bindSvg',id='absent',sourceId='new',areaField='area',valueField='readings',title='',selectionToken='')
        with self.assertRaises(ProviderError):compile_binding(action,{'visualizations':{}})
        action['areaField']='> arbitrary | pipeline()'
        with self.assertRaises(ProviderError):compile_binding(action,{'visualizations':{}})
    def test_svg_context_contains_only_bounded_path_metadata_and_reuses_current_user_read(self):
        runtime=Runtime();media=NativeMedia(runtime);item={'type':'splunk.choropleth.svg','options':{'svg':'splunk-enterprise-kvstore://fixture'},'dataSources':{'primary':'s'}};doc={'visualizations':{'map':item}};context=media.context(doc);self.assertEqual(context[0]['areaIds'],['north']);self.assertNotIn(SVG,json.dumps(context));self.assertNotIn('dataURI',json.dumps(context));resolved=media.validation_item(item);self.assertEqual(resolved['options']['svg'],URI);self.assertEqual(len(runtime.paths),1);self.assertIn('/nobody/splunk-dashboard-studio/',runtime.paths[0]);self.assertEqual(item['options']['svg'],'splunk-enterprise-kvstore://fixture')
        outputs={'s':{'fields':[{'name':'room','type':'string'},{'name':'count','type':'number'}],'results':[{'room':'wrong','count':2}]}};resolved['options'].update(areaIds='> primary | seriesByName("room")',areaValues='> primary | seriesByName("count")')
        with self.assertRaisesRegex(ProviderError,'No inspected area ID'):validate_shape(resolved,outputs)
    def test_no_external_or_traversal_asset_fetch(self):
        runtime=Runtime();media=NativeMedia(runtime);self.assertIsNone(media.svg('https://example.com/a.svg'));self.assertEqual(runtime.paths,[])
        with self.assertRaises(ProviderError):media.svg('splunk-enterprise-kvstore://../other')
