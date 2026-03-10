import sys
import threading
from pathlib import Path

from ael import run_manager


def test_thread_output_routing_is_isolated(tmp_path, monkeypatch):
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    try:
        run_manager.ensure_thread_output_proxies()
        barrier = threading.Barrier(2)

        def _writer(name: str):
            log_path = Path(tmp_path) / f"{name}.log"
            tee, handle = run_manager.open_tee(log_path, "verbose")
            try:
                with run_manager.route_thread_output(tee):
                    print(f"{name}:start")
                    barrier.wait(timeout=5)
                    print(f"{name}:end")
                    tee.flush()
            finally:
                handle.close()

        t1 = threading.Thread(target=_writer, args=("alpha",))
        t2 = threading.Thread(target=_writer, args=("beta",))
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert not t1.is_alive()
        assert not t2.is_alive()
        assert (tmp_path / "alpha.log").read_text(encoding="utf-8").splitlines() == ["alpha:start", "alpha:end"]
        assert (tmp_path / "beta.log").read_text(encoding="utf-8").splitlines() == ["beta:start", "beta:end"]
    finally:
        monkeypatch.setattr(sys, "stdout", original_stdout)
        monkeypatch.setattr(sys, "stderr", original_stderr)
