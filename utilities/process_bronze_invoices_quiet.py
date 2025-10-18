#!/usr/bin/env python3
"""
Quiet utility script to process all bronze invoices one by one using runnerLog.py
This version saves detailed output to a log file and shows only a summary.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

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

def process_single_invoice(invoice_path, log_file):
    """Process a single invoice file using runnerLog.py"""
    print(f"🔄 Processing: {Path(invoice_path).name}")
    
    try:
        # Run runnerLog.py with the invoice file path as input
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
        
        # Write detailed output to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"INVOICE: {invoice_path}\n")
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n")
            f.write("STDOUT:\n")
            f.write(stdout)
            f.write("\nSTDERR:\n")
            f.write(stderr)
            f.write("\n")
        
        # Extract key information from output
        status = "UNKNOWN"
        queue = "UNKNOWN"
        exception_id = "N/A"
        
        if "APPROVED" in stdout:
            status = "APPROVED"
            queue = "payments"
        elif "REJECTED" in stdout:
            status = "REJECTED"
            # Try to extract queue and exception ID
            for line in stdout.split('\n'):
                if "Routing Queue:" in line or "routing queue:" in line:
                    queue = line.split(':')[-1].strip().replace('`', '').replace('*', '')
                elif "Exception ID:" in line:
                    exception_id = line.split(':')[-1].strip()
        
        if process.returncode == 0:
            print(f"✅ {status} -> {queue} (ID: {exception_id})")
            return True, status, queue, exception_id
        else:
            print(f"❌ Failed (exit code: {process.returncode})")
            return False, "FAILED", "error", "N/A"
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, "ERROR", "error", "N/A"

def main():
    """Main function to process all bronze invoices sequentially."""
    print("🚀 Starting Bronze Invoice Processing (Quiet Mode)")
    print("=" * 60)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"bronze_invoice_processing_{timestamp}.log"
    
    print(f"📝 Detailed output will be saved to: {log_file}")
    
    # Get all bronze invoice files
    invoice_files = get_bronze_invoice_files()
    
    if not invoice_files:
        print("❌ No invoice files found in bronze_invoices directory")
        return
    
    print(f"📁 Found {len(invoice_files)} invoice files to process")
    print("=" * 60)
    
    # Process each invoice file
    results = []
    successful = 0
    failed = 0
    
    for i, invoice_path in enumerate(invoice_files, 1):
        print(f"[{i:2d}/{len(invoice_files)}] ", end="")
        
        # Process the invoice
        success, status, queue, exception_id = process_single_invoice(invoice_path, log_file)
        
        results.append({
            'file': Path(invoice_path).name,
            'status': status,
            'queue': queue,
            'exception_id': exception_id,
            'success': success
        })
        
        if success:
            successful += 1
        else:
            failed += 1
        
        # Small delay between processing
        if i < len(invoice_files):
            time.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed to process: {failed}")
    print(f"📁 Total files: {len(invoice_files)}")
    print(f"📝 Detailed log: {log_file}")
    
    # Status breakdown
    print("\n📋 STATUS BREAKDOWN:")
    status_counts = {}
    queue_counts = {}
    
    for result in results:
        status = result['status']
        queue = result['queue']
        
        status_counts[status] = status_counts.get(status, 0) + 1
        queue_counts[queue] = queue_counts.get(queue, 0) + 1
    
    print("\nBy Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    print("\nBy Queue:")
    for queue, count in sorted(queue_counts.items()):
        print(f"  {queue}: {count}")
    
    # Show rejected invoices
    rejected = [r for r in results if r['status'] == 'REJECTED']
    if rejected:
        print(f"\n🚨 REJECTED INVOICES ({len(rejected)}):")
        for r in rejected:
            print(f"  {r['file']} -> {r['queue']} (ID: {r['exception_id']})")
    
    # Show approved invoices
    approved = [r for r in results if r['status'] == 'APPROVED']
    if approved:
        print(f"\n✅ APPROVED INVOICES ({len(approved)}):")
        for r in approved:
            print(f"  {r['file']} -> {r['queue']}")

if __name__ == "__main__":
    main()
