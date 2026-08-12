#!/usr/bin/env python3
# MIT risk entries -> BGE-M3 embeddings via local ollama (stdlib only)
import json, urllib.request, time, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
items = json.load(open(os.path.join(BASE, 'mit_risks.json')))
out_path = os.path.join(BASE, 'emb_mit_bge.jsonl')
log_path = os.path.join(BASE, 'embed_progress.log')

def clean(s):
    return ' '.join((s or '').replace('"', ' ').split())

texts = []
for it in items:
    title = it['subcategory'] or it['category']
    d = clean(it['description'])
    texts.append((clean(title) + '. ' + d).strip() if d else clean(title))

done = 0
if os.path.exists(out_path):
    done = sum(1 for _ in open(out_path))

def embed_batch(batch):
    req = urllib.request.Request(
        'http://localhost:11434/api/embed',
        data=json.dumps({'model': 'bge-m3', 'input': batch}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())['embeddings']

B = 16
with open(out_path, 'a') as f, open(log_path, 'a') as lg:
    lg.write(f'start at {done}/{len(texts)} {time.ctime()}\n'); lg.flush()
    i = done
    while i < len(texts):
        batch = texts[i:i+B]
        embs = embed_batch(batch)
        for e in embs:
            f.write(json.dumps(e) + '\n')
        f.flush()
        i += len(batch)
        lg.write(f'{i}/{len(texts)} {time.ctime()}\n'); lg.flush()
    lg.write(f'DONE {time.ctime()}\n'); lg.flush()
print('done', len(texts))
