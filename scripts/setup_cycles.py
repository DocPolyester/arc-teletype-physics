#!/usr/bin/env python3
"""
Quick setup script for Arc Cycles
"""
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, description):
    """Run a shell command."""
    print(f"\n{'='*60}")
    print(f"→ {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"✗ Failed: {description}")
        return False
    
    print(f"✓ Done: {description}")
    return True


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║    Arc Cycles - Physics-based Multi-Mode Arc App         ║
    ║                                                           ║
    ║    Setup & Test Helper                                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    project_root = Path(__file__).parent.parent
    
    # Tests
    print("\n1️⃣  Basic Structure Tests...")
    if not run_cmd(f"python3 {project_root}/scripts/test_basic.py", "Basic imports"):
        sys.exit(1)
    
    # Create logs directory
    print("\n2️⃣  Setup Directories...")
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    print(f"✓ Logs directory: {logs_dir}")
    
    # Show info
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║  ✓ Setup Complete!                                       ║
    ║                                                           ║
    ║  Next Steps:                                             ║
    ║  1. Deploy: Ctrl+Shift+B (or ./scripts/deploy.sh)       ║
    ║  2. Run: python3 src/arc_cycles_app.py                  ║
    ║  3. Control: Teletype commands or Fader 0               ║
    ║                                                           ║
    ║  Modes Available:                                        ║
    ║  - CYCLES (default)                                      ║
    ║  - PENDULUM (oscillating)                                ║
    ║  - GRAVITY (falling particles)                           ║
    ║  - SPRING (resonance)                                    ║
    ║  - ORBIT (orbital mechanics)                             ║
    ║                                                           ║
    ║  Documentation:                                          ║
    ║  - {project_root / 'docs' / 'ARC_CYCLES_README.md'}
    ║  - {project_root / 'docs' / 'TELETYPE_INTEGRATION.md'}  ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
