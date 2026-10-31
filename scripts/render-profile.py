"""Restyle Metrics output without changing account data or API permissions."""
from pathlib import Path
import copy
import re
import html
import xml.etree.ElementTree as ET

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
S = '{http://www.w3.org/2000/svg}'
X = '{http://www.w3.org/1999/xhtml}'
ET.register_namespace('', S[1:-1])
GREEN, GOLD, TEXT, MUTED = '#8ee6a5', '#e8c477', '#e6edf5', '#96a9bd'

def txt(x, y, value, size=16, color=TEXT, anchor='start', weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(value))}</text>'

def card(height, number, title, label, content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-label="{html.escape(title)}">
    <style>text{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}.gauge-base,.gauge-arc{{fill:none;stroke:currentColor;stroke-width:5}}.gauge-base{{stroke-opacity:.18}}.gauge-arc{{stroke-linecap:round}}</style>
    <path d="M10 1H950V10H959V{height-10}H950V{height-1}H10V{height-10}H1V10H10Z" fill="#101b2b" stroke="#2b4153"/>
    <path d="M24 24h8v8h-8zm12 0h8v8h-8z" fill="{GREEN}"/>
    {txt(58,34,title,20,TEXT,weight=600)}{txt(932,33,label,12,MUTED,'end')}
    <path d="M24 52H936" stroke="#273a4b"/>
    {content}
    </svg>'''

def text_content(el):
    return ' '.join(' '.join(el.itertext()).split())

def calendar():
    root = ET.parse(ASSETS / 'metrics-calendar.svg').getroot()
    graph = next(e for e in root.iter(S+'svg') if e.get('viewBox') == '0,0 480,270')
    graph = copy.deepcopy(graph)
    graph.attrib.pop('style', None)
    graph.set('x','16'); graph.set('y','66'); graph.set('width','680'); graph.set('height','310')
    # Use a stable green scale, including on Halloween and winter dates.
    palette = {'#ebedf0':'#233649','#ffee4a':'#41644e','#ffc501':'#58976c','#fe9600':'#79c88e','#03001c':GREEN,
               '#9be9a8':'#41644e','#40c463':'#58976c','#30a14e':'#79c88e','#216e39':GREEN,
               '#0a3069':'#41644e','#0969da':'#58976c','#54aeff':'#79c88e','#b6e3ff':GREEN}
    for el in graph.iter():
        if el.get('fill','').lower() in palette: el.set('fill',palette[el.get('fill').lower()])
    fields = [text_content(e) for e in root.iter(X+'div') if e.get('class') == 'field']
    patterns = [('CURRENT STREAK',r'Current streak (.+)'),('BEST STREAK',r'Best streak (.+)'),('MOST COMMITS / DAY',r'Highest in a day at (.+)')]
    content = ET.tostring(graph,encoding='unicode')
    for i,(label,pattern) in enumerate(patterns):
        value = next((m.group(1) for f in fields if (m := re.fullmatch(pattern,f))),None)
        if value is None: raise ValueError('Missing calendar metric: '+label)
        y=112+i*82
        content += txt(728,y,label,11,MUTED)+txt(728,y+32,value,25,GOLD if i==2 else GREEN,weight=600)
    content += txt(30,379,'ONE YEAR OF BUILDING',11,MUTED)
    return card(400,'01','CONTRIBUTION CALENDAR','01 / ACTIVITY',content)

def languages():
    root = ET.parse(ASSETS / 'metrics-languages.svg').getroot()
    entries = []
    for e in root.iter(X+'div'):
        if e.get('class') == 'field language details':
            name = text_content(next(c for c in e if c.tag == X+'div'))
            pct = text_content(next(c for c in e if c.tag == X+'small'))
            entries.append((name,pct,float(pct.rstrip('%'))))
    assert entries, 'No language data; retain previous cards'
    entries.sort(key=lambda e:e[2], reverse=True)
    colors=[GREEN,GOLD,'#78b7c5','#b4a7ce','#dfaa8c','#8fa1bc']
    content=''; x=30; total=sum(e[2] for e in entries)
    for i,(name,pct,value) in enumerate(entries):
        w=900*value/total
        content+=f'<rect x="{x}" y="78" width="{w}" height="18" fill="{colors[i%6]}"/>'
        x+=w
        col=i%3; row=i//3; lx=30+col*304; ly=130+row*36
        content+=f'<rect x="{lx}" y="{ly-10}" width="8" height="8" fill="{colors[i%6]}"/>'
        content+=txt(lx+18,ly,name,16)+txt(lx+274,ly,pct,16,colors[i%6],'end')
    height=190+36*((len(entries)-1)//3)
    content+=txt(30,height-24,'PUBLIC + PRIVATE REPOSITORIES / AGGREGATED LANGUAGE USAGE',11,MUTED)
    return card(height,'02','LANGUAGE ACTIVITY','02 / CODE',content)

def achievements():
    root = ET.parse(ASSETS / 'metrics-achievements.svg').getroot()
    badges = [e for e in root.iter(X+'div') if 'achievement' in e.get('class','').split()]
    assert badges, 'No achievements; retain previous cards'
    content=''
    for i,e in enumerate(badges[:8]):
        title = next(c for c in e.iter(X+'div') if c.get('class')=='title')
        prefix = next(c for c in title if c.tag==X+'span')
        name = ' '.join((prefix.tail or '').split())
        name = name[:1].upper()+name[1:]
        rank=text_content(prefix)
        value=text_content(next(c for c in title.iter(X+'div') if c.get('class')=='value'))
        icon=copy.deepcopy(next(e.iter(S+'svg')))
        accent=GOLD if 'b' in e.get('class','').split() else GREEN
        icon.set('x','12');icon.set('y','20');icon.set('width','60');icon.set('height','60');icon.set('color',accent)
        # Masks must stay opaque; upstream gauge CSS otherwise hides their contents.
        for mask in icon.iter(S+'mask'):
            for shape in mask:
                shape.attrib.pop('class', None)
                shape.set('fill', 'white'); shape.set('stroke', 'none')
        # Upstream repeats mask ids; scope every badge before composing one SVG.
        for node in icon.iter():
            for k,v in list(node.attrib.items()):
                if k=='id': node.set(k,f'badge-{i}-{v}')
                elif 'url(#' in v: node.set(k,re.sub(r'url\(#([^)]*)\)',rf'url(#badge-{i}-\1)',v))
                elif k in ('stroke','fill') and v.startswith('#'): node.set(k,accent)
        x=30+(i%4)*228; y=74+(i//4)*116
        content+=f'<g transform="translate({x} {y})"><rect width="216" height="104" rx="4" fill="#152438" stroke="#2b4153"/>'
        content+=ET.tostring(icon,encoding='unicode')
        content+=txt(84,31,rank.upper() if rank else 'UNLOCKED',10,MUTED)
        content+=txt(84,53,name,14,TEXT,weight=600)+txt(84,78,value,17,accent)+'</g>'
    height=74+116*((min(8,len(badges))+3)//4)+35
    content+=txt(30,height-19,'COMMUNITY BADGES / BASED ON PUBLIC GITHUB ACTIVITY',11,MUTED)
    return card(height,'03','ACHIEVEMENTS','03 / UNLOCKS',content)

if __name__ == '__main__':
    for module, render in [('calendar',calendar),('languages',languages),('achievements',achievements)]:
        svg=render()
        ET.fromstring(svg)
        (ASSETS/f'profile-{module}.svg').write_text(svg)
        print(f'Rendered profile-{module}.svg')
