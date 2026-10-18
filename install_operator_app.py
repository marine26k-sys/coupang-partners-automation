"""Install a local macOS launcher for the read-only operations dashboard."""
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent
APP_NAME='살림셀렉트 관리'


def install(desktop=None):
    desktop=Path(desktop) if desktop else Path.home()/'Desktop'
    app=desktop/(APP_NAME+'.app');contents=app/'Contents'
    if app.exists():
        try:existing=plistlib.loads((contents/'Info.plist').read_bytes())
        except (OSError,ValueError):raise ValueError('동명의 기존 앱이 있어 덮어쓰지 않습니다.')
        if existing.get('CFBundleIdentifier')!='local.sallim.operator':raise ValueError('동명의 다른 앱이 있어 덮어쓰지 않습니다.')
    (contents/'MacOS').mkdir(parents=True,exist_ok=True);(contents/'Resources').mkdir(exist_ok=True)
    plist={'CFBundleName':APP_NAME,'CFBundleDisplayName':APP_NAME,'CFBundleIdentifier':'local.sallim.operator','CFBundleVersion':'1','CFBundleShortVersionString':'1.0','CFBundlePackageType':'APPL','CFBundleExecutable':'SallimOperator','LSUIElement':True,'NSHighResolutionCapable':True}
    icon=ROOT.parent/'sallim-select-catalog/logo.png'
    if icon.exists():
        iconset=ROOT/'artifacts/operator.iconset';iconset.mkdir(parents=True,exist_ok=True)
        for size in (16,32,128,256,512):
            for multiplier,suffix in ((1,''),(2,'@2x')):
                subprocess.run(['/usr/bin/sips','-z',str(size*multiplier),str(size*multiplier),str(icon),'--out',str(iconset/f'icon_{size}x{size}{suffix}.png')],check=True,capture_output=True)
        result=subprocess.run(['/usr/bin/iconutil','-c','icns',str(iconset),'-o',str(contents/'Resources/operator.icns')],capture_output=True)
        if result.returncode==0:plist['CFBundleIconFile']='operator.icns'
    (contents/'Info.plist').write_bytes(plistlib.dumps(plist))
    executable=contents/'MacOS/SallimOperator'
    executable.write_text('#!/bin/sh\nexec '+shlex.quote(str(ROOT/'.venv/bin/python'))+' '+shlex.quote(str(ROOT/'operator_launcher.py'))+'\n')
    executable.chmod(0o755)
    return app

if __name__=='__main__':print('설치 완료: '+str(install()))
