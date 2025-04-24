document.addEventListener('DOMContentLoaded', function() {
    // Configuration - uses the variables defined in your HTML script tag
    // Make sure these are defined in your HTML before this script runs
    
    // Parse start and end dates from the event
    const startingDate = new Date(startDate || '{{ event.start_date }}');
    const endingDate = new Date(endDate || '{{ event.end_date }}');
    
    // Parse event hours (from HH:MM:SS format)
    const startTimeParts = (startTime || '{{ event.start_time }}').split(':');
    const endTimeParts = (endTime || '{{ event.end_time }}').split(':');
    const startHour = parseInt(startTimeParts[0], 10);
    const startMinute = parseInt(startTimeParts[1], 10);
    const endHour = parseInt(endTimeParts[0], 10);
    const endMinute = parseInt(endTimeParts[1], 10);
    
    let saveTimeout = null;
  
    // Initialize Socket.IO connection
    const socket = io();
  
    // Generate dates between start and end dates (inclusive)
    const dates = [];
    let currentDate = new Date(startingDate);
    while (currentDate <= endingDate) {
        dates.push(new Date(currentDate));
        currentDate.setDate(currentDate.getDate() + 1);
    }
    
    // Format date for display
    function formatDate(date) {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${days[date.getDay()]} ${months[date.getMonth()]} ${date.getDate()}`;
    }
    
    // Format date for database (YYYY-MM-DD)
    function formatDateForDB(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Generate time slots for 30-minute intervals between start and end times
    const timeSlots = [];
    for (let hour = startHour; hour <= endHour; hour++) {
        for (let minute = 0; minute < 60; minute += 30) {
            // Skip times outside the range
            if (hour === endHour && minute >= endMinute) continue;
            if (hour === startHour && minute < startMinute) continue;
            
            const formattedHour = hour % 12 === 0 ? 12 : hour % 12;
            const period = hour < 12 ? 'AM' : 'PM';
            const formattedMinute = minute === 0 ? '00' : minute;
            timeSlots.push({
                display: `${formattedHour}:${formattedMinute} ${period}`,
                value: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00`
            });
        }
    }
    
    // State management
    let currentMode = 'Available';
    let isMouseDown = false;
    let lastTouchedCell = null;
    let statusTimeout = null;
    let availabilityData = [];
    
    // Generate grid
    const grid = document.getElementById('availabilityGrid');
    const statusMessage = document.getElementById('statusMessage');
    
    grid.innerHTML = '';
    grid.style.display = 'grid';
    grid.style.gridTemplateColumns = `auto repeat(${dates.length}, 1fr)`; // time column + date columns
    grid.style.gridTemplateRows = `auto repeat(${timeSlots.length}, auto)`;
      
    // First row: one empty + date headers
    grid.appendChild(createHeaderCell('Time'));
    dates.forEach(date => {
        grid.appendChild(createHeaderCell(formatDate(date)));
    });
   
    // For each time slot (each row)
    timeSlots.forEach(slot => {
        // Add time label in first column
        grid.appendChild(createTimeLabel(slot.display));
    
        // Then one cell for each date in this row
        dates.forEach(date => {
            const cell = document.createElement('div');
            cell.className = 'grid-cell Unavailable';
            cell.dataset.date = formatDateForDB(date);
            cell.dataset.time = slot.value;
            cell.dataset.status = 'Unavailable';
            grid.appendChild(cell);
        });
    });
  
    // Helper functions
    function createHeaderCell(text) {
        const cell = document.createElement('div');
        cell.className = 'header-cell';
        cell.textContent = text;
        return cell;
    }
    
    function createTimeLabel(text) {
        const cell = document.createElement('div');
        cell.className = 'time-label';
        cell.textContent = text;
        return cell;
    }
    
    function updateAvailability(cell, status) {
        const date = cell.dataset.date;
        const time = cell.dataset.time;
        
        // Update cell visually for the current user
        cell.dataset.userStatus = status;
        
        // Also update the CSS class to change the appearance
        cell.classList.remove('Available', 'Available-2', 'Available-3', 
            'Maybe', 'Maybe-2', 'Maybe-3',
            'Unavailable', 'Unavailable-2', 'Unavailable-3');
        cell.classList.add(status);
        
        // Track changes for saving later
        const existingIndex = availabilityData.findIndex(item => 
            item.date === date && item.time === time);
            
        if (existingIndex >= 0) {
            availabilityData[existingIndex].status = status;
        } else {
            availabilityData.push({
                date: date,
                time: time,
                status: status
            });
        }
    
        saveAllAvailability();
    }
    
    function saveAllAvailability() {
        // Send all availability data to the server at once
        const validAvailability = availabilityData.filter(item => {
          return /^([01]\d|2[0-3]):[0-5]\d:00$/.test(item.time);
        });
        
        // Clear existing timeout to prevent multiple rapid saves
        if (saveTimeout) {
            clearTimeout(saveTimeout);
        }
        
        saveTimeout = setTimeout(() => {
            fetch('/update_availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event_id: eventId,
                    availability: validAvailability
                })
            })
            .then(response => {
                if (!response.ok) {
                  return response.text().then(text => {
                    console.error("Server returned error response:", text);
                    throw new Error('Network response was not ok');
                });
                }
                return response.json();
            })
            .then(data => {
                showStatusMessage();
                console.log('Availability saved successfully:', data);
                
                // Emit an event via Socket.IO to notify other users
                socket.emit('availability_updated', {
                    event_id: eventId
                });
                
                // Update the heatmap to reflect your changes immediately
                loadGroupAvailability();
                calculateBestTimeToMeet();
            })
            .catch(error => {
                console.error('Error saving availability:', error);
                alert('Failed to save availability. Please try again.');
            });
        }, 300); // Small delay to prevent too many requests
    }
    
    function showStatusMessage() {
        // Clear existing timeout
        if (statusTimeout) {
            clearTimeout(statusTimeout);
        }
        
        // Show message
        statusMessage.classList.add('show');
        
        // Hide after 2 seconds
        statusTimeout = setTimeout(() => {
            statusMessage.classList.remove('show');
        }, 2000);
    }
    
    function loadSavedAvailability() {
      fetch(`/get_availability?event_id=${eventId}`)
          .then(response => response.json())
          .then(data => {
              availabilityData = data;
  
              const cells = document.querySelectorAll('.grid-cell');
              cells.forEach(cell => {
                  const date = cell.dataset.date;
                  const time = cell.dataset.time;
  
                  const found = data.find(item => item.date === date && item.time === time);
  
                  if (found) {
                      cell.dataset.userStatus = found.status;
                  }
              });
              
              // After loading personal availability, load the group data
              loadGroupAvailability();
          })
          .catch(error => {
              console.error('Error loading availability:', error);
          });
    }
  
    function timeToSeconds(timeString) {
        const [hours, minutes, seconds] = timeString.split(':').map(Number);
        return hours * 3600 + minutes * 60 + (seconds || 0);
    }
  
    function updateHeatmapCell(cell, availableCount, maybeCount, unavailableCount) {
        // Store the user's own status
        const userStatus = cell.dataset.userStatus || 'Unavailable';
        
        // Remove all status classes first
        cell.classList.remove('Available', 'Available-2', 'Available-3', 
                             'Maybe', 'Maybe-2', 'Maybe-3',
                             'Unavailable', 'Unavailable-2', 'Unavailable-3');
        
        // Apply the appropriate heatmap class based on counts
        if (availableCount > 0) {
            if (availableCount >= 3) {
                cell.classList.add('Available-3');
            } else if (availableCount === 2) {
                cell.classList.add('Available-2');
            } else {
                cell.classList.add('Available');
            }
        } else if (maybeCount > 0) {
            if (maybeCount >= 3) {
                cell.classList.add('Maybe-3');
            } else if (maybeCount === 2) {
                cell.classList.add('Maybe-2');
            } else {
                cell.classList.add('Maybe');
            }
        } else if (unavailableCount > 0) {
            if (unavailableCount >= 3) {
                cell.classList.add('Unavailable-3');
            } else if (unavailableCount === 2) {
                cell.classList.add('Unavailable-2');
            } else {
                cell.classList.add('Unavailable');
            }
        }
        
        // Make sure user's own status is visually represented
        cell.dataset.userStatus = userStatus;
    }
  
    function loadGroupAvailability() {
        fetch(`/get_group_availability?event_id=${eventId}`)
            .then(response => response.json())
            .then(data => {
                const cells = document.querySelectorAll('.grid-cell');
                cells.forEach(cell => {
                    const date = cell.dataset.date;
                    const time = cell.dataset.time;
                    const timeInSeconds = timeToSeconds(time);
  
                    const match = data.find(item => item.date === date && Number(item.time) === timeInSeconds);
                    
                    if (match) {
                        updateHeatmapCell(
                            cell, 
                            match.available_count || 0, 
                            match.maybe_count || 0, 
                            match.unavailable_count || 0
                        );
                    }
                });
                calculateBestTimeToMeet();
            })
            .catch(err => {
                console.error("Failed to load group availability:", err);
            });
    }
  
    // Event listeners for mode selection
    const modeBtns = document.querySelectorAll('.mode-btn');
    modeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove selected class from all buttons
            modeBtns.forEach(b => b.classList.remove('selected'));
            
            // Add selected class to clicked button
            this.classList.add('selected');
            
            // Update current mode
            currentMode = this.dataset.mode;
        });
    });
    
    // Event listeners for grid cells - mouse events
    grid.addEventListener('mousedown', function(e) {
        if (!e.target.classList.contains('grid-cell')) return;
        
        isMouseDown = true;
        const cell = e.target;
        updateAvailability(cell, currentMode);
        lastTouchedCell = cell;
        
        // Prevent text selection while dragging
        e.preventDefault();
    });
    
    grid.addEventListener('mouseover', function(e) {
        if (!isMouseDown || !e.target.classList.contains('grid-cell')) return;
        
        const cell = e.target;
        if (cell !== lastTouchedCell) {
            updateAvailability(cell, currentMode);
            lastTouchedCell = cell;
        }
    });
    
    // Handle mouse up anywhere on the document
    document.addEventListener('mouseup', function() {
        isMouseDown = false;
        lastTouchedCell = null;
    });
    
    // Touch events for mobile devices
    grid.addEventListener('touchstart', function(e) {
        if (!e.target.classList.contains('grid-cell')) return;
        
        isMouseDown = true;
        const cell = e.target;
        updateAvailability(cell, currentMode);
        lastTouchedCell = cell;
        
        // Prevent scrolling while dragging
        e.preventDefault();
    });
    
    grid.addEventListener('touchmove', function(e) {
        if (!isMouseDown) return;
        
        // Get the element at touch position
        const touch = e.touches[0];
        const cell = document.elementFromPoint(touch.clientX, touch.clientY);
        
        if (cell && cell.classList.contains('grid-cell') && cell !== lastTouchedCell) {
            updateAvailability(cell, currentMode);
            lastTouchedCell = cell;
        }
        
        // Prevent scrolling
        e.preventDefault();
    });
    
    grid.addEventListener('touchend', function() {
        isMouseDown = false;
        lastTouchedCell = null;
    });
  
    // Socket.IO event listener for real-time updates
    socket.on('availability_updated', function(data) {
        // Only update if it's for our current event
        if (data.event_id === eventId) {
            loadGroupAvailability();
        }
    });
    
    // Load saved availability on page load
    loadSavedAvailability();

    // Add this function to your event.js file
function calculateBestTimeToMeet() {
    fetch(`/get_group_availability?event_id=${eventId}`)
        .then(response => response.json())
        .then(data => {
            // Get the container element
            const bestTimeContainer = document.getElementById('bestTimeToMeet');
            
            // Check if any availability data exists
            if (data.length === 0) {
                bestTimeContainer.innerHTML = "<p>No availability submitted yet.</p>";
                return;
            }
            
            // Group data by time slot
            const timeSlotData = {};
            
            data.forEach(item => {
                const key = `${item.date}-${item.time}`;
                timeSlotData[key] = {
                    date: item.date,
                    time: Number(item.time),
                    available: item.available_count || 0,
                    maybe: item.maybe_count || 0,
                    unavailable: item.unavailable_count || 0
                };
            });
            
            // Find the best time slot according to the rules
            let bestSlot = null;
            let maxAvailable = -1;
            let minUnavailable = Infinity;
            
            Object.values(timeSlotData).forEach(slot => {
                // Rule 1: Highest number of "Available" users
                if (slot.available > maxAvailable) {
                    maxAvailable = slot.available;
                    minUnavailable = slot.unavailable;
                    bestSlot = slot;
                } 
                // If tied for available count, use Rule 2: Fewest "Unavailable" users
                else if (slot.available === maxAvailable && slot.unavailable < minUnavailable) {
                    minUnavailable = slot.unavailable;
                    bestSlot = slot;
                }
                // If still tied, use Rule 3: Earlier time slot (already handled by the ordering)
                else if (slot.available === maxAvailable && slot.unavailable === minUnavailable) {
                    // Compare dates and times to find the earlier slot
                    const currentDate = new Date(`${slot.date}T${secondsToTimeString(slot.time)}Z`); // Add Z to enforce UTC
                    const bestDate = new Date(`${bestSlot.date}T${secondsToTimeString(bestSlot.time)}Z`); 
                    
                    if (currentDate < bestDate) {
                        bestSlot = slot;
                    }
                }
            });
            
            // Handle case where no one is available
            if (maxAvailable === 0) {
                // Find the earliest time slot in the range
                let earliestSlot = Object.values(timeSlotData).reduce((earliest, current) => {
                    const currentDate = new Date(`${current.date}T${secondsToTimeString(current.time)}`);
                    const earliestDate = earliest ? new Date(`${earliest.date}T${secondsToTimeString(earliest.time)}`) : null;
                    
                    return !earliest || currentDate < earliestDate ? current : earliest;
                }, null);
                
                if (earliestSlot) {
                    bestTimeContainer.innerHTML = `
                        <h3>Best Time to Meet</h3>
                        <p>${formatDateForDisplay(earliestSlot.date)}, ${formatTimeDisplay(secondsToTimeString(earliestSlot.time))} - ${formatTimeDisplay(addMinutesToTime(secondsToTimeString(earliestSlot.time), 30))}</p>
                        <br>
                        <p><em>Note: No one has indicated availability yet.</em></p>
                    `;
                } else {
                    bestTimeContainer.innerHTML = "<p>No availability submitted yet.</p>";
                }
                return;
            }
            
            // Display the best time slot
            if (bestSlot) {
                bestTimeContainer.innerHTML = `
                    <h3>Best Time to Meet</h3>
                    <p>${formatDateForDisplay(bestSlot.date)}, ${formatTimeDisplay(secondsToTimeString(bestSlot.time))} - ${formatTimeDisplay(addMinutesToTime(secondsToTimeString(bestSlot.time), 30))}</p>
                    <br>
                    <p class="user-available">${maxAvailable} user${maxAvailable !== 1 ? 's' : ''} available</p>
                `;
            } else {
                bestTimeContainer.innerHTML = "<p>No availability submitted yet.</p>";
            }
        })
        .catch(error => {
            console.error('Error calculating best time:', error);
            document.getElementById('bestTimeToMeet').innerHTML = "<p>Unable to calculate best time.</p>";
        });
}

// Helper function to convert seconds to HH:MM:SS
function secondsToTimeString(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`;
}

// Helper function to format date for display
// Fixed formatDateForDisplay function
function formatDateForDisplay(dateStr) {
    // Create date parts to avoid timezone issues
    const [year, month, day] = dateStr.split('-').map(num => parseInt(num, 10));
    
    // Create date using local components (months are 0-indexed in JS Date)
    const date = new Date(year, month - 1, day);
    
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    
    return `${days[date.getDay()]}, ${months[date.getMonth()]} ${date.getDate()}`;
}

// Helper function to format time for display (12-hour format)
function formatTimeDisplay(timeStr) {
    const [hours, minutes] = timeStr.split(':');
    const hourNum = parseInt(hours, 10);
    const period = hourNum >= 12 ? 'PM' : 'AM';
    const hour12 = hourNum % 12 || 12;
    
    return `${hour12}:${minutes} ${period}`;
}

// Helper function to add minutes to a time string
function addMinutesToTime(timeStr, minutesToAdd) {
    const [hours, minutes, seconds] = timeStr.split(':');
    const date = new Date();
    date.setHours(parseInt(hours, 10));
    date.setMinutes(parseInt(minutes, 10) + minutesToAdd);
    
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:00`;
}
  });