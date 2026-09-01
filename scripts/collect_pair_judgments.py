#!/usr/bin/env python3
"""Collect pair-judgment submissions from GitHub issues.

Fetches issues titled '[pair-judgments] <rater>' from the repository, extracts
the fenced JSON block from each body, validates it against the survey, and
writes one JSON file per rater (latest submission wins) plus a combined CSV.

Usage:  python3 scripts/collect_pair_judgments.py [--issues-json FILE]
                                                  [--endpoint URL --key KEY]
        Default: GitHub issues.  With --endpoint, pulls from the Apps Script
        store (survey_endpoint.txt + read key) and merges both sources.
"""
import json, re, csv, sys, argparse, urllib.request, pathlib

REPO = 'deep1003/RAI-Risk-Taxonomy-2.0'
N_PAIRS = 135
OUT = pathlib.Path('review_logs/pair_judgments')

def fetch_issues():
    issues, page = [], 1
    while True:
        url = (f'https://api.github.com/repos/{REPO}/issues'
               f'?state=all&per_page=100&page={page}')
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'pair-judgment-collector'})
        with urllib.request.urlopen(req, timeout=60) as r:
            batch = json.loads(r.read())
        if not batch: break
        issues += batch; page += 1
    return issues

def parse(body):
    m = re.search(r'```json\s*(\{.*?\})\s*```', body or '', re.S)
    if not m: return None
    try:
        d = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    v = d.get('verdicts', '')
    if not d.get('rater') or len(v) != N_PAIRS: return None
    if set(v) - set('sdu-'): return None
    if d['rater'].strip().startswith('__'): return None   # internal test raters
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--issues-json')
    ap.add_argument('--endpoint')
    ap.add_argument('--key', default='rai-pairs-2026')
    a = ap.parse_args()
    issues = (json.load(open(a.issues_json)) if a.issues_json else fetch_issues())
    if a.issues_json and issues and isinstance(issues[0], list):   # gh --slurp
        issues = [x for page in issues for x in page]

    subs = {}
    if a.endpoint:
        req = urllib.request.Request(
            a.endpoint + '?key=' + a.key,
            headers={'User-Agent': 'pair-judgment-collector'})
        with urllib.request.urlopen(req, timeout=60) as r:
            store = json.loads(r.read())
        for d in store.get('responses', []):
            v = d.get('verdicts', '')
            if not d.get('rater') or len(v) != N_PAIRS: continue
            if d['rater'].strip().startswith('__'): continue
            d['_issue'] = 'store'; d['_created'] = d.get('received_at', '')
            key = d['rater'].strip().lower()
            if key not in subs or d['_created'] > subs[key]['_created']:
                subs[key] = d
    for it in issues:
        if 'pull_request' in it: continue
        if not (it.get('title') or '').startswith('[pair-judgments]'): continue
        d = parse(it.get('body'))
        if not d: 
            print(f"skip issue #{it['number']}: no valid JSON", file=sys.stderr)
            continue
        d['_issue'] = it['number']; d['_created'] = it['created_at']
        key = d['rater'].strip().lower()
        if key not in subs or d['_created'] > subs[key]['_created']:
            subs[key] = d

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for key, d in sorted(subs.items()):
        safe = re.sub(r'\W+', '_', d['rater'].strip())
        json.dump(d, open(OUT / f'{safe}.json', 'w'), ensure_ascii=False, indent=1)
        for k, ch in enumerate(d['verdicts'], 1):
            pid = f'P{k:03d}'
            rows.append([d['rater'], pid,
                         {'s': 'same', 'd': 'distinct', 'u': 'undecided',
                          '-': ''}[ch],
                         (d.get('notes') or {}).get(pid, '')])
    with open(OUT / 'all_judgments.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['rater', 'pair_id', 'verdict', 'note'])
        w.writerows(rows)
    done = {r: sum(1 for x in d['verdicts'] if x != '-')
            for r, d in subs.items()}
    print(f'{len(subs)} raters:', done)

if __name__ == '__main__':
    main()
