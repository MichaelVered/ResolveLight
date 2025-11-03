#!/usr/bin/env python3
"""
Regenerate the formatted learning playbook from JSONL data.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent))

from learning_agent.learning_playbook_generator import LearningPlaybookGenerator

def main():
    """Regenerate the formatted playbook."""
    print("🔄 Regenerating formatted learning playbook...")
    
    try:
        generator = LearningPlaybookGenerator()
        
        # Call the private method to regenerate the formatted file
        success = generator._generate_formatted_txt()
        
        if success:
            print("✅ Successfully regenerated learning_playbook_formatted.txt")
        else:
            print("❌ Failed to regenerate formatted playbook")
            return 1
        
        generator.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())




