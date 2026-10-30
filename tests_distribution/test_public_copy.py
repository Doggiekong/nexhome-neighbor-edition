"""Public wording contracts without changing wire keys, actions or state names."""
import ast
import json
import re
import subprocess
from pathlib import Path

from neighbor_launcher.copy import PHASE_LABELS, SCREENS

ROOT = Path(__file__).resolve().parents[1]
BASE = 'ba7a077e473fd03f198c8ed0bb6e0e6ad448d68e'


def previous(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE + ':' + path]).decode()


def shape(value):
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    return sorted(re.findall(r'\{[^{}]+\}', value))


def test_native_translations_keep_keys_and_placeholders():
    strings = json.loads((ROOT / 'custom_components/nexhome/strings.json').read_text())
    for name in ['en', 'zh-Hans']:
        value = json.loads((ROOT / f'custom_components/nexhome/translations/{name}.json').read_text())
        assert shape(value) == shape(strings)
        assert shape(value) == shape(json.loads(previous(f'custom_components/nexhome/translations/{name}.json')))
    text = (ROOT / 'custom_components/nexhome/translations/zh-Hans.json').read_text()
    for forbidden in ['Advanced local', 'Choose a gateway', 'Cannot initialize', 'Local gateway', 'Gateway']:
        assert forbidden not in text


def test_public_main_copy_has_no_internal_status_or_retired_footer():
    public = '\n'.join(' '.join(values) for values in SCREENS.values()) + '\n'.join(PHASE_LABELS.values())
    public += (ROOT / 'neighbor_launcher/web/index.html').read_text()
    manual = (ROOT / 'docs/安装与使用指南.md').read_text()
    for forbidden in ['READY', 'Installer Core', 'CONTROL_VERIFIED', '尚未向真实住户发布', '组件已部署', 'Pilot']:
        assert forbidden not in public
        assert forbidden not in manual
    assert '门锁' in manual and '多成员家庭' in manual and '不要删除' in manual
    assert '官方Home Assistant App' in manual


def test_readme_install_routes_precede_technical_section():
    text = (ROOT / 'README.md').read_text()
    main = text.split('## 技术说明')[0]
    assert 'supervisor_add_addon_repository' in main
    assert '安装与使用指南.md#route-b' in main
    for word in ['Installer Core', 'RECOVERY_REQUIRED', 'SHA256', 'runtime', 'entry', 'ownership']:
        assert word not in main


class WithoutText(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(ast.Constant(value='<text>'), node)
        return node


def test_edited_python_execution_structure_unchanged():
    paths = ['distribution/terminal.py', 'neighbor_launcher/bootstrap.py',
             'neighbor_launcher/controller.py', 'neighbor_launcher/copy.py',
             'custom_components/nexhome/const.py', 'custom_components/nexhome/config_flow.py']
    for path in paths:
        before = ast.dump(WithoutText().visit(ast.parse(previous(path))))
        after = ast.dump(WithoutText().visit(ast.parse((ROOT / path).read_text())))
        assert before == after, path


def test_all_installer_and_device_behavior_files_byte_identical():
    paths = list((ROOT / 'neighbor_installer').glob('*.py'))
    paths += [p for p in (ROOT / 'custom_components/nexhome').glob('*.py')
              if p.name not in {'const.py', 'config_flow.py'}]
    for path in paths:
        assert path.read_bytes() == previous(path.relative_to(ROOT).as_posix()).encode(), path


def test_web_actions_and_dom_ids_unchanged():
    js = (ROOT / 'neighbor_launcher/web/app.js').read_text()
    old = previous('neighbor_launcher/web/app.js')
    assert js == old.replace('友邻加强版 ${s.product_version} · 基于官方组件 ${s.upstream_base_version}',
                             '友邻加强版 ${s.product_version}')
    html = (ROOT / 'neighbor_launcher/web/index.html').read_text()
    assert re.findall(r'id="([^"]+)"', html) == re.findall(r'id="([^"]+)"', previous('neighbor_launcher/web/index.html'))
