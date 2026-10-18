"""Deploy only the allowlisted public assets; credentials stay in Wrangler storage."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT.parent/'sallim-select-catalog'
ASSETS=('index.html','app.js','style.css','logo.png','catalog.json')

def prepare(target=None):
    target=Path(target) if target else ROOT/'artifacts/cloudflare-site'
    target.mkdir(parents=True,exist_ok=True)
    for name in ASSETS:
        shutil.copy2(PUBLIC/name,target/name)
    (target/'_headers').write_text('/catalog.json\n  Cache-Control: no-store\n/app.js\n  Cache-Control: no-cache\n')
    return target

def deploy():
    target=prepare()
    node='/Users/soomin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    cli=ROOT.parent/'deploy-tools/cloudflare/node_modules/wrangler/bin/wrangler.js'
    if not cli.is_file():raise RuntimeError('Cloudflare 배포 도구 설정이 필요합니다.')
    env={**os.environ,'CLOUDFLARE_ACCOUNT_ID':'0df18abdcbe310d55d00e5ce0be213ec','WRANGLER_SEND_METRICS':'false','CI':'true'}
    result=subprocess.run([node,str(cli),'pages','deploy',str(target),'--project-name=sallim-select','--branch=main'],
        cwd=ROOT,capture_output=True,text=True,timeout=100,env=env)
    if result.returncode:raise RuntimeError('Cloudflare 배포 인증 또는 업로드 실패')

if __name__=='__main__':
    try:
        deploy();print('Cloudflare 홈페이지 갱신 완료')
    except Exception as exc:
        print('Cloudflare 홈페이지 갱신 실패: '+type(exc).__name__)
        raise SystemExit(1) from None
