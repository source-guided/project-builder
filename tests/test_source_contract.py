import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/"plugins/project-builder"
sys.path.insert(0,str(ROOT/"scripts"))
from validate_source import validate_source
from validate import validate
from package import package


def fixture(root):
    (root/"capabilities/example").mkdir(parents=True)
    (root/"references").mkdir()
    (root/"capabilities/example/SKILL.md").write_text('---\nname: example\ndescription: A source-only example capability.\n---\n\nUse [references](../../references/index.json).\n')
    (root/"source.json").write_text(json.dumps({'format':1,'id':'example','version':'1.0.0','role':'fixture','exposure':'source-only','contract':'project-builder.source/v1','entry':'references/index.json','capabilities':['capabilities/example/SKILL.md']}))
    (root/"references/index.json").write_text(json.dumps({'format':1,'entries':[{'id':'example','label':'Example','kind':'source','access':'relative','locator':'../capabilities/example/SKILL.md','topics':[]}]}))
    (root/"source-files.json").write_text(json.dumps(['source.json','source-files.json','references/index.json','capabilities/example/SKILL.md']))


class SourceContractTest(unittest.TestCase):
    def test_source_capability_is_reachable_but_not_a_global_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root)
            self.assertEqual(validate_source(root)['exposure'],'source-only')

    def test_source_rejects_plugin_and_global_skill_exports(self):
        for name in ('plugin.json','skills','plugins','.agents/skills','.agents/plugins','.codex/skills'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);fixture(root);path=root/name
                if path.suffix:path.write_text('{}')
                else:path.mkdir(parents=True)
                with self.assertRaisesRegex(ValueError,'global skills'):validate_source(root)

    def test_source_capability_cannot_hide_host_registration_or_escape_its_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';fixture(root)
            agents=root/'capabilities/example/agents';agents.mkdir()
            with self.assertRaisesRegex(ValueError,'host discovery'):validate_source(root)
            agents.rmdir();outside=root.parent/'outside.md';outside.write_text('other owner')
            data=json.loads((root/'references/index.json').read_text());data['entries'][0]['locator']='../../outside.md';(root/'references/index.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'escapes'):validate_source(root)

    def test_core_rejects_a_bundled_domain_skill_even_when_allowlisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'plugins/project-builder';shutil.copytree(PLUGIN,target);shutil.copytree(ROOT/'.agents',root/'.agents')
            extra=target/'skills/domain/SKILL.md';extra.parent.mkdir();extra.write_text('---\nname: domain\ndescription: Extra role\n---\n')
            allowed=json.loads((target/'package-files.json').read_text());allowed.append('skills/domain/SKILL.md');(target/'package-files.json').write_text(json.dumps(allowed))
            with self.assertRaisesRegex(AssertionError,'Only the reference entry'):validate(root)

    def test_extracted_core_runs_without_role_sources_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'core.zip';package(archive,PLUGIN)
            destination=root/'isolated';destination.mkdir()
            with zipfile.ZipFile(archive) as bundle:
                names=bundle.namelist();bundle.extractall(destination)
            self.assertEqual([n for n in names if n.endswith('SKILL.md')],['skills/start/SKILL.md'])
            self.assertFalse(any(n.startswith('capabilities/') for n in names))
            command="import sys,urllib.request;sys.path.insert(0,'scripts');from source_connections import offers;urllib.request.OpenerDirector.open=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network'));print(len(offers()))"
            result=subprocess.run([sys.executable,'-c',command],cwd=destination,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'5')


if __name__=='__main__':unittest.main()
