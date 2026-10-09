import io, hashlib, os, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tool_downloads as td
class Response(io.BytesIO):
    def __init__(self,data,total=None,ctype='application/octet-stream'):
        super().__init__(data);self.headers={'Content-Length':str(len(data) if total is None else total),'Content-Type':ctype}
class DownloadTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def release(self,**kwargs):return dict(url='https://www.python.org/test.exe',name='test.exe',kind='exe',**kwargs)
    def test_stream_progress_and_hash(self):
        data=b'MZ'+b'x'*300000;seen=[]
        with patch.object(td,'open_url',return_value=Response(data)):
            path=td.download(self.release(sha256=hashlib.sha256(data).hexdigest()),self.root,lambda d,t:seen.append((d,t)))
        self.assertEqual(path.read_bytes(),data);self.assertEqual(seen[-1],(len(data),len(data)));self.assertGreater(len(seen),2)
    def test_checksum_failure_deletes_partial_and_keeps_previous_file(self):
        (self.root/'test.exe').write_bytes(b'previous')
        with patch.object(td,'open_url',return_value=Response(b'MZtest')):
            with self.assertRaisesRegex(ValueError,'checksum'):td.download(self.release(sha256='0'*64),self.root)
        self.assertFalse((self.root/'test.exe.part').exists());self.assertEqual((self.root/'test.exe').read_bytes(),b'previous')
    def test_cancel_never_publishes_partial(self):
        with patch.object(td,'open_url',return_value=Response(b'MZtest')):
            with self.assertRaises(td.Cancelled):td.download(self.release(),self.root,cancel=lambda:True)
        self.assertFalse(list(self.root.iterdir()))
    def test_webpage_and_truncated_download_rejected(self):
        for response in [Response(b'<html/>',ctype='text/html'),Response(b'MZtest',total=20)]:
            with patch.object(td,'open_url',return_value=response):
                with self.assertRaises(ValueError):td.download(self.release(),self.root)
            self.assertFalse(list(self.root.iterdir()))
    def test_unknown_total_still_downloads(self):
        with patch.object(td,'open_url',return_value=Response(b'MZtest',total=0)):
            self.assertTrue(td.download(self.release(),self.root).is_file())
    def test_zip_traversal_rejected(self):
        path=self.root/'bad.zip'
        with zipfile.ZipFile(path,'w') as z:z.writestr('../escape.exe',b'MZ')
        with patch.object(td,'app_data',return_value=self.root):
            with self.assertRaisesRegex(ValueError,'Unsafe'):td.extract_tool(path,'launch4j','3.50')
        self.assertFalse((self.root/'escape.exe').exists())
    def test_managed_java_extract_keeps_existing_version(self):
        path=self.root/'java.zip'
        with zipfile.ZipFile(path,'w') as z:z.writestr('jdk/bin/java.exe',b'MZtest')
        with patch.object(td,'app_data',return_value=self.root):
            a=td.extract_tool(path,'java','25.0.1');b=td.extract_tool(path,'java','25.0.1')
        self.assertNotEqual(a,b);self.assertTrue(Path(a).is_file());self.assertTrue(Path(b).is_file())
    def test_inno_latest_and_python_stable_architecture(self):
        inno='<a href="https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe">GitHub</a>'
        python='<a href="https://www.python.org/ftp/python/3.14.8/python-3.14.8-amd64.exe">Windows installer</a><a href="https://www.python.org/ftp/python/3.15.0/python-3.15.0-amd64.exe">Windows installer</a><a href="https://www.python.org/ftp/python/3.16.0/python-3.16.0rc1-amd64.exe">Preview</a>'
        with patch.object(td,'fetch',side_effect=[inno,python]),patch.object(td,'arch',return_value='x64'):
            self.assertEqual(td.resolve_release('inno')['version'],'7.1.0');self.assertEqual(td.resolve_release('python')['version'],'3.15.0')
    def test_java_release_uses_provider_checksum(self):
        result=[{'version':{'semver':'25.0.1+8'},'binary':{'package':{'name':'jdk.zip','link':'https://github.com/adoptium/jdk.zip','checksum':'a'*64}}}]
        with patch.object(td,'fetch',return_value=result):self.assertEqual(td.resolve_release('java')['sha256'],'a'*64)
    def test_sdk_stable_installer_and_launch4j_rss(self):
        sdk='Windows SDK (10.0.28000.2957) <a href="https://go.microsoft.com/fwlink/?linkid=123">Installer</a>'
        rss='<link>https://sourceforge.net/projects/launch4j/files/launch4j-3/3.50/launch4j-3.50-win32.zip/download</link>'
        with patch.object(td,'fetch',side_effect=[sdk,rss]):
            self.assertEqual(td.resolve_release('sdk')['version'],'10.0.28000.2957');self.assertEqual(td.resolve_release('launch4j')['url'],'https://downloads.sourceforge.net/project/launch4j/launch4j-3/3.50/launch4j-3.50-win32.zip')
    def test_self_update_requires_repository_and_asset_digest(self):
        with self.assertRaisesRegex(ValueError,'repository'):td.github_release('')
        with patch.object(td,'fetch',return_value={'assets':[{'name':'ExeBuilderStudio_Setup.exe','browser_download_url':'https://github.com/test.exe'}],'tag_name':'v1.1'}):
            with self.assertRaisesRegex(ValueError,'digest'):td.github_release('Owner/Repo')
        with patch.object(td,'fetch',return_value={'assets':[{'name':'ExeBuilderStudio_Setup.exe','browser_download_url':'https://github.com/test.exe','digest':'sha256:'+'a'*64}],'tag_name':'v1.1'}):
            self.assertEqual(td.github_release('https://github.com/Owner/Repo')['version'],'1.1')
    def test_configured_tool_is_checked_before_search_and_timeout_is_not_missing(self):
        path=self.root/'java.exe';path.write_bytes(b'MZ')
        with patch.object(td,'run_capture',return_value='java version "25.0.3"'),patch('backend.java_candidates') as search:
            result=td.detect_tool('java',str(path))
        self.assertTrue(result['found']);search.assert_not_called()
        with patch.object(td,'run_capture',side_effect=td.subprocess.TimeoutExpired('java',5)):
            self.assertTrue(td.detect_tool('java',str(path))['found'])
    def test_https_only(self):
        for value in ['http://example.com/file.exe','file:///etc/passwd','https://user:secret@example.com/file']:
            with self.assertRaises(ValueError):td.validate_url(value)
if __name__=='__main__':unittest.main()
