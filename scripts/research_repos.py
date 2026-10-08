"""Record live GitHub metadata, inspected paths and immutable source revisions."""
from pathlib import Path
import json
import requests

ROOT = Path(__file__).resolve().parents[1]
REPOS = {
    'maks-sh/scikit-uplift': ['sklift/datasets/datasets.py', 'sklift/metrics/metrics.py', 'LICENSE'],
    'uber/causalml': ['README.md', 'LICENSE'],
    'feldlime/X5RetailHeroUplift': ['load_and_prepare.py', 'features', 'LICENSE'],
    'michaelf108/ecommerce-analytics-dbt': ['README.md', 'models', 'LICENSE'],
    'miguelvotre/olist-ecommerce-analytics': ['README.md', 'dbt', 'LICENSE'],
    'Ucazin/olist-ecommerce-analytics': ['README.md', 'src/generate_synthetic_olist.py', 'LICENSE'],
}

def main():
    out = ROOT / 'docs/research'
    out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers['User-Agent'] = 'CommerceIQ-public-research'
    records = []
    for repo, paths in REPOS.items():
        r = session.get(f'https://api.github.com/repos/{repo}', timeout=30)
        if r.status_code == 404:
            records.append({'repository': repo, 'status': 'Unavailable via GitHub API; search preview only'})
            continue
        r.raise_for_status()
        meta = r.json()
        commit = session.get(f'https://api.github.com/repos/{repo}/commits/{meta["default_branch"]}', timeout=30)
        commit.raise_for_status()
        sha = commit.json()['sha']
        record = {'repository': repo, 'url': meta['html_url'], 'stars': meta['stargazers_count'],
                  'pushed_at': meta['pushed_at'], 'archived': meta['archived'],
                  'license': (meta.get('license') or {}).get('spdx_id'), 'revision': sha,
                  'inspected': []}
        for path in paths:
            r = session.get(f'https://api.github.com/repos/{repo}/contents/{path}', params={'ref': sha}, timeout=30)
            record['inspected'].append({'path': path, 'status': r.status_code,
                                       'permalink': f'https://github.com/{repo}/tree/{sha}/{path}'})
            if r.ok and isinstance(r.json(), dict) and r.json().get('download_url'):
                source = session.get(r.json()['download_url'], timeout=30)
                source.raise_for_status()
                (out / (repo.replace('/', '__') + '__' + path.replace('/', '__'))).write_bytes(source.content)
        records.append(record)
        print(repo, record['stars'], record['license'], flush=True)
        (out / 'repositories.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    (out / 'repositories.json').write_text(json.dumps(records, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
