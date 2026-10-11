"""Install optional Manim on Debian 13 without root or unchecked artifacts."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PACKAGES=('libpango1.0-dev libglib2.0-dev libgio-2.0-dev libglib2.0-dev-bin '
          'libharfbuzz-dev libfreetype-dev libfontconfig-dev libfribidi-dev '
          'libcairo2-dev libpixman-1-dev libpng-dev libffi-dev libpcre2-dev '
          'libgraphite2-dev libthai-dev libdatrie-dev libgirepository-2.0-dev '
          'libsysprof-capture-4-dev zlib1g-dev libmount-dev libselinux1-dev '
          'libsepol-dev libblkid-dev libbz2-dev libx11-dev libxext-dev '
          'libxrender-dev libxcb1-dev libxcb-render0-dev libxcb-shm0-dev '
          'libxau-dev libxdmcp-dev x11proto-dev xorg-sgml-doctools xtrans-dev libxft-dev').split()


def install(refresh=False):
    if 'VERSION_CODENAME=trixie' not in Path('/etc/os-release').read_text():
        raise RuntimeError('本辅助安装器针对Debian13；其他系统按Manim官方文档安装Cairo/Pango开发依赖。')
    base=ROOT/'.system';state=base/'apt';debs=base/'debs';local=base/'root'
    for p in [state/'lists/partial',state/'cache/archives/partial',debs,local]:p.mkdir(parents=True,exist_ok=True)
    source=state/'sources.list'
    expected='deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main\n'
    if source.exists() and source.read_text()!=expected:raise RuntimeError('保留现有自定义APT来源，请另行检查。')
    source.write_text(expected)
    apt=['apt-get','-o',f'Dir::State::Lists={state}/lists','-o',f'Dir::Cache={state}/cache',
         '-o',f'Dir::Etc::sourcelist={source}','-o','Dir::Etc::sourceparts=-',
         '-o','APT::Sandbox::User='+os.getenv('USER','agent'),'-o','APT::Update::Error-Mode=any']
    missing=[p for p in PACKAGES if not list(debs.glob(p+'_*.deb'))]
    if refresh or missing:
        subprocess.run([*apt,'update'],check=True)
        subprocess.run([*apt,'download',*(PACKAGES if refresh else missing)],cwd=debs,check=True)
    for package in debs.glob('*.deb'):subprocess.run(['dpkg-deb','-x',str(package),str(local)],check=True)
    for link in (local/'usr/lib/x86_64-linux-gnu').glob('*.so'):
        if link.is_symlink() and not link.exists():
            target=os.readlink(link);system=Path('/usr/lib/x86_64-linux-gnu')/target
            if system.exists():
                destination=link.parent/target
                if not destination.exists():destination.symlink_to(system)
    build_env=os.environ.copy()
    build_env.update(CC='gcc',CXX='g++',PKG_CONFIG_PATH=':'.join(str(local/x) for x in ['usr/lib/x86_64-linux-gnu/pkgconfig','usr/share/pkgconfig','usr/lib/pkgconfig']),PKG_CONFIG_SYSROOT_DIR=str(local))
    build_env['CFLAGS']=subprocess.check_output(['pkg-config','--cflags','pangocairo'],env=build_env,text=True).strip()
    build_env['LDFLAGS']=subprocess.check_output(['pkg-config','--libs','pangocairo'],env=build_env,text=True).strip()
    subprocess.run([sys.executable,'-m','pip','install','-r',str(ROOT/'requirements-manim.txt')],env=build_env,check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');a=p.parse_args();install(a.refresh)
