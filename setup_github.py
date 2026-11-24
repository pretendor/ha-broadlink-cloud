"""Fill in GitHub metadata before first publication (no online access needed).

Usage: python setup_github.py --owner GITHUB_USERNAME --repo ha-broadlink-cloud
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_DEFAULT = 'ha-broadlink-cloud'
PLACEHOLDER_OWNER = '__GITHUB_OWNER__'
PLACEHOLDER_REPO = '__GITHUB_REPO__'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True, help='Personal GitHub account name')
    parser.add_argument('--repo', default=REPO_DEFAULT, help='GitHub repository name')
    args = parser.parse_args()
    owner, repo = args.owner.strip(), args.repo.strip()
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', owner):
        parser.error('Invalid GitHub username/owner')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or repo in {'.', '..'}:
        parser.error('Invalid GitHub repository name')

    manifest_path = ROOT / 'custom_components' / 'broadlink_cloud' / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update({
        'documentation': f'https://github.com/{owner}/{repo}#readme',
        'issue_tracker': f'https://github.com/{owner}/{repo}/issues',
        'codeowners': [f'@{owner}'],
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    for rel in ('README.md', 'PUBLISHING.md'):
        path = ROOT / rel
        content = path.read_text(encoding='utf-8')
        content = content.replace(PLACEHOLDER_OWNER, owner).replace(PLACEHOLDER_REPO, repo)
        content = content.replace('YOUR_GITHUB_USERNAME/ha-broadlink-cloud', f'{owner}/{repo}')
        path.write_text(content, encoding='utf-8')

    print(f'GitHub metadata updated: https://github.com/{owner}/{repo}')
    print('Next: create an empty PUBLIC repository and publish this folder.')
    print('Never commit Home Assistant storage, password files, session tokens or device dumps.')


if __name__ == '__main__':
    main()
