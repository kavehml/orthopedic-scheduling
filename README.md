# Orthopedic Surgery Resident Scheduling System

A comprehensive scheduling system for managing orthopedic surgery residents across multiple hospital sites with advanced optimization capabilities.

## Features

- **Smart Scheduling**: Automated schedule optimization with constraint enforcement
- **Resident Management**: Track residents by entry year, program year (R1-R5), and specialty
- **Year View**: Calendar-style view of schedules by academic year
- **Student View**: Individual resident schedule views with PDF export
- **Configuration**: Flexible configuration of rotations, constraints, and program parameters
- **Specialty-Based Priority**: R5 residents get priority for their specialty rotations
- **Site Coverage**: Ensures all sites meet minimum staffing requirements

## Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Open in browser**:
   ```
   http://127.0.0.1:5000
   ```

## Deployment

See `QUICK_DEPLOY.md` for easy deployment instructions to Railway (free tier available).

## Configuration

- `config.json`: Program settings (blocks per year, program years, etc.)
- `rotation_constraints.json`: Detailed rotation constraints and site requirements

## Requirements

- Python 3.11+
- Flask 3.0+
- Flask-CORS 4.0+
