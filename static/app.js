// Main application JavaScript

const API_BASE = '/api';

// Helper function to calculate program year (R1-R5) for a resident in a given academic year
// Returns: negative if not started, 1-5 for active, 0 for graduated
function getProgramYear(resident, academicYear) {
    if (resident.get_year_for_academic_year) {
        return resident.get_year_for_academic_year(academicYear);
    }
    // Calculate from entry_year if available
    if (resident.entry_year) {
        const yearsInProgram = academicYear - resident.entry_year;
        if (yearsInProgram < 0) return yearsInProgram; // Negative: not started yet
        if (yearsInProgram >= 5) return 0; // Graduated
        return yearsInProgram + 1; // R1 = year 1, R2 = year 2, etc.
    }
    // Fallback to program_year or year
    return resident.program_year || resident.year || 1;
}

// Helper function to format program year status for display
function formatProgramYearStatus(programYear) {
    if (programYear < 0) {
        return `Starts in ${Math.abs(programYear)} year${Math.abs(programYear) > 1 ? 's' : ''}`;
    } else if (programYear === 0) {
        return 'Graduated';
    } else {
        return `R${programYear}`;
    }
}

let currentBlockId = null;

// Tab switching
function showTab(tabName, clickedElement) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    if (clickedElement) {
        clickedElement.classList.add('active');
    } else {
        // Find the tab button for this tab
        document.querySelectorAll('.tab').forEach(tab => {
            if (tab.textContent.includes(tabName) || tab.onclick && tab.onclick.toString().includes(tabName)) {
                tab.classList.add('active');
            }
        });
    }
    document.getElementById(tabName).classList.add('active');
    
    // Load data for the tab
    if (tabName === 'schedule') {
        loadSchedule();
    } else if (tabName === 'year-view') {
        loadYearView();
    } else if (tabName === 'student-view') {
        loadStudentView();
    } else if (tabName === 'residents') {
        loadResidents();
    } else if (tabName === 'blocks') {
        loadBlocks();
    } else if (tabName === 'config') {
        loadConfig();
    }
}

// Load schedule view
async function loadSchedule() {
    try {
        const [residentsRes, blocksRes, assignmentsRes, configRes] = await Promise.all([
            fetch(`${API_BASE}/residents`).catch(e => { console.error('Error fetching residents:', e); return {ok: false}; }),
            fetch(`${API_BASE}/blocks`).catch(e => { console.error('Error fetching blocks:', e); return {ok: false}; }),
            fetch(`${API_BASE}/assignments`).catch(e => { console.error('Error fetching assignments:', e); return {ok: false}; }),
            fetch(`${API_BASE}/config`).catch(e => { console.error('Error fetching config:', e); return {ok: false}; })
        ]);
        
        if (!residentsRes.ok || !blocksRes.ok || !assignmentsRes.ok || !configRes.ok) {
            throw new Error('Failed to fetch data from server');
        }
        
        const residents = await residentsRes.json();
        const blocks = await blocksRes.json();
        const assignments = await assignmentsRes.json();
        const config = await configRes.json();
        
        // Update stats
        const statsHtml = `
            <div class="stat-card">
                <h4>Total Residents</h4>
                <div class="value">${residents.length}</div>
            </div>
            <div class="stat-card">
                <h4>Total Blocks</h4>
                <div class="value">${blocks.length}</div>
            </div>
            <div class="stat-card">
                <h4>Assigned Blocks</h4>
                <div class="value">${assignments.length}</div>
            </div>
        `;
        document.getElementById('schedule-stats').innerHTML = statsHtml;
        
        // Group blocks by year
        const blocksByYear = {};
        blocks.forEach(block => {
            if (!blocksByYear[block.year]) {
                blocksByYear[block.year] = [];
            }
            blocksByYear[block.year].push(block);
        });
        
        // Create schedule grid
        let gridHtml = '';
        Object.keys(blocksByYear).sort().forEach(year => {
            gridHtml += `<h3 style="grid-column: 1/-1; margin-top: 20px;">Academic Year ${year}</h3>`;
            blocksByYear[year].sort((a, b) => a.block_number - b.block_number).forEach(block => {
                const blockAssignments = assignments.filter(a => a.block_id === block.id);
                const assignedResidents = blockAssignments.map(a => {
                    const r = residents.find(res => res.id === a.resident_id);
                    if (!r) return null;
                    // Calculate program year for this academic year
                    const programYear = getProgramYear(r, block.year);
                    return {id: r.id, name: r.name, programYear: programYear};
                }).filter(r => r !== null && r.programYear > 0 && r.programYear <= 5); // Filter out graduated/not yet in program
                
                const capacity = block.max_capacity || block.capacity || 1;
                const isFull = assignedResidents.length >= capacity;
                
                const rotation = block.rotation || block.site;
                gridHtml += `
                    <div class="schedule-card ${assignedResidents.length > 0 ? 'assigned' : ''}" onclick="showAssignModal('${block.id}')">
                        <strong>Block ${block.block_number}</strong><br>
                        <small style="font-weight: bold; color: #2c3e50;">${rotation}</small><br>
                        <small>${block.site}</small><br>
                        <small style="color: #666;">Capacity: ${assignedResidents.length}/${capacity}</small><br>
                        ${assignedResidents.length > 0 ? 
                            assignedResidents.map(r => 
                                `<div style="margin: 5px 0; padding: 5px; background: #e8f5e9; border-radius: 3px;">
                                    <strong>${r.name}</strong> <small>(${formatProgramYearStatus(r.programYear)})</small>
                                    <button class="btn btn-danger" style="float: right; padding: 2px 8px; font-size: 11px;" 
                                            onclick="event.stopPropagation(); removeResidentFromBlock('${block.id}', '${r.id}')">×</button>
                                </div>`
                            ).join('') : 
                            '<em>Unassigned</em>'
                        }
                        ${!isFull ? '<br><small style="color: #3498db;">Click to add resident</small>' : ''}
                    </div>
                `;
            });
        });
        
        document.getElementById('schedule-grid').innerHTML = gridHtml;
    } catch (error) {
        console.error('Error loading schedule:', error);
        alert('Error loading schedule');
    }
}

// Load residents
async function loadResidents() {
    try {
        const [residentsRes, assignmentsRes] = await Promise.all([
            fetch(`${API_BASE}/residents`),
            fetch(`${API_BASE}/assignments`)
        ]);
        
        const residents = await residentsRes.json();
        const assignments = await assignmentsRes.json();
        
        const currentYear = new Date().getFullYear();
        const tbody = document.querySelector('#residents-table tbody');
        
        // Process all residents and show them all in one list
        const processedResidents = residents.map(resident => {
            const entryYear = resident.entry_year || (currentYear - (resident.program_year || resident.year || 1) + 1);
            const currentProgramYear = getProgramYear(resident, currentYear);
            return {...resident, entryYear, currentProgramYear};
        });
        
        // Sort by entry year (newest first), then by ID
        processedResidents.sort((a, b) => {
            if (a.entryYear !== b.entryYear) return b.entryYear - a.entryYear; // Newest first
            return a.id.localeCompare(b.id);
        });
        
        // Show all residents in one list
        const html = processedResidents.map(resident => {
            const residentAssignments = assignments.filter(a => a.resident_id === resident.id);
            const statusText = formatProgramYearStatus(resident.currentProgramYear);
            
            // Style based on status
            let rowStyle = '';
            if (resident.currentProgramYear === 0) {
                rowStyle = 'background: #f9f9f9; color: #666;'; // Graduated
            } else if (resident.currentProgramYear < 0) {
                rowStyle = 'background: #fff9e6; color: #856404;'; // Not started yet
            }
            
            return `
                <tr style="${rowStyle}">
                    <td>${resident.id}</td>
                    <td>${resident.name}</td>
                    <td>${resident.entryYear}</td>
                    <td>${statusText}</td>
                    <td>${resident.specialty || 'Undecided'}</td>
                    <td>${residentAssignments.length}</td>
                    <td>
                        <button class="btn btn-primary" onclick="showEditResidentModal('${resident.id}')" style="margin-right: 5px;">Edit</button>
                        <button class="btn btn-danger" onclick="deleteResident('${resident.id}')">Delete</button>
                    </td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = html;
    } catch (error) {
        console.error('Error loading residents:', error);
        alert('Error loading residents');
    }
}

// Load blocks
async function loadBlocks() {
    try {
        const yearFilter = document.getElementById('year-filter').value;
        const url = yearFilter ? `${API_BASE}/blocks?year=${yearFilter}` : `${API_BASE}/blocks`;
        
        const [blocksRes, assignmentsRes, residentsRes] = await Promise.all([
            fetch(url),
            fetch(`${API_BASE}/assignments`),
            fetch(`${API_BASE}/residents`)
        ]);
        
        const blocks = await blocksRes.json();
        const assignments = await assignmentsRes.json();
        const residents = await residentsRes.json();
        
        // Update year filter options
        const years = [...new Set(blocks.map(b => b.year))].sort();
        const yearSelect = document.getElementById('year-filter');
        const currentValue = yearSelect.value;
        yearSelect.innerHTML = '<option value="">All Years</option>' + 
            years.map(y => `<option value="${y}">${y}</option>`).join('');
        if (currentValue) yearSelect.value = currentValue;
        
            const tbody = document.querySelector('#blocks-table tbody');
        tbody.innerHTML = blocks.map(block => {
            const blockAssignments = assignments.filter(a => a.block_id === block.id);
            const assignedResidents = blockAssignments.map(a => {
                const r = residents.find(res => res.id === a.resident_id);
                if (!r) return null;
                // Add calculated program year for display
                const programYear = getProgramYear(r, block.year);
                return {...r, displayProgramYear: programYear};
            }).filter(r => r !== null && r.displayProgramYear > 0 && r.displayProgramYear <= 5);
            
            const capacity = block.max_capacity || block.capacity || 1;
            const isFull = assignedResidents.length >= capacity;
            
            const rotation = block.rotation || block.site;
            return `
                <tr>
                    <td>${block.id}</td>
                    <td>${block.block_number}</td>
                    <td>${block.year}</td>
                    <td><strong>${rotation}</strong><br><small>${block.site}</small></td>
                    <td>
                        ${assignedResidents.length > 0 ? 
                            assignedResidents.map(r => 
                                `<div style="margin: 2px 0;">
                                    ${r.name} (${formatProgramYearStatus(r.displayProgramYear || r.program_year || r.year)})
                                    <button class="btn btn-danger" style="padding: 2px 6px; font-size: 11px; margin-left: 5px;" 
                                            onclick="removeResidentFromBlock('${block.id}', '${r.id}')">×</button>
                                </div>`
                            ).join('') : 
                            '<em>Unassigned</em>'
                        }
                        <br><small style="color: #666;">${assignedResidents.length}/${capacity} residents</small>
                    </td>
                    <td>
                        ${!isFull ? `<button class="btn btn-primary" onclick="showAssignModal('${block.id}')">Add Resident</button>` : 
                          '<small style="color: #999;">Full</small>'}
                        ${assignedResidents.length > 0 ? 
                            `<button class="btn btn-danger" onclick="deleteAllAssignments('${block.id}')">Clear All</button>` : ''}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading blocks:', error);
        alert('Error loading blocks');
    }
}

// Load configuration
async function loadConfig() {
    try {
        const [configRes, rotationConstraintsRes, residentsRes] = await Promise.all([
            fetch(`${API_BASE}/config`),
            fetch(`${API_BASE}/rotation-constraints`),
            fetch(`${API_BASE}/residents`)
        ]);
        
        const config = await configRes.json();
        const rotationConstraints = await rotationConstraintsRes.json();
        const residents = await residentsRes.json();
        
        // Load basic program settings
        document.getElementById('blocks-per-year').value = config.program.blocks_per_year;
        document.getElementById('program-years').value = config.program.program_years;
        
        // Load entry year configuration
        loadEntryYearConfig(residents);
        
        // Load rotation constraints
        loadRotationConstraints(rotationConstraints);
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

// Load entry year configuration
function loadEntryYearConfig(residents) {
    const container = document.getElementById('entry-year-config');
    container.innerHTML = '';
    
    // Count residents by entry year
    const residentsByEntryYear = {};
    residents.forEach(r => {
        const entryYear = r.entry_year || new Date().getFullYear();
        residentsByEntryYear[entryYear] = (residentsByEntryYear[entryYear] || 0) + 1;
    });
    
    // Create dropdowns for years 2021-2040
    for (let year = 2021; year <= 2040; year++) {
        const div = document.createElement('div');
        div.style.cssText = 'display: flex; flex-direction: column; gap: 5px;';
        
        const label = document.createElement('label');
        label.textContent = `Entry Year ${year}:`;
        label.style.cssText = 'font-weight: 500; font-size: 14px;';
        
        const input = document.createElement('input');
        input.type = 'number';
        input.min = '0';
        input.max = '20';
        input.value = residentsByEntryYear[year] || 0;
        input.id = `entry-year-${year}`;
        input.style.cssText = 'padding: 8px; border: 1px solid #ddd; border-radius: 4px;';
        
        div.appendChild(label);
        div.appendChild(input);
        container.appendChild(div);
    }
}

// Load rotation constraints
function loadRotationConstraints(rotationConstraints) {
    // Store for saving
    window.currentRotationConstraints = rotationConstraints;
    
    const tbody = document.getElementById('rotation-constraints-tbody');
    tbody.innerHTML = '';
    
    const rotations = rotationConstraints.rotations || {};
    const rotationNames = Object.keys(rotations).sort();
    
    rotationNames.forEach(rotationName => {
        const rotation = rotations[rotationName];
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: 500;">${rotationName}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">${rotation.site || 'Unknown'}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                <input type="number" id="min-${rotationName}" min="1" max="20" value="${rotation.min_residents_per_block || 1}" 
                       style="width: 80px; padding: 5px; text-align: center; border: 1px solid #ddd; border-radius: 4px;">
            </td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                <input type="number" id="max-${rotationName}" min="1" max="20" value="${rotation.max_residents_per_block || 1}" 
                       style="width: 80px; padding: 5px; text-align: center; border: 1px solid #ddd; border-radius: 4px;">
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Save configuration
async function saveConfig() {
    try {
        // Save basic program settings
        const config = {
            program: {
                blocks_per_year: parseInt(document.getElementById('blocks-per-year').value),
                program_years: parseInt(document.getElementById('program-years').value)
            }
        };
        
        const configRes = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (!configRes.ok) {
            throw new Error('Failed to save program configuration');
        }
        
        // Save entry year configuration
        const entryYearConfig = {};
        for (let year = 2021; year <= 2040; year++) {
            const input = document.getElementById(`entry-year-${year}`);
            if (input) {
                const count = parseInt(input.value) || 0;
                if (count > 0) {
                    entryYearConfig[year] = count;
                }
            }
        }
        
        const entryYearRes = await fetch(`${API_BASE}/entry-year-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(entryYearConfig)
        });
        
        if (!entryYearRes.ok) {
            throw new Error('Failed to save entry year configuration');
        }
        
        // Save rotation constraints
        const rotationConstraints = { rotations: {} };
        const rotationNames = Object.keys(window.currentRotationConstraints?.rotations || {});
        
        rotationNames.forEach(rotationName => {
            const minInput = document.getElementById(`min-${rotationName}`);
            const maxInput = document.getElementById(`max-${rotationName}`);
            
            if (minInput && maxInput) {
                rotationConstraints.rotations[rotationName] = {
                    ...window.currentRotationConstraints.rotations[rotationName],
                    min_residents_per_block: parseInt(minInput.value) || 1,
                    max_residents_per_block: parseInt(maxInput.value) || 1
                };
            }
        });
        
        // Preserve other rotation constraint data
        if (window.currentRotationConstraints) {
            rotationConstraints.site_minimums = window.currentRotationConstraints.site_minimums;
            rotationConstraints.global_constraints = window.currentRotationConstraints.global_constraints;
            rotationConstraints.period_constraints = window.currentRotationConstraints.period_constraints;
        }
        
        const rotationRes = await fetch(`${API_BASE}/rotation-constraints`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rotationConstraints)
        });
        
        if (!rotationRes.ok) {
            throw new Error('Failed to save rotation constraints');
        }
        
        alert('Configuration saved! Please refresh the page to see changes.');
        location.reload();
    } catch (error) {
        console.error('Error saving config:', error);
        alert('Error saving configuration: ' + error.message);
    }
}

// Load year view
async function loadYearView() {
    try {
        const yearSelect = document.getElementById('year-view-select');
        const selectedYear = parseInt(yearSelect.value);
        
        // Always populate year dropdown (in case it's empty or needs refresh)
        const [yearViewBlocksRes] = await Promise.all([
            fetch(`${API_BASE}/blocks`)
        ]);
        const allYearBlocks = await yearViewBlocksRes.json();
        const years = [...new Set(allYearBlocks.map(b => b.year))].sort();
        
        const currentValue = yearSelect.value;
        yearSelect.innerHTML = '<option value="">Select a year...</option>';
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year.toString() === currentValue) {
                option.selected = true;
            }
            yearSelect.appendChild(option);
        });
        
        if (!selectedYear) {
            document.getElementById('year-view-table-container').innerHTML = 
                '<p style="color: #666; text-align: center; padding: 40px;">Please select a year to view the schedule</p>';
            document.getElementById('download-pdf-btn').style.display = 'none';
            return;
        }
        
        // Fetch data for selected year
        const [yearBlocksRes, assignmentsRes, residentsRes] = await Promise.all([
            fetch(`${API_BASE}/blocks`),
            fetch(`${API_BASE}/assignments`),
            fetch(`${API_BASE}/residents`)
        ]);
        
        const allBlocks = await yearBlocksRes.json();
        const allAssignments = await assignmentsRes.json();
        const allResidents = await residentsRes.json();
        
        // Filter for selected year
        const yearBlocks = allBlocks.filter(b => b.year === selectedYear);
        const yearAssignments = allAssignments.filter(a => a.year === selectedYear);
        
        // Get active residents for this year
        const activeResidents = allResidents.filter(r => {
            const programYear = getProgramYear(r, selectedYear);
            return programYear > 0 && programYear <= 5;
        }).sort((a, b) => {
            // Sort by name
            return (a.name || a.id).localeCompare(b.name || b.id);
        });
        
        // Create a map: (resident_id, block_number) -> rotation
        const residentBlockMap = {};
        yearAssignments.forEach(assignment => {
            const block = yearBlocks.find(b => b.id === assignment.block_id);
            if (block) {
                const key = `${assignment.resident_id}-${block.block_number}`;
                residentBlockMap[key] = assignment.rotation || block.rotation || block.site;
            }
        });
        
        // Create table
        let tableHTML = '<table id="year-view-table"><thead><tr><th>Resident</th>';
        
        // Add column headers for blocks 1-13
        for (let blockNum = 1; blockNum <= 13; blockNum++) {
            tableHTML += `<th>Block ${blockNum}</th>`;
        }
        tableHTML += '</tr></thead><tbody>';
        
        // Add rows for each resident
        activeResidents.forEach(resident => {
            const programYear = getProgramYear(resident, selectedYear);
            const residentLabel = `${resident.name || resident.id} (R${programYear})`;
            tableHTML += `<tr><td>${residentLabel}</td>`;
            
            // Add cells for each block
            for (let blockNum = 1; blockNum <= 13; blockNum++) {
                const key = `${resident.id}-${blockNum}`;
                const rotation = residentBlockMap[key];
                
                if (rotation) {
                    tableHTML += `<td><div class="year-view-resident">${rotation}</div></td>`;
                } else {
                    tableHTML += `<td><div class="year-view-empty">-</div></td>`;
                }
            }
            
            tableHTML += '</tr>';
        });
        
        tableHTML += '</tbody></table>';
        
        document.getElementById('year-view-table-container').innerHTML = tableHTML;
        
        // Show download button
        document.getElementById('download-pdf-btn').style.display = 'inline-block';
        
    } catch (error) {
        console.error('Error loading year view:', error);
        document.getElementById('year-view-table-container').innerHTML = 
            '<p style="color: red; text-align: center; padding: 40px;">Error loading year view</p>';
        document.getElementById('download-pdf-btn').style.display = 'none';
    }
}

// Download Year View as PDF
function downloadYearViewPDF() {
    try {
        const yearSelect = document.getElementById('year-view-select');
        const selectedYear = yearSelect.value;
        const table = document.getElementById('year-view-table');
        
        if (!table || !selectedYear) {
            alert('Please select a year and load the schedule first');
            return;
        }
        
        // Check if jsPDF is available
        if (typeof window.jspdf === 'undefined') {
            alert('PDF library not loaded. Please refresh the page.');
            return;
        }
        
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('landscape', 'pt', 'a4');
        
        // Add title
        doc.setFontSize(18);
        doc.text(`Resident Schedule - Year ${selectedYear}`, 40, 30);
        
        // Prepare table data
        const tableData = [];
        const headers = ['Resident'];
        
        // Get headers (Block 1-13)
        for (let i = 1; i <= 13; i++) {
            headers.push(`Block ${i}`);
        }
        
        // Get table rows
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const rowData = [];
            
            cells.forEach((cell, index) => {
                if (index === 0) {
                    // Resident name (first column)
                    rowData.push(cell.textContent.trim());
                } else {
                    // Rotation name or "-"
                    const rotationDiv = cell.querySelector('.year-view-resident');
                    const emptyDiv = cell.querySelector('.year-view-empty');
                    if (rotationDiv) {
                        rowData.push(rotationDiv.textContent.trim());
                    } else if (emptyDiv) {
                        rowData.push('-');
                    } else {
                        rowData.push(cell.textContent.trim() || '-');
                    }
                }
            });
            
            tableData.push(rowData);
        });
        
        // Generate PDF table
        doc.autoTable({
            head: [headers],
            body: tableData,
            startY: 50,
            styles: {
                fontSize: 8,
                cellPadding: 3,
                overflow: 'linebreak',
                cellWidth: 'wrap'
            },
            headStyles: {
                fillColor: [52, 152, 219],
                textColor: 255,
                fontStyle: 'bold'
            },
            alternateRowStyles: {
                fillColor: [249, 249, 249]
            },
            margin: { left: 40, right: 40 },
            tableWidth: 'auto'
        });
        
        // Save PDF
        doc.save(`Resident_Schedule_${selectedYear}.pdf`);
        
    } catch (error) {
        console.error('Error generating PDF:', error);
        alert('Error generating PDF. Please try again.');
    }
}

// Load student view
async function loadStudentView() {
    try {
        const studentSelect = document.getElementById('student-select');
        const yearFilter = document.getElementById('student-year-filter');
        const selectedStudentId = studentSelect.value;
        const selectedYearFilter = yearFilter.value;
        
        // Fetch all residents
        const residentsRes = await fetch(`${API_BASE}/residents`);
        const allResidents = await residentsRes.json();
        
        // Populate student dropdown if empty
        if (studentSelect.options.length <= 1) {
            // Filter to show active residents (or all if needed)
            const activeResidents = allResidents.filter(r => {
                const currentYear = new Date().getFullYear();
                const programYear = getProgramYear(r, currentYear);
                return programYear > 0 && programYear <= 5;
            }).sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id));
            
            studentSelect.innerHTML = '<option value="">Select a student...</option>';
            activeResidents.forEach(resident => {
                const option = document.createElement('option');
                option.value = resident.id;
                const currentYear = new Date().getFullYear();
                const programYear = getProgramYear(resident, currentYear);
                option.textContent = `${resident.name || resident.id} (R${programYear})`;
                studentSelect.appendChild(option);
            });
        }
        
        if (!selectedStudentId) {
            document.getElementById('student-view-table-container').innerHTML = 
                '<p style="color: #666; text-align: center; padding: 40px;">Please select a student to view their schedule</p>';
            document.getElementById('download-student-pdf-btn').style.display = 'none';
            return;
        }
        
        // Find selected student
        const selectedStudent = allResidents.find(r => r.id === selectedStudentId);
        if (!selectedStudent) {
            document.getElementById('student-view-table-container').innerHTML = 
                '<p style="color: red; text-align: center; padding: 40px;">Student not found</p>';
            return;
        }
        
        // Fetch blocks and assignments
        const [blocksRes, assignmentsRes] = await Promise.all([
            fetch(`${API_BASE}/blocks`),
            fetch(`${API_BASE}/assignments`)
        ]);
        
        const allBlocks = await blocksRes.json();
        const allAssignments = await assignmentsRes.json();
        
        // Filter assignments for this student
        const studentAssignments = allAssignments.filter(a => a.resident_id === selectedStudentId);
        
        // Get all years this student was active
        const studentYears = new Set();
        studentAssignments.forEach(assignment => {
            studentYears.add(assignment.year);
        });
        
        // Filter by program year if specified
        let filteredYears = Array.from(studentYears).sort();
        if (selectedYearFilter !== 'all') {
            const targetProgramYear = parseInt(selectedYearFilter);
            filteredYears = filteredYears.filter(year => {
                const programYear = getProgramYear(selectedStudent, year);
                return programYear === targetProgramYear;
            });
        }
        
        if (filteredYears.length === 0) {
            document.getElementById('student-view-table-container').innerHTML = 
                '<p style="color: #666; text-align: center; padding: 40px;">No schedule found for the selected filters</p>';
            document.getElementById('download-student-pdf-btn').style.display = 'none';
            return;
        }
        
        // Create table
        let tableHTML = '<table id="student-view-table"><thead><tr><th>Year</th>';
        
        // Add column headers for blocks 1-13
        for (let blockNum = 1; blockNum <= 13; blockNum++) {
            tableHTML += `<th>Block ${blockNum}</th>`;
        }
        tableHTML += '</tr></thead><tbody>';
        
        // Add rows for each year
        filteredYears.forEach(year => {
            const programYear = getProgramYear(selectedStudent, year);
            tableHTML += `<tr><td><strong>${year} (R${programYear})</strong></td>`;
            
            // Get assignments for this year
            const yearAssignments = studentAssignments.filter(a => a.year === year);
            const yearBlocks = allBlocks.filter(b => b.year === year);
            
            // Create map: block_number -> rotation
            const blockRotationMap = {};
            yearAssignments.forEach(assignment => {
                const block = yearBlocks.find(b => b.id === assignment.block_id);
                if (block) {
                    blockRotationMap[block.block_number] = assignment.rotation || block.rotation || block.site;
                }
            });
            
            // Add cells for each block
            for (let blockNum = 1; blockNum <= 13; blockNum++) {
                const rotation = blockRotationMap[blockNum];
                if (rotation) {
                    tableHTML += `<td><div class="year-view-resident">${rotation}</div></td>`;
                } else {
                    tableHTML += `<td><div class="year-view-empty">-</div></td>`;
                }
            }
            
            tableHTML += '</tr>';
        });
        
        tableHTML += '</tbody></table>';
        
        document.getElementById('student-view-table-container').innerHTML = tableHTML;
        
        // Show download button
        document.getElementById('download-student-pdf-btn').style.display = 'inline-block';
        
    } catch (error) {
        console.error('Error loading student view:', error);
        document.getElementById('student-view-table-container').innerHTML = 
            '<p style="color: red; text-align: center; padding: 40px;">Error loading student schedule</p>';
        document.getElementById('download-student-pdf-btn').style.display = 'none';
    }
}

// Download Student View as PDF
function downloadStudentViewPDF() {
    try {
        const studentSelect = document.getElementById('student-select');
        const yearFilter = document.getElementById('student-year-filter');
        const selectedStudentId = studentSelect.value;
        const selectedYearFilter = yearFilter.value;
        const table = document.getElementById('student-view-table');
        
        if (!table || !selectedStudentId) {
            alert('Please select a student and load the schedule first');
            return;
        }
        
        // Check if jsPDF is available
        if (typeof window.jspdf === 'undefined') {
            alert('PDF library not loaded. Please refresh the page.');
            return;
        }
        
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('landscape', 'pt', 'a4');
        
        // Get student name
        const studentOption = studentSelect.options[studentSelect.selectedIndex];
        const studentName = studentOption.textContent.split(' (')[0];
        const yearFilterText = selectedYearFilter === 'all' ? 'All Years' : `R${selectedYearFilter}`;
        
        // Add title
        doc.setFontSize(18);
        doc.text(`Student Schedule - ${studentName} (${yearFilterText})`, 40, 30);
        
        // Prepare table data
        const tableData = [];
        const headers = ['Year'];
        
        // Get headers (Block 1-13)
        for (let i = 1; i <= 13; i++) {
            headers.push(`Block ${i}`);
        }
        
        // Get table rows
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const rowData = [];
            
            cells.forEach((cell, index) => {
                if (index === 0) {
                    // Year (first column)
                    rowData.push(cell.textContent.trim());
                } else {
                    // Rotation name or "-"
                    const rotationDiv = cell.querySelector('.year-view-resident');
                    const emptyDiv = cell.querySelector('.year-view-empty');
                    if (rotationDiv) {
                        rowData.push(rotationDiv.textContent.trim());
                    } else if (emptyDiv) {
                        rowData.push('-');
                    } else {
                        rowData.push(cell.textContent.trim() || '-');
                    }
                }
            });
            
            tableData.push(rowData);
        });
        
        // Generate PDF table
        doc.autoTable({
            head: [headers],
            body: tableData,
            startY: 50,
            styles: {
                fontSize: 8,
                cellPadding: 3,
                overflow: 'linebreak',
                cellWidth: 'wrap'
            },
            headStyles: {
                fillColor: [52, 152, 219],
                textColor: 255,
                fontStyle: 'bold'
            },
            alternateRowStyles: {
                fillColor: [249, 249, 249]
            },
            margin: { left: 40, right: 40 },
            tableWidth: 'auto'
        });
        
        // Save PDF
        const fileName = `${studentName.replace(/\s+/g, '_')}_Schedule_${yearFilterText.replace(/\s+/g, '_')}.pdf`;
        doc.save(fileName);
        
    } catch (error) {
        console.error('Error generating PDF:', error);
        alert('Error generating PDF. Please try again.');
    }
}

// Add resident
function showAddResidentModal() {
    // Populate entry year dropdown
    const currentYear = new Date().getFullYear();
    const yearSelect = document.getElementById('resident-entry-year');
    yearSelect.innerHTML = '';
    // Show years from 5 years ago to 5 years in the future
    for (let year = currentYear - 4; year <= currentYear + 5; year++) {
        const option = document.createElement('option');
        option.value = year;
        const programYearInCurrentYear = currentYear - year + 1;
        let statusText = '';
        if (programYearInCurrentYear < 1) {
            statusText = `(Starts in ${year - currentYear} year${year - currentYear > 1 ? 's' : ''})`;
        } else if (programYearInCurrentYear > 5) {
            statusText = '(Graduated)';
        } else {
            statusText = `(R${programYearInCurrentYear} in ${currentYear})`;
        }
        option.textContent = `${year} ${statusText}`;
        if (year === currentYear) option.selected = true;
        yearSelect.appendChild(option);
    }
    document.getElementById('add-resident-modal').style.display = 'block';
}

async function addResident() {
    try {
        const name = document.getElementById('resident-name').value;
        const entryYear = parseInt(document.getElementById('resident-entry-year').value);
        const currentYear = new Date().getFullYear();
        
        if (!name) {
            alert('Please enter a name');
            return;
        }
        
        // Calculate program year based on entry year
        const programYear = currentYear - entryYear + 1;
        
        const specialty = document.getElementById('resident-specialty').value || 'Undecided';
        
        const res = await fetch(`${API_BASE}/residents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name, 
                program_year: programYear,
                entry_year: entryYear,
                specialty: specialty
            })
        });
        
        if (res.ok) {
            closeModal('add-resident-modal');
            document.getElementById('resident-name').value = '';
            loadResidents();
            loadSchedule();
        } else {
            alert('Error adding resident');
        }
    } catch (error) {
        console.error('Error adding resident:', error);
        alert('Error adding resident');
    }
}

// Edit resident
async function showEditResidentModal(residentId) {
    try {
        const res = await fetch(`${API_BASE}/residents`);
        const residents = await res.json();
        const resident = residents.find(r => r.id === residentId);
        
        if (!resident) {
            alert('Resident not found');
            return;
        }
        
        document.getElementById('edit-resident-id').value = residentId;
        document.getElementById('edit-resident-name').value = resident.name || '';
        
        // Set specialty
        document.getElementById('edit-resident-specialty').value = resident.specialty || 'Undecided';
        
        // Populate entry year dropdown
        const currentYear = new Date().getFullYear();
        const yearSelect = document.getElementById('edit-resident-entry-year');
        yearSelect.innerHTML = '';
        const entryYear = resident.entry_year || (currentYear - (resident.program_year || 1) + 1);
        
        for (let year = currentYear - 4; year <= currentYear + 2; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `${year} (R${currentYear - year + 1} in ${currentYear})`;
            if (year === entryYear) option.selected = true;
            yearSelect.appendChild(option);
        }
        
        document.getElementById('edit-resident-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading resident:', error);
        alert('Error loading resident');
    }
}

async function saveResidentEdit() {
    try {
        const residentId = document.getElementById('edit-resident-id').value;
        const name = document.getElementById('edit-resident-name').value;
        const entryYear = parseInt(document.getElementById('edit-resident-entry-year').value);
        const currentYear = new Date().getFullYear();
        
        if (!name) {
            alert('Please enter a name');
            return;
        }
        
        // Calculate program year based on entry year
        const programYear = currentYear - entryYear + 1;
        
        const specialty = document.getElementById('edit-resident-specialty').value || 'Undecided';
        
        const res = await fetch(`${API_BASE}/residents/${residentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name,
                program_year: programYear,
                entry_year: entryYear,
                specialty: specialty
            })
        });
        
        if (res.ok) {
            closeModal('edit-resident-modal');
            loadResidents();
            loadSchedule();
        } else {
            alert('Error updating resident');
        }
    } catch (error) {
        console.error('Error updating resident:', error);
        alert('Error updating resident');
    }
}

// Delete resident
async function deleteResident(id) {
    if (!confirm('Are you sure you want to delete this resident?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/residents/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadResidents();
            loadSchedule();
        } else {
            alert('Error deleting resident');
        }
    } catch (error) {
        console.error('Error deleting resident:', error);
        alert('Error deleting resident');
    }
}

// Show assign block modal
async function showAssignModal(blockId) {
    currentBlockId = blockId;
    
    try {
        const [residentsRes, blocksRes] = await Promise.all([
            fetch(`${API_BASE}/residents`),
            fetch(`${API_BASE}/blocks`)
        ]);
        
        const residents = await residentsRes.json();
        const allBlocks = await blocksRes.json();
        const currentBlock = allBlocks.find(b => b.id === blockId);
        const academicYear = currentBlock ? currentBlock.year : new Date().getFullYear();
        
        const residentSelect = document.getElementById('assign-resident');
        
        residentSelect.innerHTML = residents
            .map(r => {
                const programYear = getProgramYear(r, academicYear);
                if (programYear <= 0 || programYear > 5) return null; // Skip graduated/not yet in program
                return `<option value="${r.id}">${r.name} (${formatProgramYearStatus(programYear)})</option>`;
            })
            .filter(opt => opt !== null)
            .join('');
        
        document.getElementById('assign-block-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading data for assignment:', error);
    }
}

// Save assignment
async function saveAssignment() {
    try {
        const residentId = document.getElementById('assign-resident').value;
        const blockId = currentBlockId;
        
        // Get block details
        const blockDetailsRes = await fetch(`${API_BASE}/blocks`);
        const allBlocks = await blockDetailsRes.json();
        const block = allBlocks.find(b => b.id === blockId);
        
        const res = await fetch(`${API_BASE}/assignments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resident_id: residentId,
                block_id: blockId,
                rotation: block.rotation || block.site,
                site: block.site,
                block_number: block.block_number,
                year: block.year
            })
        });
        
        if (res.ok) {
            closeModal('assign-block-modal');
            loadSchedule();
            loadBlocks();
        } else {
            const error = await res.json();
            alert('Error assigning block: ' + (error.error || 'Block may be at capacity'));
        }
    } catch (error) {
        console.error('Error saving assignment:', error);
        alert('Error saving assignment');
    }
}

// Remove a specific resident from a block
async function removeResidentFromBlock(blockId, residentId) {
    if (!confirm('Are you sure you want to remove this resident from the block?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/assignments/${blockId}?resident_id=${residentId}`, { method: 'DELETE' });
        if (res.ok) {
            loadSchedule();
            loadBlocks();
        } else {
            alert('Error removing assignment');
        }
    } catch (error) {
        console.error('Error deleting assignment:', error);
        alert('Error removing assignment');
    }
}

// Delete all assignments from a block
async function deleteAllAssignments(blockId) {
    if (!confirm('Are you sure you want to remove all residents from this block?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/assignments/${blockId}`, { method: 'DELETE' });
        if (res.ok) {
            loadSchedule();
            loadBlocks();
        } else {
            alert('Error removing assignments');
        }
    } catch (error) {
        console.error('Error deleting assignments:', error);
        alert('Error removing assignments');
    }
}

// Optimize schedule
async function optimizeSchedule() {
    if (!confirm('This will generate a new optimized schedule. Existing assignments may be overwritten. Continue?')) {
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await res.json();
        
        if (res.ok && data.status === 'success') {
            alert(`Schedule optimized! Generated ${data.assignments.length} assignments.`);
            loadSchedule();
            loadBlocks();
        } else {
            const errorMsg = data.message || data.error || 'Unknown error';
            console.error('Optimization error:', data);
            alert('Error optimizing schedule: ' + errorMsg);
        }
    } catch (error) {
        console.error('Error optimizing schedule:', error);
        alert('Error optimizing schedule: ' + error.message);
    }
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    try {
        loadSchedule();
    } catch (error) {
        console.error('Error initializing:', error);
        alert('Error loading schedule. Please check the browser console for details.');
    }
});

