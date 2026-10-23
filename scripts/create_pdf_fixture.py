"""Authored PDF acceptance fixture; no lab data or secrets."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape,A4
out=Path(__file__).resolve().parents[1]/'output/pdf/service-operations-brief.pdf'
out.parent.mkdir(parents=True, exist_ok=True)
c=canvas.Canvas(str(out),pagesize=landscape(A4)); W,H=landscape(A4)
ink=HexColor('#25364A'); muted=HexColor('#526477'); blue=HexColor('#157B99')
def text(x,y,s,size=12,color=ink):
 c.setFillColor(color);c.setFont('Helvetica',size);c.drawString(x,y,s)
def box(x,y,w,h,title,subtitle):
 c.setFillColor(HexColor('#F2F7FA'));c.setStrokeColor(HexColor('#A2B5C5'));c.roundRect(x,y,w,h,7,fill=1)
 text(x+12,y+h-22,title,13);text(x+12,y+13,subtitle,10,muted)
text(38,H-46,'Service operations',25)
text(38,H-70,'A dashboard layout brief - synthetic acceptance exercise',12,muted)
text(38,H-103,'Overview  |  Analysis',13,blue)
box(38,353,240,108,'Requests','Reuse the existing sample KPI')
box(295,353,240,108,'Error rate','Reuse the existing sample KPI')
box(552,353,250,108,'p95 latency','Reuse the existing sample KPI')
box(38,187,764,149,'Latency over time','Wide line chart using the existing sample source')
box(38,52,370,118,'Service latency comparison','Vertical columns; label sample approximation')
box(425,52,377,118,'Services','Keep the working row-to-detail drilldown')
text(38,24,'Page 1 / 2 - Keep current sources, field names and working Service detail page.',10,muted)
c.showPage()
text(38,H-46,'Analysis: optional interpretation',24)
text(38,H-72,'Add this tab alongside Overview and the existing Service detail tab.',12,muted)
box(38,292,475,185,'Latency analysis','Reuse a copy of the existing trend chart and sample source')
box(532,419,270,58,'Show notes / Hide notes','Native Studio button toggles the notes')
box(532,292,270,110,'Interpretation','Only visible when notes are enabled')
lines=[
'Behavior and acceptance checks',
'1. Default state: notes hidden; button says Show notes.',
'2. Clicking Show notes reveals a markdown panel and changes the button to Hide notes.',
'3. Clicking Hide notes hides it again. Use native Studio token evaluation and visibility.',
'4. Notes say: Authored sample data. Investigate real fields before drawing conclusions.',
'5. Keep the existing pages, all sample columns, inputs and table drilldown intact.',
'6. Do not execute searches, infer production results or save automatically.'
]
for i,s in enumerate(lines):text(38,245-i*27,s,13 if i==0 else 11)
text(38,24,'Page 2 / 2 - This PDF is a layout reference, not authorization to run external actions.',10,muted)
c.save();print(out)
