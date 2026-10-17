"""Local scheduler entry point with opt-in, locking and redacted private logs."""
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


def redact(text, values):
    for name, value in values.items():
        if value and any(word in name for word in ('KEY', 'TOKEN', 'SECRET')):
            text = text.replace(value, '[REDACTED]')
    return re.sub(r'(?i)(code|state|access_token|refresh_token|key)=([^\s&]+)',
                  r'\1=[REDACTED]', text)


def main():
    os.umask(0o077)
    values = dotenv_values(ROOT / '.env')
    if values.get('AUTOMATION_ENABLED', '').lower() != 'true':
        print('예약 실행 비활성 상태입니다.')
        return
    folder = ROOT / 'artifacts'
    folder.mkdir(exist_ok=True)
    with (folder / 'scheduler.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        args = [sys.executable, str(ROOT / 'main.py')]
        if '--check' in sys.argv:
            args.append('--check')
        now = datetime.now(ZoneInfo('Asia/Seoul'))
        slot = '18' if now.hour >= 18 else '09'
        run_env = {**os.environ, **{k:v for k,v in values.items() if v is not None}}
        run_env['AUTOMATION_RUN_KEY'] = now.strftime('%Y-%m-%d') + '-' + slot
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                                timeout=540, env=run_env)
        insights_output = ''
        if '--check' not in sys.argv and run_env.get('THREADS_ENABLED','').lower() == 'true':
            # Read-only collection cannot fail or repeat a public publication.
            try:
                insights = subprocess.run([sys.executable, str(ROOT / 'content_tools.py'), 'insights'],
                    cwd=ROOT, capture_output=True, text=True, timeout=90, env=run_env)
                insights_output = f'성과 수집 exit={insights.returncode}\n' + insights.stdout
            except subprocess.TimeoutExpired:
                insights_output = '성과 수집 시간 초과 (발행 결과 유지)\n'
        log = folder / 'scheduler.log'
        if log.exists() and log.stat().st_size > 1_000_000:
            log.replace(folder / 'scheduler.previous.log')
        stamp = datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
        with log.open('a') as out:
            os.chmod(log, 0o600)
            out.write(f'[{stamp}] exit={result.returncode}\n')
            out.write(redact(result.stdout + result.stderr + insights_output, values) + '\n')
        if result.returncode:
            print('실행 실패: 보호된 로컬 기록을 확인하세요.')
        else:
            print('실행 완료')
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
