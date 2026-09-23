"""Assemble a deployable, ROM-free static site with provenance and notices."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

parser=argparse.ArgumentParser()
parser.add_argument('--desktop',type=Path,required=True)
parser.add_argument('--emscripten',type=Path,required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parent
public=root/'public'
allowed={'build-info.json','compact.html','embed.html','index.html','integrated.html','integrated.js','LICENSE.txt','ngpcraft.mjs','ngpcraft.wasm','player.js','THIRD_PARTY_NOTICES.txt'}
unexpected={p.name for p in public.iterdir()}-allowed
if unexpected:
    raise SystemExit('Unexpected public files; review before packaging: '+', '.join(sorted(unexpected)))
shutil.copyfile(root/'LICENSE',public/'LICENSE.txt')
parts=['NgpCraft Web Player\n\nThe player compiles the NgpCraft desktop C++ core and its clean-room HLE BIOS directly. No Libretro, RetroArch, Qt, SDL or proprietary BIOS is included.\n\nCompiler runtime notices follow.\n']
for label,path in [
    ('Emscripten', 'LICENSE'),
    ('musl libc', 'system/lib/libc/musl/COPYRIGHT'),
    ('LLVM libc++', 'system/lib/libcxx/LICENSE.TXT'),
    ('LLVM libc++abi', 'system/lib/libcxxabi/LICENSE.TXT'),
    ('LLVM compiler-rt', 'system/lib/compiler-rt/LICENSE.TXT'),
]:
    parts.extend(['\n\n===== '+label+' =====\n', (args.emscripten/path).read_text(encoding='utf-8')])
parts.append('\n\n===== dlmalloc =====\nDoug Lea malloc (dlmalloc), public domain / CC0. Emscripten modifications covered by its license above. See https://gee.cs.oswego.edu/dl/html/malloc.html\n')
(public/'THIRD_PARTY_NOTICES.txt').write_bytes(''.join(parts).encode('utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
sources=list((args.desktop/'cpp/src').glob('*.cpp'))+list((args.desktop/'cpp/src').glob('*.hpp'))+list((args.desktop/'cpp/include').glob('*.h'))+[args.desktop/'hle_bios/bios_hle.bin']
commit=subprocess.run(['git','-C',str(args.desktop),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
manifest={'desktop_commit':commit,'source_sha256':{p.relative_to(args.desktop).as_posix():sha(p) for p in sources},'files':{p.name:{'bytes':p.stat().st_size,'gzip_bytes':len(gzip.compress(p.read_bytes(),mtime=0)),'sha256':sha(p)} for p in public.iterdir() if p.is_file() and p.name!='build-info.json'}}
(public/'build-info.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
dist=root/'dist'
dist.mkdir(exist_ok=True)
with zipfile.ZipFile(dist/'NgpCraft-Web-Player.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in public.iterdir():
        if p.is_file(): z.write(p,p.name)
    z.write(root/'README.md','README.md')
    z.write(root/'VERIFICATION.md','VERIFICATION.md')
    z.write(root/'INTEGRATION.md','INTEGRATION.md')
runtime=['ngpcraft.wasm','ngpcraft.mjs','player.js']
print(json.dumps({'runtime_bytes':sum(manifest['files'][p]['bytes'] for p in runtime),'runtime_gzip_bytes':sum(manifest['files'][p]['gzip_bytes'] for p in runtime),'integrated_runtime_gzip_bytes':sum(manifest['files'][p]['gzip_bytes'] for p in runtime+['integrated.js']),'zip_bytes':(dist/'NgpCraft-Web-Player.zip').stat().st_size},indent=2))
