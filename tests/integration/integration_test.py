#!/usr/bin/env python3
"""
Integration test script to verify nirva_service project structure and services.
"""

import subprocess
import sys
import time
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_command(cmd: str, timeout: int = 30) -> tuple[int, str]:
    """Run a shell command with timeout."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, f"Command timed out after {timeout} seconds"


def test_imports():
    """Test that all main modules can be imported."""
    print("Testing imports...")

    try:
        from nirva_service import __version__

        print(f"✓ nirva_service version: {__version__}")

        from nirva_service.config import (
            AnalyzerServerConfig,
            AppserviceServerConfig,
            ChatServerConfig,
        )

        print("✓ Config modules imported successfully")

        from nirva_service.models import ChatMessage, JournalFile

        print("✓ Model modules imported successfully")

        from nirva_service.services.app_services import appservice_server_fastapi

        print("✓ App services imported successfully")

        from nirva_service.services.langgraph_services import chat_server_fastapi

        print("✓ LangGraph services imported successfully")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_type_checking():
    """Test MyPy type checking."""
    print("\nTesting type checking...")

    code, output = run_command("make type-check-all")
    if code == 0:
        print("✓ Type checking passed")
        return True
    else:
        print(f"✗ Type checking failed: {output}")
        return False


def test_basic_tests():
    """Run basic tests."""
    print("\nRunning basic tests...")

    code, output = run_command("make test", timeout=10)
    if code == 0:
        print("✓ All tests passed")
        return True
    else:
        print(f"✗ Tests failed: {output}")
        return False


def test_service_startup():
    """Test that services can start up correctly."""
    print("\nTesting service startup...")

    project_root = Path(__file__).parent.parent.parent

    # Test chat service (port 8500)
    print("Testing chat service...")
    process = subprocess.Popen(
        [sys.executable, str(project_root / "scripts" / "run_chat_server.py")],
        cwd=project_root,
    )

    # Wait for startup
    time.sleep(3)

    try:
        response = requests.get("http://localhost:8500/docs", timeout=5)
        if response.status_code == 200:
            print("✓ Chat service started successfully")
            chat_success = True
        else:
            print(f"✗ Chat service returned status {response.status_code}")
            chat_success = False
    except Exception as e:
        print(f"✗ Chat service failed: {e}")
        chat_success = False
    finally:
        process.terminate()
        process.wait()

    # Wait a bit before next test
    time.sleep(1)

    # Test analyzer service (port 8600)
    print("Testing analyzer service...")
    process = subprocess.Popen(
        [sys.executable, str(project_root / "scripts" / "run_analyzer_server.py")],
        cwd=project_root,
    )

    # Wait for startup
    time.sleep(3)

    try:
        response = requests.get("http://localhost:8600/docs", timeout=5)
        if response.status_code == 200:
            print("✓ Analyzer service started successfully")
            analyzer_success = True
        else:
            print(f"✗ Analyzer service returned status {response.status_code}")
            analyzer_success = False
    except Exception as e:
        print(f"✗ Analyzer service failed: {e}")
        analyzer_success = False
    finally:
        process.terminate()
        process.wait()

    return chat_success and analyzer_success


def main():
    """Run all integration tests."""
    print("🚀 Running nirva_service integration tests...\n")

    tests = [
        ("Import Tests", test_imports),
        ("Type Checking", test_type_checking),
        ("Unit Tests", test_basic_tests),
        ("Service Startup", test_service_startup),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS:")
    print("=" * 60)

    all_passed = True
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
        if not success:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Project structure is working correctly.")
        return 0
    else:
        print("❌ SOME TESTS FAILED! Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
