"""Validated native macOS build plans. Never invoke a shell for user inputs."""
import os, re, sys, shutil, tempfile, subprocess, plistlib
from pathlib import Path
from backend import require_file, safe_name
from PIL import Image, ImageOps

def require_mac():
    if sys.platform != 'darwin':
        raise ValueError('Build APP / DMG on macOS. Windows cannot build a Mac app locally.')

def bundle_id(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z][A-Za-z0-9-]*)+', value):
        raise ValueError('Invalid Bundle ID; example: com.khurkham.myapp')
    return value

def executable(value):
    # Resolving a venv interpreter symlink loses pyvenv.cfg and its packages.
    path=Path(os.path.abspath(Path(value).expanduser()))
    if not path.is_file() or not os.access(path,os.X_OK):
        raise ValueError('Select an executable macOS tool: '+str(path))
    return str(path)

def fresh_output(output, target):
    if not str(output).strip(): raise ValueError('Select an output folder')
    out=Path(output).expanduser().resolve()
    if (out/target).exists(): raise ValueError('Output already exists. Choose a new output folder or name.')
    out.mkdir(parents=True,exist_ok=True)
    return out

def python_plan(python, source, output, name, identifier, icon='', data='', hidden='', architecture='native', identity=''):
    require_mac(); py=executable(python); source=require_file(source,'.py'); safe_name(name); bundle_id(identifier)
    if architecture not in ('native','arm64','x86_64','universal2'):raise ValueError('Invalid architecture')
    out=fresh_output(output,'dist/'+name+'.app')
    if (out/'dist'/name).exists():raise ValueError('Output already exists')
    args=['-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name',name,'--osx-bundle-identifier',identifier,'--distpath',str(out/'dist'),'--workpath',str(out/'work'),'--specpath',str(out)]
    if architecture!='native':args+=['--target-architecture',architecture]
    if identity:args+=['--codesign-identity',identity]
    if icon:args+=['--icon',str(require_file(icon,'.icns'))]
    if data:
        folder=Path(data).expanduser().resolve()
        if not folder.is_dir():raise ValueError('Invalid data folder')
        if folder==out or folder in out.parents:raise ValueError('Data folder cannot contain build output')
        args+=['--add-data',str(folder)+':'+folder.name]
    for module in hidden.split(','):
        if module.strip():
            if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',module.strip()):raise ValueError('Invalid hidden import')
            args+=['--hidden-import',module.strip()]
    return py,args+[str(source)],source.parent,out/'dist'/(name+'.app')

def java_plan(tool, folder, jar, output, name, identifier, version='1.0.0', main_class='', icon='', runtime=''):
    require_mac(); tool=executable(tool); safe_name(name); bundle_id(identifier)
    folder=Path(folder).expanduser().resolve()
    if not folder.is_dir():raise ValueError('Select a release folder containing JAR and dependencies')
    if Path(jar).name!=jar or '/' in jar or '\\' in jar:raise ValueError('Enter JAR filename only')
    require_file(folder/jar,'.jar')
    if not re.fullmatch(r'\d+(?:\.\d+){0,2}',version):raise ValueError('Use a numeric version, for example 1.0.0')
    out=fresh_output(output,name+'.app')
    if out==folder or folder in out.parents:raise ValueError('Output must be outside the JAR input folder')
    args=['--type','app-image','--input',str(folder),'--main-jar',jar,'--dest',str(out),'--name',name,'--app-version',version,'--mac-package-identifier',identifier]
    if main_class:args+=['--main-class',main_class]
    if icon:args+=['--icon',str(require_file(icon,'.icns'))]
    if runtime:
        r=Path(runtime).expanduser().resolve()
        if not (r/'bin/java').is_file():raise ValueError('Runtime must contain bin/java (a macOS runtime)')
        args+=['--runtime-image',str(r)]
    return tool,args,folder,out/(name+'.app')

def require_app(value):
    app=Path(value).expanduser().resolve()
    if app.suffix.lower()!='.app' or not (app/'Contents/Info.plist').is_file() or not (app/'Contents/MacOS').is_dir():raise ValueError('Select a valid .app bundle')
    with open(app/'Contents/Info.plist','rb') as f:plistlib.load(f)
    return app

def build_dmg(app, output, name):
    require_mac(); app=require_app(app); safe_name(name); out=fresh_output(output,name+'.dmg')
    if out==app or app in out.parents:raise ValueError('DMG output must be outside the app bundle')
    tool=shutil.which('hdiutil')
    if not tool:raise ValueError('hdiutil not found')
    # Staging contains only the app and the Applications shortcut, never work/spec files.
    with tempfile.TemporaryDirectory(prefix='ebs-dmg-') as tmp:
        stage=Path(tmp)/'stage'; stage.mkdir(); shutil.copytree(app,stage/app.name,symlinks=True)
        (stage/'Applications').symlink_to('/Applications',target_is_directory=True)
        result=subprocess.run([tool,'create','-volname',name,'-srcfolder',str(stage),'-format','UDZO',str(out/(name+'.dmg'))],check=True,capture_output=True,text=True)
    return result.stdout

def convert_icns(source, target):
    with Image.open(require_file(source)) as image:
        image=ImageOps.exif_transpose(image).convert('RGBA'); image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
        square=Image.new('RGBA',(1024,1024));square.alpha_composite(image,((1024-image.width)//2,(1024-image.height)//2));square.save(target,format='ICNS')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('app');parser.add_argument('output');parser.add_argument('name');a=parser.parse_args()
    print(build_dmg(a.app,a.output,a.name))
