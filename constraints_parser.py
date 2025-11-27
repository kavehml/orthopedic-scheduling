"""
Parser for constraints from CSV file
"""
import pandas as pd
from typing import Dict, List, Optional
import re


def parse_constraints_csv(filepath: str = "CONTRAINTS.csv") -> Dict:
    """Parse the constraints CSV file and return structured constraints"""
    
    # Read the CSV
    df = pd.read_csv(filepath, header=None)
    
    # Extract global constraints
    global_constraints = {
        "blocks_per_year": 13,
        "block_duration_weeks": 4,
        "program_years": 5,
        "residents_per_year": "5-6",
        "r1_ortho_blocks_only": 5,
        "no_single_month_blocks": True,
        "min_juniors_at_mgh": 3,
        "min_mch_blocks_r2_to_r5": 2,
        "one_elective_per_year_r3_to_r5": True,
        "elective_not_in_p2_p3": True,
        "hand_rotation_r4": True
    }
    
    # Extract period-specific constraints
    period_constraints = {
        "r1_mgh_trauma_p3": True,
        "r1_mgh_spine_p3": True,
        "no_r4_mgh_trauma_p12_p13": True,
        "only_r5_mgh_trauma_p12_p13": True
    }
    
    # Parse rotation constraints from the table
    rotations = {}
    current_site = None
    
    # Find the rotation table (starts around row 23)
    for idx, row in df.iterrows():
        if idx < 22:  # Skip header rows
            continue
            
        row_values = [str(val).strip() if pd.notna(val) else "" for val in row.values]
        
        # Check if this is a site header
        if any("Site" in val or "Hospital" in val for val in row_values if val):
            # Extract site name
            site_name = next((val for val in row_values if val and ("Site" in val or "Hospital" in val)), None)
            if site_name:
                current_site = site_name
                # Extract min residents at site
                min_residents_match = re.search(r'(\d+)', site_name.split(',')[-1] if ',' in site_name else "")
                if not min_residents_match:
                    # Try to find it in the row
                    for val in row_values:
                        if val and val.isdigit():
                            min_residents_match = re.search(r'(\d+)', val)
                            break
                if min_residents_match:
                    rotations[current_site] = {
                        "min_residents_at_site": int(min_residents_match.group(1)),
                        "rotations": {}
                    }
            continue
        
        # Check if this is a rotation row
        rotation_name = row_values[1] if len(row_values) > 1 and row_values[1] else None
        
        if rotation_name and rotation_name not in ["", "Notes", "Rotation Label"]:
            # Parse rotation data
            rotation_data = {
                "site": current_site or "Other",
                "rotation_name": rotation_name,
                "min_blocks_total": None,
                "max_blocks_total": None,
                "eligible_years": [],
                "allowed_if_needed": [],
                "min_residents_per_block": None,
                "max_residents_per_block": None,
                "special_notes": ""
            }
            
            # Parse columns (approximate positions based on CSV structure)
            # Column indices: 0=empty, 1=rotation, 2-4=empty, 5=min_residents_site, 6=min_blocks, 7=max_blocks, 8=eligible, 9=allowed_if_needed, 10=min_accom, 11=max_accom
            
            # Min blocks
            if len(row_values) > 6 and row_values[6]:
                try:
                    rotation_data["min_blocks_total"] = int(float(row_values[6]))
                except:
                    pass
            
            # Max blocks
            if len(row_values) > 7 and row_values[7]:
                try:
                    rotation_data["max_blocks_total"] = int(float(row_values[7]))
                except:
                    pass
            
            # Eligible years
            if len(row_values) > 8 and row_values[8]:
                eligible_str = row_values[8]
                rotation_data["eligible_years"] = parse_year_list(eligible_str)
            
            # Allowed if needed
            if len(row_values) > 9 and row_values[9]:
                allowed_str = row_values[9]
                rotation_data["allowed_if_needed"] = parse_year_list(allowed_str)
            
            # Min residents per block
            if len(row_values) > 10 and row_values[10]:
                try:
                    rotation_data["min_residents_per_block"] = int(float(row_values[10]))
                except:
                    pass
            
            # Max residents per block
            if len(row_values) > 11 and row_values[11]:
                try:
                    rotation_data["max_residents_per_block"] = int(float(row_values[11]))
                except:
                    pass
            
            # Special notes (check row 2 for MGH/Spine)
            if len(row_values) > 2 and row_values[2]:
                rotation_data["special_notes"] = row_values[2]
            
            rotations[rotation_name] = rotation_data
    
    return {
        "global": global_constraints,
        "period_specific": period_constraints,
        "rotations": rotations
    }


def parse_year_list(year_str: str) -> List[int]:
    """Parse a string like 'R1,R2,R3' or 'R3, R4, R5' into list of years [1,2,3]"""
    if not year_str or year_str == "":
        return []
    
    years = []
    for part in year_str.split(','):
        part = part.strip()
        # Extract R1, R2, etc.
        match = re.search(r'R(\d+)', part.upper())
        if match:
            years.append(int(match.group(1)))
    
    return sorted(set(years))


if __name__ == "__main__":
    # Test the parser
    constraints = parse_constraints_csv()
    import json
    print(json.dumps(constraints, indent=2))

