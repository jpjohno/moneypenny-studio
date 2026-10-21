"""Opening captured meshes must not execute embedded Blender source scripts."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def launcher(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/launch_blender.py'
    spec = importlib.util.spec_from_file_location('blender_launcher_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / 'captured study.blend'
    source.write_bytes(b'preserve the source')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'blender_path', lambda: tmp_path / 'Blender executable')
    run = Mock(return_value=0)
    monkeypatch.setattr(module.subprocess, 'call', run)
    return module, source, run


def test_captured_study_opens_with_embedded_scripts_disabled_and_no_rig_panel(launcher, monkeypatch):
    module, source, run = launcher
    monkeypatch.setattr(module.sys, 'argv', ['launch', '--file', str(source), '--no-controls'])
    assert module.main() == 0
    args = run.call_args.args[0]
    assert args == [str(source.parent / 'Blender executable'), '--disable-autoexec', str(source)]
    assert source.read_bytes() == b'preserve the source'


def test_regular_rig_still_gets_our_explicit_motion_panel(launcher, monkeypatch):
    module, source, run = launcher
    monkeypatch.setattr(module.sys, 'argv', ['launch', '--file', str(source)])
    assert module.main() == 0
    args = run.call_args.args[0]
    assert args[1:3] == ['--disable-autoexec', str(source)]
    assert args[3:] == ['--python', str(source.parent / 'scripts/character/studio_controls.py')]


def test_path_check_does_not_launch_blender(launcher, monkeypatch):
    module, source, run = launcher
    monkeypatch.setattr(module.sys, 'argv', ['launch', '--file', str(source), '--no-controls', '--check'])
    assert module.main() == 0
    run.assert_not_called()


def test_missing_explicit_source_cannot_launch_another_scene(launcher, monkeypatch):
    module, source, run = launcher
    monkeypatch.setattr(module.sys, 'argv', ['launch', '--file', str(source.parent / 'missing.blend'), '--no-controls'])
    with pytest.raises(SystemExit, match='Local character source was not found'):
        module.main()
    run.assert_not_called()
