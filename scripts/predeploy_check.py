#!/usr/bin/env python3
"""Pre-deploy structural control for directcare-home.
Replaces the hand-maintained robots.txt disallow list as the PRIMARY defence.
Fails (exit 1) if any DEPLOYABLE html would ship unrendered template content.
Content-based, not name-based: filenames like 'testosterone' must never trip it."""
import re,glob,io,sys,os
ign=[l.strip() for l in io.open('.vercelignore') if l.strip() and not l.startswith('#')]
def ignored(f): return any(f==i or f.startswith(i.rstrip('/')+'/') for i in ign)
TOKEN=re.compile(r'\{\{\s*[A-Z][A-Z0-9_]{1,}\s*\}\}')     # {{TITLE}} style
NAME =re.compile(r'(^|/)_')                                # leading-underscore convention only
fail=[]
for f in sorted(glob.glob('**/*.html',recursive=True)):
    if ignored(f): continue
    s=io.open(f,encoding='utf-8',errors='ignore').read()
    toks=sorted(set(TOKEN.findall(s)))
    if toks: fail.append((f,'PLACEHOLDER_TOKENS',', '.join(toks[:4])))
    elif NAME.search(f): fail.append((f,'UNDERSCORE_PREFIX','partial/template naming convention'))
if fail:
    print("PRE-DEPLOY CHECK: FAIL")
    for f,why,d in fail: print(f"  {why:<20} {f}  [{d}]")
    sys.exit(1)
print(f"PRE-DEPLOY CHECK: PASS — no deployable file carries template tokens or _ prefix")
sys.exit(0)
