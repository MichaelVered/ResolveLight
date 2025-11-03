# Learning Playbook Formatting Fix

## Problem
The `learning_playbook_formatted.txt` file had corrupted formatting in the **APPROVAL CONDITIONS** and **KEY DISTINGUISHING FACTORS** sections. Content was being printed character-by-character on separate numbered lines, making it unreadable.

### Example of Bad Formatting:
```
APPROVAL CONDITIONS
--------------------------------------------------------------------------------
1. 1
2. .
3.  
4. T
5. e
6. c
7. h
8. n
9. i
10. c
11. a
12. l
...
```

## Root Cause
1. **Data Type Mismatch**: The code assumed `approval_conditions` and `key_distinguishing_factors` were always lists, but the JSONL data stored them as strings with newline separators.
2. **Character Iteration**: When iterating over a string in Python, it iterates character-by-character, causing each character to be printed on its own line.
3. **Duplicate Numbering**: Some entries already had numbering in the stored string (e.g., "1. Presence of..."), which combined with the code's numbering resulted in "1. 1. Presence of...".

## Solution
Updated `learning_agent/learning_playbook_generator.py` to handle both data formats correctly:

### Changes Made:

1. **Flexible Data Type Handling** (Lines 307-316 and 360-363):
   - Check if the field is a string, list, or other type
   - For strings: split by newlines to extract individual items
   - For lists: use directly
   - Handle edge cases gracefully

2. **Word Wrapping** (Lines 329-347 and 376-394):
   - Added proper line wrapping for long conditions/factors
   - Maintains consistent numbering across wrapped lines
   - Uses indentation (3 spaces) for continuation lines

3. **Remove Duplicate Numbering** (Lines 320-327 and 367-374):
   - Detect existing numbering patterns like "1. " or "2. "
   - Strip the existing number before adding new numbering
   - Prevents "1. 1. " double numbering issues

### Code Snippet:
```python
# Handle both list and string formats
if isinstance(joint_factors, str):
    # If it's a string, split by newlines to get individual factors
    factors = [line.strip() for line in joint_factors.split('\n') if line.strip()]
elif isinstance(joint_factors, list):
    factors = joint_factors
else:
    factors = []

# Remove existing numbering if present
factor_clean = factor.strip()
if factor_clean and factor_clean[0].isdigit():
    match = re.match(r'^\d+\.\s*', factor_clean)
    if match:
        factor_clean = factor_clean[match.end():]
```

## Result
Both sections now display correctly:

### Correct Formatting:
```
KEY DISTINGUISHING FACTORS
--------------------------------------------------------------------------------
1. Presence of 'notes' field explaining the discount.
2. Explanation relates to market conditions.

APPROVAL CONDITIONS
--------------------------------------------------------------------------------
1. Invoice 'notes' field explains a discount.
2. Discount explanation indicates market adjustment or similar
   conditions.
```

## Testing
- ✅ Verified all 7 entries are properly formatted
- ✅ Handles string format (entries 1-6)
- ✅ Handles list format (entry 7)
- ✅ Removes duplicate numbering
- ✅ Proper word wrapping for long lines
- ✅ Preserves indentation for continuation lines

## Files Modified
- `learning_agent/learning_playbook_generator.py` - Fixed formatting logic for both sections

## Files Generated
- `learning_playbooks/learning_playbook_formatted.txt` - Regenerated with correct formatting




