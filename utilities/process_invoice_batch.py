#!/usr/bin/env python3
"""
Utility script to process all invoices from a selected folder using runnerLog.py
This script will present available invoice folders and run each invoice file through the ResolveLight system sequentially.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def get_available_invoice_folders():
    """Get all available invoice folders from the json_files directory."""
    json_files_dir = Path("json_files")
    if not json_files_dir.exists():
        print(f"❌ JSON files directory not found: {json_files_dir}")
        return []
    
    # Get all subdirectories in json_files
    folders = []
    for item in json_files_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if the folder contains JSON files
            json_files = list(item.glob("*.json"))
            if json_files:
                folders.append({
                    'name': item.name,
                    'path': item,
                    'file_count': len(json_files)
                })
    
    return sorted(folders, key=lambda x: x['name'])

def display_folder_menu(folders):
    """Display the available folders as a numbered menu."""
    print("\n📁 Available Invoice Folders:")
    print("=" * 50)
    
    for i, folder in enumerate(folders, 1):
        print(f"  {i}. {folder['name']:<25} ({folder['file_count']} files)")
    
    print(f"  {len(folders) + 1}. Exit")
    print("=" * 50)

def get_user_folder_selection(folders):
    """Get user selection for which folder to process."""
    while True:
        try:
            choice = input(f"\nSelect a folder to process (1-{len(folders) + 1}): ").strip()
            
            if not choice:
                print("❌ Please enter a selection")
                continue
            
            choice_num = int(choice)
            
            if choice_num == len(folders) + 1:
                print("👋 Goodbye!")
                return None
            
            if 1 <= choice_num <= len(folders):
                selected_folder = folders[choice_num - 1]
                print(f"✅ Selected: {selected_folder['name']} ({selected_folder['file_count']} files)")
                return selected_folder
            else:
                print(f"❌ Invalid selection. Please choose between 1 and {len(folders) + 1}")
                
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return None

def get_invoice_files(selected_folder):
    """Get all JSON invoice files from the selected folder."""
    folder_path = selected_folder['path']
    
    if not folder_path.exists():
        print(f"❌ Selected folder not found: {folder_path}")
        return []
    
    invoice_files = []
    for file_path in folder_path.glob("*.json"):
        invoice_files.append(str(file_path))
    
    return sorted(invoice_files)

def process_single_invoice(invoice_path):
    """Process a single invoice file using runnerLog.py"""
    print(f"\n🔄 Processing: {invoice_path}")
    print("=" * 60)
    
    try:
        # Run runnerLog.py with the invoice file path as input
        # We'll simulate the interactive input by providing the file path
        process = subprocess.Popen(
            [sys.executable, "runnerLog.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Send the invoice file path as input to the runner
        stdout, stderr = process.communicate(input=f"Process invoice: {invoice_path}\nquit\n")
        
        print("📤 Output:")
        print(stdout)
        
        if stderr:
            print("⚠️ Errors/Warnings:")
            print(stderr)
        
        if process.returncode == 0:
            print(f"✅ Successfully processed: {invoice_path}")
        else:
            print(f"❌ Failed to process: {invoice_path} (exit code: {process.returncode})")
            
        return process.returncode == 0
        
    except Exception as e:
        print(f"❌ Error processing {invoice_path}: {e}")
        return False

def main():
    """Main function to process invoices from a user-selected folder."""
    print("🚀 Invoice Batch Processing Utility")
    print("=" * 60)
    
    # Get available invoice folders
    folders = get_available_invoice_folders()
    
    if not folders:
        print("❌ No invoice folders found in json_files directory")
        return
    
    # Display folder menu and get user selection
    display_folder_menu(folders)
    selected_folder = get_user_folder_selection(folders)
    
    if not selected_folder:
        return
    
    # Get invoice files from selected folder
    invoice_files = get_invoice_files(selected_folder)
    
    if not invoice_files:
        print(f"❌ No invoice files found in {selected_folder['name']} directory")
        return
    
    print(f"\n📁 Processing {len(invoice_files)} invoice files from {selected_folder['name']}:")
    for i, file_path in enumerate(invoice_files, 1):
        print(f"  {i}. {Path(file_path).name}")
    
    # Confirm processing
    print(f"\n⚠️  About to process {len(invoice_files)} invoices from {selected_folder['name']}")
    confirm = input("Continue? (y/N): ").lower().strip()
    
    if confirm not in ['y', 'yes']:
        print("❌ Processing cancelled by user")
        return
    
    print(f"\n🔄 Starting sequential processing...")
    print("=" * 60)
    
    # Process each invoice file
    successful = 0
    failed = 0
    
    for i, invoice_path in enumerate(invoice_files, 1):
        print(f"\n📋 Processing {i}/{len(invoice_files)}")
        
        # Process the invoice
        success = process_single_invoice(invoice_path)
        
        if success:
            successful += 1
        else:
            failed += 1
        
        # Add a small delay between processing
        if i < len(invoice_files):  # Don't delay after the last file
            print(f"\n⏳ Waiting 2 seconds before next invoice...")
            time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"📁 Folder processed: {selected_folder['name']}")
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed to process: {failed}")
    print(f"📁 Total files: {len(invoice_files)}")
    
    if failed > 0:
        print(f"\n⚠️ {failed} files failed to process. Check the output above for details.")
    else:
        print(f"\n🎉 All {len(invoice_files)} invoice files processed successfully!")

if __name__ == "__main__":
    main()
