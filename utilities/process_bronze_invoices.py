#!/usr/bin/env python3
"""
Utility script to process all bronze invoices one by one using runnerLog.py
This script will run each invoice file through the ResolveLight system sequentially.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def get_bronze_invoice_files():
    """Get all JSON invoice files from the bronze_invoices directory."""
    bronze_dir = Path("json_files/bronze_invoices")
    if not bronze_dir.exists():
        print(f"❌ Bronze invoices directory not found: {bronze_dir}")
        return []
    
    invoice_files = []
    for file_path in bronze_dir.glob("*.json"):
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
    """Main function to process all bronze invoices sequentially."""
    print("🚀 Starting Bronze Invoice Processing")
    print("=" * 60)
    
    # Get all bronze invoice files
    invoice_files = get_bronze_invoice_files()
    
    if not invoice_files:
        print("❌ No invoice files found in bronze_invoices directory")
        return
    
    print(f"📁 Found {len(invoice_files)} invoice files to process:")
    for i, file_path in enumerate(invoice_files, 1):
        print(f"  {i}. {file_path}")
    
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
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed to process: {failed}")
    print(f"📁 Total files: {len(invoice_files)}")
    
    if failed > 0:
        print(f"\n⚠️ {failed} files failed to process. Check the output above for details.")
    else:
        print(f"\n🎉 All {len(invoice_files)} invoice files processed successfully!")

if __name__ == "__main__":
    main()
