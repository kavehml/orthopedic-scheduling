"""
Flask web application for resident scheduling system
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from models import ScheduleData, Resident, Assignment, Block
from optimizer import ScheduleOptimizer
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# Global schedule data instance
# Initialize with error handling for cloud deployment
try:
    schedule_data = ScheduleData()
except Exception as e:
    print(f"Error initializing ScheduleData: {e}")
    import traceback
    traceback.print_exc()
    # Create empty instance as fallback
    from models import ScheduleData
    schedule_data = ScheduleData()
    schedule_data.residents = []
    schedule_data.blocks = []
    schedule_data.assignments = []

# Check if rotation_constraints.json exists - if so, always use it (force reinitialize blocks)
try:
    if os.path.exists("rotation_constraints.json"):
        # Load residents from data.json if it exists
        try:
            with open("data.json", 'r') as f:
                data = json.load(f)
            # Load residents (but don't reinitialize them) - handle old format
            residents_data = data.get("residents", [])
            schedule_data.residents = []
            current_year = datetime.now().year
            for r in residents_data:
                # Handle backward compatibility: old format had 'year' instead of 'program_year' and 'entry_year'
                if "entry_year" not in r:
                    # Old format - estimate entry year based on program year
                    program_year = r.get("program_year") or r.get("year", 1)
                    r["entry_year"] = current_year - (program_year - 1)
                if "program_year" not in r and "year" in r:
                    r["program_year"] = r["year"]
                    del r["year"]
                # Handle missing specialty field
                if "specialty" not in r:
                    r["specialty"] = "Undecided"
                schedule_data.residents.append(Resident(**r))
            # Clear assignments since blocks will change
            schedule_data.assignments = []
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            # No data file or invalid data - residents already initialized in __init__
            print(f"Note: Could not load data.json: {e}")
            pass
        
        # Ensure we have the correct number of residents for all years
        try:
            schedule_data.ensure_residents_for_all_years()
        except Exception as e:
            print(f"Warning: Could not ensure residents for all years: {e}")
        
        # Force reinitialize BLOCKS ONLY with rotation constraints
        schedule_data.blocks = []  # Clear old blocks
        # Reinitialize blocks (but preserve residents)
        rotation_constraints = schedule_data._load_rotation_constraints()
        rotations = rotation_constraints.get("rotations", {})
        if rotations:
            blocks_per_year = schedule_data.config["program"]["blocks_per_year"]
            program_years = schedule_data.config["program"]["program_years"]
            current_year = datetime.now().year
            block_id = 1
            
            for year_offset in range(program_years):
                academic_year = current_year + year_offset
                for block_num in range(1, blocks_per_year + 1):
                    for rotation_name, rotation_info in rotations.items():
                        site = rotation_info.get("site", "Unknown")
                        min_cap = rotation_info.get("min_residents_per_block", 1)
                        max_cap = rotation_info.get("max_residents_per_block", 1)
                        
                        schedule_data.blocks.append(Block(
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
            print("Warning: No rotations found in rotation_constraints.json")
    else:
        # No rotation constraints - load normally
        try:
            schedule_data.load("data.json")
        except FileNotFoundError:
            print("Note: No data.json found, using default initialization")
            pass
except Exception as e:
    print(f"Error during app initialization: {e}")
    import traceback
    traceback.print_exc()
    # Continue with whatever we have


@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint for Railway"""
    return jsonify({"status": "ok", "message": "Application is running"}), 200


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(schedule_data.config)


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    new_config = request.json
    schedule_data.config.update(new_config)
    
    # Save config
    with open('config.json', 'w') as f:
        json.dump(schedule_data.config, f, indent=2)
    
    return jsonify({"status": "success", "config": schedule_data.config})


@app.route('/api/rotation-constraints', methods=['GET'])
def get_rotation_constraints():
    """Get rotation constraints"""
    try:
        with open('rotation_constraints.json', 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"rotations": {}, "site_minimums": {}, "global_constraints": {}, "period_constraints": {}})


@app.route('/api/rotation-constraints', methods=['POST'])
def update_rotation_constraints():
    """Update rotation constraints"""
    new_constraints = request.json
    
    # Load existing constraints to preserve structure
    try:
        with open('rotation_constraints.json', 'r') as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = {"rotations": {}, "site_minimums": {}, "global_constraints": {}, "period_constraints": {}}
    
    # Update rotations with new min/max values
    if "rotations" in new_constraints:
        for rotation_name, rotation_data in new_constraints["rotations"].items():
            if rotation_name in existing["rotations"]:
                existing["rotations"][rotation_name].update(rotation_data)
            else:
                existing["rotations"][rotation_name] = rotation_data
    
    # Preserve other fields
    if "site_minimums" in new_constraints:
        existing["site_minimums"] = new_constraints["site_minimums"]
    if "global_constraints" in new_constraints:
        existing["global_constraints"] = new_constraints["global_constraints"]
    if "period_constraints" in new_constraints:
        existing["period_constraints"] = new_constraints["period_constraints"]
    
    # Save updated constraints
    with open('rotation_constraints.json', 'w') as f:
        json.dump(existing, f, indent=2)
    
    # Update blocks with new capacities
    for block in schedule_data.blocks:
        if block.rotation in existing["rotations"]:
            rotation_info = existing["rotations"][block.rotation]
            block.min_capacity = rotation_info.get("min_residents_per_block", 1)
            block.max_capacity = rotation_info.get("max_residents_per_block", 1)
    
    schedule_data.save("data.json")
    
    return jsonify({"status": "success", "constraints": existing})


@app.route('/api/entry-year-config', methods=['GET'])
def get_entry_year_config():
    """Get entry year configuration (how many residents per entry year)"""
    # Count residents by entry year
    entry_year_counts = {}
    for resident in schedule_data.residents:
        entry_year = resident.entry_year
        entry_year_counts[entry_year] = entry_year_counts.get(entry_year, 0) + 1
    
    return jsonify(entry_year_counts)


@app.route('/api/entry-year-config', methods=['POST'])
def update_entry_year_config():
    """Update entry year configuration - create/remove residents to match target counts"""
    target_counts = request.json  # {year: count}
    
    # Count current residents by entry year
    current_by_year = {}
    for resident in schedule_data.residents:
        entry_year = resident.entry_year
        if entry_year not in current_by_year:
            current_by_year[entry_year] = []
        current_by_year[entry_year].append(resident)
    
    # For each year in target_counts, ensure we have the right number
    for entry_year, target_count in target_counts.items():
        entry_year = int(entry_year)
        target_count = int(target_count)
        current_residents = current_by_year.get(entry_year, [])
        current_count = len(current_residents)
        
        if target_count > current_count:
            # Add residents
            for i in range(target_count - current_count):
                resident_id = f"R{len(schedule_data.residents) + 1:03d}"
                resident = Resident(
                    id=resident_id,
                    name=f"Resident {len(schedule_data.residents) + 1}",
                    program_year=1,  # Will be calculated based on entry year
                    entry_year=entry_year
                )
                schedule_data.residents.append(resident)
        elif target_count < current_count:
            # Remove residents (remove the last ones added)
            to_remove = current_count - target_count
            residents_to_remove = current_residents[-to_remove:]
            for resident in residents_to_remove:
                schedule_data.remove_resident(resident.id)
    
    schedule_data.save("data.json")
    
    return jsonify({"status": "success", "counts": target_counts})


@app.route('/api/residents', methods=['GET'])
def get_residents():
    """Get all residents"""
    return jsonify([r.to_dict() for r in schedule_data.residents])


@app.route('/api/residents', methods=['POST'])
def add_resident():
    """Add a new resident"""
    data = request.json
    program_year = data.get('program_year') or data.get('year', 1)  # Backward compatibility
    specialty = data.get('specialty', 'Undecided')
    entry_year = data.get('entry_year')
    resident = schedule_data.add_resident(
        name=data.get('name', ''),
        program_year=program_year,
        entry_year=entry_year,
        specialty=specialty
    )
    schedule_data.save("data.json")
    return jsonify(resident.to_dict())


@app.route('/api/residents/<resident_id>', methods=['PUT'])
def update_resident(resident_id):
    """Update a resident"""
    data = request.json
    resident = schedule_data.update_resident(resident_id, **data)
    if resident:
        schedule_data.save("data.json")
        return jsonify(resident.to_dict())
    return jsonify({"error": "Resident not found"}), 404


@app.route('/api/residents/<resident_id>', methods=['DELETE'])
def delete_resident(resident_id):
    """Delete a resident"""
    schedule_data.remove_resident(resident_id)
    schedule_data.save("data.json")
    return jsonify({"status": "success"})


@app.route('/api/blocks', methods=['GET'])
def get_blocks():
    """Get all blocks"""
    year = request.args.get('year', type=int)
    if year:
        blocks = [b for b in schedule_data.blocks if b.year == year]
    else:
        blocks = schedule_data.blocks
    return jsonify([b.to_dict() for b in blocks])


@app.route('/api/assignments', methods=['GET'])
def get_assignments():
    """Get all assignments"""
    resident_id = request.args.get('resident_id')
    block_id = request.args.get('block_id')
    year = request.args.get('year', type=int)
    
    assignments = schedule_data.assignments
    if resident_id:
        assignments = [a for a in assignments if a.resident_id == resident_id]
    if block_id:
        assignments = [a for a in assignments if a.block_id == block_id]
    if year:
        assignments = [a for a in assignments if a.year == year]
    
    return jsonify([a.to_dict() for a in assignments])


@app.route('/api/assignments', methods=['POST'])
def add_assignment():
    """Add an assignment (allows multiple residents per block)"""
    try:
        data = request.json
        # Get rotation from block if not provided
        rotation = data.get('rotation')
        if not rotation:
            # Find the block to get its rotation
            block = next((b for b in schedule_data.blocks if b.id == data['block_id']), None)
            if block:
                rotation = block.rotation
            else:
                rotation = data.get('site', 'Unknown')
        
        assignment = schedule_data.add_assignment(
            resident_id=data['resident_id'],
            block_id=data['block_id'],
            rotation=rotation,
            site=data['site'],
            block_number=data['block_number'],
            year=data['year']
        )
        schedule_data.save("data.json")
        return jsonify(assignment.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/assignments/<block_id>', methods=['DELETE'])
def delete_assignment(block_id):
    """Delete an assignment. Can delete specific resident or all residents from block."""
    resident_id = request.args.get('resident_id')
    schedule_data.remove_assignment(block_id, resident_id)
    schedule_data.save("data.json")
    return jsonify({"status": "success"})


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """Generate optimized schedule"""
    try:
        optimizer = ScheduleOptimizer(schedule_data)
        new_assignments = optimizer.optimize()
        
        if not new_assignments:
            return jsonify({"status": "error", "message": "No solution found - check if you have residents and blocks configured"}), 400
        
        # Clear ALL existing assignments (optimizing for all years)
        schedule_data.assignments = []
        
        # Add new assignments (clear any potential duplicates first)
        for assignment in new_assignments:
            # Remove any existing assignment for this block+resident combination
            schedule_data.assignments = [
                a for a in schedule_data.assignments 
                if not (a.block_id == assignment.block_id and a.resident_id == assignment.resident_id)
            ]
            # Now add the new assignment
            try:
                schedule_data.add_assignment(
                    assignment.resident_id,
                    assignment.block_id,
                    assignment.rotation,
                    assignment.site,
                    assignment.block_number,
                    assignment.year
                )
            except ValueError as e:
                # If capacity issue, skip and continue (shouldn't happen in optimization)
                print(f"Warning: Could not add assignment: {e}")
                continue
        
        schedule_data.save("data.json")
        stats = optimizer.get_optimization_stats()
        return jsonify({
            "status": "success",
            "assignments": [a.to_dict() for a in new_assignments],
            "stats": stats
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Error during optimization: {error_msg}"}), 500


@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """Get complete schedule view"""
    return jsonify(schedule_data.to_dict())


@app.route('/api/schedule', methods=['POST'])
def save_schedule():
    """Save complete schedule"""
    data = request.json
    schedule_data.save("data.json")
    return jsonify({"status": "success"})


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Get port from environment variable (for Cloud Run/Railway) or use default
    port = int(os.environ.get('PORT', 5000))
    # For Railway/Cloud, bind to 0.0.0.0 to accept external connections
    host = os.environ.get('HOST', '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("=" * 50)
    print(f"Starting server at http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    try:
        app.run(debug=debug, host=host, port=port, use_reloader=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

