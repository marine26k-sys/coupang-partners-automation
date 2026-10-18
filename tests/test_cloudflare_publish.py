from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cloudflare_publish

class PublicPackageTests(unittest.TestCase):
    def test_only_allowlisted_public_files_and_no_store_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir()
            for name in cloudflare_publish.ASSETS:(source/name).write_text('public')
            (source/'.env').write_text('SECRET=private')
            (source/'history.sqlite3').write_text('private')
            target=Path(folder)/'out'
            with patch.object(cloudflare_publish,'PUBLIC',source):cloudflare_publish.prepare(target)
            self.assertEqual({p.name for p in target.iterdir()},set(cloudflare_publish.ASSETS)|{'_headers'})
            self.assertIn('Cache-Control: no-store',(target/'_headers').read_text())
