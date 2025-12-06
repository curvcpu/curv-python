"""
Pytest configuration for toml_schema_parsing tests.

This file contains hooks that track test failures so fixtures can
preserve temp files for debugging when tests fail.
"""
import pytest

# ---------------------------------------------------------------------------
# Track test failures per class so fixtures can preserve temp files
# ---------------------------------------------------------------------------
_failed_test_classes: set = set()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Track which test classes have had failures.
    
    This hook runs after each test phase (setup, call, teardown).
    If a test fails during the 'call' phase, we record its class
    so the fixture teardown can preserve temp files for debugging.
    """
    outcome = yield
    rep = outcome.get_result()
    
    # Only track failures during the actual test execution ('call' phase)
    if rep.when == "call" and rep.failed:
        if item.cls is not None:
            _failed_test_classes.add(item.cls)


def class_had_failures(cls) -> bool:
    """Check if a test class had any test failures."""
    return cls in _failed_test_classes
