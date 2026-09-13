import json
import platform
import threading
import time
from pathlib import Path

import psutil


class Resources:
    """Sample process RSS and OS-available RAM; also record OS process peak RSS."""
    def __init__(self):
        self.process = psutil.Process()
        self.samples = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self):
        while not self.stop.is_set():
            self.samples.append((self.process.memory_info().rss, psutil.virtual_memory().available))
            self.stop.wait(0.02)

    def __enter__(self):
        self.started = time.perf_counter()
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join()
        self.elapsed = time.perf_counter() - self.started

    def report(self):
        info = self.process.memory_info()
        return dict(wall_seconds=self.elapsed, sampled_peak_rss_bytes=max(x[0] for x in self.samples),
                    os_process_peak_rss_bytes=getattr(info, 'peak_wset', None),
                    representative_rss_bytes=info.rss,
                    minimum_available_system_ram_bytes=min(x[1] for x in self.samples),
                    sampling_interval_seconds=0.02)


def machine():
    import numpy, scipy, pandas, pyarrow
    cpu = platform.processor()
    if platform.system() == 'Windows':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    display_adapters = []
    if platform.system() == 'Windows':
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}') as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    name = winreg.EnumKey(key,i)
                    if name.isdigit():
                        with winreg.OpenKey(key,name) as adapter:
                            display_adapters.append(winreg.QueryValueEx(adapter,'DriverDesc')[0])
        except OSError:
            pass
    return dict(os=platform.platform(), python=platform.python_version(), cpu=cpu,
                physical_cores=psutil.cpu_count(logical=False), logical_cores=psutil.cpu_count(),
                total_ram_bytes=psutil.virtual_memory().total,
                versions={m.__name__:m.__version__ for m in [numpy, scipy, pandas, pyarrow, psutil]},
                gpu_compute_used=False,display_adapters=display_adapters)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
