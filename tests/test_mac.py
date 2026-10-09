import os, plistlib, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import mac_backend as mac

class MacPlans(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.tool=self.root/'python3';self.tool.write_text('tool');self.tool.chmod(0o755)
        self.source=self.root/'main.py';self.source.write_text('print(1)')
    def tearDown(self):self.tmp.cleanup()
    def plan(self,**kw):
        values=dict(python=str(self.tool),source=str(self.source),output=str(self.root/'out'),name='My App',identifier='com.khurkham.app');values.update(kw)
        with patch('mac_backend.sys.platform','darwin'):return mac.python_plan(**values)
    @unittest.skipIf(os.name=='nt', 'Unix interpreter symlink semantics')
    def test_virtual_environment_interpreter_symlink_preserved(self):
        venv=self.root/'venv/bin';venv.mkdir(parents=True);link=venv/'python3';link.symlink_to(self.tool)
        self.assertEqual(mac.executable(str(link)),str(link))

    def test_cross_build_rejected(self):
        with patch('mac_backend.sys.platform','win32'),self.assertRaises(ValueError):mac.require_mac()
    def test_app_arguments_and_data_with_spaces(self):
        data=self.root/'my assets';data.mkdir()
        _,args,_,target=self.plan(data=str(data),architecture='arm64',identity='Developer ID Application: Name')
        self.assertIn('--windowed',args);self.assertIn('--onedir',args);self.assertNotIn('--onefile',args)
        self.assertIn(str(data)+':my assets',args);self.assertEqual(target.name,'My App.app')
        self.assertIn('Developer ID Application: Name',args)
    def test_data_output_recursion_rejected(self):
        with self.assertRaises(ValueError):self.plan(data=str(self.root),output=str(self.root/'out'))
    def test_invalid_identifier_and_architecture(self):
        for kw in [{'identifier':'bad id'},{'architecture':'bad'}]:
            with self.assertRaises(ValueError):self.plan(**kw)
    def test_existing_app_not_overwritten(self):
        (self.root/'out/dist/My App.app').mkdir(parents=True)
        with self.assertRaises(ValueError):self.plan()
    def test_java_stages_dependencies_without_copying_output(self):
        folder=self.root/'jars';folder.mkdir();(folder/'app.jar').write_bytes(b'jar')
        with patch('mac_backend.sys.platform','darwin'):
            _,args,_,target=mac.java_plan(str(self.tool),str(folder),'app.jar',str(self.root/'out'),'Game','com.khurkham.game')
            self.assertIn(str(folder),args);self.assertEqual(target.name,'Game.app')
            with self.assertRaises(ValueError):mac.java_plan(str(self.tool),str(folder),'../app.jar',str(self.root/'out'),'Game','com.khurkham.game')
    def test_dmg_staging_and_applications_shortcut(self):
        app=self.root/'Game.app';(app/'Contents/MacOS').mkdir(parents=True)
        with open(app/'Contents/Info.plist','wb') as f:plistlib.dump({'CFBundleName':'Game'},f)
        def run(args,**kwargs):
            stage=Path(args[args.index('-srcfolder')+1]);self.assertEqual(sorted(p.name for p in stage.iterdir()),['Applications','Game.app'])
            self.assertEqual(os.readlink(stage/'Applications'),'/Applications')
            return type('Result',(),{'stdout':'done'})()
        with patch('mac_backend.sys.platform','darwin'),patch('mac_backend.shutil.which',return_value='/usr/bin/hdiutil'),patch('mac_backend.subprocess.run',side_effect=run):
            self.assertEqual(mac.build_dmg(str(app),str(self.root/'out'),'Game'),'done')
    def test_invalid_app_rejected(self):
        with self.assertRaises(ValueError):mac.require_app(self.root)
    def test_icns_contains_multiple_sizes(self):
        from PIL import Image
        image=self.root/'logo.png';Image.new('RGBA',(100,200),'blue').save(image)
        target=self.root/'icon.icns';mac.convert_icns(image,target)
        with Image.open(target) as im:self.assertEqual(im.format,'ICNS');self.assertGreater(len(im.info['sizes']),3)
