"""Temporary deployment entry; same pinned bundle/core as native HA application."""

import argparse
import getpass
import json
import os
import stat
from pathlib import Path

from neighbor_installer.artifact import Artifact
from neighbor_installer.engine import Installer
from neighbor_installer.files import InstallerError, load
from neighbor_installer.lifecycle import SupervisorLifecycle

from .container_lifecycle import ContainerLifecycle
from .controller import Controller
from .copy import PHASE_LABELS


def _deploy(controller, *, confirm=False, handoff=False, output=print):
    def step(action, **payload):
        if not controller.start(action, payload):
            raise InstallerError("BOOTSTRAP_OPERATION_ALREADY_RUNNING")
        controller.worker.join()
        view = controller.view()
        if view.get("upstream_base_version"):
            output("友邻加强版 " + view["product_version"] + "；基于官方组件 " + view["upstream_base_version"])
        output(view["title"])
        output(view["description"])
        return view

    if controller.state["screen"] in {"interrupted", "recovery"}:
        output("上一次操作需要先检查恢复进度，请保留现状并查看脱敏诊断。")
        return 2
    if controller.state["screen"] == "handoff":
        if not handoff:
            output("请先按 HACS 正常界面完成移除，再重新执行并确认。")
            return 2
        view = step("handoff")
    else:
        view = step("check")
        if view.get("component_current") and view["screen"] in {"installed", "latest", "configured", "ready"}:
            return _finish(controller, view, output)
        if view["screen"] not in {"fresh", "official", "update"}:
            return 2
        view = step("prepare")
        if view["screen"] != "confirm":
            return 2
        if not confirm:
            output("检查完成，尚未安装。确认备份及短暂重启后，使用 --confirm 再执行。")
            return 2
        view = step("confirm", plan=view["plan"], confirmed=True)
    if view["screen"] in {"installed", "latest", "configured", "ready"}:
        return _finish(controller, view, output)
    return 2


def _finish(controller, view, output):
    output("友邻加强版已经安装，请在 Home Assistant 连接 NexHome 并试一次控制。")
    origin = getattr(controller.engine.lifecycle, '_ha_url', '').rstrip('/')
    output(origin + view['native_url'])
    output("已有配置会沿用；选择一盏灯操作并核对状态后，才算完成首次使用。")
    return 0


def deploy(controller, *, confirm=False, handoff=False, output=print):
    prior = controller.engine.observer

    def progress(event):
        if prior:
            prior(event)
        label = PHASE_LABELS.get(event.get("phase"))
        if label:
            output(label)

    controller.engine.observer = progress
    try:
        return _deploy(controller, confirm=confirm, handoff=handoff, output=output)
    finally:
        controller.engine.observer = prior


def verify_completion(controller, *, output=print):
    """Explicit user acknowledgement; read-only proof check, never a device command."""
    for action in ('check', 'check_setup'):
        if not controller.start(action):
            return 2
        controller.worker.join()
        if controller.view()['screen'] not in {'installed','configured','ready'}:
            output("尚未确认连接，请保留现状并检查 Home Assistant。")
            return 2
    if controller.view()['completion'].get('stage') != 'CONTROL_VERIFIED':
        output("还没有确认设备可以正常控制，请先在 Home Assistant 操作一盏灯并检查状态。")
        return 2
    if controller.view()['screen']=='ready':
        output(controller.view()['title'])
        return 0
    if not controller.start('acknowledge_ready'):
        return 2
    controller.worker.join()
    view=controller.view()
    output(view['title'])
    output(view['description'])
    return 0 if view['screen']=='ready' else 2


def read_private_token(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise InstallerError("TEMPORARY_TOKEN_FILE_PERMISSIONS")
        value = stream.read(8193).strip()
    if not value or len(value) > 8192 or not value.isascii() or any(c.isspace() for c in value):
        raise InstallerError("TEMPORARY_TOKEN_FILE_INVALID")
    return value


def main():
    parser = argparse.ArgumentParser(description="NexHome 滨融府友邻加强版：安装完成后返回 Home Assistant")
    parser.add_argument("--config", required=True)
    parser.add_argument("--package", required=True, help="已下载并核验来源的固定开发测试安装包目录")
    parser.add_argument("--container", help="现有 HA Docker 容器名称；不创建容器")
    parser.add_argument("--ha-url", default="http://homeassistant:80")
    parser.add_argument("--token-file", help="仅 Container：当前用户专有的临时授权文件；用后自行撤销并删除")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--hacs-completed", action="store_true")
    parser.add_argument("--verify-completion", action="store_true", help="确认已找到设备并完成首次操作；只检查证据，不发送控制")
    args = parser.parse_args()
    try:
        package = Path(args.package).resolve()
        bundle = package / "bundle"
        artifact = Artifact.open(bundle, (bundle / "artifact.sha256").read_text().strip())
        if args.container:
            # Input stays in process memory, never argv, URL, logs or persistent state.
            token = (
                read_private_token(args.token_file)
                if args.token_file
                else getpass.getpass("请输入此 Home Assistant 的临时授权（不会保存）：")
            )
            runtime = ContainerLifecycle(args.container, args.config, token, args.ha_url)
        else:
            runtime = SupervisorLifecycle(os.environ.get("SUPERVISOR_TOKEN"), proxy_core=True, timeout=210)
        engine = Installer(args.config, runtime, trusted_trees=load(package / "trusted-trees.json", {}))
        controller = Controller(engine, artifact, engine.state / "bootstrap-ui")
        if args.verify_completion:
            return verify_completion(controller)
        return deploy(controller, confirm=args.confirm, handoff=args.hacs_completed)
    except Exception as error:
        print("这一步没有完成，请保留现状。未确认来源的安装不会被覆盖。")
        # Stable code only; never raw external response bodies.
        if isinstance(error, InstallerError):
            print(json.dumps({"technical_error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
