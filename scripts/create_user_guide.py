#!/usr/bin/env python3
"""Export the Markdown user guide to a paginated PDF; ReportLab is development-only."""
import argparse
from datetime import date
import hashlib
import html
import json
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
except ImportError:
    raise SystemExit('PDF export needs ReportLab in a development Python environment; the installed app does not require it.') from None

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT/'package.json').read_text())['version']
SOURCE = ROOT/'docs/user-guide.md'
ONLINE = 'https://github.com/LeiterConsulting/constellation/blob/main/'
INK, MUTED, ACCENT = colors.HexColor('#263238'), colors.HexColor('#52636b'), colors.HexColor('#24775f')
WIDTH = A4[0] - 100
EDITION = date.today()


def plain(text):
    return text.replace('→',' > ').replace('…','...').replace('—','-').replace('–','-').replace('’',"'").replace('“','"').replace('”','"').replace('·',' / ').replace('\u00a0',' ')


def target(url):
    parsed=urlsplit(url)
    if parsed.scheme:
        if parsed.scheme not in ('https','http','mailto'): raise ValueError('Unsupported guide link.')
        return url
    if not parsed.path:return '#'+parsed.fragment
    path=posixpath.normpath(posixpath.join('docs',parsed.path))
    return ONLINE+path+('#'+parsed.fragment if parsed.fragment else '')


def inline(text):
    text=html.escape(plain(text),quote=False)
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:'<a color="#24775f" href="'+html.escape(target(html.unescape(m[2])),quote=True)+'">'+m[1]+'</a>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<i>\1</i>',text)
    text=re.sub(r'\x60([^\x60]+)\x60',r'<font name="Courier">\1</font>',text)
    return text


styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='GuideTitle',fontName='Helvetica-Bold',fontSize=27,leading=31,textColor=INK,spaceAfter=14,keepWithNext=True))
styles.add(ParagraphStyle(name='GuideHeading',fontName='Helvetica-Bold',fontSize=16,leading=20,textColor=INK,spaceBefore=15,spaceAfter=9,keepWithNext=True))
styles.add(ParagraphStyle(name='GuideBody',fontName='Helvetica',fontSize=10.3,leading=15.2,textColor=INK,spaceAfter=9))
styles.add(ParagraphStyle(name='GuideList',parent=styles['GuideBody'],leftIndent=17,firstLineIndent=0,bulletIndent=0,spaceAfter=7))
styles.add(ParagraphStyle(name='GuideCaption',fontName='Helvetica-Oblique',fontSize=8.5,leading=12,textColor=MUTED,spaceBefore=6,spaceAfter=12))
styles.add(ParagraphStyle(name='GuideQuote',parent=styles['GuideBody'],leftIndent=12,rightIndent=12,backColor=colors.HexColor('#eef4f1'),borderPadding=8,spaceBefore=5,spaceAfter=13))
styles.add(ParagraphStyle(name='GuideCell',parent=styles['GuideBody'],fontSize=9,leading=12,spaceAfter=0))


class Guide(SimpleDocTemplate):
    def afterFlowable(self,flowable):
        if hasattr(flowable,'bookmark'):
            self.canv.bookmarkPage(flowable.bookmark)
            self.canv.addOutlineEntry(flowable.getPlainText(),flowable.bookmark,level=flowable.level,closed=False)


def header(canvas,doc):
    canvas.saveState();canvas.setDateFormatter(lambda *parts: 'D:' + EDITION.strftime('%Y%m%d') + '000000Z');canvas.setTitle('Constellation '+VERSION+' user guide');canvas.setAuthor('Constellation documentation');canvas.setCreator('Constellation guide exporter')
    canvas.setSubject('Guide SHA-256 '+hashlib.sha256(SOURCE.read_bytes()).hexdigest()+'; screenshots SHA-256 '+hashlib.sha256((ROOT/'docs/images/manifest.json').read_bytes()).hexdigest())
    canvas.setFillColor(INK);canvas.setFont('Helvetica-Bold',9);canvas.drawString(50,A4[1]-32,'CONSTELLATION')
    canvas.setFillColor(MUTED);canvas.setFont('Helvetica',8.5);canvas.drawRightString(A4[0]-50,A4[1]-32,'User guide / '+VERSION)
    canvas.setStrokeColor(colors.HexColor('#d7dfe0'));canvas.line(50,44,A4[0]-50,44)
    canvas.setFont('Helvetica',8);canvas.drawString(50,30,'Documentation edition / '+EDITION.strftime('%B')+' '+str(EDITION.day)+', '+str(EDITION.year));canvas.drawRightString(A4[0]-50,30,str(doc.page));canvas.restoreState()


def export(output):
    lines=SOURCE.read_text().splitlines();story=[];index=0
    while index<len(lines):
        line=lines[index].strip()
        if not line:index+=1;continue
        if line.startswith('# '):
            p=Paragraph(inline(line[2:]),styles['GuideTitle']);p.bookmark='constellation-user-guide';p.level=0;story.append(p);index+=1;continue
        if line.startswith('## '):
            title=line[3:];slug=re.sub(r'[^\w\- ]','',title.lower()).replace(' ','-')
            if slug=='build-your-first-dashboard':story.append(PageBreak())
            p=Paragraph(inline(title),styles['GuideHeading']);p.bookmark=slug;p.level=1;story.append(p);index+=1;continue
        image=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if image:
            path=(SOURCE.parent/image[2]).resolve()
            if not path.is_relative_to(ROOT)or path.is_symlink()or not path.is_file():raise ValueError('Unreviewed guide image.')
            width,height=ImageReader(str(path)).getSize();picture=Image(str(path),width=WIDTH,height=WIDTH*height/width);elements=[picture];index+=1
            while index<len(lines)and not lines[index].strip():index+=1
            if index<len(lines)and lines[index].strip().startswith('*')and not lines[index].strip().startswith('**'):
                elements.append(Paragraph(inline(lines[index].strip()),styles['GuideCaption']));index+=1
            story.append(KeepTogether(elements));continue
        if line.startswith('|'):
            rows=[]
            while index<len(lines)and lines[index].strip().startswith('|'):
                cells=[c.strip()for c in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c)for c in cells):
                    if not rows:cells=['**'+c+'**'for c in cells]
                    rows.append([Paragraph(inline(c),styles['GuideCell'])for c in cells])
                index+=1
            count=len(rows[0]);widths=[WIDTH*.34,WIDTH*.66]if count == 2 else[WIDTH/count]*count
            table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f1ee')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d7dfe0'))]));story.extend([table,Spacer(1,10)]);continue
        if line.startswith('> '):story.append(Paragraph(inline(line[2:]),styles['GuideQuote']));index+=1;continue
        item=re.match(r'^(\d+\.|-)\s+(.+)',line)
        if item:
            story.append(Paragraph(inline(item[2]),styles['GuideList'],bulletText=item[1]if item[1]!='-'else'-'));index+=1;continue
        paragraphs=[line];index+=1
        while index<len(lines)and lines[index].strip()and not re.match(r'^(#|!\[|\||>|\d+\.|-)\s*',lines[index].strip()):
            paragraphs.append(lines[index].strip());index+=1
        story.append(Paragraph(inline(' '.join(paragraphs)),styles['GuideBody']))
    output.parent.mkdir(parents=True,exist_ok=True)
    Guide(str(output),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=55,bottomMargin=59,title='Constellation '+VERSION+' user guide',author='Constellation documentation',invariant=1).build(story,onFirstPage=header,onLaterPages=header)
    print(json.dumps({'pdf':str(output),'guideSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'pdfSha256':hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'output/pdf'/('constellation-'+VERSION+'-user-guide.pdf'));parser.add_argument('--edition-date',default=date.today().isoformat());args=parser.parse_args();EDITION=date.fromisoformat(args.edition_date);export(args.output)
