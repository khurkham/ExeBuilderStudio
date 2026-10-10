"""Official release discovery, cancellable streaming and local tool detection."""
import gzip, zlib, hashlib, html, json, os, platform, re, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from html.parser import HTMLParser
APP_VERSION = '1.0.0'
BUILD_REVISION = '2026.10.10.4'
# Publisher configures this before building. End users do not set an update source.
UPDATE_REPOSITORY = 'khurkham/ExeBuilderStudio'
NAMES = {'java':'Java (Temurin JDK)', 'launch4j':'Launch4j', 'inno':'Inno Setup', 'python':'Python', 'pyinstaller':'PyInstaller', 'sdk':'Windows SDK / SignTool', 'studio':'ExeBuilderStudio'}
class Cancelled(Exception): pass

def app_data():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'ExeBuilderStudio'

def version_key(value):
    parts = [int(x) for x in re.findall(r'\d+', str(value))]
    while parts and parts[-1] == 0: parts.pop()
    return tuple(parts)

def validate_url(url):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password:
        raise ValueError('Download source must use HTTPS.')
    return url

class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

OPENER=build_opener(HTTPSHandler(),HTTPSRedirects())
def open_url(url):
    validate_url(url)
    response=OPENER.open(Request(url,headers={'User-Agent':'ExeBuilderStudio/1.0','Accept':'application/json,text/html,*/*','Accept-Encoding':'identity'}),timeout=20)
    validate_url(response.geturl())
    return response

def fetch(url,as_json=False):
    with open_url(url) as r:
        encoding=r.headers.get('Content-Encoding','').lower()
        data=r.read(8*1024*1024+1)
    if len(data)>8*1024*1024:raise ValueError('Release metadata is too large.')
    if encoding=='gzip' or data[:2]==b'\x1f\x8b':data=gzip.decompress(data)
    elif encoding=='deflate':data=zlib.decompress(data)
    if len(data)>8*1024*1024:raise ValueError('Release metadata is too large.')
    text=data.decode('utf-8')
    return json.loads(text) if as_json else text

class Links(HTMLParser):
    def __init__(self,text):
        super().__init__();self.links=[];self.current=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.current=[dict(attrs).get('href',''),'']
    def handle_data(self,data):
        if self.current:self.current[1]+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.current:self.links.append(tuple(self.current));self.current=None

def arch():
    machine=os.environ.get('PROCESSOR_ARCHITEW6432',os.environ.get('PROCESSOR_ARCHITECTURE',platform.machine())).lower()
    return 'aarch64' if 'arm' in machine else 'x64' if '64' in machine else 'x86'

def github_release(repo):
    repo=repo.strip().removesuffix('.git').rstrip('/')
    if repo.startswith('https://github.com/'):repo=repo[len('https://github.com/'):].split('/releases')[0]
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('The publisher update repository is invalid.')
    release=fetch('https://api.github.com/repos/'+repo+'/releases/latest',True)
    assets=[a for a in release.get('assets',[]) if a['name'].lower().endswith('.exe') and 'setup' in a['name'].lower()]
    if not assets:raise ValueError('The latest release needs an ExeBuilderStudio_Setup.exe asset.')
    asset=next((a for a in assets if a['name'].lower()=='exebuilderstudio_setup.exe'),assets[0])
    digest=asset.get('digest') or ''
    checksum=digest[7:] if digest.startswith('sha256:') else ''
    if not checksum:raise ValueError('GitHub release asset has no SHA-256 digest. Re-upload the Setup asset.')
    revision=re.search(r'Build revision:\s*([0-9.]+)',release.get('body') or '')
    return dict(build_revision=revision[1].rstrip('.') if revision else '',version=release['tag_name'].lstrip('vV'),url=asset['browser_download_url'],name=asset['name'],sha256=checksum,kind='exe',publisher='')

def resolve_release(key,repo='',java_major='25'):
    if key=='studio':return github_release(repo)
    if key=='java':
        rows=fetch(f'https://api.adoptium.net/v3/assets/latest/{int(java_major)}/hotspot?architecture={arch()}&image_type=jdk&os=windows&vendor=eclipse',True)
        if not rows:raise ValueError('No Java release for this architecture.')
        row=rows[0];package=row['binary']['package']
        return dict(version=row['version'].get('openjdk_version',row['version']['semver']),url=package['link'],name=package['name'],sha256=package['checksum'],kind='zip')
    if key=='inno':
        base='https://jrsoftware.org/isdl.php';links=Links(fetch(base)).links
        suffix='x86' if arch()=='x86' else 'x64'
        urls=[urljoin(base,u) for u,_ in links if re.search(r'innosetup-[\d.]+-'+suffix+r'\.exe$',u)]
        if not urls:urls=[urljoin(base,u) for u,_ in links if re.search(r'innosetup-[\d.]+\.exe$',u)]
        if not urls:raise ValueError('Cannot find Inno Setup installer on the official page.')
        url=max(urls,key=lambda x:version_key(Path(urlparse(x).path).name));name=Path(urlparse(url).path).name
        return dict(version=re.search(r'innosetup-([\d.]+)',name)[1].rstrip('.'),url=url,name=name,kind='exe',publisher='Pyrsys')
    if key=='python':
        links=Links(fetch('https://www.python.org/downloads/windows/')).links
        suffix={'x64':'amd64','x86':'win32','aarch64':'arm64'}[arch()]
        urls=[u for u,t in links if re.search(r'/python-\d+\.\d+\.\d+-'+suffix+r'\.exe$',u) and urlparse(u).hostname=='www.python.org']
        if not urls:raise ValueError('Cannot find a stable Windows Python installer.')
        url=max(urls,key=lambda x:version_key(Path(urlparse(x).path).name));name=Path(urlparse(url).path).name
        return dict(version=re.search(r'python-([\d.]+)',name)[1],url=url,name=name,kind='exe',publisher='Python Software Foundation')
    if key=='launch4j':
        text=fetch('https://sourceforge.net/projects/launch4j/rss?path=/launch4j-3')
        urls=re.findall(r'https://sourceforge\.net/projects/launch4j/files/launch4j-3/[\d.]+/launch4j-[\d.]+-win32\.zip/download',html.unescape(text))
        if not urls:raise ValueError('Cannot find the Launch4j Windows ZIP in the official release feed.')
        src=max(urls,key=version_key);url=src.replace('https://sourceforge.net/projects/launch4j/files/','https://downloads.sourceforge.net/project/launch4j/').removesuffix('/download')
        name=Path(urlparse(url).path).name
        return dict(version=re.search(r'launch4j-([\d.]+)-',name)[1],url=url,name=name,kind='zip')
    if key=='sdk':
        base='https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads'
        text=fetch(base);links=Links(text).links
        urls=[u for u,t in links if t.strip().lower()=='installer' and urlparse(u).hostname=='go.microsoft.com']
        if not urls:raise ValueError('Cannot find the stable SDK installer on the official Microsoft page.')
        version=re.search(r'10\.0\.\d+\.\d+',text)
        return dict(version=version[0] if version else 'Latest',url=urls[0],name='winsdksetup.exe',kind='exe',publisher='Microsoft')
    raise ValueError('Unknown tool: '+key)

def download(release,directory,progress=lambda done,total:None,cancel=lambda:False):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    name=release['name']
    if Path(name).name!=name or '/' in name or '\\' in name:raise ValueError('Invalid release filename.')
    target=directory/name;partial=target.with_name(name+'.part');digest=hashlib.sha256();done=0
    try:
        with open_url(release['url']) as response, partial.open('wb') as output:
            content_type=response.headers.get('Content-Type','').lower()
            if 'text/html' in content_type:raise ValueError('Server returned a web page instead of an installer.')
            total=int(response.headers.get('Content-Length','0'));progress(0,total)
            while True:
                if cancel():raise Cancelled()
                chunk=response.read(128*1024)
                if not chunk:break
                output.write(chunk);digest.update(chunk);done+=len(chunk);progress(done,total)
        if cancel():raise Cancelled()
        if not done or (total and done!=total):raise ValueError('Download incomplete. Please retry.')
        if release.get('sha256') and digest.hexdigest().lower()!=release['sha256'].lower():raise ValueError('SHA-256 checksum mismatch.')
        if release['kind']=='zip':
            if not zipfile.is_zipfile(partial):raise ValueError('Downloaded file is not a ZIP archive.')
            with zipfile.ZipFile(partial) as z:
                if z.testzip():raise ValueError('ZIP archive is damaged.')
        else:
            with partial.open('rb') as check:
                if check.read(2)!=b'MZ':raise ValueError('Downloaded file is not a Windows executable.')
        partial.replace(target);return target
    except Exception:
        partial.unlink(missing_ok=True);raise

def extract_tool(path,key,version):
    root=app_data()/'tools'/key;root.mkdir(parents=True,exist_ok=True)
    target=root/re.sub(r'[^A-Za-z0-9_.-]','_',version)
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        base=Path(tmp)
        with zipfile.ZipFile(path) as z:
            if sum(x.file_size for x in z.infolist())>2*1024**3:raise ValueError('ZIP archive is too large.')
            for item in z.infolist():
                normalized=item.filename.replace('\\','/')
                if normalized.startswith('/') or '..' in Path(normalized).parts or ':' in normalized:raise ValueError('Unsafe archive path.')
                if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive contains a symbolic link.')
            z.extractall(base)
        pattern='java.exe' if key=='java' else 'launch4jc.exe'
        executable=next(base.rglob(pattern),None)
        if executable is None:raise ValueError('Archive does not contain '+pattern)
        if target.exists():
            suffix=1
            while target.with_name(target.name+f'-{suffix}').exists():suffix+=1
            target=target.with_name(target.name+f'-{suffix}')
        relative=executable.relative_to(base);shutil.move(str(base),str(target))
    return str(target/relative)

def run_capture(args,timeout=5):
    p=subprocess.run(args,capture_output=True,text=True,errors='replace',timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:raise ValueError((p.stdout+p.stderr).strip() or 'Command failed')
    return (p.stdout+p.stderr).strip()

def executable_version(path):
    if os.name!='nt':return ''
    # Argument is supplied through the environment, never embedded in PowerShell code.
    env=os.environ.copy();env['EBS_TOOL_PATH']=str(path)
    result=subprocess.run([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-Command','(Get-Item -LiteralPath $env:EBS_TOOL_PATH).VersionInfo.ProductVersion'],env=env,capture_output=True,text=True,errors='replace',timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return result.stdout.strip()

def normalize_tool_path(value):
    return os.path.expandvars(os.path.expanduser(str(value).strip().strip('"')))

def registered_tool_paths(key):
    """Read installed locations without scanning drives or contacting the network."""
    try: import winreg
    except ImportError: return []
    names={'inno':('inno setup', 'ISCC.exe'), 'launch4j':('launch4j','launch4jc.exe'),
           'python':('python','python.exe'), 'java':('jdk','bin/java.exe')}
    if key not in names: return []
    needle,exe=names[key]; paths=[]
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root,winreg.EnumKey(root,index)) as item:
                                name=str(winreg.QueryValueEx(item,'DisplayName')[0]).lower()
                                if needle in name:
                                    location=normalize_tool_path(winreg.QueryValueEx(item,'InstallLocation')[0])
                                    if location: paths.append(str(Path(location)/exe))
                        except OSError: continue
            except OSError: continue
    if key=='python':
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive,r'SOFTWARE\Python',0,winreg.KEY_READ|view) as root:
                        for i in range(winreg.QueryInfoKey(root)[0]):
                            with winreg.OpenKey(root,winreg.EnumKey(root,i)) as company:
                                for j in range(winreg.QueryInfoKey(company)[0]):
                                    try:
                                        with winreg.OpenKey(company,winreg.EnumKey(company,j)+r'\InstallPath') as install:
                                            try: paths.append(str(winreg.QueryValueEx(install,'ExecutablePath')[0]))
                                            except OSError: paths.append(str(Path(winreg.QueryValueEx(install,'')[0])/'python.exe'))
                                    except OSError: continue
                except OSError: continue
    return paths

def detect_tool(key,configured=''):
    from backend import java_candidates
    from signing import detect_signtool
    configured=normalize_tool_path(configured)
    if key=='studio':return {'path':sys.executable,'version':APP_VERSION,'build_revision':BUILD_REVISION,'found':True}
    if key=='pyinstaller':
        if not configured or not Path(configured).is_file():
            return {'found':False,'path':configured,'version':'','error':'Select an installed Python interpreter first.'}
        # A missing module is different from an interpreter that cannot be queried.
        script='import importlib.util; s=importlib.util.find_spec("PyInstaller"); print("EBS_MISSING" if s is None else __import__("PyInstaller").__version__)'
        try: v=run_capture([configured,'-c',script],timeout=3)
        except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
            return {'found':False,'path':configured,'version':'','error':str(exc)}
        return {'found':v!='EBS_MISSING','path':configured,'version':'' if v=='EBS_MISSING' else v}
    names={'launch4j':'launch4jc.exe','inno':'ISCC.exe','python':'python.exe'}
    def probe(path,timeout=3):
        try:
            if key=='python':v=run_capture([path,'-c','import sys; print(".".join(map(str,sys.version_info[:3])))'],timeout=timeout)
            elif key=='java':v=run_capture([path,'-version'],timeout=timeout)
            else:v=executable_version(path)
            return {'found':True,'path':path,'version':v}
        except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
            # Preserve presence; show inability to verify rather than "not installed".
            return {'found':True,'path':path,'version':'','error':str(exc)}
    if configured and Path(configured).is_file():
        if key in ('inno','launch4j','sdk') and Path(configured).name.lower()!= {'inno':'iscc.exe','launch4j':'launch4jc.exe','sdk':'signtool.exe'}[key]:
            return {'found':False,'path':configured,'version':'','error':'Select '+{'inno':'ISCC.exe (compiler, not ISIDE.exe)','launch4j':'launch4jc.exe','sdk':'signtool.exe'}[key]}
        return probe(configured)
    paths=[]
    if key=='java':paths+=java_candidates()
    if key=='sdk':paths+=[detect_signtool()]
    if key in names:
        found=shutil.which(names[key])
        if found:paths.append(found)
    paths+=registered_tool_paths(key)
    roots=[Path(os.environ.get('ProgramFiles','C:/Program Files')),Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)')),Path(os.environ.get('LOCALAPPDATA',str(Path.home())))]
    if key=='inno':paths += [str(root/sub/f'Inno Setup {n}'/'ISCC.exe') for root in roots for sub in ('','Programs') for n in [7,6,5]]
    if key=='launch4j':paths += [str(root/sub/'Launch4j/launch4jc.exe') for root in roots for sub in ('','Programs')]
    if key=='python':
        for root in roots:
            paths += [str(p) for pattern in ['Programs/Python/Python*/python.exe','Python/pythoncore-*/python.exe','Python*/python.exe'] for p in root.glob(pattern)]
    pattern=names.get(key,'java.exe' if key=='java' else '')
    if pattern:paths += [str(p) for p in sorted((app_data()/'tools'/key).glob('**/'+pattern),reverse=True)]
    # One bounded probe, no serial five-second queries for every Python installation.
    for path in dict.fromkeys(paths):
        if path and Path(path).is_file() and 'windowsapps' not in str(path).lower():return probe(path)
    return {'found':False,'path':'','version':''}

def windows_powershell():
    system=os.environ.get('SystemRoot',os.environ.get('WINDIR','C:/Windows'))
    candidate=Path(system)/'System32/WindowsPowerShell/v1.0/powershell.exe'
    if candidate.is_file():return str(candidate)
    fallback=shutil.which('powershell.exe')
    if fallback:return fallback
    raise FileNotFoundError('Windows PowerShell was not found: '+str(candidate))

def verify_publisher(path,publisher):
    if os.name!='nt':raise ValueError('Install tools on Windows.')
    if not Path(path).is_file():raise FileNotFoundError('Downloaded installer was not found: '+str(path))
    env=os.environ.copy();env['EBS_INSTALLER_PATH']=str(path);env['EBS_EXPECTED_PUBLISHER']=publisher
    script='$s=Get-AuthenticodeSignature -LiteralPath $env:EBS_INSTALLER_PATH; if ($s.Status -ne "Valid" -or $s.SignerCertificate.Subject -notlike ("*"+$env:EBS_EXPECTED_PUBLISHER+"*")) {throw "Installer signature or publisher verification failed"}'
    p=subprocess.run([windows_powershell(),'-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,text=True,errors='replace',timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:raise ValueError(p.stderr.strip() or 'Installer verification failed.')
