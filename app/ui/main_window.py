"""Main application window for ExeBuilderStudio.

UI orchestration lives here; the root main.py remains the stable launcher.
"""
import sys, os, shutil, subprocess, tempfile, zipfile
from pathlib import Path
from PySide6.QtCore import QProcess, QSettings, QUrl, Qt, QObject, QThread, Signal
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QPushButton,QComboBox,QTabWidget,QPlainTextEdit,QFileDialog,QLabel,QMessageBox,QScrollArea,QLayout,QProgressBar)
from backend import *
from app.services.macos_builder import create_macos_build_kit
from app.services.windows_native_builder import build_windows_installer, resolve_jdk_home
from app.services.jdk_manager import discover_jdk_homes, validate_jdk_home
from app.services.macos_updates import MacUpdateCard
from app.services.universal_updates import UniversalUpdateCard
from download_ui import add_tool_card, add_about_updater
from tool_downloads import APP_VERSION
from ui_assets import resource, apply_font

# English, Thai, Shan. Labels are switched together; technical tool names stay unchanged.
from app.translations import T


class BuildWorker(QObject):
    """Build a native installer away from the UI thread and stream progress/log output."""
    progress = Signal(int, str)
    log = Signal(str)
    completed = Signal(bool, str, str)

    def __init__(self, *, target_os, kind, source, output, name, icon, interpreter,
                 compiler, jdk_home, overwrite):
        super().__init__()
        self.target_os = target_os
        self.kind = kind
        self.source = source
        self.output = output
        self.name = name
        self.icon = icon
        self.interpreter = interpreter
        self.compiler = compiler
        self.jdk_home = jdk_home
        self.overwrite = overwrite
        self._cancelled = False
        self._active_process = None

    def cancel(self):
        """Request cancellation and terminate the currently running build tool."""
        self._cancelled = True
        process = self._active_process
        if process is not None:
            try:
                process.terminate()
            except OSError:
                pass

    def set_active_process(self, process):
        self._active_process = process
        if process is not None and self._cancelled:
            try:
                process.terminate()
            except OSError:
                pass

    def _check_cancelled(self):
        if self._cancelled:
            raise RuntimeError('Build cancelled by user.')

    def _find_macos_python(self):
        """Find a real Python 3 interpreter for target-project packaging on macOS."""
        candidates = []
        if self.interpreter:
            selected = Path(self.interpreter).expanduser()
            # A frozen PyInstaller app executable is not a Python interpreter for venv creation.
            if selected.is_file() and not (getattr(sys, 'frozen', False) and selected.resolve() == Path(sys.executable).resolve()):
                candidates.append(selected)
        for command in (shutil.which('python3'), '/opt/homebrew/bin/python3', '/usr/local/bin/python3'):
            if command:
                candidates.append(Path(command))
        candidates.extend(sorted(Path('/Library/Frameworks/Python.framework/Versions').glob('*/bin/python3'), reverse=True))
        seen = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                if str(resolved) in seen or not resolved.is_file():
                    continue
                seen.add(str(resolved))
                result = subprocess.run([str(resolved), '--version'], capture_output=True, text=True, timeout=5)
                version_text = (result.stdout or result.stderr).strip()
                if result.returncode == 0 and version_text.startswith('Python 3.'):
                    return str(resolved)
            except (OSError, subprocess.SubprocessError):
                continue
        raise FileNotFoundError(
            'Python 3 was not found. Install Python 3.11 or 3.12 on this Mac, then retry the Python-to-DMG build.'
        )

    def run(self):
        """Run the selected native build and publish only a complete installer."""
        try:
            self.progress.emit(3, 'Validating build settings')
            source_path = Path(self.source).expanduser().resolve()
            if not source_path.exists():
                raise ValueError('Select a valid source file or project folder.')
            output_dir = Path(self.output).expanduser().resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            suffix = '_Setup.exe' if self.target_os == 'windows' else '_Setup.dmg'
            target = output_dir / f'{self.name}{suffix}'

            if self.target_os == 'windows':
                self.progress.emit(8, 'Starting Windows installer build')
                result = build_windows_installer(
                    kind=self.kind, source=self.source, output=str(output_dir), name=self.name,
                    icon=self.icon, interpreter=self.interpreter, compiler=self.compiler,
                    jdk_home=self.jdk_home, overwrite=self.overwrite,
                    log=lambda message: self.log.emit(str(message).rstrip()),
                    progress=lambda value, message: self.progress.emit(value, message),
                    process_callback=self.set_active_process,
                )
                self.completed.emit(True, str(result), str(output_dir))
                return

            # macOS packaging runs on a worker thread too, keeping the UI responsive.
            with tempfile.TemporaryDirectory(prefix='ebs_direct_build_') as temp:
                temp_path = Path(temp)
                self.progress.emit(10, 'Preparing macOS build files')
                kit = create_macos_build_kit(kind=self.kind, source=self.source,
                                             output=str(temp_path), name=self.name, icon=self.icon)
                with zipfile.ZipFile(kit) as archive:
                    archive.extractall(temp_path)
                kit_root = temp_path / f'{self.name}_macOS_Build_Kit'
                build_env = os.environ.copy()
                selected_jdk = self.jdk_home
                if not selected_jdk:
                    discovered = discover_jdk_homes()
                    if discovered:
                        selected_jdk = discovered[0][1]
                if selected_jdk:
                    valid, detail = validate_jdk_home(selected_jdk)
                    if not valid:
                        raise ValueError(detail)
                    selected = str(Path(selected_jdk).expanduser().resolve())
                    build_env['JAVA_HOME'] = selected
                    build_env['PATH'] = str(Path(selected) / 'bin') + os.pathsep + build_env.get('PATH', '')
                if self.kind == 'python':
                    build_env['EBS_PYTHON'] = self._find_macos_python()
                self.progress.emit(25, 'Building macOS application and runtime')
                process = subprocess.Popen(
                    ['/bin/bash', str(kit_root / 'build_macos.sh')], cwd=kit_root,
                    env=build_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                self.set_active_process(process)
                line_count = 0
                try:
                    if process.stdout is not None:
                        for line in process.stdout:
                            self.log.emit(line.rstrip())
                            line_count += 1
                            self.progress.emit(min(84, 30 + line_count), 'Building macOS installer (estimated)')
                    return_code = process.wait()
                finally:
                    self.set_active_process(None)
                    if process.stdout is not None:
                        process.stdout.close()
                self._check_cancelled()
                if return_code != 0:
                    raise RuntimeError(f'macOS installer build failed (exit code {return_code}). See the log for details.')
                dist = kit_root / 'dist'
                candidates = sorted(dist.glob('*_Setup.dmg')) or sorted(dist.glob('*.dmg'))
                if not candidates:
                    raise RuntimeError('Build finished without producing a DMG installer. Review the log.')
                self.progress.emit(90, 'Publishing installer')
                staged_target = output_dir / ('.' + target.name + '.new')
                try:
                    shutil.copy2(candidates[0], staged_target)
                    os.replace(staged_target, target)
                finally:
                    try:
                        staged_target.unlink(missing_ok=True)
                    except OSError:
                        pass
            self.progress.emit(100, 'Build complete')
            self.log.emit('Installer created successfully: ' + str(target))
            self.completed.emit(True, str(target), str(output_dir))
        except Exception as exc:
            message = 'Build cancelled by user.' if self._cancelled else str(exc)
            self.log.emit('Error: ' + message)
            self.completed.emit(False, message, self.output)


class Window(QMainWindow):
 def __init__(self):
    super().__init__(); self.settings=QSettings('Khurkham','ExeBuilderStudio'); self.labels=[]; self.fields={}; self.last_output=''; self.busy=False; self.tool_cards=[]; self.active_download=None
    self.resize(1080,820); root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root)
    head=QHBoxLayout(); self.logo=QLabel(); self.logo.setPixmap(QPixmap(str(resource("logo.png"))).scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation)); self.logo.setFixedSize(72,72); head.addWidget(self.logo); self.setWindowIcon(QIcon(str(resource("app.icns" if sys.platform == "darwin" and resource("app.icns").is_file() else "app.ico")))); self.title=QLabel(); head.addWidget(self.title); head.addStretch(); self.lang=QComboBox(); self.lang.addItems(['English','ไทย','တႆး']); self.lang.setCurrentIndex(int(self.settings.value('language',1))); head.addWidget(self.lang); layout.addLayout(head)
    # Main workflow tabs are grouped by target platform and task.
    self.tabs=QTabWidget(); layout.addWidget(self.tabs); self.pages={}
    # Keep one clear workflow per target platform; legacy EXE tabs duplicated the Windows setup flows.
    for key in ['win_java','win_python','mac_java','mac_python','icon','win_tools','mac_tools']:
      page=QWidget(); form=QFormLayout(page); form.setSizeConstraint(QLayout.SetMinimumSize); form.setVerticalSpacing(12); self.pages[key]=form
      scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page); self.tabs.addTab(scroll,key)
    # Build tabs collect the source, output location, application name, and optional icon.
    for page, kind in [('win_java', 'java'), ('win_python', 'python'), ('mac_java', 'java'), ('mac_python', 'python')]:
      self.field(page, 'source', kind='file' if kind == 'java' else 'project')
      self.field(page, 'output', kind='dir')
      self.field(page, 'name', default='MyApplication')
      self.field(page, 'icon', kind='image')
      note = QLabel(); note.setWordWrap(True)
      note_key = ('win_java_note' if kind == 'java' else 'win_python_note') if page.startswith('win_') else ('mac_java_note' if kind == 'java' else 'mac_python_note')
      self.labels.append((note, note_key)); self.pages[page].addRow(note)
      callback = (lambda p=page, k=kind: self.build_direct(p, k))
      button_key = 'buildwin' if page.startswith('win_') else 'buildmac'
      self.button(page, button_key, callback)
    # Logo converter supports both Windows ICO and macOS ICNS formats.
    self.field('icon','source',kind='image'); self.field('icon','output',kind='dir'); self.field('icon','name',default='app')
    self.icon_format = QComboBox(); self.icon_format.addItems(['Windows desktop icon (.ico)', 'macOS desktop icon (.icns)'])
    self.pages['icon'].addRow(QLabel('Output icon format'), self.icon_format)
    self.button('icon','convert',self.make_icon)
    # Keep tool paths internally for automatic detection and existing build services.
    # Users no longer need to edit executable paths manually.
    tool_defaults={
      'ISCC':self.detect('ISCC.exe',['Inno Setup 6/ISCC.exe','Inno Setup 7/ISCC.exe']),
      'Python interpreter':sys.executable if not getattr(sys,'frozen',False) else (shutil.which('python') or ''),
    }
    for key,default in tool_defaults.items():
      edit=QLineEdit(str(self.settings.value('tools/'+key,default)))
      self.fields['tools/'+key]=edit
    self.tools_intro=QLabel(); self.tools_intro.setWordWrap(True)
    self.pages['win_tools'].addRow(self.tools_intro)
    # Let users explicitly choose which installed JDK is used for Java installer builds.
    self.jdk_selector = QComboBox()
    self.jdk_selector.setMinimumContentsLength(28)
    self.jdk_refresh = QPushButton('Refresh JDK list')
    self.jdk_browse = QPushButton('Browse JDK folder…')
    jdk_row = QWidget(); jdk_layout = QHBoxLayout(jdk_row); jdk_layout.setContentsMargins(0, 0, 0, 0)
    jdk_layout.addWidget(self.jdk_selector, 1); jdk_layout.addWidget(self.jdk_refresh); jdk_layout.addWidget(self.jdk_browse)
    self.jdk_label = QLabel('JDK used for Java builds (JDK 17 or newer)')
    self.pages['win_tools'].addRow(self.jdk_label, jdk_row)
    self.jdk_selector.currentIndexChanged.connect(self.persist_jdk_selection)
    self.jdk_refresh.clicked.connect(self.refresh_jdk_choices)
    self.jdk_browse.clicked.connect(self.browse_jdk_folder)
    self.refresh_jdk_choices()
    # Windows-specific tool cards remain in their own tab.
    for key in ['java','inno','python','pyinstaller']:
      add_tool_card(self,key,self.pages['win_tools'])
    self.win_tool_rows = {}
    for tool_key, tool_title in [('wix', 'WiX Toolset (optional)'), ('ico', 'ICO icon conversion')]:
      value = QLabel('Checking…'); value.setWordWrap(True)
      self.win_tool_rows[tool_key] = value
      self.pages['win_tools'].addRow(tool_title + ':', value)
    # macOS tools have a local status row and explicit official-download/help action.
    self.mac_tools_note = QLabel(); self.mac_tools_note.setWordWrap(True)
    self.pages['mac_tools'].addRow(self.mac_tools_note)
    self.mac_tool_rows = {}
    self.mac_tool_links = {
      'java': ('Java JDK / jpackage', 'https://adoptium.net/temurin/releases/'),
      'python': ('Python 3', 'https://www.python.org/downloads/macos/'),
      'pyinstaller': ('PyInstaller', 'https://pyinstaller.org/en/stable/installation.html'),
      'xcode': ('Xcode Command Line Tools', 'https://developer.apple.com/xcode/resources/'),
      'hdiutil': ('hdiutil (DMG)', 'https://support.apple.com/guide/terminal/welcome/mac'),
      'icns': ('ICNS conversion', 'https://pillow.readthedocs.io/en/stable/'),
    }
    self.mac_tools_check_buttons = []
    for tool_key, (tool_title, url) in self.mac_tool_links.items():
      status = QLabel('Not checked yet'); status.setWordWrap(True)
      self.mac_tool_rows[tool_key] = status
      actions = QWidget(); actions_layout = QHBoxLayout(actions); actions_layout.setContentsMargins(0, 0, 0, 0)
      check_button = QPushButton('Check')
      check_button.clicked.connect(lambda checked=False, k=tool_key: self.check_mac_tool(k))
      download_button = QPushButton('Download / Help')
      download_button.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
      actions_layout.addWidget(check_button); actions_layout.addWidget(download_button)
      self.mac_tools_check_buttons.append(check_button)
      self.pages['mac_tools'].addRow(tool_title + ':', status)
      self.pages['mac_tools'].addRow(actions)
    self.mac_tools_refresh = QPushButton('Check all macOS tools')
    self.mac_tools_refresh.clicked.connect(self.refresh_platform_tools)
    self.pages['mac_tools'].addRow(self.mac_tools_refresh)
    self.refresh_platform_tools()
    about=QWidget(); box=QVBoxLayout(about); logo=QLabel(); logo.setPixmap(QPixmap(str(resource('logo.png'))).scaled(140,140,Qt.KeepAspectRatio,Qt.SmoothTransformation)); box.addWidget(logo); self.about_text=QLabel(); self.about_text.setWordWrap(True); box.addWidget(self.about_text); self.mac_update_note=None; self.mac_update_card=None
    # Preserve the original About metadata above all update controls.
    self.about_text.setText(
      f'EXE Builder Studio • Version {APP_VERSION}\n'
      'Developed by Khurkham Langkhur\n'
      'Java / Python EXE, Inno Setup, ICO\n'
      'Embedded fonts: TH Sarabun New / A J Kunheing E-T-M 05'
    )
    # Keep the original platform-specific About card and its existing controls.
    if sys.platform == 'darwin':
      self.mac_update_card=MacUpdateCard(); box.addWidget(self.mac_update_card)
    else:
      add_about_updater(self,box)
    # Add the cross-platform updater below the original About content; do not replace it.
    self.universal_update_card=UniversalUpdateCard(); box.addWidget(self.universal_update_card)
    box.addStretch(); about_scroll=QScrollArea(); about_scroll.setWidgetResizable(True); about_scroll.setWidget(about); self.about_index=self.tabs.addTab(about_scroll,'About')
    self.status=QLabel(); layout.addWidget(self.status)
    # Show a horizontal progress bar and current build phase so long builds feel responsive.
    self.progress_detail=QLabel('Ready')
    layout.addWidget(self.progress_detail)
    self.build_progress=QProgressBar(); self.build_progress.setRange(0,100); self.build_progress.setValue(0)
    # Keep the bar itself text-free: Qt may localize its built-in percentage digits.
    # The progress_detail label below renders percentages with Python's ASCII digits (0-9).
    self.build_progress.setFormat(''); self.build_progress.setVisible(False); layout.addWidget(self.build_progress)
    self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(10000); self.log.setMaximumHeight(200); layout.addWidget(self.log)
    self.build_thread=None; self.build_worker=None
    row=QHBoxLayout(); self.stop=QPushButton(); self.labels.append((self.stop,'stop')); self.stop.clicked.connect(self.cancel); row.addWidget(self.stop); self.open=QPushButton(); self.labels.append((self.open,'open')); self.open.clicked.connect(self.open_output); row.addWidget(self.open); layout.addLayout(row)
    self.process=QProcess(self); self.process.setProcessChannelMode(QProcess.MergedChannels); self.process.readyReadStandardOutput.connect(self.read_output); self.process.finished.connect(self.finished); self.process.errorOccurred.connect(self.process_error)
    self.on_success=None; self.process_output=''
    self.lang.currentIndexChanged.connect(self.translate); self.translate()
    # Only set JAVA_HOME when the detected executable belongs to a full JDK.
    # Oracle's Common Files\Java\javapath entry may expose java.exe without jpackage.
    java_path=str(self.settings.value('downloads/java/path',''))
    jdk_home=resolve_jdk_home(java_path) if os.name == 'nt' and java_path and Path(java_path).is_file() else ''
    if jdk_home:
      os.environ['JAVA_HOME']=jdk_home
      os.environ['PATH']=str(Path(jdk_home)/'bin')+os.pathsep+os.environ.get('PATH','')
 # Create a labeled input row and optional Browse button for a project field.
 # Build a labeled input row and wire file/folder selection where needed.
 def field(self, page, key, kind='text', default=''):
    label_key = key
    if page == 'win_python' or page == 'mac_python':
      if key == 'source': label_key = 'python_source'
    elif page == 'mac_java' and key == 'source':
      label_key = 'mac_java_source'
    elif page == 'mac_python' and key == 'source':
      label_key = 'mac_python_source'
    label_text = T.get(label_key, (label_key, label_key, label_key))[self.lang.currentIndex() if hasattr(self, 'lang') else 0]
    edit = QLineEdit(str(default))
    edit.setClearButtonEnabled(True)
    self.fields[f'{page}/{key}'] = edit
    if kind in ('file', 'project', 'dir', 'image'):
      browse = QPushButton(T['browse'][self.lang.currentIndex() if hasattr(self, 'lang') else 0])
      browse.clicked.connect(lambda checked=False, e=edit, k=kind, title=label_text: self.browse_field(e, k, title))
      row = QWidget(); row_layout = QHBoxLayout(row); row_layout.setContentsMargins(0,0,0,0); row_layout.addWidget(edit, 1); row_layout.addWidget(browse)
      self.pages[page].addRow(label_text, row)
    else:
      self.pages[page].addRow(label_text, edit)
    return edit

 # Open the appropriate native picker based on the selected field type.
 def browse_field(self, edit, kind, title):
    if kind == 'project':
      choice = QMessageBox(self); choice.setWindowTitle('Select Python source'); choice.setText('Choose a Python entry file or the whole project folder.')
      file_button = choice.addButton('Python file (.py)', QMessageBox.AcceptRole)
      folder_button = choice.addButton('Project folder', QMessageBox.ActionRole)
      choice.addButton(QMessageBox.Cancel); choice.exec()
      clicked = choice.clickedButton()
      if clicked == file_button:
        path = QFileDialog.getOpenFileName(self, title, edit.text(), 'Python files (*.py);;All files (*)')[0]
      elif clicked == folder_button:
        path = QFileDialog.getExistingDirectory(self, title, edit.text())
      else: return
    elif kind == 'dir':
      path = QFileDialog.getExistingDirectory(self, title, edit.text())
    else:
      filters = {'image':'Images (*.ico *.icns *.png *.jpg *.jpeg);;All files (*)', 'file':'Supported files (*.jar *.py *.exe *.msi *.iss);;All files (*)'}
      path = QFileDialog.getOpenFileName(self, title, edit.text(), filters.get(kind, 'All files (*)'))[0]
    if path: edit.setText(path)

 # Create a translated action button for the selected tab.
 def button(self, page, key, callback):
    label = T.get(key, (key,key,key))[self.lang.currentIndex() if hasattr(self, 'lang') else 0]
    widget = QPushButton(label); widget.clicked.connect(lambda checked=False: self.guard(callback))
    self.pages[page].addRow(widget)
    self.labels.append((widget, key))
    return widget

 # Read the text value of a field, returning an empty string when absent.
 def v(self, page, key):
    widget = self.fields.get(f'{page}/{key}')
    if widget is None: return ''
    if isinstance(widget, QLineEdit): return widget.text().strip()
    return ''

 # Run a UI action safely and show useful error details rather than crashing.
 def guard(self, callback):
    try:
      return callback()
    except Exception as exc:
      self.log.appendPlainText(f'Error: {exc}')
      self.status.setText('Failed')
      QMessageBox.warning(self, 'EXE Builder Studio', str(exc))


 def check_mac_tool(self, tool_key):
    """Check a macOS prerequisite locally; never attempts silent installation."""
    if sys.platform != 'darwin':
      message = 'Check this tool on a Mac; it cannot be detected from Windows.'
    elif tool_key == 'java':
      homes = []
      java_home = os.environ.get('JAVA_HOME', '')
      if java_home and (Path(java_home) / 'bin' / 'jpackage').is_file(): homes.append(java_home)
      root = Path('/Library/Java/JavaVirtualMachines')
      if root.exists(): homes.extend(str(p) for p in root.glob('*.jdk/Contents/Home') if (p / 'bin' / 'jpackage').is_file())
      message = homes[0] if homes else 'JDK 17+ with jpackage not detected'
    elif tool_key == 'python':
      executable = shutil.which('python3')
      if executable:
        try:
          result = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=5)
          message = (result.stdout or result.stderr).strip() or executable
        except Exception as exc: message = 'Found but could not query: ' + str(exc)
      else: message = 'Python 3 not detected'
    elif tool_key == 'pyinstaller':
      executable = shutil.which('python3')
      if not executable: message = 'Requires Python 3'
      else:
        try:
          result = subprocess.run([executable, '-m', 'PyInstaller', '--version'], capture_output=True, text=True, timeout=5)
          message = (result.stdout or result.stderr).strip() if result.returncode == 0 else 'Not installed'
        except Exception: message = 'Not installed'
    elif tool_key == 'xcode':
      message = 'Installed' if Path('/Library/Developer/CommandLineTools').exists() or Path('/Applications/Xcode.app').exists() else 'Not detected (only needed by some build dependencies)'
    elif tool_key == 'hdiutil':
      message = 'Available' if Path('/usr/bin/hdiutil').is_file() else 'Not available; macOS only'
    else:
      try:
        import PIL.Image
        message = 'Available (Pillow)' if sys.platform == 'darwin' else 'Pillow available; verify ICNS support on Mac'
      except Exception: message = 'Use the built-in converter when supported; otherwise see Pillow documentation'
    self.mac_tool_rows[tool_key].setText(message)
    return message

 def refresh_platform_tools(self):
    """Refresh both platform checklists without silently installing software."""
    for tool_key in self.mac_tool_rows:
      self.check_mac_tool(tool_key)
    if hasattr(self, 'win_tool_rows'):
      wix = shutil.which('wix') or shutil.which('wix.exe') or shutil.which('candle.exe')
      self.win_tool_rows['wix'].setText('Installed: ' + wix if wix else 'Optional; not detected')
      try:
        import PIL.Image
        ico_status = 'Available (Pillow)'
      except Exception:
        ico_status = 'Built-in conversion when supported; Pillow not detected'
      self.win_tool_rows['ico'].setText(ico_status)

 def refresh_jdk_choices(self, selected_path=None):
    """Refresh the selector with installed JDKs that include jpackage."""
    saved = selected_path or str(self.settings.value('tools/jdk_home', ''))
    self.jdk_selector.blockSignals(True)
    self.jdk_selector.clear()
    self.jdk_selector.addItem('Auto-detect JDK', '')
    for label, home in discover_jdk_homes():
      self.jdk_selector.addItem(label, home)
    if saved:
      match = next((i for i in range(self.jdk_selector.count())
                    if str(self.jdk_selector.itemData(i) or '') == str(Path(saved).expanduser())), -1)
      if match < 0:
        valid, version = validate_jdk_home(saved)
        if valid:
          self.jdk_selector.addItem(f'JDK {version} — {saved}', str(Path(saved).expanduser()))
          match = self.jdk_selector.count() - 1
      self.jdk_selector.setCurrentIndex(match if match >= 0 else 0)
    else:
      self.jdk_selector.setCurrentIndex(0)
    self.jdk_selector.blockSignals(False)
    self.persist_jdk_selection()

 def persist_jdk_selection(self, *_):
    """Persist the selected JDK home; empty means automatic discovery."""
    if not hasattr(self, 'jdk_selector'):
      return
    self.settings.setValue('tools/jdk_home', str(self.jdk_selector.currentData() or ''))

 def browse_jdk_folder(self):
    """Allow selecting a specific JDK installation folder manually."""
    folder = QFileDialog.getExistingDirectory(self, 'Select JDK home folder', self.jdk_selector.currentData() or '')
    if not folder:
      return
    valid, version = validate_jdk_home(folder)
    if not valid:
      QMessageBox.warning(self, 'Invalid JDK folder', version)
      return
    self.refresh_jdk_choices(folder)
    self.log.appendPlainText(f'Selected JDK {version}: {folder}')

 def selected_jdk_home(self):
    """Return the chosen JDK home or an empty string for auto-detection."""
    return str(self.jdk_selector.currentData() or '') if hasattr(self, 'jdk_selector') else ''

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
    self.tools_intro.setText([
      'Build native installers only on their target operating system. Windows builds *_Setup.exe; macOS builds *_Setup.dmg. No cloud build, GitHub repository, or token is required. Launch4j is not required.',
      'ให้สร้างตัวติดตั้งบนระบบปฏิบัติการเป้าหมายเท่านั้น: Windows สร้าง *_Setup.exe และ Mac สร้าง *_Setup.dmg ไม่ใช้ Cloud Build, GitHub Repository หรือ Token และไม่จำเป็นต้องใช้ Launch4j',
      'သၢင်ႈ installer ၼိူဝ် OS ဢၼ်မႅၼ်ႈၵၼ်ၵူၺ်း: Windows သၢင်ႈ *_Setup.exe၊ Mac သၢင်ႈ *_Setup.dmg။ ဢမ်ႇၸႂ်ႉ Cloud Build၊ GitHub Repository၊ ဢမ်ႇလူဝ်ႇ Launch4j'
    ][self.lang.currentIndex()])
    self.jdk_label.setText(['JDK used for Java builds (JDK 17 or newer)', 'JDK ที่ใช้สร้างตัวติดตั้ง Java (JDK 17 ขึ้นไป)', 'JDK ဢၼ်ၸႂ်ႉသၢင်ႈ Java (JDK 17 ၶိုၼ်ႈၵႂႃႇ)'][i])
    self.jdk_refresh.setText(['Refresh JDK list', 'ค้นหา JDK อีกครั้ง', 'ၸႅတ်ႈထတ်း JDK ထႅင်ႈ'][i])
    self.jdk_browse.setText(['Browse JDK folder…', 'เลือกโฟลเดอร์ JDK…', 'လိူၵ်ႈၾူဝ်ႇလ်ႇတိူဝ်ႇ JDK…'][i])
    self.mac_tools_note.setText([
      'macOS prerequisites are listed separately. Use Check to inspect this Mac and Download / Help to open the official vendor page. hdiutil is built into macOS; Xcode tools are only needed by some dependencies.',
      'รายการเครื่องมือ macOS แยกไว้ด้านล่าง กดตรวจสอบเพื่อตรวจบน Mac และกดดาวน์โหลด/คู่มือเพื่อเปิดเว็บไซต์ทางการ hdiutil มีมากับ macOS ส่วน Xcode จำเป็นเฉพาะบาง Dependencies',
      'macOS ၶိူင်ႈမိုဝ်းၸႅၵ်ႇဝႆႉတၢင်းတႂ်ႈ။ ၸႅတ်ႈထတ်းတႃႇတူၺ်းၼိူဝ် Mac၊ Download / Help တေပိုတ်ႇဝႅပ်ႉတၢင်းၵၢၼ်။ hdiutil မီးမႃးၸွမ်း macOS'
    ][i])
    self.mac_tools_refresh.setText(['Check all macOS tools', 'ตรวจสอบเครื่องมือ macOS ทั้งหมด', 'ၸႅတ်ႈထတ်းၶိူင်ႈမိုဝ်း macOS တင်းသဵင်ႈ'][i])
    for button in self.mac_tools_check_buttons:
      button.setText(['Check', 'ตรวจสอบ', 'ၸႅတ်ႈထတ်း'][i])
    self.about_text.setText([
      f'EXE Builder Studio • Version {APP_VERSION}\nDeveloped by Khurkham Langkhur\nJava / Python EXE, Inno Setup, ICO\nEmbedded fonts: TH Sarabun New / A J Kunheing E-T-M 05',
      f'EXE Builder Studio • เวอร์ชัน {APP_VERSION}\nผู้พัฒนา: Khurkham Langkhur\nJava / Python EXE, Inno Setup, ICO\nฟอนต์ที่ฝัง: TH Sarabun New / A J Kunheing E-T-M 05',
      f'EXE Builder Studio • ဝႃးသျိၼ်း {APP_VERSION}\nၽူႈသၢင်ႈ: Khurkham Langkhur\nJava / Python EXE, Inno Setup, ICO\nၾွၼ်ႉ: TH Sarabun New / A J Kunheing E-T-M 05'
    ][i])
    if self.mac_update_card is not None:
      self.mac_update_card.set_language(i)
    if getattr(self, 'universal_update_card', None) is not None:
      self.universal_update_card.set_language(i)
 # Persist normal UI settings and clear obsolete settings from older versions.
 def save_settings(self):
    for key,w in self.fields.items():
      if isinstance(w,QLineEdit):self.settings.setValue(key,w.text())
    self.settings.remove('remote_macos/repository')
    self.log.appendPlainText('Settings saved.')
 def output(self,page):
    value=self.v(page,'output')
    if not value:raise ValueError('Select an output folder')
    p=Path(value).resolve(); p.mkdir(parents=True,exist_ok=True); self.last_output=str(p); return p
 def available(self,path):return str(require_file(path,'.exe'))
 # Start a local process without blocking the Qt event loop.
 def start(self,exe,args,cwd=None,callback=None,label=None):
    # Tool installation and process launching are kept separate from native installer builds.
    if os.name!='nt':raise ValueError('This tool action is supported on Windows only.')
    self.save_settings(); self.busy=True; self.tabs.setEnabled(False); self.status.setText(label or 'Running…')
    self.on_success=callback; self.process_output=''
    self.stop.setEnabled(True)
    self.log.appendPlainText(exe+' '+repr(args)); self.process.setWorkingDirectory(str(cwd or Path.cwd())); self.process.start(exe,args)
 def read_output(self):
    value=bytes(self.process.readAllStandardOutput()).decode('utf-8',errors='replace')
    self.process_output+=value
    if value:self.log.appendPlainText(value)
 def process_error(self,error):
    self.log.appendPlainText(self.process.errorString())
    if self.process.state()==QProcess.NotRunning:
      self.on_success=None; self.unlock('Failed')
 def unlock(self,text):self.busy=False; self.tabs.setEnabled(True); self.stop.setEnabled(True); self.status.setText(text)
 # Unlock the interface after a process exits; run follow-up steps only on success.
 def finished(self,code,status):
    self.read_output(); callback=self.on_success; self.on_success=None
    ok=code==0 and status==QProcess.NormalExit
    self.unlock('Success' if ok else f'Failed / stopped ({code}); following steps skipped')
    self.log.appendPlainText(self.status.text())
    if ok and callback:self.guard(lambda:callback(self.process_output))
 def cancel(self):
    if self.active_download and self.active_download.worker:
      self.active_download.worker.cancel()
    elif self.build_worker is not None:
      self.progress_detail.setText('Stopping build…')
      self.build_worker.cancel()
    elif self.busy:
      self.process.kill()
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
 def build_direct(self, page, kind):
    """Validate a native build request, then run it in a background thread."""
    # Enforce native builds: Windows creates EXE installers, while macOS creates DMG installers.
    target_os = 'windows' if page.startswith('win_') else 'macos'
    host_os = 'windows' if os.name == 'nt' else ('macos' if sys.platform == 'darwin' else 'linux')
    if target_os != host_os:
      if target_os == 'windows' and host_os == 'macos':
        QMessageBox.warning(self, 'Build Setup.exe on Windows',
          'กรุณาไปสร้างไฟล์ Setup.exe บนเครื่อง Windows เท่านั้น\n\nPlease build the Windows .exe installer on a Windows computer.')
        return
      if target_os == 'macos' and host_os == 'windows':
        QMessageBox.warning(self, 'Build Setup.dmg on Mac',
          'กรุณาไปสร้างไฟล์ Setup.dmg บนเครื่อง Mac เท่านั้น\n\nPlease build the macOS .dmg installer on a Mac computer.')
        return
      target_label = 'Windows' if target_os == 'windows' else 'macOS'
      host_label = 'Windows' if host_os == 'windows' else ('macOS' if host_os == 'macos' else 'Linux')
      QMessageBox.warning(self, 'Unsupported build platform',
        f'กรุณาสร้างตัวติดตั้ง {target_label} บนเครื่อง {target_label} เท่านั้น\n\nCannot build a native {target_label} installer on {host_label}.')
      return
    if self.busy:
      QMessageBox.information(self, 'Build in progress', 'Please wait for the current task to finish.')
      return
    source = self.v(page, 'source')
    output = self.output(page)
    name = safe_name(self.v(page, 'name') or 'MyApplication')
    icon = self.v(page, 'icon')
    suffix = '_Setup.exe' if target_os == 'windows' else '_Setup.dmg'
    target = output / f'{name}{suffix}'
    overwrite = False
    if target.exists():
      answer = QMessageBox.question(
        self, 'Installer already exists',
        f'The output file already exists:\n{target}\n\nReplace it after the new build succeeds?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
      )
      if answer != QMessageBox.Yes:
        self.status.setText('Build cancelled; existing installer was kept.')
        self.log.appendPlainText('Build cancelled because the output file already exists: ' + str(target))
        return
      overwrite = True

    self.save_settings()
    self.busy = True
    self.tabs.setEnabled(False)
    self.stop.setEnabled(True)
    self.build_progress.setValue(0)
    self.build_progress.setVisible(True)
    self.progress_detail.setText('Starting build… (percentage is an estimate)')
    self.status.setText('Building installer…')
    self.log.appendPlainText('Starting installer build: ' + str(target))

    self.build_thread = QThread(self)
    self.build_worker = BuildWorker(
      target_os=target_os, kind=kind, source=source, output=str(output), name=name, icon=icon,
      interpreter=self.v('tools', 'Python interpreter') or sys.executable,
      compiler=self.v('tools', 'ISCC') or self.detect('ISCC.exe', ['Inno Setup 6/ISCC.exe','Inno Setup 7/ISCC.exe']),
      jdk_home=self.selected_jdk_home(), overwrite=overwrite
    )
    self.build_worker.moveToThread(self.build_thread)
    self.build_thread.started.connect(self.build_worker.run)
    self.build_worker.progress.connect(self.update_build_progress)
    self.build_worker.log.connect(self.log.appendPlainText)
    self.build_worker.completed.connect(self.build_finished)
    self.build_worker.completed.connect(self.build_thread.quit)
    self.build_thread.finished.connect(self.build_worker.deleteLater)
    self.build_thread.finished.connect(self.clear_build_thread)
    self.build_thread.start()

 def update_build_progress(self, value, message):
    """Update the horizontal progress bar from worker-thread progress signals."""
    self.build_progress.setValue(max(0, min(100, int(value))))
    self.progress_detail.setText(f'{message} — {self.build_progress.value()}% (estimated)')

 def build_finished(self, success, detail, output):
    """Restore the UI and report the worker's final result."""
    self.busy = False
    self.tabs.setEnabled(True)
    self.stop.setEnabled(True)
    self.last_output = output
    if success:
      self.build_progress.setValue(100)
      self.progress_detail.setText('Build complete — 100%')
      self.status.setText('Installer created successfully')
      self.log.appendPlainText('Installer created successfully: ' + detail)
      QMessageBox.information(self, 'Build complete', 'Installer created successfully:\n' + detail)
    else:
      self.progress_detail.setText('Build stopped before completion — progress is approximate')
      self.status.setText('Cancelled' if 'cancelled' in detail.lower() else 'Failed')
      if 'cancelled' not in detail.lower():
        QMessageBox.warning(self, 'Build failed', detail)

 def clear_build_thread(self):
    """Release worker references after QThread has stopped."""
    self.build_worker = None
    self.build_thread = None

 # Manual Installer-tab workflow removed; builds now flow directly to Setup.exe.
 def make_icon(self):
    # Convert a source image into the platform-specific desktop icon format.
    out=self.output('icon'); name=safe_name(self.v('icon','name'))
    suffix = '.ico' if self.icon_format.currentIndex() == 0 else '.icns'
    target=out/(name+suffix)
    if target.exists():raise ValueError(f'{suffix} file already exists. Choose a new name or output folder.')
    convert_icon(self.v('icon','source'),target); self.log.appendPlainText(str(target)); self.status.setText('Success')
 def closeEvent(self,event):
    if self.busy:
      QMessageBox.information(self,'Running','Stop the current task before closing.'); event.ignore()
    else:self.save_settings(); event.accept()
