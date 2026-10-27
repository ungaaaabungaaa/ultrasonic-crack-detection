"""Test the installed distribution from outside its source checkout."""

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    wheel = Path(sys.argv[1]).resolve(strict=True)
    with zipfile.ZipFile(wheel) as archive:
        assert sum(x.file_size for x in archive.infolist()) < 200_000
        assert not any(
            "__pycache__" in name or name.endswith(".pyc") for name in archive.namelist()
        )
    with tempfile.TemporaryDirectory(prefix="ultrasonic-wheel-") as temporary:
        root = Path(temporary)
        target = root / "installed"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--no-compile",
                "--target",
                str(target),
                str(wheel),
            ],
            check=True,
            cwd=root,
        )
        env = {**os.environ, "PYTHONPATH": str(target), "MPLCONFIGDIR": str(root / "mpl")}
        probe = r"""
from pathlib import Path
import json
import socket
from unittest.mock import patch
import ultrasonic_lab
from ultrasonic_lab.cli import main
assert Path(ultrasonic_lab.__file__).resolve().is_relative_to(Path('installed').resolve())
with patch.object(socket, 'create_connection', side_effect=AssertionError('Offline workflow tried network')):
    assert main(['benchmark', '--output', 'study']) == 0
    assert main(['analyze', '--trace', 'study/examples/evaluation-040-r0.csv',
                 '--metadata', 'study/examples/evaluation-040-r0.json', '--output', 'scan']) == 0
metrics = json.loads(Path('study/metrics.json').read_text())
assert metrics['specimen_count'] == 184 and metrics['trace_count'] == 552
assert metrics['groups']['evaluation']['total_specimens'] == 80
assert json.loads(Path('scan/metrics.json').read_text())['decision'] is None
assert Path('study/waveforms.png').stat().st_size > 1000
print('Installed wheel: complete offline benchmark, file adapter, figures, and report passed.')
"""
        subprocess.run([sys.executable, "-c", probe], check=True, cwd=root, env=env)
        subprocess.run(
            [sys.executable, "-m", "ultrasonic_lab", "--version"], check=True, cwd=root, env=env
        )


if __name__ == "__main__":
    main()
