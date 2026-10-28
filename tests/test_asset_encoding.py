"""Synthetic encoding cases; no native rendering claim."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from native_text_encoding import normalize_reference_text

class AssetEncodingTests(unittest.TestCase):
    def test_only_literal_hex_on_an_existing_icon_is_json_encoded(self):
        doc={'visualizations':{'icon':{'type':'splunk.singlevalueicon'},'table':{'type':'splunk.table'}}}
        action={'op':'set','path':'/visualizations/icon/options/iconColor','value':'#53a051'}
        self.assertEqual(normalize_reference_text(action,doc),dict(action,value='"#53a051"'))
        self.assertEqual(action['value'],'#53a051')
        for path,value in [('/visualizations/missing/options/iconColor','#53a051'),('/visualizations/table/options/iconColor','#53a051'),('/visualizations/icon/options/src','#53a051'),(action['path'],'red'),(action['path'],'#53a051 trailing'),(action['path'],'> primary | lastPoint()')]:
            other=dict(action,path=path,value=value)
            self.assertEqual(normalize_reference_text(other,doc),other)
