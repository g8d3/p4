import json, glob, subprocess, os
base='/home/vuos/code/p4/e032-ai-skills-digest/ag-11-engine/videos/dia-3-imagenes'
tr=os.path.join(base,'transcripts')
voices=[]
for path in sorted(glob.glob(os.path.join(tr,'*.json'))):
    n=int(os.path.basename(path)[:2])
    d=json.load(open(path))
    r=d['results']['channels'][0]['alternatives'][0]
    words=[]
    for i,w in enumerate(r.get('words',[])):
        words.append({'id':f'w{i}','text':w['word'],'start':round(w['start'],3),'end':round(w['end'],3)})
    mp3=f'assets/voice/{n:02d}.mp3'
    dur=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',os.path.join(base,mp3)]).decode().strip()
    voices.append({'frame':n,'path':mp3,'duration_s':round(float(dur),3),'words':words})
meta={'bgm':None,'bgm_pending':False,'voices':voices,'sfx':[]}
out=os.path.join(base,'audio_meta.json')
json.dump(meta,open(out,'w'),ensure_ascii=False,indent=1)
total=sum(v['duration_s'] for v in voices)
print(f'voices={len(voices)} total_audio={total:.2f}s  -> {out}')
