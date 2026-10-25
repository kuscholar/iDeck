#!/usr/bin/env python3
"""Collect main debug-dylib relink inputs from an Xcode build log.

This copies object code; keep the output private until source/license review.
Use only a trusted build log. No build or signing is executed by this tool.
"""
from pathlib import Path
import shlex,shutil,json,hashlib,argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('build_log',type=Path)
parser.add_argument('output',type=Path)
options=parser.parse_args()
out=options.output.resolve();out.mkdir(parents=True,exist_ok=False)
log=options.build_log.read_text()
lines=[x.strip() for x in log.splitlines() if '/clang++ ' in x and x.rstrip().endswith('/Madeira.debug.dylib')]
assert len(lines)==1
args=shlex.split(lines[0])[1:]
search=[Path(x[2:]) for x in args if x.startswith('-L')]
manifest=[]
def stage(src,rel):
 dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 manifest.append({'path':rel,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
 return '@ROOT@/'+rel
new=[];i=0
while i<len(args):
 a=args[i]
 if a.startswith('-L') or a.startswith('-F'):i+=1;continue
 if a=='-isysroot':new.extend([a,'@SDK@']);i+=2;continue
 if a=='-filelist':
  objs=Path(args[i+1]).read_text().splitlines()
  for n,obj in enumerate(objs):new.append(stage(Path(obj.strip('"')),f'objects/{n:04d}-{Path(obj.strip(chr(34))).name}'))
  i+=2;continue
 if a=='-Xlinker' and args[i+1] in ['-object_path_lto','-dependency_info','-add_ast_path','-map']:
  assert args[i+2]=='-Xlinker';i+=4;continue
 if a=='-o':new.extend(['-o','@ROOT@/Madeira.debug.dylib']);i+=2;continue
 if a.startswith('-l') and a not in ['-lc++','-lz','-lsqlite3','-llzma']:
  name='lib'+a[2:]+'.a';found=next((p/name for p in search if (p/name).is_file()),None)
  assert found, name
  new.append(stage(found,'libraries/'+name));i+=1;continue
 new.append(a);i+=1
(out/'link-args.json').write_text(json.dumps(new,indent=2)+'\n')
(out/'INPUTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'relink.py').write_text('''#!/usr/bin/env python3
import json,subprocess
#!/usr/bin/env python3
"""Collect main debug-dylib relink inputs from an Xcode build log.

This copies object code; keep the output private until source/license review.
Use only a trusted build log. No build or signing is executed by this tool.
"""
from pathlib import Path
root=Path(__file__).resolve().parent
sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
clang=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip()
args=[x.replace('@ROOT@',str(root)).replace('@SDK@',sdk) for x in json.loads((root/'link-args.json').read_text())]
subprocess.run([clang]+args,check=True)
print('Relink complete. Copy Madeira.debug.dylib into a disposable app copy and re-sign.')
''')
print('Staged',len(manifest),'link inputs')
