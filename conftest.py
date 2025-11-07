import shutil
import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        marker = item.get_closest_marker("tool_required")
        if marker:
            if not marker.args:
                continue
            tool_name = str(marker.args[0])
            if shutil.which(tool_name) is None:
                item.add_marker(pytest.mark.skip(reason=f"{tool_name} not found in PATH"))


