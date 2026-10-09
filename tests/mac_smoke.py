"""Actual native Mac integration builds, invoked by CI after the test suite."""
import sys, subprocess, tempfile, plistlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mac_backend as mac
mac.require_mac()
with tempfile.TemporaryDirectory(prefix='ebs-smoke-') as tmp:
    root=Path(tmp);source=root/'hello.py';source.write_text('from PySide6.QtWidgets import QApplication\na=QApplication([])\nprint("PYTHON_APP_OK",flush=True)\n')
    data=root/'assets';data.mkdir();(data/'test.txt').write_text('embedded')
    py,args,cwd,app=mac.python_plan(sys.executable,str(source),str(root/'python'),'Smoke','com.khurkham.smoke',data=str(data))
    subprocess.run([py]+args,cwd=cwd,check=True)
    mac.require_app(app)
    assert list(app.rglob('test.txt')), 'Missing bundled data'
    result=subprocess.run([str(app/'Contents/MacOS/Smoke')],check=True,capture_output=True,text=True,timeout=60)
    assert 'PYTHON_APP_OK' in result.stdout,result.stdout
    mac.build_dmg(str(app),str(root/'dmg'),'Smoke')
    subprocess.run(['hdiutil','verify',str(root/'dmg/Smoke.dmg')],check=True)
    # Real jpackage with a manifest main class and an automatically bundled runtime.
    jars=root/'jars';jars.mkdir();java=root/'Hello.java';java.write_text('public class Hello { public static void main(String[] args) { System.out.println("JAVA_APP_OK"); } }')
    subprocess.run(['javac','-d',str(jars),str(java)],check=True)
    subprocess.run(['jar','--create','--file',str(jars/'hello.jar'),'--main-class','Hello','-C',str(jars),'Hello.class'],check=True)
    import shutil
    tool,args,cwd,app=mac.java_plan(shutil.which('jpackage'),str(jars),'hello.jar',str(root/'java'),'JavaSmoke','com.khurkham.javasmoke')
    subprocess.run([tool]+args,cwd=cwd,check=True);mac.require_app(app)
    result=subprocess.run([str(app/'Contents/MacOS/JavaSmoke')],check=True,capture_output=True,text=True,timeout=60)
    assert 'JAVA_APP_OK' in result.stdout,result.stdout
print('Native Python APP, Java APP, embedded data, executable launch and DMG smoke passed')
