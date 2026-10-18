"""Start or reuse our loopback server, then open its read-only dashboard."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent


def ours(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/health',timeout=1) as response:
            return response.read(100)==b'sallim-operator-v1'
    except Exception:return False


def ensure_server():
    folder=ROOT/'artifacts';folder.mkdir(exist_ok=True);state=folder/'operator-runtime.json'
    try:
        port=json.loads(state.read_text())['port']
        if isinstance(port,int) and 8876<=port<=8885 and ours(port):return port
    except (OSError,ValueError,KeyError,TypeError):pass
    for port in range(8876,8886):
        if ours(port):return port
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',port))
            except OSError:continue
        log=folder/'operator-server.log'
        fd=os.open(log,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        with os.fdopen(fd,'ab') as out:
            subprocess.Popen([sys.executable,str(ROOT/'operator_dashboard.py'),'--port',str(port)],cwd=ROOT,stdout=out,stderr=out,start_new_session=True)
        for attempt in range(30):
            if ours(port):
                state.write_text(json.dumps({'port':port}));state.chmod(0o600)
                return port
            time.sleep(.1)
    raise RuntimeError('관리 화면을 실행할 로컬 포트가 없습니다.')

if __name__=='__main__':
    os.umask(0o077)
    port=ensure_server()
    subprocess.run(['/usr/bin/open',f'http://127.0.0.1:{port}/'],check=True)
