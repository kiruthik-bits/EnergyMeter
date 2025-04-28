// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/statistics.js
console.log("--- statistics.js loaded ---");

// --- Declare variables ---
let deviceSelect, timeRangeSelect, loadingIndicator, errorMessage, selectPromptMessage, statsDisplay;
let avgPowerEl, peakPowerEl, peakTimeEl, totalEnergyEl, statsDeviceTitleEl;

// --- API Endpoints ---
const DEVICES_API_URL = '/api/devices';
const STATS_API_URL = '/api/statistics'; // Base URL

// --- Helper Functions ---
function showLoading() {
    console.log("showLoading called");
    if (loadingIndicator) loadingIndicator.classList.remove('d-none');
    if (errorMessage) errorMessage.classList.add('d-none');
    if (selectPromptMessage) selectPromptMessage.classList.add('d-none');
    if (statsDisplay) statsDisplay.classList.add('d-none'); // Hide stats while loading
}

function hideLoading() {
    console.log("hideLoading called");
    if (loadingIndicator) loadingIndicator.classList.add('d-none');
}

function showError(message) {
    console.log("showError called with message:", message);
    if (errorMessage) {
        errorMessage.textContent = message || 'An unknown error occurred.';
        errorMessage.classList.remove('d-none');
    }
    if (selectPromptMessage) selectPromptMessage.classList.add('d-none');
    if (statsDisplay) statsDisplay.classList.add('d-none');
}

function showSelectPrompt() {
     console.log("showSelectPrompt called");
     if (selectPromptMessage) selectPromptMessage.classList.remove('d-none');
     if (errorMessage) errorMessage.classList.add('d-none');
     if (statsDisplay) statsDisplay.classList.add('d-none');
     if (loadingIndicator) loadingIndicator.classList.add('d-none');
}

function displayStats(stats) {
    console.log("displayStats called with:", stats);
    if (!statsDisplay || !avgPowerEl || !peakPowerEl || !peakTimeEl || !totalEnergyEl || !statsDeviceTitleEl) {
        console.error("Stats display elements not found.");
        showError("Failed to update statistics display.");
        return;
    }

    statsDeviceTitleEl.textContent = `Statistics for ${stats.device_id} (Last ${stats.time_range_hours} Hours)`;
    avgPowerEl.textContent = stats.average_power_watts !== null ? stats.average_power_watts.toFixed(2) : 'N/A';

    // Update Peak Usage using timestamp_unix
    if (stats.peak_usage && stats.peak_usage.timestamp_unix !== null && stats.peak_usage.timestamp_unix !== undefined) {
        peakPowerEl.textContent = stats.peak_usage.power.toFixed(2);
        // Format Unix epoch timestamp nicely
        try {
            // Convert Unix epoch seconds to milliseconds for Date constructor
            const peakDate = new Date(stats.peak_usage.timestamp_unix * 1000);
            peakTimeEl.textContent = `at ${peakDate.toLocaleString()}`;
        } catch (e) {
            console.error("Error formatting peak date:", e);
            peakTimeEl.textContent = 'at (invalid date)';
        }
    } else {
        peakPowerEl.textContent = 'N/A';
        peakTimeEl.textContent = '';
    }

    totalEnergyEl.textContent = stats.total_energy_kwh !== null ? stats.total_energy_kwh.toFixed(3) : 'N/A';

    statsDisplay.classList.remove('d-none');
    if (selectPromptMessage) selectPromptMessage.classList.add('d-none');
}


// --- Data Fetching ---
async function fetchDevices() {
    console.log("fetchDevices function started");
    if (!deviceSelect) {
        console.error("Device select element not found.");
        showError("Page element missing: device select.");
        return;
    }
    try {
        const response = await fetch(DEVICES_API_URL);
        console.log("fetchDevices API response status:", response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const devices = await response.json();
        console.log("fetchDevices received devices:", devices);

        deviceSelect.innerHTML = ''; // Clear existing options

        if (!Array.isArray(devices) || devices.length === 0) {
             console.log("fetchDevices: No devices found or invalid format.");
             deviceSelect.innerHTML = '<option value="" selected disabled>No devices found</option>';
             showError('No devices found in the database.');
             return;
        }

        // Add placeholder option
        const placeholderOption = document.createElement('option');
        placeholderOption.value = "";
        placeholderOption.textContent = "-- Select a Device --";
        placeholderOption.disabled = true;
        placeholderOption.selected = true;
        deviceSelect.appendChild(placeholderOption);

        // Populate dropdown
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device;
            option.textContent = device;
            deviceSelect.appendChild(option);
        });
        console.log("fetchDevices: Populated device dropdown.");

        // Show initial prompt
        showSelectPrompt();

    } catch (error) {
        console.error('Error fetching devices:', error);
        if (deviceSelect) deviceSelect.innerHTML = '<option value="" selected disabled>Error loading devices</option>';
        showError(`Could not load device list: ${error.message}`);
    }
    console.log("fetchDevices function finished");
}

async function fetchAndDisplayStats() {
    console.log("fetchAndDisplayStats function started");
    if (!deviceSelect || !timeRangeSelect) {
         console.error("Dropdown elements not found.");
         return;
    }
    const selectedDevice = deviceSelect.value;
    const selectedHours = timeRangeSelect.value;
    console.log(`Selected Device: ${selectedDevice}, Selected Hours: ${selectedHours}`);

    if (!selectedDevice) {
        console.log("fetchAndDisplayStats: No device selected.");
        showSelectPrompt();
        return;
    }

    showLoading();

    try {
        const url = `${STATS_API_URL}?device_id=${encodeURIComponent(selectedDevice)}&hours=${selectedHours}`;
        console.log("fetchAndDisplayStats: Fetching URL:", url);
        const response = await fetch(url);
        console.log("fetchAndDisplayStats: API response status:", response.status);

        if (!response.ok) {
            let errorMsg = `HTTP error! status: ${response.status}`;
             try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore */ }
            throw new Error(errorMsg);
        }

        const statsData = await response.json(); // API now returns peak_usage: {timestamp_unix: ..., power: ...}
        console.log("fetchAndDisplayStats: Received stats:", statsData);

        if (statsData.average_power_watts === null && statsData.peak_usage === null && statsData.total_energy_kwh === null) {
             showError("No data found for the selected device and time range to calculate statistics.");
        } else {
             displayStats(statsData);
        }

    } catch (error) {
        console.error('Error fetching or processing statistics:', error);
        showError(`Error loading statistics: ${error.message}`);
    } finally {
        hideLoading();
    }
    console.log("fetchAndDisplayStats function finished");
}


// --- Event Listeners & Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMContentLoaded event fired");

    // Assign elements AFTER DOM is loaded
    deviceSelect = document.getElementById('device-select');
    timeRangeSelect = document.getElementById('time-range-select');
    loadingIndicator = document.getElementById('loading-indicator');
    errorMessage = document.getElementById('error-message');
    selectPromptMessage = document.getElementById('select-prompt-message');
    statsDisplay = document.getElementById('stats-display');
    avgPowerEl = document.getElementById('avg-power');
    peakPowerEl = document.getElementById('peak-power');
    peakTimeEl = document.getElementById('peak-time');
    totalEnergyEl = document.getElementById('total-energy');
    statsDeviceTitleEl = document.getElementById('stats-device-title');

    // Check if elements were found before adding listeners/calling functions
    if (deviceSelect && timeRangeSelect) {
        deviceSelect.addEventListener('change', fetchAndDisplayStats);
        timeRangeSelect.addEventListener('change', fetchAndDisplayStats);

        // Fetch devices initially
        fetchDevices();
    } else {
        console.error("Could not find essential dropdown elements (device-select or time-range-select).");
        if(errorMessage) {
            errorMessage.textContent = "Error initializing page controls.";
            errorMessage.classList.remove('d-none');
        }
         if (selectPromptMessage) selectPromptMessage.classList.add('d-none'); // Hide prompt if controls failed
    }
});
