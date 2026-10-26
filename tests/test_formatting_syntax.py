"""Synthetic SPL formatting syntax; native search validation remains mandatory."""
import copy,json,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"splunk/constellation/bin"))
from formatting_syntax import repair_query,selected_table_syntax,revise_tail_rounding
from studio_contract import apply_changes
class FormattingSyntaxTests(unittest.TestCase):
 def test_increased_precision_revises_every_self_round_in_the_pure_formatting_tail(self):
  base='search index="fixture_index" | stats max(value) AS peak avg(other) AS mean latest(_time) AS seen BY entity'
  tail=' | eval peak=round(peak,0), mean=round(mean,2) | eval seen=strftime(seen,"%Y|%m,%d") | eval peak=round(peak,1)'
  expected=base+tail.replace('peak=round(peak,0)','peak=round(peak,1)')
  self.assertEqual(revise_tail_rounding(base+tail,{'peak':1}),expected)
  self.assertEqual(revise_tail_rounding(expected,{'peak':1}),expected)
  self.assertEqual(revise_tail_rounding('| '+base+tail,{'peak':1}),'| '+expected)
 def test_rounding_revision_never_crosses_a_semantic_step_or_unknown_assignment(self):
  prefix='search index="fixture_index" | stats max(value) AS peak | eval peak=round(peak,0)'
  for barrier in ('where peak>20','sort -peak','table peak','eval total=peak*2','eval peak=round(other,0)','eval peak=round(peak,0),'):
   query=prefix+' | '+barrier+' | eval peak=round(peak,2)'
   expected=prefix+' | '+barrier+' | eval peak=round(peak,1)'
   self.assertEqual(revise_tail_rounding(query,{'peak':1}),expected,barrier)
 def test_agent_validates_corrected_query_before_accepting_without_another_model_call(self):
  from test_reliability_journey import Provider,Runtime,reply
  from test_drafts_and_data import blank
  from agent_service import AgentService
  from provider_service import ProviderError
  class Outputs(Runtime):
   def preview(self,body):
    if body.get('fieldDiscovery'): return super().preview(body)
    self.calls.append(body)
    if ') peak=' in body['query']:raise ProviderError('Malformed eval',422,'preview_failed')
    return {'state':'complete','fields':[{'name':n}for n in ('count','peak')],'results':[{'count':'12','peak':'42'}]}
  doc=blank()['definition'];doc.update(visualizations={'table':{'type':'splunk.table','title':'Observations','options':{'table':'> primary | frameBySeriesNames("count")'},'dataSources':{'primary':'source'}}},dataSources={'source':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats count','queryParameters':{'earliest':'-24h','latest':'now'}}}},layout={'type':'grid','structure':[{'item':'table'}]})
  before=copy.deepcopy(doc);provider=Provider([reply([{'op':'search','id':'source','pipeline':'| stats count max(duration) AS peak | eval count=round(count,0) peak=round(peak,2)'}])]);runtime=Outputs()
  result=AgentService(provider,runtime).assist({'prompt':'Add max(duration) AS peak to this selected table.','definition':doc,'revision':0,'selected':'table','dataContext':blank()['dataContext']})
  fixed=apply_changes(doc,result['changes']);self.assertIn('), peak=',fixed['dataSources']['source']['options']['query']);self.assertIn('"peak"',fixed['visualizations']['table']['options']['table'])
  self.assertEqual(result['recovery']['modelCalls'],1);self.assertEqual(result['recovery']['queryChecks'],2);self.assertEqual(doc,before)
  self.assertEqual(len([c for c in runtime.calls if isinstance(c,dict)]),2)
  from search_service import search_feedback
  feedback=search_feedback("Error in 'EvalCommand': malformed PRIVATE VALUE")
  self.assertIn('commas',feedback);self.assertNotIn('PRIVATE',feedback)
 def test_exact_omitted_commas_preserve_scope_expressions_and_quoted_format(self):
  prefix='search index="fixture_index" | stats avg(value) AS mean max(value) AS peak latest(_time) AS seen BY entity '
  suffix='| eval mean=round(mean,2) peak=round(peak,2) | eval seen=strftime(seen,"%Y|%m,%d %H:%M:%S")'
  self.assertEqual(repair_query(prefix+suffix),prefix+suffix.replace(') peak=', '), peak='))
  self.assertEqual(repair_query('| '+prefix+suffix),'| '+prefix+suffix.replace(') peak=', '), peak='))
  mixed='| stats count AS a | eval a=round(a,1), b=round(b,0) seen=strftime(seen,"%Y-%m-%d")'
  self.assertEqual(repair_query(mixed),mixed.replace(') seen=', '), seen='))
 def test_unknown_boolean_arithmetic_casts_and_raw_event_stages_stay_unchanged(self):
  for tail in ('eval a=round(a,1) AND b=round(b,1)','eval a=round(a,1) + b=round(b,1)','eval a=round(other,1) b=round(b,1)','eval a=round(a,2) b=tonumber(b)','eval a=round(a,2),','eval a=round(a,2)b=round(b,1)','eval a=round(a,2), b=round(b,1)'):
   q='| stats count AS a | '+tail;self.assertEqual(repair_query(q),q)
  q='search index="fixture_index" | eval a=round(a,2) b=round(b,1) | stats avg(a)';self.assertEqual(repair_query(q),q)
 def fixture(self):
  return {'title':'Fixture','description':'','visualizations':{'table':{'type':'splunk.table','dataSources':{'primary':'s'},'options':{'table':'> primary | frameBySeriesNames("mean")'},'future':{'preserve':True}}},'dataSources':{'s':{'type':'ds.search','options':{'query':'search index="fixture_index" | stats avg(value) AS mean max(value) AS peak BY entity'}}},'layout':{'type':'absolute','structure':[]}}
 def test_only_changed_selected_exclusive_existing_spl_table_is_repaired(self):
  before=self.fixture();doc=copy.deepcopy(before);doc['dataSources']['s']['options']['query']+=' | eval mean=round(mean,2) peak=round(peak,2)';original=copy.deepcopy(doc)
  changes=selected_table_syntax(doc,before,'table');self.assertEqual(len(changes),1);self.assertEqual(doc,original)
  fixed=apply_changes(doc,changes);self.assertEqual(fixed['visualizations'],doc['visualizations']);self.assertIn('), peak=',fixed['dataSources']['s']['options']['query'])
  self.assertEqual(selected_table_syntax(doc,doc,'table'),[])
  for change in ('no_selection','shared','chain','spl2','new_table'):
   candidate=copy.deepcopy(doc);previous=copy.deepcopy(before);selected='table'
   if change=='no_selection':selected=''
   if change=='shared':candidate['visualizations']['other']=copy.deepcopy(candidate['visualizations']['table'])
   if change=='chain':candidate['dataSources']['other']={'type':'ds.chain','options':{'extend':'s','query':'| stats count'}}
   if change=='spl2':candidate['dataSources']['s']['type']='ds.spl2'
   if change=='new_table':previous['visualizations']={}
   self.assertEqual(selected_table_syntax(candidate,previous,selected),[],change)
