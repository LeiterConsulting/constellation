import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from table_projection import validate_creation_columns
from provider_service import ProviderError

class RawCreationColumnTests(unittest.TestCase):
    def test_explicit_raw_fields_must_be_returned_and_displayed(self):
        profile={'baseQuery':'search index="fixture"','fields':[{'name':x}for x in ('_time','host','load','cpu_instance')]}
        doc={'visualizations':{'raw':{'type':'splunk.table','dataSources':{'primary':'source'},'options':{'table':'> primary | frameBySeriesNames("_time", "host", "load")'}}},'dataSources':{'source':{'type':'ds.search','options':{'query':'search index="fixture" | table _time host load'}}}}
        before=copy.deepcopy(doc);prompt='Build a raw reading table with _time, host, load. Also include cpu_instance in the raw table.'
        for fields in (['_time','host','load'],['_time','host','load','cpu_instance']):
            with self.assertRaisesRegex(ProviderError,'cpu_instance'):validate_creation_columns(prompt,doc,{},profile,[{'source':'source','fields':fields}])
        self.assertEqual(doc,before)
        doc['visualizations']['raw']['options']['table']='> primary'
        validate_creation_columns(prompt,doc,{},profile,[{'source':'source','fields':['_time','host','load','cpu_instance']}])
        validate_creation_columns(prompt,before,{'visualizations':{'existing':{}}},profile,[{'source':'source','fields':['_time','host','load']}])
    def test_unknown_fields_and_ambiguous_targets_are_not_invented_or_rewritten(self):
        profile={'baseQuery':'search index="fixture"','fields':[{'name':'host'}]};doc={'visualizations':{},'dataSources':{}}
        validate_creation_columns('Build a raw table with missing_field.',doc,{},profile,[])
        validate_creation_columns('Build a raw table with host.',doc,{},profile,[])
        self.assertEqual(doc,{'visualizations':{},'dataSources':{}})
