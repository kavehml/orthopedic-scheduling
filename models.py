"""
Data models for resident scheduling system
"""
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Resident:
    """Represents a resident"""
    id: str
    name: str
    program_year: int  # 1-5 (R1, R2, R3, R4, R5)
    entry_year: int  # Year they entered the program
    specialty: str = "Undecided"  # Specialty field
    preferences: Optional[Dict] = None
    
    def to_dict(self):
        return asdict(self)
    
    def get_year_for_academic_year(self, academic_year: int) -> int:
        """Calculate what program year (R1-R5) this resident is in for a given academic year
        Returns:
            - Negative number if not started yet (e.g., -1 means starts next year)
            - 1-5 for active residents (R1-R5)
            - 0 for graduated
        """
        years_in_program = academic_year - self.entry_year
        if years_in_program < 0:
            return years_in_program  # Negative: not in program yet (e.g., -1 = starts next year)
        if years_in_program >= 5:
            return 0  # Graduated
        return years_in_program + 1  # R1 = year 1, R2 = year 2, etc.
    
    def is_active_in_year(self, academic_year: int) -> bool:
        """Check if resident is active (not graduated and has started) in given academic year"""
        program_year = self.get_year_for_academic_year(academic_year)
        return 1 <= program_year <= 5


@dataclass
class Block:
    """Represents a time block for a specific rotation"""
    id: str
    block_number: int  # 1-13 (P1-P13)
    year: int  # Academic year
    rotation: str  # Rotation name (e.g., "JGH-Arthro", "MGH/Trauma")
    site: str  # Hospital site
    min_capacity: int = 1  # Minimum residents required
    max_capacity: int = 1  # Maximum residents allowed
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)
    
    @property
    def capacity(self):
        """Return max capacity for backward compatibility"""
        return self.max_capacity


@dataclass
class Assignment:
    """Represents a resident-block assignment"""
    resident_id: str
    block_id: str
    rotation: str  # Rotation name
    site: str
    block_number: int
    year: int
    
    def to_dict(self):
        return asdict(self)


class ScheduleData:
    """Manages all scheduling data"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.residents: List[Resident] = []
        self.blocks: List[Block] = []
        self.assignments: List[Assignment] = []
        self._initialize_data()  # Always initialize - load() will override if data exists
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "program": {
                "blocks_per_year": 13,
                "program_years": 5,
                "new_residents_per_year": 5
            },
            "optimization": {
                "objectives": ["balance_workload", "minimize_conflicts", "ensure_coverage"],
                "constraints": {
                    "max_blocks_per_resident_per_year": 13,
                    "min_blocks_per_resident_per_year": 10,
                    "allow_same_site_consecutive": True
                }
            }
        }
    
    def _load_rotation_constraints(self) -> Dict:
        """Load rotation constraints from JSON file"""
        try:
            with open("rotation_constraints.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _initialize_data(self):
        """Initialize residents and blocks based on config and rotation constraints"""
        blocks_per_year = self.config["program"]["blocks_per_year"]
        program_years = self.config["program"]["program_years"]
        
        # Load rotation constraints
        rotation_constraints = self._load_rotation_constraints()
        rotations = rotation_constraints.get("rotations", {})
        
        # Initialize residents - distribute across program years based on entry year
        # Assume we start with current year and distribute residents across R1-R5
        current_year = datetime.now().year
        new_residents_per_year = self.config["program"].get("new_residents_per_year", 5)
        
        # Create residents for each program year
        resident_id = 1
        for program_year in range(1, program_years + 1):  # R1 through R5
            entry_year = current_year - (program_year - 1)  # R1 entered this year, R2 entered last year, etc.
            num_in_year = new_residents_per_year
            
            for i in range(num_in_year):
                self.residents.append(Resident(
                    id=f"R{resident_id:03d}",
                    name=f"Resident {resident_id}",
                    program_year=program_year,
                    entry_year=entry_year,
                    specialty="Undecided"
                ))
                resident_id += 1
        
        # Initialize blocks for each rotation (all rotations run in all 13 blocks per year)
        current_year = datetime.now().year
        block_id = 1
        
        # If we have rotation constraints, create blocks for each rotation
        if rotations:
            for year_offset in range(program_years):
                academic_year = current_year + year_offset
                for block_num in range(1, blocks_per_year + 1):
                    for rotation_name, rotation_info in rotations.items():
                        site = rotation_info.get("site", "Unknown")
                        min_cap = rotation_info.get("min_residents_per_block", 1)
                        max_cap = rotation_info.get("max_residents_per_block", 1)
                        
                        self.blocks.append(Block(
                            id=f"B{block_id:04d}",
                            block_number=block_num,
                            year=academic_year,
                            rotation=rotation_name,
                            site=site,
                            min_capacity=min_cap,
                            max_capacity=max_cap
                        ))
                        block_id += 1
        else:
            # Fallback to old behavior if no rotation constraints
            sites = self.config["program"].get("sites", ["Site A", "Site B", "Site C"])
            for year_offset in range(program_years):
                academic_year = current_year + year_offset
                for block_num in range(1, blocks_per_year + 1):
                    site = sites[(block_num - 1) % len(sites)]
                    capacity = self.config["program"].get("residents_per_block", 1)
                    self.blocks.append(Block(
                        id=f"B{block_id:04d}",
                        block_number=block_num,
                        year=academic_year,
                        rotation=f"Rotation-{site}",
                        site=site,
                        min_capacity=1,
                        max_capacity=capacity
                    ))
                    block_id += 1
    
    def add_resident(self, name: str, program_year: int, entry_year: Optional[int] = None, specialty: str = "Undecided") -> Resident:
        """Add a new resident"""
        if entry_year is None:
            entry_year = datetime.now().year
        resident_id = f"R{len(self.residents) + 1:03d}"
        resident = Resident(id=resident_id, name=name, program_year=program_year, entry_year=entry_year, specialty=specialty)
        self.residents.append(resident)
        return resident
    
    def remove_resident(self, resident_id: str):
        """Remove a resident and their assignments"""
        self.residents = [r for r in self.residents if r.id != resident_id]
        self.assignments = [a for a in self.assignments if a.resident_id != resident_id]
    
    def update_resident(self, resident_id: str, **kwargs):
        """Update resident properties"""
        for resident in self.residents:
            if resident.id == resident_id:
                for key, value in kwargs.items():
                    # Handle backward compatibility: 'year' -> 'program_year'
                    if key == 'year' and 'program_year' not in kwargs:
                        key = 'program_year'
                    # Always allow setting specialty (it's a dataclass field)
                    if key == 'specialty' or hasattr(resident, key):
                        setattr(resident, key, value)
                return resident
        return None
    
    def get_active_residents_for_year(self, academic_year: int) -> List[Resident]:
        """Get all residents who are active (not graduated) in a given academic year"""
        return [r for r in self.residents if r.is_active_in_year(academic_year)]
    
    def add_new_r1_residents(self, academic_year: int, count: int):
        """Add new R1 residents for a given academic year"""
        new_residents = []
        for i in range(count):
            resident_id = f"R{len(self.residents) + 1:03d}"
            resident = Resident(
                id=resident_id,
                name=f"Resident {len(self.residents) + 1}",
                program_year=1,
                entry_year=academic_year,
                specialty="Undecided"
            )
            self.residents.append(resident)
            new_residents.append(resident)
        return new_residents
    
    def ensure_residents_for_all_years(self):
        """Ensure we have the correct number of residents for each entry year"""
        current_year = datetime.now().year
        new_residents_per_year = self.config["program"].get("new_residents_per_year", 5)
        program_years = self.config["program"]["program_years"]
        
        # Check each entry year from (current_year - program_years + 1) to current_year
        for entry_year in range(current_year - program_years + 1, current_year + 1):
            # Count how many residents we have for this entry year
            residents_for_year = [r for r in self.residents if r.entry_year == entry_year]
            current_count = len(residents_for_year)
            
            # If we need more, add them
            if current_count < new_residents_per_year:
                needed = new_residents_per_year - current_count
                self.add_new_r1_residents(entry_year, needed)
        
        # Also ensure we have residents for future years if blocks exist for them
        if self.blocks:
            max_year = max(b.year for b in self.blocks)
            for future_year in range(current_year + 1, max_year + 1):
                entry_year = future_year
                residents_for_year = [r for r in self.residents if r.entry_year == entry_year]
                if len(residents_for_year) < new_residents_per_year:
                    needed = new_residents_per_year - len(residents_for_year)
                    self.add_new_r1_residents(entry_year, needed)
    
    def add_assignment(self, resident_id: str, block_id: str, rotation: str, site: str, block_number: int, year: int):
        """Add an assignment (allows multiple residents per block)"""
        # Check if block exists and has capacity
        block = next((b for b in self.blocks if b.id == block_id), None)
        if not block:
            raise ValueError(f"Block {block_id} not found")
        
        # Check if resident is already assigned to ANY rotation in this block period
        # (residents can only be on one rotation per block period)
        existing_same_period = [a for a in self.assignments 
                               if a.resident_id == resident_id 
                               and a.block_number == block_number 
                               and a.year == year]
        if existing_same_period:
            raise ValueError(f"Resident {resident_id} is already assigned to {existing_same_period[0].rotation} in block {block_number}, year {year}")
        
        # Check if resident is already assigned to this specific block
        existing = [a for a in self.assignments if a.resident_id == resident_id and a.block_id == block_id]
        if existing:
            return existing[0]  # Already assigned
        
        # Check max capacity
        current_assignments = [a for a in self.assignments if a.block_id == block_id]
        if len(current_assignments) >= block.max_capacity:
            raise ValueError(f"Block {block_id} is at max capacity ({block.max_capacity} residents)")
        
        assignment = Assignment(
            resident_id=resident_id,
            block_id=block_id,
            rotation=rotation,
            site=site,
            block_number=block_number,
            year=year
        )
        self.assignments.append(assignment)
        return assignment
    
    def remove_assignment(self, block_id: str, resident_id: str = None):
        """Remove an assignment. If resident_id is provided, remove only that assignment. Otherwise remove all for the block."""
        if resident_id:
            self.assignments = [a for a in self.assignments 
                              if not (a.block_id == block_id and a.resident_id == resident_id)]
        else:
            self.assignments = [a for a in self.assignments if a.block_id != block_id]
    
    def get_resident_assignments(self, resident_id: str) -> List[Assignment]:
        """Get all assignments for a resident"""
        return [a for a in self.assignments if a.resident_id == resident_id]
    
    def get_block_assignment(self, block_id: str) -> Optional[Assignment]:
        """Get assignment for a specific block"""
        matches = [a for a in self.assignments if a.block_id == block_id]
        return matches[0] if matches else None
    
    def to_dict(self) -> Dict:
        """Convert all data to dictionary for JSON serialization"""
        return {
            "residents": [r.to_dict() for r in self.residents],
            "blocks": [b.to_dict() for b in self.blocks],
            "assignments": [a.to_dict() for a in self.assignments],
            "config": self.config
        }
    
    def save(self, filepath: str = "data.json"):
        """Save data to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load(self, filepath: str = "data.json"):
        """Load data from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Load residents, handling old format
            residents_data = data.get("residents", [])
            self.residents = []
            for r in residents_data:
                # Handle backward compatibility: old format had 'year' instead of 'program_year' and 'entry_year'
                if "entry_year" not in r:
                    # Old format - estimate entry year based on program year
                    program_year = r.get("program_year") or r.get("year", 1)
                    current_year = datetime.now().year
                    r["entry_year"] = current_year - (program_year - 1)
                if "program_year" not in r and "year" in r:
                    r["program_year"] = r["year"]
                    del r["year"]
                # Handle backward compatibility: add specialty if missing
                if "specialty" not in r:
                    r["specialty"] = "Undecided"
                self.residents.append(Resident(**r))
            
            # Load blocks and ensure they have rotation and capacity set
            blocks_data = data.get("blocks", [])
            default_capacity = self.config["program"].get("residents_per_block", 1)
            self.blocks = []
            for b in blocks_data:
                # Ensure rotation is set (for blocks created before rotation feature)
                if "rotation" not in b:
                    b["rotation"] = b.get("site", "Unknown")
                # Ensure capacity is set (for blocks created before capacity feature)
                if "min_capacity" not in b:
                    b["min_capacity"] = 1
                if "max_capacity" not in b:
                    if "capacity" in b:
                        b["max_capacity"] = b["capacity"]
                    else:
                        b["max_capacity"] = default_capacity
                # Remove old capacity field if present
                if "capacity" in b:
                    del b["capacity"]
                self.blocks.append(Block(**b))
            
            # Load assignments, handling old format without rotation field
            assignments_data = data.get("assignments", [])
            self.assignments = []
            for a in assignments_data:
                # If rotation is missing, try to get it from the block or use site as fallback
                if "rotation" not in a:
                    # Try to find the block to get its rotation
                    block = next((b for b in self.blocks if b.id == a.get("block_id")), None)
                    if block:
                        a["rotation"] = block.rotation
                    else:
                        a["rotation"] = a.get("site", "Unknown")
                self.assignments.append(Assignment(**a))
            if "config" in data:
                self.config = data["config"]
                # Update capacity for existing blocks if config changed
                default_capacity = self.config["program"].get("residents_per_block", 1)
                for block in self.blocks:
                    if block.max_capacity <= 0:
                        block.max_capacity = default_capacity
                    if block.min_capacity <= 0:
                        block.min_capacity = 1
        except FileNotFoundError:
            pass  # Use initialized data

