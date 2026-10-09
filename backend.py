from pathlib import Path
import os, re, shutil, sys, xml.etree.ElementTree as ET
from PIL import Image, ImageOps

def require_file(value, suffix=None):
    p=Path(value).expanduser().resolve()
    if not p.is_file() or (suffix and p.suffix.lower()!=suffix):
        raise ValueError(f'Invalid file: {p}')
    return p

def safe_name(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}',name) or name.endswith(('.', ' ')):
        raise ValueError('Use an English application name: letters, numbers, spaces, _ or -')
    if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('Reserved Windows name')
    return name

def convert_icon(source, target):
    with Image.open(require_file(source)) as img:
        img=ImageOps.exif_transpose(img).convert('RGBA')
        img.thumbnail((256,256),Image.Resampling.LANCZOS)
        square=Image.new('RGBA',(256,256)); square.alpha_composite(img,((256-img.width)//2,(256-img.height)//2))
        square.save(target,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])

def java_candidates():
    result=[]
    if shutil.which('java'): result.append(shutil.which('java'))
    if os.environ.get('JAVA_HOME'): result.append(str(Path(os.environ['JAVA_HOME'])/'bin/java.exe'))
    for root in [os.environ.get('ProgramFiles','C:/Program Files'),os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)')]:
        for vendor in ['Java','Eclipse Adoptium','Microsoft','Amazon Corretto']:
            result.extend(str(p) for p in (Path(root)/vendor).glob('*/bin/java.exe'))
    return list(dict.fromkeys(p for p in result if Path(p).is_file()))

def launch_config(jar, output, icon='', minimum='17', bundled=False, console=False):
    require_file(jar,'.jar')
    if not re.fullmatch(r'\d+(\.\d+){0,3}',minimum): raise ValueError('Invalid Java minimum version')
    root=ET.Element('launch4jConfig')
    for key,value in [('dontWrapJar','false'),('headerType','console' if console else 'gui'),('jar',str(Path(jar).resolve())),('outfile',str(Path(output).resolve())),('errTitle',Path(output).stem),('chdir','.'),('downloadUrl','https://adoptium.net/temurin/releases/'),('icon',str(require_file(icon,'.ico')) if icon else '')]:
        ET.SubElement(root,key).text=value
    jre=ET.SubElement(root,'jre')
    for key,value in [('path','jre' if bundled else '%JAVA_HOME%;%PATH%'),('requiresJdk','false'),('requires64Bit','false'),('minVersion',minimum)]: ET.SubElement(jre,key).text=value
    config=Path(output).parent/'launch4j.xml'
    ET.indent(root); ET.ElementTree(root).write(config,encoding='utf-8',xml_declaration=True)
    return config

def inno_script(folder, exe, name, version, publisher, output, icon=''):
    folder=Path(folder).resolve(); require_file(folder/exe,'.exe'); safe_name(name)
    if not re.fullmatch(r'\d+(\.\d+){0,3}',version): raise ValueError('Invalid version')
    def q(s):
        if any(c in str(s) for c in '\r\n{}'): raise ValueError('Unsupported characters in installer field')
        return '"'+str(s).replace('"','""')+'"'
    # Stable AppId allows later versions to update the same installation.
    import uuid
    appid=str(uuid.uuid5(uuid.NAMESPACE_URL,'exe-builder-studio:'+publisher+':'+name))
    text=f'''[Setup]
AppId={{{{{appid}}}}}
AppName={q(name)}
AppVersion={version}
AppPublisher={q(publisher)}
DefaultDirName={{localappdata}}\\Programs\\{name}
DefaultGroupName={q(name)}
PrivilegesRequired=lowest
OutputDir={q(Path(output).resolve())}
OutputBaseFilename={name}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={{app}}\\{exe}
'''
    if icon: text+='SetupIconFile='+q(require_file(icon,'.ico'))+'\n'
    text+=f'''
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: {q(folder/'*')}; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{{group}}\\{name}"; Filename: "{{app}}\\{exe}"
Name: "{{userdesktop}}\\{name}"; Filename: "{{app}}\\{exe}"; Tasks: desktopicon
[Run]
Filename: "{{app}}\\{exe}"; Description: "Launch {name}"; Flags: nowait postinstall skipifsilent
'''
    Path(output).mkdir(parents=True,exist_ok=True)
    p=Path(output)/f'{name}.iss'; p.write_text(text,encoding='utf-8-sig'); return p
