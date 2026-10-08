"""Fetch original public datasets; never replace failed downloads with synthetic data."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
import requests

ROOT = Path(__file__).resolve().parents[1]
X5 = {
    'uplift_train.csv.gz': '2720bbb659daa9e0989b2777b6a42d19',
    'clients.csv.gz': 'b9cdeb2806b732771de03e819b3354c5',
    'purchases.csv.gz': '48d2de13428e24e8b61d66fef02957a8',
}

def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    partial = path.with_suffix(path.suffix + '.partial')
    with requests.get(url, stream=True, timeout=(30, 120)) as r:
        r.raise_for_status()
        with partial.open('wb') as out:
            for chunk in r.iter_content(2**20):
                out.write(chunk)
    partial.replace(path)

def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', choices=['olist', 'x5', 'all'], default='all')
    parser.add_argument('--x5-full', action='store_true', help='Also fetch 647 MB historical purchases')
    args = parser.parse_args()
    entries = []
    if args.dataset in ('olist', 'all'):
        url = 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce'
        archive = ROOT / 'data/raw/olist.zip'
        download(url, archive)
        with zipfile.ZipFile(archive) as z:
            destination = (ROOT / 'data/raw/olist').resolve()
            for member in z.infolist():
                target = (destination / member.filename).resolve()
                if not target.is_relative_to(destination):
                    raise ValueError('Unsafe ZIP member')
            z.extractall(destination)
        entries.append({'file': 'olist.zip', 'source': url, 'sha256': digest(archive)})
    if args.dataset in ('x5', 'all'):
        for name, md5 in X5.items():
            if name == 'purchases.csv.gz' and not args.x5_full:
                continue
            url = 'https://sklift.s3.eu-west-2.amazonaws.com/' + name
            path = ROOT / 'data/raw/x5' / name
            download(url, path)
            if digest(path, 'md5') != md5:
                raise ValueError(f'Upstream checksum mismatch: {name}')
            entries.append({'file': name, 'source': url, 'sha256': digest(path), 'upstream_md5': md5})
    manifest = ROOT / 'data/manifest.json'
    existing = json.loads(manifest.read_text())['files'] if manifest.exists() else []
    by_file = {e['file']: e for e in existing + entries}
    manifest.write_text(json.dumps({'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                                    'files': list(by_file.values())}, indent=2), encoding='utf-8')
    print('Verified:', ', '.join(e['file'] for e in entries), flush=True)

if __name__ == '__main__':
    main()
