import math
import os


def get_nprocs() -> int:
    """Return an estimate of the effective CPU count for the current process."""

    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        pass

    try:
        path_v2 = "/sys/fs/cgroup/cpu.max"
        if os.path.exists(path_v2):
            quota, period = open(path_v2, encoding="utf-8").read().split()
            if quota != "max":
                return max(1, math.ceil(int(quota) / int(period)))

        quota_v1 = "/sys/fs/cgroup/cpu/cpu.cfs_quota_us"
        period_v1 = "/sys/fs/cgroup/cpu/cpu.cfs_period_us"
        if os.path.exists(quota_v1) and os.path.exists(period_v1):
            quota = int(open(quota_v1, encoding="utf-8").read())
            period = int(open(period_v1, encoding="utf-8").read())
            if quota > 0 and period > 0:
                return max(1, math.ceil(quota / period))
    except Exception:  # noqa: BLE001 - cgroup probing is best-effort
        pass

    return os.cpu_count() or 1

