"""Reproduce the full real-data project with the current Python interpreter."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
steps=[['scripts/download_data.py','--x5-full'],['scripts/run_olist.py'],['scripts/run_diagnostics.py'],
       ['scripts/build_x5_features.py'],['scripts/run_x5.py'],['scripts/render_report.py'],
       ['-m','pytest','-q'],['scripts/check_dashboard.py']]
for step in steps:
    print('RUN:', ' '.join(step),flush=True)
    subprocess.run([sys.executable,*step],cwd=ROOT,check=True)
