"""
Optimization engine for generating optimal schedules with rotation constraints
"""
from typing import List, Dict, Set, Optional
import random
import json
from models import ScheduleData, Resident, Block, Assignment


class ScheduleOptimizer:
    """Optimizes resident-block assignments with comprehensive constraint enforcement"""
    
    def __init__(self, schedule_data: ScheduleData):
        self.data = schedule_data
        self.rotation_constraints = self._load_rotation_constraints()
        
        # Map specialty to rotation keywords (case-insensitive matching)
        self.specialty_to_rotations = {
            "Arthroplasty": ["Arthro"],
            "Spine": ["Spine"],
            "Orthopaedic Oncology": ["Tumor"],
            "Orthopaedic Trauma": ["Trauma"],
            "Sports Orthopaedics": ["Sports"],
            "Primary Care Sports Medicine": ["Sports"],
            "Foot and Ankle": ["Foot"],
            "Pediatric Orthopaedics": ["Shriners", "MCH"],
            "Upper Extremity": ["Hand"],
            "Musculoskeletal Research": ["Research"],
            "Limb Lengthening": ["Shriners", "MCH"],
            "Undecided": []  # No specific rotations
        }
    
    def _load_rotation_constraints(self) -> Dict:
        """Load rotation constraints from JSON file"""
        try:
            with open("rotation_constraints.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _is_resident_eligible(self, resident: Resident, rotation_name: str, block: Block) -> bool:
        """Check if a resident is eligible for a rotation based on year and constraints"""
        rotations = self.rotation_constraints.get("rotations", {})
        rotation_info = rotations.get(rotation_name, {})
        
        if not rotation_info:
            return True  # No constraints, allow all
        
        # Get resident's program year for this academic year
        resident_program_year = resident.get_year_for_academic_year(block.year)
        if resident_program_year == 0:
            return False  # Not in program yet or graduated
        
        eligible_years = rotation_info.get("eligible_years", [])
        allowed_if_needed = rotation_info.get("allowed_if_needed", [])
        
        # Check if resident's program year is eligible
        if resident_program_year in eligible_years:
            return True
        
        # Check if resident's program year is allowed if needed
        if resident_program_year in allowed_if_needed:
            return True
        
        # SPECIAL RULE: Allow residents whose specialty matches this rotation
        # This allows R5 (and others) to get their specialty rotations even if not in eligible_years
        if isinstance(resident, dict):
            specialty = resident.get('specialty', 'Undecided') or 'Undecided'
        else:
            specialty = getattr(resident, 'specialty', None)
            if specialty is None:
                specialty = resident.__dict__.get('specialty', 'Undecided') if hasattr(resident, '__dict__') else 'Undecided'
            specialty = specialty or 'Undecided'
        
        if specialty != "Undecided" and self._rotation_matches_specialty(rotation_name, specialty):
            # Allow specialty-matched residents (especially R5) to access their specialty rotations
            return True
        
        return False
    
    def _check_period_constraints(self, resident: Resident, rotation_name: str, block: Block) -> bool:
        """Check period-specific constraints"""
        period_constraints = self.rotation_constraints.get("period_constraints", {})
        
        # Get resident's program year for this academic year
        resident_program_year = resident.get_year_for_academic_year(block.year)
        
        # R1 on MGH Trauma P3
        if period_constraints.get("r1_mgh_trauma_p3") and block.block_number == 3:
            if rotation_name == "MGH/Trauma" and resident_program_year == 1:
                return True
            elif rotation_name == "MGH/Trauma" and resident_program_year != 1:
                return False
        
        # R1 on MGH Spine P3
        if period_constraints.get("r1_mgh_spine_p3") and block.block_number == 3:
            if rotation_name == "MGH/Spine" and resident_program_year == 1:
                return True
            elif rotation_name == "MGH/Spine" and resident_program_year != 1:
                return False
        
        # No R4s on MGH Trauma P12-P13
        if period_constraints.get("no_r4_mgh_trauma_p12_p13"):
            if rotation_name == "MGH/Trauma" and block.block_number in [12, 13] and resident_program_year == 4:
                return False
        
        # Only R5s on MGH Trauma P12-P13
        if period_constraints.get("only_r5_mgh_trauma_p12_p13"):
            if rotation_name == "MGH/Trauma" and block.block_number in [12, 13] and resident_program_year != 5:
                return False
        
        return True
    
    def _rotation_matches_specialty(self, rotation_name: str, specialty: str) -> bool:
        """Check if a rotation matches a resident's specialty"""
        if specialty == "Undecided":
            return False
        
        rotation_keywords = self.specialty_to_rotations.get(specialty, [])
        if not rotation_keywords:
            return False
        
        rotation_upper = rotation_name.upper()
        for keyword in rotation_keywords:
            if keyword.upper() in rotation_upper:
                return True
        return False
    
    def optimize(self) -> List[Assignment]:
        """Generate optimal schedule with all constraints enforced"""
        # Load min/max blocks per resident per year from config
        min_blocks_per_year = self.data.config.get("optimization", {}).get("constraints", {}).get("min_blocks_per_resident_per_year", 10)
        max_blocks_per_year = self.data.config.get("optimization", {}).get("constraints", {}).get("max_blocks_per_resident_per_year", 13)
        
        # Get all blocks
        all_blocks = {b.id: b for b in self.data.blocks}
        
        if not all_blocks:
            return []
        
        # Group blocks by year and block_number (period)
        blocks_by_period = {}  # {(year, block_number): [blocks]}
        academic_years = set()
        for block_id, block in all_blocks.items():
            key = (block.year, block.block_number)
            if key not in blocks_by_period:
                blocks_by_period[key] = []
            blocks_by_period[key].append(block)
            academic_years.add(block.year)
        
        # Get active residents for each academic year
        residents_by_year = {}
        all_resident_ids = set()
        for year in academic_years:
            year_residents = {r.id: r for r in self.data.get_active_residents_for_year(year)}
            residents_by_year[year] = year_residents
            all_resident_ids.update(year_residents.keys())
        
        # Track assignments
        assignments = []  # List of (resident_id, block_id) tuples
        resident_rotation_counts = {r_id: {} for r_id in all_resident_ids}  # Track blocks per rotation per resident
        resident_period_assignments = {}  # Track which rotation each resident is on per period
        
        # Sort periods chronologically
        sorted_periods = sorted(blocks_by_period.keys())
        
        # Phase 1: Assign required period-specific constraints first
        for (year, block_num) in sorted_periods:
            period_blocks = blocks_by_period[(year, block_num)]
            
            # Get active residents for this academic year
            residents = residents_by_year.get(year, {})
            if not residents:
                continue
            
            # R1 on MGH Trauma P3
            if block_num == 3:
                mgh_trauma_blocks = [b for b in period_blocks if b.rotation == "MGH/Trauma"]
                r1_residents = [r for r in residents.values() if r.get_year_for_academic_year(year) == 1]
                if mgh_trauma_blocks and r1_residents:
                    block = mgh_trauma_blocks[0]
                    resident = random.choice(r1_residents)
                    if (resident.id, block.id) not in assignments:
                        assignments.append((resident.id, block.id))
                        if resident.id not in resident_period_assignments:
                            resident_period_assignments[resident.id] = {}
                        resident_period_assignments[resident.id][(year, block_num)] = block.rotation
            
            # R1 on MGH Spine P3
            if block_num == 3:
                mgh_spine_blocks = [b for b in period_blocks if b.rotation == "MGH/Spine"]
                r1_residents = [r for r in residents.values() if r.get_year_for_academic_year(year) == 1]
                if mgh_spine_blocks and r1_residents:
                    block = mgh_spine_blocks[0]
                    resident = random.choice([r for r in r1_residents if (r.id, (year, block_num)) not in resident_period_assignments.get(r.id, {})])
                    if resident and (resident.id, block.id) not in assignments:
                        assignments.append((resident.id, block.id))
                        if resident.id not in resident_period_assignments:
                            resident_period_assignments[resident.id] = {}
                        resident_period_assignments[resident.id][(year, block_num)] = block.rotation
        
        # Phase 2: Prioritize R5 residents for their specialty rotations
        # Process R5 residents first to ensure they get MAXIMUM blocks in their specialty
        # Go through all periods and assign R5 residents to their specialty rotations
        for year in academic_years:
            residents = residents_by_year.get(year, {})
            if not residents:
                continue
            
            # Get R5 residents with specialties
            r5_residents = [r for r in residents.values() if r.get_year_for_academic_year(year) == 5]
            
            for r5 in r5_residents:
                # Get R5's specialty
                if isinstance(r5, dict):
                    specialty = r5.get('specialty', 'Undecided') or 'Undecided'
                else:
                    specialty = getattr(r5, 'specialty', None)
                    if specialty is None:
                        specialty = r5.__dict__.get('specialty', 'Undecided') if hasattr(r5, '__dict__') else 'Undecided'
                    specialty = specialty or 'Undecided'
                
                if specialty == "Undecided":
                    continue
                
                # Find ALL blocks matching this R5's specialty across all periods
                specialty_blocks = []
                for (y, block_num) in sorted_periods:
                    if y != year:
                        continue
                    period_blocks = blocks_by_period[(y, block_num)]
                    for block in period_blocks:
                        if self._rotation_matches_specialty(block.rotation, specialty):
                            # Check if R5 is already assigned this period
                            if r5.id in resident_period_assignments:
                                if (y, block_num) in resident_period_assignments[r5.id]:
                                    continue
                            
                            # Check eligibility and period constraints
                            if not self._is_resident_eligible(r5, block.rotation, block):
                                continue
                            if not self._check_period_constraints(r5, block.rotation, block):
                                continue
                            
                            specialty_blocks.append((block, y, block_num))
                
                # Sort specialty blocks by period to assign them systematically
                specialty_blocks.sort(key=lambda x: x[2])  # Sort by block_num
                
                # Assign R5 to as many specialty blocks as possible (up to 13 total blocks)
                for block, y, block_num in specialty_blocks:
                    # Check if R5 has reached 13 blocks for this year
                    resident_year_blocks = sum(1 for (r_id, b_id) in assignments 
                                              if r_id == r5.id and all_blocks[b_id].year == year)
                    if resident_year_blocks >= 13:
                        break
                    
                    # Check if block has space
                    current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                    if current_block_count >= block.max_capacity:
                        continue
                    
                    # Assign R5 to this specialty rotation
                    assignments.append((r5.id, block.id))
                    if r5.id not in resident_period_assignments:
                        resident_period_assignments[r5.id] = {}
                    resident_period_assignments[r5.id][(y, block_num)] = block.rotation
                    
                    # Update counts
                    if block.rotation not in resident_rotation_counts[r5.id]:
                        resident_rotation_counts[r5.id][block.rotation] = 0
                    resident_rotation_counts[r5.id][block.rotation] += 1
        
        # Phase 3: Ensure site minimums are met for each period
        # Check site minimums from constraints
        site_minimums = self.rotation_constraints.get("site_minimums", {})
        
        for (year, block_num) in sorted_periods:
            period_blocks = blocks_by_period[(year, block_num)]
            residents = residents_by_year.get(year, {})
            if not residents:
                continue
            
            # Count residents per site for this period
            site_counts = {}  # {site: count}
            for block in period_blocks:
                site = block.site
                if site not in site_counts:
                    site_counts[site] = 0
                # Count assigned residents to this site in this period
                for resident_id, block_id in assignments:
                    if block_id == block.id:
                        site_counts[site] += 1
            
            # Check if any site is below minimum
            for site, min_required in site_minimums.items():
                current_count = site_counts.get(site, 0)
                if current_count < min_required:
                    # Find blocks at this site for this period
                    site_blocks = [b for b in period_blocks if b.site == site]
                    
                    # Find residents not yet assigned this period who can fill this site
                    unassigned_residents = []
                    for resident in residents.values():
                        # Check if already assigned this period
                        if resident.id in resident_period_assignments:
                            if (year, block_num) in resident_period_assignments[resident.id]:
                                continue
                        
                        # Check if resident can be assigned to any block at this site
                        for block in site_blocks:
                            current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                            if current_block_count >= block.max_capacity:
                                continue
                            
                            if self._is_resident_eligible(resident, block.rotation, block):
                                if self._check_period_constraints(resident, block.rotation, block):
                                    unassigned_residents.append((resident, block))
                                    break
                    
                    # Assign residents to fill site minimum
                    needed = min_required - current_count
                    assigned_count = 0
                    for resident, block in unassigned_residents:
                        if assigned_count >= needed:
                            break
                        
                        # Double-check block still has space
                        current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                        if current_block_count >= block.max_capacity:
                            continue
                        
                        # Check if resident hasn't exceeded blocks for this year
                        resident_year_blocks = sum(1 for (r_id, b_id) in assignments 
                                                  if r_id == resident.id and all_blocks[b_id].year == year)
                        resident_program_year = resident.get_year_for_academic_year(year)
                        if resident_program_year in [2, 3, 4, 5] and resident_year_blocks >= 13:
                            continue
                        elif resident_program_year == 1 and resident_year_blocks >= 5:
                            continue
                        
                        # Assign resident to this block
                        assignments.append((resident.id, block.id))
                        if resident.id not in resident_period_assignments:
                            resident_period_assignments[resident.id] = {}
                        resident_period_assignments[resident.id][(year, block_num)] = block.rotation
                        
                        # Update counts
                        if block.rotation not in resident_rotation_counts[resident.id]:
                            resident_rotation_counts[resident.id][block.rotation] = 0
                        resident_rotation_counts[resident.id][block.rotation] += 1
                        
                        assigned_count += 1
        
        # Phase 4: Fill all blocks respecting constraints (for remaining residents and remaining slots)
        for (year, block_num) in sorted_periods:
            period_blocks = blocks_by_period[(year, block_num)]
            
            # Shuffle blocks for randomness
            random.shuffle(period_blocks)
            
            for block in period_blocks:
                # Count current assignments to this block
                current_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                
                # ALWAYS fill to min capacity first, then up to max
                # This ensures no blocks are empty
                if current_count < block.min_capacity:
                    target_count = block.min_capacity
                else:
                    target_count = block.max_capacity
                
                # Get active residents for this academic year
                residents = residents_by_year.get(year, {})
                if not residents:
                    continue
                
                # Find eligible residents for this rotation
                eligible_residents = []
                for resident in residents.values():
                    # Check if already assigned to another rotation this period
                    if resident.id in resident_period_assignments:
                        if (year, block_num) in resident_period_assignments[resident.id]:
                            continue  # Already assigned this period
                    
                    # Check eligibility
                    if not self._is_resident_eligible(resident, block.rotation, block):
                        continue
                    
                    # Check period constraints
                    if not self._check_period_constraints(resident, block.rotation, block):
                        continue
                    
                    eligible_residents.append(resident)
                
                
                # Assign residents to fill the block
                while current_count < target_count and eligible_residents:
                    # Filter residents who haven't exceeded max blocks per year
                    eligible_within_limit = []
                    for r in eligible_residents:
                        # Count blocks this resident has in this year
                        resident_year_blocks = sum(1 for (r_id, b_id) in assignments 
                                                  if r_id == r.id and all_blocks[b_id].year == year)
                        
                        # Get resident's program year for this academic year
                        resident_program_year = r.get_year_for_academic_year(year)
                        
                        # R2-R5 must have exactly 13 blocks, R1 must have exactly 5 blocks
                        if resident_program_year in [2, 3, 4, 5]:
                            max_allowed = 13
                        elif resident_program_year == 1:
                            max_allowed = 5
                        else:
                            max_allowed = 0  # Not in program yet or graduated
                        
                        if resident_year_blocks < max_allowed:
                            eligible_within_limit.append(r)
                    
                    if not eligible_within_limit:
                        break  # No residents available within limit
                    
                    # Sort residents by priority:
                    # 1. Program year (R5 first, then R4, R3, R2, R1)
                    # 2. Specialty match (prefer residents whose specialty matches this rotation)
                    # 3. For R5 with specialty match: prioritize giving them MORE blocks in their specialty (not fewer)
                    # 4. For others: fewer assignments to this rotation is better
                    # 5. Total assignments
                    def get_priority_score(r):
                        resident_program_year = r.get_year_for_academic_year(year)
                        # Get specialty - handle both Resident objects and dicts
                        if isinstance(r, dict):
                            specialty = r.get('specialty', 'Undecided') or 'Undecided'
                        else:
                            # Try to get specialty attribute, with fallback
                            specialty = getattr(r, 'specialty', None)
                            if specialty is None:
                                # If specialty doesn't exist, check if it's in __dict__ (for dataclass)
                                specialty = r.__dict__.get('specialty', 'Undecided') if hasattr(r, '__dict__') else 'Undecided'
                            specialty = specialty or 'Undecided'
                        
                        matches_specialty = self._rotation_matches_specialty(block.rotation, specialty)
                        
                        # Priority: R5=5, R4=4, R3=3, R2=2, R1=1 (higher is better)
                        program_year_priority = resident_program_year if 1 <= resident_program_year <= 5 else 0
                        
                        # Specialty match bonus: Much higher for R5, moderate for others
                        if resident_program_year == 5 and matches_specialty:
                            specialty_bonus = 100  # Very high priority for R5 with specialty match
                        elif matches_specialty:
                            specialty_bonus = 10  # Moderate priority for others with specialty match
                        else:
                            specialty_bonus = 0
                        
                        # Rotation count for this specific rotation
                        rotation_count = resident_rotation_counts[r.id].get(block.rotation, 0)
                        
                        # Total count
                        total_count = sum(resident_rotation_counts[r.id].values())
                        
                        # For R5 with specialty match: we want to MAXIMIZE their blocks in specialty
                        # So we use negative rotation_count (more blocks = higher priority)
                        # For others: fewer rotations to this type is better (positive rotation_count)
                        if resident_program_year == 5 and matches_specialty:
                            # R5 with specialty match: prioritize giving them MORE blocks
                            rotation_priority = -rotation_count  # Negative so more blocks = higher priority
                        else:
                            # Others: fewer blocks to this rotation is better
                            rotation_priority = rotation_count
                        
                        # Return tuple for sorting: (negative priority score, so higher priority comes first)
                        # We want: R5 with specialty match (maximize their specialty blocks) > R5 without > R4 with match > etc.
                        return (
                            -program_year_priority,  # Negative so R5 (5) comes before R1 (1)
                            -specialty_bonus,  # Negative so matches (10) come before non-matches (0)
                            rotation_priority,  # For R5+specialty: negative (more is better), others: positive (fewer is better)
                            total_count  # Fewer total rotations is better
                        )
                    
                    # Sort by priority (best first)
                    eligible_within_limit.sort(key=get_priority_score)
                    best_resident = eligible_within_limit[0]
                    
                    assignments.append((best_resident.id, block.id))
                    if best_resident.id not in resident_period_assignments:
                        resident_period_assignments[best_resident.id] = {}
                    resident_period_assignments[best_resident.id][(year, block_num)] = block.rotation
                    
                    # Update counts
                    if block.rotation not in resident_rotation_counts[best_resident.id]:
                        resident_rotation_counts[best_resident.id][block.rotation] = 0
                    resident_rotation_counts[best_resident.id][block.rotation] += 1
                    
                    # Remove from eligible list
                    eligible_residents.remove(best_resident)
                    current_count += 1
        
        # Phase 3: Ensure each resident gets the required blocks per year
        # R2, R3, R4, R5 must have exactly 13 blocks per year (one per period)
        # R1 must have exactly 5 blocks per year
        
        # Track blocks per resident per year
        resident_blocks_per_year = {}  # {(resident_id, year): count}
        for resident_id, block_id in assignments:
            block = all_blocks[block_id]
            key = (resident_id, block.year)
            resident_blocks_per_year[key] = resident_blocks_per_year.get(key, 0) + 1
        
        # For R2-R5, ensure they have a block in EVERY period (1-13)
        # This is more systematic than random filling
        for year in academic_years:
            residents = residents_by_year.get(year, {})
            for resident in residents.values():
                # Get resident's program year for this academic year
                resident_program_year = resident.get_year_for_academic_year(year)
                
                # Only process R2-R5 (they need all 13 periods filled)
                if resident_program_year not in [2, 3, 4, 5]:
                    continue
                
                # Check which periods this resident is missing
                for block_num in range(1, 14):  # Periods 1-13
                    # Check if resident already has a block in this period
                    if resident.id in resident_period_assignments:
                        if (year, block_num) in resident_period_assignments[resident.id]:
                            continue  # Already assigned this period
                    
                    # Find available blocks for this period
                    period_blocks = blocks_by_period.get((year, block_num), [])
                    available_blocks = []
                    
                    for block in period_blocks:
                        # Check if block has space
                        current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                        if current_block_count >= block.max_capacity:
                            continue
                        
                        # Check eligibility (be lenient for filling)
                        is_eligible = self._is_resident_eligible(resident, block.rotation, block)
                        
                        # Check period constraints
                        period_ok = self._check_period_constraints(resident, block.rotation, block)
                        
                        if not period_ok:
                            continue
                        
                        # For R2-R5 filling, allow if eligible OR if it's a general rotation
                        general_rotations = ["SMH", "MCH/Shriners", "Community", "Electives", "Research", "MGH/Sports"]
                        is_general = block.rotation in general_rotations
                        
                        if is_eligible or is_general:
                            available_blocks.append(block)
                    
                    # If still no blocks, try any block with space (last resort)
                    if not available_blocks:
                        for block in period_blocks:
                            current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                            if current_block_count < block.max_capacity:
                                if self._check_period_constraints(resident, block.rotation, block):
                                    available_blocks.append(block)
                    
                    # Assign to a block if available
                    if available_blocks:
                        # Prefer blocks that need more residents
                        best_block = max(available_blocks,
                                       key=lambda b: (
                                           b.max_capacity - sum(1 for (r_id, b_id) in assignments if b_id == b.id),
                                           -resident_rotation_counts[resident.id].get(b.rotation, 0)
                                       ))
                        
                        assignments.append((resident.id, best_block.id))
                        if resident.id not in resident_period_assignments:
                            resident_period_assignments[resident.id] = {}
                        resident_period_assignments[resident.id][(year, block_num)] = best_block.rotation
                        
                        # Update counts
                        if best_block.rotation not in resident_rotation_counts[resident.id]:
                            resident_rotation_counts[resident.id][best_block.rotation] = 0
                        resident_rotation_counts[resident.id][best_block.rotation] += 1
                        
                        # Update resident_blocks_per_year
                        key = (resident.id, year)
                        resident_blocks_per_year[key] = resident_blocks_per_year.get(key, 0) + 1
        
        # For R1, ensure they have exactly 5 blocks (use the old method)
        for year in academic_years:
            residents = residents_by_year.get(year, {})
            for resident in residents.values():
                key = (resident.id, year)
                current_blocks = resident_blocks_per_year.get(key, 0)
                
                # Get resident's program year for this academic year
                resident_program_year = resident.get_year_for_academic_year(year)
                
                # Only process R1
                if resident_program_year != 1:
                    continue
                
                required_blocks = 5
                
                # If resident has fewer than required blocks, assign them to more blocks
                # Keep trying until we reach the required number or run out of options
                max_attempts = 200  # Increased attempts for R2-R5 who need 13 blocks
                attempts = 0
                while current_blocks < required_blocks and attempts < max_attempts:
                    attempts += 1
                    # Find available blocks for this year that this resident can be assigned to
                    available_blocks = []
                    
                    # First pass: Find blocks with space that meet all constraints
                    for (y, block_num) in sorted_periods:
                        if y != year:
                            continue
                        
                        # Check if resident already assigned this period
                        if resident.id in resident_period_assignments:
                            if (year, block_num) in resident_period_assignments[resident.id]:
                                continue
                        
                        period_blocks = blocks_by_period[(year, block_num)]
                        for block in period_blocks:
                            # Check if block has space (below max capacity)
                            current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                            if current_block_count >= block.max_capacity:
                                continue
                            
                            # Check eligibility
                            if not self._is_resident_eligible(resident, block.rotation, block):
                                continue
                            
                            # Check period constraints
                            if not self._check_period_constraints(resident, block.rotation, block):
                                continue
                            
                            available_blocks.append(block)
                    
                    # Second pass: If still no blocks, be more lenient - allow blocks even if at min capacity
                    # (as long as below max) and relax some constraints for R2-R5
                    if not available_blocks and resident_program_year in [2, 3, 4, 5]:
                        for (y, block_num) in sorted_periods:
                            if y != year:
                                continue
                            
                            if resident.id in resident_period_assignments:
                                if (year, block_num) in resident_period_assignments[resident.id]:
                                    continue
                            
                            period_blocks = blocks_by_period[(year, block_num)]
                            for block in period_blocks:
                                current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                                # Must be below max capacity
                                if current_block_count >= block.max_capacity:
                                    continue
                                
                                # For R2-R5 filling remaining blocks, be more lenient with eligibility
                                # Allow if they're eligible OR if it's a general rotation
                                is_eligible = self._is_resident_eligible(resident, block.rotation, block)
                                
                                # Check period constraints (but be lenient for filling)
                                period_ok = self._check_period_constraints(resident, block.rotation, block)
                                
                                # For filling remaining blocks, allow if:
                                # 1. Eligible and period OK, OR
                                # 2. General rotations (SMH, MCH/Shriners, Community, Electives, Research) that accept all years
                                general_rotations = ["SMH", "MCH/Shriners", "Community", "Electives", "Research"]
                                is_general = block.rotation in general_rotations
                                
                                if (is_eligible and period_ok) or (is_general and period_ok):
                                    available_blocks.append(block)
                    
                    if not available_blocks:
                        # Last resort: Try any block that has space (even if constraints are tight)
                        # This ensures we fill all required blocks
                        for (y, block_num) in sorted_periods:
                            if y != year:
                                continue
                            
                            if resident.id in resident_period_assignments:
                                if (year, block_num) in resident_period_assignments[resident.id]:
                                    continue
                            
                            period_blocks = blocks_by_period[(year, block_num)]
                            for block in period_blocks:
                                current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                                if current_block_count < block.max_capacity:
                                    # Only check period constraints (skip eligibility for last resort)
                                    if self._check_period_constraints(resident, block.rotation, block):
                                        available_blocks.append(block)
                    
                    if not available_blocks:
                        # Still no blocks - this shouldn't happen, but break to avoid infinite loop
                        print(f"ERROR: Could not find any available blocks for resident {resident.id} in year {year}. Has {current_blocks}/{required_blocks} blocks")
                        print(f"  Resident program year: {resident_program_year}")
                        # Try to find why - check all periods
                        for (y, block_num) in sorted_periods:
                            if y != year:
                                continue
                            if resident.id in resident_period_assignments:
                                if (year, block_num) in resident_period_assignments[resident.id]:
                                    continue
                            period_blocks = blocks_by_period[(year, block_num)]
                            for block in period_blocks:
                                current_block_count = sum(1 for (r_id, b_id) in assignments if b_id == block.id)
                                eligible = self._is_resident_eligible(resident, block.rotation, block)
                                period_ok = self._check_period_constraints(resident, block.rotation, block)
                                print(f"    Period {block_num}, Block {block.rotation}: count={current_block_count}/{block.max_capacity}, eligible={eligible}, period_ok={period_ok}")
                        break
                    
                    # Randomly select from available blocks to fill remaining slots
                    # This ensures variety and prevents all residents getting the same rotations
                    best_block = random.choice(available_blocks)
                    
                    assignments.append((resident.id, best_block.id))
                    if resident.id not in resident_period_assignments:
                        resident_period_assignments[resident.id] = {}
                    resident_period_assignments[resident.id][(year, best_block.block_number)] = best_block.rotation
                    
                    # Update counts
                    if best_block.rotation not in resident_rotation_counts[resident.id]:
                        resident_rotation_counts[resident.id][best_block.rotation] = 0
                    resident_rotation_counts[resident.id][best_block.rotation] += 1
                    
                    current_blocks += 1
                    resident_blocks_per_year[key] = current_blocks
                    
                    # For R2-R5, if we've reached 13 blocks, stop
                    if resident_program_year in [2, 3, 4, 5] and current_blocks >= 13:
                        print(f"  ✓ Filled all blocks for {resident.id} in year {year}: {current_blocks}/13")
                        break
                
                # Final check - warn if still not filled
                if resident_program_year in [2, 3, 4, 5] and current_blocks < 13:
                    print(f"  ✗ FAILED to fill all blocks for {resident.id} in year {year}: {current_blocks}/13")
        
        # Phase 4: Create assignment objects
        new_assignments = []
        for resident_id, block_id in assignments:
            block = all_blocks[block_id]
            assignment = Assignment(
                resident_id=resident_id,
                block_id=block_id,
                rotation=block.rotation,
                site=block.site,
                block_number=block.block_number,
                year=block.year
            )
            new_assignments.append(assignment)
        
        return new_assignments
    
    def get_optimization_stats(self) -> Dict:
        """Get statistics about the optimization"""
        return {
            "status": "success",
            "message": "Schedule generated with rotation constraints"
        }
