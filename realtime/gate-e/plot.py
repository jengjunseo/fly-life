"""Static measurement plots using bundled Pillow. No neural simulation imports."""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

report=Path(sys.argv[1])
names=json.loads((report/'e4-runs.json').read_text())['repeats']
data=[json.loads((report/(n+'-timeline-data.json')).read_text()) for n in names]
stats=[json.loads((report/(n+'.json')).read_text())['brain_statistics'] for n in names]
font_path='C:/Windows/Fonts/segoeui.ttf'
font=ImageFont.truetype(font_path,18)
small=ImageFont.truetype(font_path,15)
title=ImageFont.truetype(font_path,25)
blue='#2563eb';green='#16a34a';red='#dc2626';gray='#64748b';ink='#0f172a'

def text(draw,xy,label,kind=font,color=ink):
    draw.text(xy,str(label),fill=color,font=kind)

im=Image.new('RGB',(1450,990),'white');d=ImageDraw.Draw(im)
text(d,(75,20),'Gate E: strong workload / profiler OFF / CPU6 / HIGH priority',title)
text(d,(75,58),'20s persistent runs; known 2s frozen-noise replay. Not streaming/pipeline certification.',font,gray)
text(d,(75,89),'Blue: compute   Green: 35ms target   Red: 50ms floor   Shaded: first 0.5s warmup',font,gray)
left,right=100,1400
max_ms=max(row['wall_compute_ms'] for run in data for row in run['rows'])
ymax=math.ceil(max_ms/20)*20
for i,(run,s) in enumerate(zip(data,stats)):
    top,bottom=173+i*257,355+i*257
    text(d,(100,top-32),f"Repeat {i}: mean {s['mean_ms']:.2f}, p99 {s['p99_ms']:.2f} ms; misses {s['deadline_misses']}/390")
    px=lambda t:left+(right-left)*t/20
    py=lambda v:bottom-(bottom-top)*v/ymax
    d.rectangle((left,top,px(.5),bottom),fill='#f1f5f9')
    for value in range(0,ymax+1,20):
        y=py(value);d.line((left,y,right,y),fill='#e2e8f0')
        text(d,(49,y-10),value,small,gray)
    for t in range(0,21,2):
        x=px(t);d.line((x,top,x,bottom),fill='#e2e8f0')
        text(d,(x-8,bottom+7),t,small,gray)
    for value,color in [(35,green),(50,red)]:
        y=py(value)
        for x in range(left,right,15):d.line((x,y,min(x+8,right),y),fill=color,width=2)
    points=[(px(r['neural_end_s']),py(r['wall_compute_ms'])) for r in run['rows']]
    d.line(points,fill=blue,width=2)
    d.line((left,top,left,bottom,right,bottom),fill=gray,width=1)
text(d,(570,943),'Completed neural time (seconds)',font)
text(d,(15,129),'ms',small,gray)
im.save(report/'timeline.png')

im=Image.new('RGB',(1450,510),'white');d=ImageDraw.Draw(im)
text(d,(65,20),'Gate E: strong-workload timing histograms / profiler OFF',title)
text(d,(65,57),'390 measured 50ms windows per repeat. Red: 50ms floor. Different distributions expose timing variance.',font,gray)
for i,(run,s) in enumerate(zip(data,stats)):
    left,right=85+i*466,460+i*466;top,bottom=138,400
    text(d,(left,top-38),f"Repeat {i}, p99 {s['p99_ms']:.2f} ms",font)
    counts=run['diagnosis']['hist_counts'];edges=run['diagnosis']['hist_edges_ms']
    max_count=math.ceil(max(counts)/20)*20
    xmin,xmax=edges[0],edges[-1]
    px=lambda v:left+(right-left)*(v-xmin)/(xmax-xmin)
    py=lambda v:bottom-(bottom-top)*v/max_count
    for c in range(0,max_count+1,20):
        y=py(c);d.line((left,y,right,y),fill='#e2e8f0');text(d,(left-35,y-9),c,small,gray)
    for j,c in enumerate(counts):
        d.rectangle((px(edges[j])+1,py(c),px(edges[j+1])-1,bottom),fill=blue)
    if xmin<=50<=xmax:
        x=px(50);d.line((x,top,x,bottom),fill=red,width=3)
    for v in [xmin,(xmin+xmax)/2,xmax]:text(d,(px(v)-20,bottom+9),f'{v:.1f}',small,gray)
    d.line((left,top,left,bottom,right,bottom),fill=gray)
    text(d,(left+62,453),'Quantum compute (ms)',font)
    text(d,(left-35,top-24),'n',small,gray)
im.save(report/'histogram.png')
print('Timeline and histogram rendered from measured JSON rows.')
