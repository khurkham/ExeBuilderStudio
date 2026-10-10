"""In-app tool cards. Network/process work runs outside the GUI thread."""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QProcess, QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QProgressBar,QLineEdit,QComboBox,QMessageBox,QApplication,QGridLayout,QLayout,QSizePolicy
from tool_downloads import *
WORDS={
 'unchecked':('Not checked yet. Click Check program.','ยังไม่ได้ตรวจสอบ กดตรวจสอบโปรแกรม','ၸႂ်ႉၵူတ်ႇပရူဝ်ႇၵရမ်ႇ။'),
 'check':('Check program','ตรวจสอบโปรแกรม','ၵူတ်ႇပရူဝ်ႇၵရမ်ႇ'),
 'download':('Download','ดาวน์โหลด','လူတ်ႇ'),
 'update':('Update','อัปเดต','ဢပ်ႉတဵတ်ႉ'),
 'install':('Install downloaded file','ติดตั้งไฟล์ที่ดาวน์โหลด','တိတ်းတင်ႈၾၢႆႇလူတ်ႇယဝ်ႉ'),
 'missing':('Not installed. Please download the program.','ยังไม่มีในเครื่อง กรุณาดาวน์โหลดโปรแกรม','ဢမ်ႇမီးၼႂ်းၶွမ်း။ ၶႅၼ်းတေႃႈလူတ်ႇပရူဝ်ႇၵရမ်ႇ။'),
 'unverified':('Found; version could not be verified','พบไฟล์โปรแกรม แต่ตรวจสอบเวอร์ชันไม่ได้','မီးၾၢႆႇပရူဝ်ႇၵရမ်ႇ။ ၵူတ်ႇဝႃးသျိၼ်းဢမ်ႇလႆႈ။'),
 'found':('Installed','พบโปรแกรมในเครื่อง','မီးၼႂ်းၶွမ်းယဝ်ႉ'),
 'ready':('Ready to install','ดาวน์โหลดเสร็จ พร้อมติดตั้ง','လူတ်ႇယဝ်ႉ တိတ်းတင်ႈလႆႈ'),
 'checking':('Checking…','กำลังตรวจสอบ…','တိုၵ်ႉၵူတ်ႇ…'),
 'resolving':('Checking latest release…','กำลังตรวจสอบรุ่นล่าสุด…','တိုၵ်ႉၵူတ်ႇဝႃးသျိၼ်းမႂ်ႇ…'),
 'downloading':('Downloading…','กำลังดาวน์โหลด…','တိုၵ်ႉလူတ်ႇ…'),
 'installing':('Installing…','กำลังติดตั้ง…','တိုၵ်ႉတိတ်းတင်ႈ…'),
 'current':('Already up to date','เป็นรุ่นปัจจุบันแล้ว','ပဵၼ်ဝႃးသျိၼ်းမႂ်ႇယဝ်ႉ'),
 'cancelled':('Cancelled; incomplete file removed','ยกเลิกแล้ว ลบไฟล์ที่ดาวน์โหลดไม่ครบแล้ว','ယုၵ်ႉလိူၵ်ႈယဝ်ႉ'),
 'failed':('Failed','ไม่สำเร็จ','ဢမ်ႇယဝ်ႉ'),
 'repo':('Update source: GitHub repository (owner/repository)','แหล่งอัปเดต: GitHub repository (owner/repository)','တီႈဢပ်ႉတဵတ်ႉ: GitHub repository (owner/repository)'),
 'save':('Save update source','บันทึกแหล่งอัปเดต','သိမ်းတီႈဢပ်ႉတဵတ်ႉ'),
 'saved':('Update source saved','บันทึกแหล่งอัปเดตแล้ว','သိမ်းတီႈဢပ်ႉတဵတ်ႉယဝ်ႉ'),
 'notconfigured':('The publisher has not enabled online updates yet.','ผู้พัฒนายังไม่ได้เปิดบริการอัปเดตออนไลน์','ၽူႈသၢင်ႈဢမ်ႇပႆႇပိုတ်ႇလွင်ႈဢပ်ႉတဵတ်ႉဢွၼ်ႇလၢႆး။'),
 'note':('Download → Install → Check. Update checks the latest release, downloads it and opens installation when newer.','ดาวน์โหลด → ติดตั้ง → ตรวจสอบ ปุ่มอัปเดตตรวจรุ่นล่าสุด ดาวน์โหลดและเปิดการติดตั้งเมื่อมีรุ่นใหม่','လူတ်ႇ → တိတ်းတင်ႈ → ၵူတ်ႇ။ ဢပ်ႉတဵတ်ႉၵူတ်ႇဝႃးသျိၼ်းမႂ်ႇတီႈတၢင်းၵၢၼ်။'),
 'sdk_note':('SDK download progress covers the setup file. The Microsoft installer shows progress for SDK components. Select Signing Tools for Desktop Apps.','แถบดาวน์โหลด SDK แสดงความคืบหน้าของไฟล์ Setup ส่วนองค์ประกอบ SDK แสดงในหน้าติดตั้ง Microsoft ให้เลือก Signing Tools for Desktop Apps','SDK Setup ၼႄလွင်ႈလူတ်ႇ။ လိူၵ်ႈ Signing Tools for Desktop Apps ၼႂ်းတူဝ်တိတ်းတင်ႈ Microsoft။'),
 'pip_note':('PyInstaller uses the selected Python. Package downloads show activity and detailed pip output in the log.','PyInstaller ใช้ Python ที่เลือก ขณะดาวน์โหลดแพ็กเกจจะแสดงแถบการทำงานและรายละเอียด pip ใน Log','PyInstaller ၸႂ်ႉ Python ဢၼ်လိူၵ်ႈ။ ၼႄ pip ၼႂ်း Log။'),
 'java_note':('Java is installed in this app’s tools folder. Choose the Java major version required by your project.','Java ติดตั้งในโฟลเดอร์เครื่องมือของแอป เลือกรุ่นหลักให้ตรงกับโปรเจกต์','Java တိတ်းတင်ႈၼႂ်းၾူဝ်ႇလ်ႇတိူဝ်ႇၶိူင်ႈမိုဝ်း။ လိူၵ်ႈဝႃးသျိၼ်းႁႂ်ႈမႅၼ်ႈ project။'),
}

class ToolWorker(QThread):
    phase=Signal(str);progress=Signal(object,object);log=Signal(str);result=Signal(object);failed=Signal(str)
    def __init__(self,key,action,configured='',repo='',java_major='25',artifact=None,parent=None):
        super().__init__(parent);self.key=key;self.action=action;self.configured=configured;self.repo=repo;self.java_major=java_major;self.artifact=artifact;self.child=None
    def cancel(self):
        self.requestInterruption()
        child=self.child
        if child and child.poll() is None:
            try:child.terminate()
            except OSError:pass
    def run_pip(self,args):
        if not self.configured or not Path(self.configured).is_file():raise ValueError('Select a working Python interpreter in Tools first.')
        self.child=subprocess.Popen([self.configured,'-m','pip']+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for line in self.child.stdout:
            self.log.emit(line.rstrip())
            if self.isInterruptionRequested():self.child.terminate();break
        code=self.child.wait();self.child=None
        if self.isInterruptionRequested():raise Cancelled()
        if code:raise ValueError('pip failed. Check the log above.')
    def run(self):
        try:
            if self.action=='check':
                self.phase.emit('checking');self.result.emit({'detected':detect_tool(self.key,self.configured)});return
            if self.action=='install':
                self.phase.emit('installing');artifact=self.artifact;path=Path(artifact['path']);release=artifact['release']
                if not path.exists():raise ValueError('Downloaded file is missing. Download again.')
                if self.key=='pyinstaller':
                    self.run_pip(['install','--upgrade','--no-index','--find-links',str(path),'PyInstaller>=6.10,<7'])
                    self.result.emit({'detected':detect_tool(self.key,self.configured),'installed':True});return
                if file_hash(path)!=artifact['digest']:raise ValueError('Downloaded file changed. Download again.')
                if release['kind']=='zip':
                    executable=extract_tool(path,self.key,release['version']);self.result.emit({'installed':True,'detected':{'path':executable,'version':release['version'],'found':True}});return
                if release.get('publisher'):verify_publisher(path,release['publisher'])
                if self.isInterruptionRequested():raise Cancelled()
                # Use the normal installer UI. No silent installation or elevated shell is used.
                self.child=subprocess.Popen([str(path)])
                code=self.child.wait();self.child=None
                if code not in (0,3010):raise ValueError(f'Installer exited with code {code}; check again or retry.')
                detected=detect_tool(self.key,'')
                if not detected['found'] and self.configured:detected=detect_tool(self.key,self.configured)
                self.result.emit({'detected':detected,'installed':True,'restart':code==3010});return
            self.phase.emit('resolving')
            if self.key=='pyinstaller':
                directory=app_data()/'downloads'/'pyinstaller'/str(time.time_ns());directory.mkdir(parents=True)
                self.phase.emit('downloading');self.run_pip(['download','--only-binary=:all:','--dest',str(directory),'PyInstaller>=6.10,<7'])
                self.result.emit({'artifact':{'path':str(directory),'release':{'version':'Latest compatible','kind':'pip'},'digest':''}});return
            release=resolve_release(self.key,self.repo,self.java_major)
            if self.isInterruptionRequested():raise Cancelled()
            local=detect_tool(self.key,self.configured)
            if self.action=='update' and local['found']:
                value=local['version']
                if self.key=='java':
                    match=__import__('re').search(r'version "([^"]+)"',value);value=match[1] if match else ''
                new_build=self.key=='studio' and version_key(value)==version_key(release['version']) and version_key(release.get('build_revision',''))>version_key(local.get('build_revision',''))
                if not new_build and value and version_key(release['version']) and version_key(value)>=version_key(release['version']):self.result.emit({'current':True,'detected':local,'latest':release['version']});return
            self.phase.emit('downloading');path=download(release,app_data()/'downloads'/self.key,self.progress.emit,self.isInterruptionRequested)
            if release.get('publisher'):verify_publisher(path,release['publisher'])
            if self.isInterruptionRequested():raise Cancelled()
            self.result.emit({'artifact':{'path':str(path),'release':release,'digest':file_hash(path)},'latest':release['version']})
        except Cancelled:self.failed.emit('cancelled')
        except Exception as e:self.failed.emit(str(e))

def file_hash(path):
    digest=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

class ToolCard(QWidget):
    def __init__(self,host,key):
        super().__init__();self.host=host;self.key=key;self.worker=None;self.artifact=None;self.install_after_update=False;self.state='unchecked';self.detail='';self.detected=None
        self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Minimum)
        layout=QVBoxLayout(self);layout.setSizeConstraint(QLayout.SetMinimumSize);head=QHBoxLayout();self.title=QLabel(NAMES[key]);head.addWidget(self.title);head.addStretch()
        self.java_major=None
        if key=='java':
            self.java_major=QComboBox();self.java_major.addItems(['25','21','17','11','8']);self.java_major.setCurrentText(str(host.settings.value('downloads/java_major','25')));head.addWidget(self.java_major)
        layout.addLayout(head);self.status=QLabel();self.status.setWordWrap(True);self.status.setTextInteractionFlags(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.TextSelectableByMouse);layout.addWidget(self.status)
        self.bar=QProgressBar();self.bar.setRange(0,100);self.bar.setValue(0);self.bar.setVisible(False);layout.addWidget(self.bar)
        row=QGridLayout();self.buttons={}
        for index,action in enumerate(['check','download','update','install']):
            button=QPushButton();button.clicked.connect(lambda checked=False,a=action:self.begin(a));row.addWidget(button,index//2,index%2);self.buttons[action]=button
        layout.addLayout(row);self.note=QLabel();self.note.setWordWrap(True);layout.addWidget(self.note)
        stored=host.settings.value('downloads/'+key+'/artifact','')
        if stored:
            try:
                artifact=json.loads(stored)
                if Path(artifact['path']).exists():self.artifact=artifact;self.state='ready';self.detail=artifact['path']
            except (ValueError,KeyError,TypeError):pass
        self.translate()
    def fit_content(self):
        layout=self.layout()
        layout.invalidate()
        required=layout.totalHeightForWidth(max(1,self.width()))
        self.setMinimumHeight(max(layout.minimumSize().height(),required))
        self.updateGeometry()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.fit_content()
    def word(self,key):return WORDS[key][self.host.lang.currentIndex()]
    def translate(self):
        for action,button in self.buttons.items():button.setText(self.word(action)+((' '+NAMES[self.key]) if action in ('download','update') else ''))
        for button in self.buttons.values():button.setMinimumHeight(max(44,button.fontMetrics().height()+24))
        self.buttons['install'].setEnabled(self.artifact is not None and self.worker is None)
        notes=['note']+(['sdk_note'] if self.key=='sdk' else ['pip_note'] if self.key=='pyinstaller' else ['java_note'] if self.key=='java' else [])
        self.note.setText('\n'.join(self.word(n) for n in notes));self.status.setText((self.word(self.state) if self.state in WORDS else self.state)+ ('\n'+self.detail if self.detail else ''))
        self.fit_content()
    def configured(self):
        field={'launch4j':'tools/launch4jc','inno':'tools/ISCC','python':'tools/Python interpreter','pyinstaller':'tools/Python interpreter','sdk':'signing/signtool'}.get(self.key)
        return self.host.fields[field].text().strip() if field else str(self.host.settings.value('downloads/java/path','')) if self.key=='java' else ''
    def begin(self,action):
        if self.host.busy:return
        repo=UPDATE_REPOSITORY
        if self.key=='studio' and action in ('download','update'):
            if not repo:self.state='notconfigured';self.detail='';self.translate();return
        if action=='install' and self.key=='studio':
            try:
                artifact=self.artifact;path=Path(artifact['path'])
                if file_hash(path)!=artifact['digest']:raise ValueError('Downloaded file changed. Download again.')
                # Validate source record; the digest was received from GitHub at download time.
                if artifact['digest']!=artifact['release']['sha256']:raise ValueError('Update checksum mismatch.')
                ok,pid=QProcess.startDetached(str(path),[],str(path.parent))
                if not ok:raise ValueError('Cannot start the update installer.')
                self.host.save_settings();QApplication.instance().quit()
            except Exception as e:self.state='failed';self.detail=str(e);self.translate()
            return
        if self.java_major:self.host.settings.setValue('downloads/java_major',self.java_major.currentText())
        self.install_after_update=False
        self.host.busy=True;self.host.tabs.setEnabled(False);self.host.stop.setEnabled(action!='install');self.host.active_download=self
        self.worker=ToolWorker(self.key,action,self.configured(),repo,self.java_major.currentText() if self.java_major else '25',self.artifact,self)
        self.worker.phase.connect(self.phase);self.worker.progress.connect(self.progress);self.worker.log.connect(self.host.log.appendPlainText);self.worker.result.connect(self.complete);self.worker.failed.connect(self.fail);self.worker.finished.connect(self.cleanup)
        self.bar.setVisible(True);self.bar.setRange(0,0);self.worker.start()
    def phase(self,state):self.state=state;self.detail='';self.translate();self.host.status.setText(self.word(state)+' '+NAMES[self.key])
    def progress(self,done,total):
        if total:self.bar.setRange(0,100);self.bar.setValue(min(100,int(done*100/total)))
        else:self.bar.setRange(0,0)
        self.detail=f'{done/1024/1024:.1f} MB'+(f' / {total/1024/1024:.1f} MB' if total else '');self.translate()
    def complete(self,result):
        if 'artifact' in result:
            self.install_after_update=self.worker is not None and self.worker.action=='update'
            self.artifact=result['artifact'];self.host.settings.setValue('downloads/'+self.key+'/artifact',json.dumps(self.artifact));self.state='ready';self.detail=self.artifact['release']['version']+'\n'+self.artifact['path'];self.bar.setRange(0,100);self.bar.setValue(100)
        else:
            self.detected=result['detected'];self.state='current' if result.get('current') else 'found' if self.detected['found'] else 'missing';self.detail=(self.detected['version']+'\n'+self.detected['path']).strip()
            if self.detected.get('error'):self.state='unverified' if self.detected['found'] else 'failed';self.detail+='\n'+self.detected['error']
            elif self.detected['found'] and not self.detected['version']:self.state='unverified'
            if self.detected['found']:
                field={'launch4j':'tools/launch4jc','inno':'tools/ISCC','python':'tools/Python interpreter','sdk':'signing/signtool'}.get(self.key)
                if field:self.host.fields[field].setText(self.detected['path'])
                self.host.settings.setValue('downloads/'+self.key+'/path',self.detected['path']);self.host.save_settings()
                if self.key=='java':os.environ['JAVA_HOME']=str(Path(self.detected['path']).parent.parent);os.environ['PATH']=str(Path(self.detected['path']).parent)+os.pathsep+os.environ.get('PATH','')
            if result.get('restart'):self.detail+='\nRestart Windows to finish installation.'
        self.translate();self.host.log.appendPlainText(NAMES[self.key]+': '+self.status.text())
    def fail(self,error):self.state='cancelled' if error=='cancelled' else 'failed';self.detail='' if error=='cancelled' else error;self.translate();self.host.log.appendPlainText(NAMES[self.key]+': '+self.status.text())
    def cleanup(self):
        if self.state=='ready':
            self.bar.setRange(0,100);self.bar.setValue(100)
        else:
            self.bar.setRange(0,100);self.bar.setValue(0);self.bar.hide()
        worker=self.worker;self.worker=None;self.host.active_download=None;self.host.unlock(self.status.text().split('\n')[0]);self.translate();worker.deleteLater()
        if self.install_after_update:
            self.install_after_update=False;QTimer.singleShot(0,lambda:self.begin('install'))


def add_tool_card(host,key,form):
    card=ToolCard(host,key);form.addRow(card);host.tool_cards.append(card);return card

def add_about_updater(host,layout):
    card=ToolCard(host,'studio');host.tool_cards.append(card);layout.addWidget(card)

def translate_downloads(host):
    for card in host.tool_cards:card.translate()
