#!/usr/bin/env python3
"""
Utility script to clear all log files in the system_logs directory
This script will empty all log files while preserving their structure.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def get_system_logs_dir():
    """Get the system_logs directory path."""
    # Get the project root (parent of utilities directory)
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / "system_logs"
    return logs_dir

def get_log_files():
    """Get all log files in the system_logs directory."""
    logs_dir = get_system_logs_dir()
    
    if not logs_dir.exists():
        print(f"❌ System logs directory not found: {logs_dir}")
        return []
    
    log_files = []
    for file_path in logs_dir.glob("*.log"):
        log_files.append(file_path)
    
    return sorted(log_files)

def clear_log_file(file_path):
    """Clear a single log file by truncating it to 0 bytes."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("")
        return True
    except Exception as e:
        print(f"❌ Error clearing {file_path.name}: {e}")
        return False

def clear_all_logs():
    """Clear all log files in the system_logs directory."""
    print("🧹 ResolveLight System Logs Cleaner")
    print("=" * 50)
    
    logs_dir = get_system_logs_dir()
    if not logs_dir.exists():
        print(f"❌ System logs directory not found: {logs_dir}")
        return False
    
    log_files = get_log_files()
    
    if not log_files:
        print("ℹ️  No log files found in system_logs directory")
        return True
    
    print(f"📁 System logs directory: {logs_dir}")
    print(f"📄 Found {len(log_files)} log files to clear:")
    
    for log_file in log_files:
        print(f"   - {log_file.name}")
    
    print()
    
    # Ask for confirmation
    response = input("⚠️  Are you sure you want to clear ALL log files? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled by user")
        return False
    
    print("\n🔄 Clearing log files...")
    
    success_count = 0
    failed_files = []
    
    for log_file in log_files:
        print(f"   Clearing {log_file.name}...", end=" ")
        
        if clear_log_file(log_file):
            print("✅")
            success_count += 1
        else:
            print("❌")
            failed_files.append(log_file.name)
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"   ✅ Successfully cleared: {success_count} files")
    
    if failed_files:
        print(f"   ❌ Failed to clear: {len(failed_files)} files")
        for failed_file in failed_files:
            print(f"      - {failed_file}")
    else:
        print("   🎉 All log files cleared successfully!")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return len(failed_files) == 0

def show_log_status():
    """Show current status of log files without clearing them."""
    print("📊 ResolveLight System Logs Status")
    print("=" * 50)
    
    log_files = get_log_files()
    
    if not log_files:
        print("ℹ️  No log files found in system_logs directory")
        return
    
    logs_dir = get_system_logs_dir()
    print(f"📁 System logs directory: {logs_dir}")
    print(f"📄 Found {len(log_files)} log files:")
    print()
    
    total_size = 0
    for log_file in log_files:
        try:
            size = log_file.stat().st_size
            total_size += size
            
            # Format file size
            if size == 0:
                size_str = "0 B"
            elif size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            print(f"   📄 {log_file.name:<35} {size_str:>8}")
            
        except Exception as e:
            print(f"   ❌ {log_file.name:<35} Error: {e}")
    
    print("-" * 50)
    
    # Format total size
    if total_size == 0:
        total_str = "0 B"
    elif total_size < 1024:
        total_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        total_str = f"{total_size / 1024:.1f} KB"
    else:
        total_str = f"{total_size / (1024 * 1024):.1f} MB"
    
    print(f"   📊 Total size: {total_str}")

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            show_log_status()
            return
        elif command == "clear":
            clear_all_logs()
            return
        elif command in ["help", "-h", "--help"]:
            print("ResolveLight System Logs Utility")
            print("=" * 40)
            print("Usage:")
            print("  python clear_system_logs.py           # Interactive mode")
            print("  python clear_system_logs.py status    # Show log file status")
            print("  python clear_system_logs.py clear     # Clear all logs (non-interactive)")
            print("  python clear_system_logs.py help      # Show this help")
            return
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'python clear_system_logs.py help' for usage information")
            return
    
    # Interactive mode
    print("ResolveLight System Logs Utility")
    print("=" * 40)
    print("1. Show log status")
    print("2. Clear all logs")
    print("3. Exit")
    print()
    
    while True:
        try:
            choice = input("Select an option (1-3): ").strip()
            
            if choice == "1":
                show_log_status()
                print()
            elif choice == "2":
                clear_all_logs()
                break
            elif choice == "3":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")
                print()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    main()
