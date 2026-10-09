import sys, os, shutil, json
from pathlib import Path
from PySide6.QtCore import QProcess, QSettings, QUrl, QTimer, Qt
from PySide6.QtGui import QFont, QFontDatabase, QDesktopServices, QPixmap, QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QPushButton,QComboBox,QTabWidget,QPlainTextEdit,QFileDialog,QCheckBox,QLabel,QMessageBox,QScrollArea,QLayout)
from backend import *
from signing import *
from download_ui import add_tool_card, add_about_updater, translate_downloads
from tool_downloads import APP_VERSION, BUILD_REVISION
from ui_assets import resource, load_fonts, apply_font, FAMILIES, FONT_ERRORS

# English, Thai, Shan. Labels are switched together; technical tool names stay unchanged.
T={
 'title':('EXE Builder Studio','โปรแกรมสร้าง EXE','ပရူဝ်ႇၵရမ်ႇသၢင်ႈ EXE'),
 'java':('Java JAR → EXE','Java JAR → EXE','Java JAR → EXE'),
 'python':('Python → EXE','Python → EXE','Python → EXE'),
 'installer':('Installer','ตัวติดตั้ง','တူဝ်တိတ်းတင်ႈ'),
 'icon':('Logo → ICO','โลโก้ → ICO','လူဝ်ႇၵူဝ်ႇ → ICO'),
 'tools':('Tools / Java','เครื่องมือ / Java','ၶိူင်ႈမိုဝ်း / Java'),
 'browse':('Browse','เลือกไฟล์','လိူၵ်ႈၾၢႆႇ'),
 'build':('Build EXE','สร้าง EXE','သၢင်ႈ EXE'),
 'source':('Source file','ไฟล์ต้นฉบับ','ၾၢႆႇတူၼ်ႈတေႃ'),
 'output':('Output folder','โฟลเดอร์ผลลัพธ์','ၾူဝ်ႇလ်ႇတိူဝ်ႇဢွၵ်ႇ'),
 'name':('App name (English)','ชื่อโปรแกรม (อังกฤษ)','ၸိုဝ်ႈပရူဝ်ႇၵရမ်ႇ (ဢင်းၵိတ်ႉ)'),
 'version':('Version','เวอร์ชัน','ဝႃးသျိၼ်း'),
 'publisher':('Publisher','ผู้พัฒนา','ၽူႈသၢင်ႈ'),
 'minimum':('Minimum Java version','Java ขั้นต่ำ','Java ဝႃးသျိၼ်းတႅမ်ႇသုတ်း'),
 'jre':('Bundle Java folder (optional)','โฟลเดอร์ Java ที่รวมไปด้วย (ไม่บังคับ)','ၾူဝ်ႇလ်ႇတိူဝ်ႇ Java (လိူၵ်ႈလႆႈ)'),
 'console':('Show console','แสดง Console','ၼႄ Console'),
 'onefile':('Single EXE file','ไฟล์ EXE เดียว','EXE ၾၢႆႇလဵဝ်'),
 'data':('Extra data folder (optional)','โฟลเดอร์ข้อมูลเพิ่มเติม (ไม่บังคับ)','ၾူဝ်ႇလ်ႇတိူဝ်ႇၶေႃႈမုၼ်း (လိူၵ်ႈလႆႈ)'),
 'hidden':('Hidden imports (comma-separated)','Hidden imports (คั่นด้วยจุลภาค)','Hidden imports (ၶႅၼ်ႈၽၢတ်ႇၵွမ်ႇမႃႇ)'),
 'folder':('Release folder to install','โฟลเดอร์โปรแกรมที่จะติดตั้ง','ၾူဝ်ႇလ်ႇတိူဝ်ႇပရူဝ်ႇၵရမ်ႇ'),
 'exe':('EXE filename in release folder','ชื่อไฟล์ EXE ในโฟลเดอร์','ၸိုဝ်ႈၾၢႆႇ EXE'),
 'makeinstaller':('Build installer','สร้างตัวติดตั้ง','သၢင်ႈတူဝ်တိတ်းတင်ႈ'),
 'convert':('Convert to ICO','แปลงเป็น ICO','ပိၼ်ႇပဵၼ် ICO'),
 'check':('Check Java','ตรวจ Java','ၵူတ်ႇထတ်း Java'),
 'stop':('Stop','หยุด','ၵိုတ်း'),
 'open':('Open output folder','เปิดโฟลเดอร์ผลลัพธ์','ပိုတ်ႇၾူဝ်ႇလ်ႇတိူဝ်ႇဢွၵ်ႇ'),
 'save':('Save tool settings','บันทึกเครื่องมือ','သိမ်းၶိူင်ႈမိုဝ်း'),
 'installjava':('Download / install Java','ดาวน์โหลด / ติดตั้ง Java','လူတ်ႇ / တိတ်းတင်ႈ Java'),
 'runinstaller':('Run downloaded installer','เปิดไฟล์ติดตั้งที่ดาวน์โหลดแล้ว','ပိုတ်ႇၾၢႆႇတိတ်းတင်ႈ'),
 'installpython':('Install PyInstaller in selected Python','ติดตั้ง PyInstaller ใน Python ที่เลือก','တိတ်းတင်ႈ PyInstaller ၼႂ်း Python'),
 'ready':('Ready • Build on Windows','พร้อมใช้งาน • สร้าง EXE บน Windows','တူဝ်ႈတၼ်း • သၢင်ႈ EXE ၼိူဝ် Windows'),
 'signing':('Certificates / signing','ใบรับรอง / ลงนาม','ဝႂ်ယိုၼ်ယၼ် / လူင်းလၢႆးမိုဝ်း'),
 'signtool':('SignTool.exe','SignTool.exe','SignTool.exe'),
 'signmode':('Certificate source','แหล่งใบรับรอง','ဝႂ်ယိုၼ်ယၼ်'),
 'certpublisher':('Test certificate publisher','ผู้พัฒนาในใบรับรองทดสอบ','ၽူႈသၢင်ႈဝႂ်ယိုၼ်ယၼ်'),
 'thumbprint':('Certificate thumbprint','Thumbprint ใบรับรอง','Thumbprint ဝႂ်ယိုၼ်ယၼ်'),
 'timestamp':('RFC 3161 timestamp URL (optional)','URL ประทับเวลา RFC 3161 (ไม่บังคับ)','RFC 3161 timestamp URL'),
 'autosign':('Sign EXE and Setup after build','ลงนาม EXE และ Setup หลังสร้าง','လူင်းလၢႆးမိုဝ်း EXE / Setup'),
 'createcert':('Create / reuse test certificate','สร้าง / ใช้ใบรับรองทดสอบเดิม','သၢင်ႈ / ၸႂ်ႉဝႂ်ယိုၼ်ယၼ်'),
 'listcert':('List installed Code Signing certificates','เลือกใบรับรอง Code Signing ในเครื่อง','လိူၵ်ႈဝႂ်ယိုၼ်ယၼ် Code Signing'),
 'pfx':('Existing certificate (.pfx / .p12)','ใบรับรองที่มีอยู่ (.pfx / .p12)','ဝႂ်ယိုၼ်ယၼ် (.pfx / .p12)'),
 'pfxpassword':('PFX password (not saved)','รหัสผ่าน PFX (ไม่บันทึก)','မၢႆလပ်ႉ PFX (ဢမ်ႇသိမ်း)'),
 'importcert':('Import existing PFX certificate','นำเข้าใบรับรอง PFX ที่มีอยู่','ဢဝ်ဝႂ်ယိုၼ်ယၼ် PFX ၶဝ်ႈ'),
 'target':('File to sign / verify','ไฟล์ที่จะลงนาม / ตรวจสอบ','ၾၢႆႇလူင်းလၢႆးမိုဝ်း'),
 'signfile':('Sign selected file','ลงนามไฟล์ที่เลือก','လူင်းလၢႆးမိုဝ်းၾၢႆႇ'),
 'verifyfile':('Verify signature and Windows trust','ตรวจลายเซ็นและความเชื่อถือของ Windows','ၵူတ်ႇလၢႆးမိုဝ်း / Windows'),
 'downloadsdk':('Download Microsoft Windows SDK','ดาวน์โหลด Windows SDK จาก Microsoft','လူတ်ႇ Windows SDK'),
 'installsdk':('Install SDK → create certificate','ติดตั้ง SDK → สร้างใบรับรอง','တိတ်းတင်ႈ SDK → သၢင်ႈဝႂ်ယိုၼ်ယၼ်'),
 'certfolder':('Open public certificate folder','เปิดโฟลเดอร์ใบรับรองสาธารณะ','ပိုတ်ႇၾူဝ်ႇလ်ႇတိူဝ်ႇဝႂ်ယိုၼ်ယၼ်'),
 'signnote':('A self-signed certificate is for testing. It does not make other PCs trust your app. No Trusted Root installation is performed.',
             'ใบรับรองสร้างเองใช้ทดสอบ เครื่องอื่นจะไม่เชื่อถืออัตโนมัติ โปรแกรมไม่เพิ่มใบรับรองเข้า Trusted Root',
             'ဝႂ်ယိုၼ်ယၼ်သၢင်ႈဢွၵ်ႇႁင်းၵူၺ်း ပဵၼ်တႃႇၸမ်း။ Windows တၢင်ႇၶိူင်ႈ ဢမ်ႇယုမ်ႇယမ်ဢတ်ႉတၼူဝ်ႇ။'),
}

class Window(QMainWindow):
 def __init__(self):
    super().__init__(); self.settings=QSettings('Khurkham','ExeBuilderStudio'); self.labels=[]; self.fields={}; self.last_output=''; self.busy=False; self.tool_cards=[]; self.active_download=None
    self.resize(1080,820); root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root)
    head=QHBoxLayout(); self.logo=QLabel(); self.logo.setPixmap(QPixmap(str(resource("logo.png"))).scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation)); self.logo.setFixedSize(72,72); head.addWidget(self.logo); self.setWindowIcon(QIcon(str(resource("app.ico")))); self.title=QLabel(); head.addWidget(self.title); head.addStretch(); self.lang=QComboBox(); self.lang.addItems(['English','ไทย','တႆး']); self.lang.setCurrentIndex(int(self.settings.value('language',1))); head.addWidget(self.lang); layout.addLayout(head)
    self.tabs=QTabWidget(); layout.addWidget(self.tabs); self.pages={}
    for key in ['java','python','installer','icon','tools','signing']:
      page=QWidget(); form=QFormLayout(page); form.setSizeConstraint(QLayout.SetMinimumSize); form.setVerticalSpacing(12); self.pages[key]=form
      scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page); self.tabs.addTab(scroll,key)
    for page in ['java','python']:
      self.field(page,'source',kind='file'); self.field(page,'output',kind='dir'); self.field(page,'name',default='MyApplication'); self.field(page,'icon',kind='ico'); self.check(page,'console')
    self.field('java','minimum',default='17'); self.field('java','jre',kind='dir'); self.button('java','build',self.build_java)
    self.check('python','onefile',True); self.field('python','data',kind='dir'); self.field('python','hidden'); self.button('python','build',self.build_python)
    for key,kind,default in [('folder','dir',''),('exe',None,'MyApplication.exe'),('name',None,'MyApplication'),('version',None,'1.0'),('publisher',None,'Khurkham'),('output','dir',''),('icon','ico','')]: self.field('installer',key,kind,default)
    self.button('installer','makeinstaller',self.build_installer)
    self.field('icon','source',kind='image'); self.field('icon','output',kind='dir'); self.field('icon','name',default='app'); self.button('icon','convert',self.make_icon)
    self.field('tools','launch4jc',kind='file',default=self.detect('launch4jc.exe',['Launch4j/launch4jc.exe']))
    self.field('tools','ISCC',kind='file',default=self.detect('ISCC.exe',['Inno Setup 6/ISCC.exe','Inno Setup 7/ISCC.exe']))
    self.field('tools','Python interpreter',kind='file',default=sys.executable if not getattr(sys,'frozen',False) else (shutil.which('python') or ''))
    self.button('tools','save',self.save_settings)
    for key in ['java','launch4j','inno','python','pyinstaller']:add_tool_card(self,key,self.pages['tools'])
    note=QLabel(); note.setWordWrap(True); self.labels.append((note,'signnote')); self.pages['signing'].addRow(note)
    self.field('signing','signtool',kind='file',default=detect_signtool())
    self.signmode=QComboBox(); self.signmode.addItems(['Self-signed test / ใบรับรองทดสอบ','CurrentUser\\My','LocalMachine\\My'])
    self.signmode.setCurrentIndex(int(self.settings.value('signing/mode',0)))
    label=QLabel(); self.labels.append((label,'signmode')); self.pages['signing'].addRow(label,self.signmode)
    self.field('signing','certpublisher',default=certificate_metadata().get('publisher','Khurkham'))
    self.field('signing','thumbprint',default=certificate_metadata().get('thumbprint',''))
    self.field('signing','timestamp'); self.check('signing','autosign',False)
    self.fields['signing/autosign'].setChecked(str(self.settings.value('signing/autosign','false')).lower()=='true')
    self.button('signing','createcert',self.create_certificate); self.button('signing','listcert',self.list_certificates)
    self.field('signing','pfx',kind='pfx'); self.field('signing','pfxpassword')
    self.fields['signing/pfxpassword'].setEchoMode(QLineEdit.Password); self.fields['signing/pfxpassword'].clear()
    self.button('signing','importcert',self.import_certificate)
    self.field('signing','target',kind='signfile'); self.button('signing','signfile',self.sign_selected); self.button('signing','verifyfile',self.verify_selected)
    add_tool_card(self,'sdk',self.pages['signing'])
    self.button('signing','certfolder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(certificate_dir()))))
    about=QWidget(); box=QVBoxLayout(about); logo=QLabel(); logo.setPixmap(QPixmap(str(resource('logo.png'))).scaled(140,140,Qt.KeepAspectRatio,Qt.SmoothTransformation)); box.addWidget(logo); self.about_text=QLabel(); self.about_text.setWordWrap(True); box.addWidget(self.about_text); add_about_updater(self,box); box.addStretch(); about_scroll=QScrollArea(); about_scroll.setWidgetResizable(True); about_scroll.setWidget(about); self.about_index=self.tabs.addTab(about_scroll,'About')
    self.status=QLabel(); layout.addWidget(self.status); self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(10000); self.log.setMaximumHeight(200); layout.addWidget(self.log)
    row=QHBoxLayout(); self.stop=QPushButton(); self.labels.append((self.stop,'stop')); self.stop.clicked.connect(self.cancel); row.addWidget(self.stop); self.open=QPushButton(); self.labels.append((self.open,'open')); self.open.clicked.connect(self.open_output); row.addWidget(self.open); layout.addLayout(row)
    self.process=QProcess(self); self.process.setProcessChannelMode(QProcess.MergedChannels); self.process.readyReadStandardOutput.connect(self.read_output); self.process.finished.connect(self.finished); self.process.errorOccurred.connect(self.process_error)
    self.on_success=None; self.process_output=''; self.input_payload=None
    self.process.started.connect(self.write_input)
    self.lang.currentIndexChanged.connect(self.translate); self.translate()
    java_path=str(self.settings.value('downloads/java/path',''))
    if java_path and Path(java_path).is_file():
      os.environ['JAVA_HOME']=str(Path(java_path).parent.parent); os.environ['PATH']=str(Path(java_path).parent)+os.pathsep+os.environ.get('PATH','')
    QTimer.singleShot(0,self.bootstrap_certificate)
 def detect(self,name,rel):
    found=shutil.which(name)
    if found:return found
    for root in [os.environ.get('ProgramFiles','C:/Program Files'),os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)')]:
      for r in rel:
       p=Path(root)/r
       if p.is_file(): return str(p)
    return ''
 def translate(self):
    i=self.lang.currentIndex(); self.settings.setValue('language',i); self.setWindowTitle(T['title'][i]); self.title.setText(T['title'][i]+' • '+APP_VERSION); self.title.setStyleSheet('font-size:26px; color:#7dcfff;')
    apply_font(self,i)
    for widget,key in self.labels: widget.setText(T.get(key,(key,key,key))[i])
    for j,key in enumerate(self.pages): self.tabs.setTabText(j,T[key][i])
    self.tabs.setTabText(self.about_index,['About','เกี่ยวกับ','လွင်ႈပရူဝ်ႇၵရမ်ႇ'][i])
    self.about_text.setText(['EXE Builder Studio • Version 1.0\nDeveloped by Khurkham Langkhur\nJava / Python EXE, Inno Setup, ICO\nEmbedded fonts: ', 'EXE Builder Studio • เวอร์ชัน 1.0\nพัฒนาโดย Khurkham Langkhur\nสร้าง EXE จาก Java / Python สร้างตัวติดตั้ง และแปลง ICO\nฟอนต์ที่ฝัง: ', 'EXE Builder Studio • ဝႃးသျိၼ်း 1.0\nၽူႈသၢင်ႈ Khurkham Langkhur\nJava / Python EXE, Inno Setup, ICO\nၾွၼ်ႉ: '][i].replace('1.0',APP_VERSION)+' / '.join(FAMILIES.values()))
    translate_downloads(self)
    if not self.busy:self.status.setText(T['ready'][i])
 def field(self,page,key,kind=None,default=''):
    label=QLabel(); self.labels.append((label,key)); edit=QLineEdit(str(self.settings.value(page+'/'+key,default))); self.fields[page+'/'+key]=edit
    row=QWidget(); box=QHBoxLayout(row); box.setContentsMargins(0,0,0,0); box.addWidget(edit)
    if kind:
      button=QPushButton(); self.labels.append((button,'browse')); button.clicked.connect(lambda checked=False:self.browse(edit,kind,page,key)); box.addWidget(button)
    self.pages[page].addRow(label,row)
 def browse(self,edit,kind,page,key):
    if kind=='dir': value=QFileDialog.getExistingDirectory(self,'Folder',edit.text())
    else:
      filters={'ico':'Icon (*.ico)','image':'Images (*.png *.jpg *.jpeg *.bmp *.webp *.ico)', 'pfx':'Certificate (*.pfx *.p12)', 'signfile':'Signable files (*.exe *.dll *.msi)'}
      filt=filters.get(kind,'JAR (*.jar)' if page=='java' and key=='source' else 'Python (*.py)' if page=='python' and key=='source' else 'Executable (*.exe);;All files (*)')
      value=QFileDialog.getOpenFileName(self,'File',edit.text(),filt)[0]
    if value:edit.setText(value)
 def check(self,page,key,on=False):
    c=QCheckBox(); c.setChecked(on); self.fields[page+'/'+key]=c; self.labels.append((c,key)); self.pages[page].addRow(c)
 def button(self,page,key,fn):
    b=QPushButton(); self.labels.append((b,key)); b.clicked.connect(lambda checked=False:self.guard(fn)); self.pages[page].addRow(b)
 def v(self,page,key):return self.fields[page+'/'+key].text().strip()
 def checked(self,page,key):return self.fields[page+'/'+key].isChecked()
 def guard(self,fn):
    if self.busy: return
    try:fn()
    except Exception as e:self.status.setText(['Failed','ไม่สำเร็จ','ဢမ်ႇယဝ်ႉ'][self.lang.currentIndex()]); self.log.appendPlainText(str(e)); QMessageBox.warning(self,'EXE Builder Studio',str(e))
 def save_settings(self):
    for key,w in self.fields.items():
      if isinstance(w,QLineEdit) and key!='signing/pfxpassword':self.settings.setValue(key,w.text())
    self.settings.remove('signing/pfxpassword')
    self.settings.setValue('signing/mode',self.signmode.currentIndex())
    self.settings.setValue('signing/autosign',self.checked('signing','autosign'))
    self.log.appendPlainText('Settings saved.')
 def output(self,page):
    value=self.v(page,'output')
    if not value:raise ValueError('Select an output folder')
    p=Path(value).resolve(); p.mkdir(parents=True,exist_ok=True); self.last_output=str(p); return p
 def available(self,path):return str(require_file(path,'.exe'))
 def start(self,exe,args,cwd=None,callback=None,payload=None,label=None):
    if os.name!='nt':raise ValueError('Build EXE on Windows.')
    self.save_settings(); self.busy=True; self.tabs.setEnabled(False); self.status.setText(label or 'Running…')
    self.on_success=callback; self.process_output=''; self.input_payload=payload
    self.stop.setEnabled(not (payload and payload.get('action')=='install-sdk'))
    self.log.appendPlainText(exe+' '+repr(args)); self.process.setWorkingDirectory(str(cwd or Path.cwd())); self.process.start(exe,args)
 def write_input(self):
    if self.input_payload is not None:
      self.process.write(json.dumps(self.input_payload,ensure_ascii=True).encode('utf-8'))
      self.process.closeWriteChannel(); self.input_payload=None
 def read_output(self):
    value=bytes(self.process.readAllStandardOutput()).decode('utf-8',errors='replace')
    self.process_output+=value
    if value:self.log.appendPlainText(value)
 def process_error(self,error):
    self.log.appendPlainText(self.process.errorString())
    if self.process.state()==QProcess.NotRunning:
      self.on_success=None; self.input_payload=None; self.unlock('Failed')
 def unlock(self,text):self.busy=False; self.tabs.setEnabled(True); self.stop.setEnabled(True); self.status.setText(text)
 def finished(self,code,status):
    self.read_output(); callback=self.on_success; self.on_success=None; self.input_payload=None
    ok=code==0 and status==QProcess.NormalExit
    self.unlock('Success' if ok else f'Failed / stopped ({code}); following steps skipped')
    self.log.appendPlainText(self.status.text())
    if ok and callback:self.guard(lambda:callback(self.process_output))
 def cancel(self):
    if self.active_download and self.active_download.worker:self.active_download.worker.cancel()
    elif self.busy:self.process.kill()
 def open_output(self):
    if self.last_output:QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output))
 def check_java(self):
    candidates=java_candidates(); self.log.appendPlainText('Java: '+ ('\n'.join(candidates) if candidates else 'Not found. Use Download / install Java, then Check Java.'))
    if candidates and os.name=='nt':self.start(candidates[0],['-version'])
 def run_downloaded_installer(self):
    if os.name!='nt':raise ValueError('Install tools on Windows.')
    path=QFileDialog.getOpenFileName(self,'Select installer','','Installer (*.exe *.msi)')[0]
    if path:os.startfile(path)
 def install_python_tool(self):self.start(self.available(self.v('tools','Python interpreter')),['-m','pip','install','PyInstaller>=6.10,<7'])
 def certificate_operation(self,request,callback=None):
    exe,args=powershell_command(); self.start(exe,args,callback=callback,payload=request,label='Certificate / SDK operation…')
 def bootstrap_certificate(self):
    candidates=java_candidates(); self.log.appendPlainText('Java: '+('\n'.join(candidates) if candidates else 'Not found.'))
    if os.name=='nt':self.guard(lambda:self.certificate_operation({'action':'ensure'},self.certificate_ready))
 def certificate_ready(self,output):
    result=parse_result(output)
    if self.signmode.currentIndex()==0:
      self.fields['signing/thumbprint'].setText(result['thumbprint'])
      self.fields['signing/certpublisher'].setText(result['publisher'])
    self.log.appendPlainText('Self-signed TEST certificate '+('created' if result['created'] else 'reused')+'. Other Windows PCs do not trust it automatically.')
    self.save_settings()
 def create_certificate(self):
    self.signmode.setCurrentIndex(0)
    self.certificate_operation({'action':'ensure','publisher':self.v('signing','certpublisher')},self.certificate_ready)
 def list_certificates(self):
    machine=self.signmode.currentIndex()==2
    def selected(output):
      rows=parse_result(output)
      if not rows:raise ValueError('No active Code Signing certificate with a private key in the selected store.')
      dialog=QMessageBox(self); dialog.setWindowTitle('Code Signing certificates')
      dialog.setText('Choose a certificate • เลือกใบรับรอง')
      for row in rows:
        button=dialog.addButton(row['subject']+' | '+row['expires'][:10]+' | '+row['thumbprint'],QMessageBox.ActionRole)
        button.setProperty('thumbprint',row['thumbprint']); button.setProperty('self_signed',row['self_signed'])
      dialog.addButton(QMessageBox.Cancel); dialog.exec(); button=dialog.clickedButton()
      if button and button.property('thumbprint'):
        self.fields['signing/thumbprint'].setText(button.property('thumbprint'))
        self.signmode.setCurrentIndex(2 if machine else 1); self.save_settings()
    self.certificate_operation({'action':'list','machine_store':machine},selected)
 def import_certificate(self):
    pfx=require_file(self.v('signing','pfx'))
    if pfx.suffix.lower() not in ('.pfx','.p12'):raise ValueError('Select a PFX or P12 certificate.')
    password=self.fields['signing/pfxpassword'].text(); self.fields['signing/pfxpassword'].clear()
    def imported(output):
      row=parse_result(output); self.signmode.setCurrentIndex(1)
      self.fields['signing/thumbprint'].setText(row['thumbprint']); self.save_settings()
      self.log.appendPlainText('Imported: '+row['subject']+(' (SELF-SIGNED TEST)' if row['self_signed'] else ''))
    self.certificate_operation({'action':'import','path':str(pfx),'password':password},imported)
 def install_sdk(self):
    path=QFileDialog.getOpenFileName(self,'Microsoft Windows SDK installer','','SDK installer (*.exe)')[0]
    if not path:return
    def installed(output):
      result=parse_result(output); tool=detect_signtool()
      if not tool:raise ValueError('SignTool not found. Run the SDK installer again and select Windows SDK Signing Tools for Desktop Apps.')
      self.fields['signing/signtool'].setText(tool)
      if result.get('restart_required'):self.log.appendPlainText('Windows SDK requests a restart.')
      self.certificate_operation({'action':'ensure','publisher':self.v('signing','certpublisher')},self.certificate_ready)
    self.certificate_operation({'action':'install-sdk','path':path},installed)
 def signing_options(self):
    tool=self.available(self.v('signing','signtool') or detect_signtool())
    certificate=thumbprint(self.v('signing','thumbprint'))
    return tool,certificate,self.v('signing','timestamp'),self.signmode.currentIndex()==2
 def auto_options(self):
    return self.signing_options() if self.checked('signing','autosign') else None
 def sign_target(self,target,options,callback=None):
    tool,certificate,timestamp,machine=options
    args=sign_arguments(target,certificate,timestamp,machine)
    def signed(output):
      self.log.appendPlainText('Signature written: '+str(target)+'. Use Verify to check Windows trust; signing alone does not establish trust.')
      self.status.setText('Signed • Windows trust not yet verified')
      if callback:callback(output)
    self.start(tool,args,Path(target).parent,callback=signed,label='Signing…')
 def sign_selected(self):self.sign_target(self.v('signing','target'),self.signing_options())
 def verify_selected(self):
    tool=self.available(self.v('signing','signtool') or detect_signtool())
    def verified(output):self.status.setText('Signature verified • trusted by Windows on this PC')
    self.log.appendPlainText('Self-signed certificates normally fail trust verification. This does not mean the file is unsigned.')
    self.start(tool,verify_arguments(self.v('signing','target')),callback=verified,label='Verifying signature and Windows trust…')
 def build_java(self):
    signing=self.auto_options()
    tool=self.available(self.v('tools','launch4jc')); jar=require_file(self.v('java','source'),'.jar'); out=self.output('java'); name=safe_name(self.v('java','name')); release=out/name
    if release.exists() and any(release.iterdir()):raise ValueError('Release folder exists. Choose a new output folder or name.')
    release.mkdir(exist_ok=True); bundle=self.v('java','jre')
    if bundle:
      jre=Path(bundle).resolve()
      if not (jre/'bin/java.exe').is_file():raise ValueError('Java folder must contain bin/java.exe')
      if jre==release or jre in release.parents:raise ValueError('Java source cannot contain output folder')
      shutil.copytree(jre,release/'jre')
    # Include adjacent lib folder when present for manifest Class-Path JARs.
    if (jar.parent/'lib').is_dir():shutil.copytree(jar.parent/'lib',release/'lib')
    config=launch_config(jar,release/(name+'.exe'),self.v('java','icon'),self.v('java','minimum'),bool(bundle),self.checked('java','console'))
    self.last_output=str(release); target=release/(name+'.exe')
    self.start(tool,[str(config)],release,callback=(lambda output:self.sign_target(target,signing)) if signing else None)
 def build_python(self):
    signing=self.auto_options()
    py=self.available(self.v('tools','Python interpreter')); source=require_file(self.v('python','source'),'.py'); out=self.output('python'); name=safe_name(self.v('python','name'))
    if (out/'dist'/name).exists() or (out/'dist'/(name+'.exe')).exists():raise ValueError('Output exists. Select a new output folder or name.')
    args=['-m','PyInstaller','--noconfirm','--clean','--name',name,'--distpath',str(out/'dist'),'--workpath',str(out/'work'),'--specpath',str(out),'--onefile' if self.checked('python','onefile') else '--onedir']
    if not self.checked('python','console'):args+=['--windowed']
    if self.v('python','icon'):args+=['--icon',str(require_file(self.v('python','icon'),'.ico'))]
    if self.v('python','data'):
      data=Path(self.v('python','data')).resolve()
      if not data.is_dir():raise ValueError('Invalid data folder')
      if data==out or data in out.parents:raise ValueError('Data folder cannot contain build output')
      args+=['--add-data',str(data)+':'+data.name]
    for module in self.v('python','hidden').split(','):
      if module.strip():args+=['--hidden-import',module.strip()]
    args+=[str(source)]; self.last_output=str(out/'dist')
    target=out/'dist'/(name+'.exe') if self.checked('python','onefile') else out/'dist'/name/(name+'.exe')
    self.start(py,args,source.parent,callback=(lambda output:self.sign_target(target,signing)) if signing else None)
 def build_installer(self):
    signing=self.auto_options()
    tool=self.available(self.v('tools','ISCC')); out=self.output('installer'); folder=Path(self.v('installer','folder')).resolve()
    if not self.v('installer','folder') or not folder.is_dir():raise ValueError('Select a release folder')
    if out==folder or folder in out.parents:raise ValueError('Installer output must be outside the release folder')
    exe=self.v('installer','exe')
    if Path(exe).name!=exe or '/' in exe or '\\' in exe:raise ValueError('Enter EXE filename only')
    name=safe_name(self.v('installer','name'))
    script=inno_script(folder,exe,name,self.v('installer','version'),self.v('installer','publisher'),out,self.v('installer','icon'))
    target=out/(name+'_Setup.exe')
    def compile_installer(output=''):
      self.start(tool,[str(script)],out,callback=(lambda result:self.sign_target(target,signing)) if signing else None)
    if signing:self.sign_target(folder/exe,signing,compile_installer)
    else:compile_installer()
 def make_icon(self):
    out=self.output('icon'); name=safe_name(self.v('icon','name')); target=out/(name+'.ico')
    if target.exists():raise ValueError('ICO exists. Choose a new name.')
    convert_icon(self.v('icon','source'),target); self.log.appendPlainText(str(target)); self.status.setText('Success')
 def closeEvent(self,event):
    if self.busy:
      QMessageBox.information(self,'Running','Stop the current task before closing.'); event.ignore()
    else:self.save_settings(); event.accept()

def main():
 if os.name=='nt':
  import ctypes
  ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Khurkham.ExeBuilderStudio')
 app=QApplication(sys.argv); base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
 load_fonts()
 if FONT_ERRORS:QMessageBox.warning(None,'Embedded fonts','\n'.join(FONT_ERRORS))
 app.setStyleSheet('QWidget {background:#101c30; color:#e7edf7;} QLineEdit,QPlainTextEdit,QComboBox {background:#192b45; border:1px solid #355074; border-radius:5px; padding:6px;} QPushButton {background:#235e8e; border-radius:5px; padding:9px;} QPushButton:hover {background:#317bb4;} QPushButton:disabled {color:#8292a8;} QTabBar::tab {padding:12px; margin-right:5px; border:1px solid #355074; border-top-left-radius:12px; border-top-right-radius:12px; background:#192b45;} QTabBar::tab:selected {background:#235e8e; border-bottom:3px solid #7dcfff;} QProgressBar {border:1px solid #355074; border-radius:5px; text-align:center; min-height:20px;} QProgressBar::chunk {background:#43b6dd;}')
 app.setWindowIcon(QIcon(str(resource('app.ico'))))
 w=Window(); w.show(); sys.exit(app.exec())
if __name__=='__main__':main()
