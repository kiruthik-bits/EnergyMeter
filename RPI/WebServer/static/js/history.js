// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/history.js
console.log("--- history.js loaded ---");

// --- Declare variables, but don't assign elements yet ---
let deviceSelect, timeRangeSelect, plotlyChartDiv, loadingIndicator, errorMessage, noDataMessage;

// --- API Endpoints ---
const DEVICES_API_URL = '/api/devices';
const HISTORY_API_URL = '/api/historical_data'; // Base URL

// --- Helper Functions ---
// ... (showLoading, hideLoading, showError, showNoData - keep these) ...
function showLoading() {
    console.log("showLoading called");
    // Add checks in case elements aren't found (robustness)
    if (loadingIndicator) loadingIndicator.classList.remove('d-none');
    if (errorMessage) errorMessage.classList.add('d-none');
    if (noDataMessage) noDataMessage.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'none';
}

function hideLoading() {
    console.log("hideLoading called");
    if (loadingIndicator) loadingIndicator.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'block';
}

function showError(message) {
    console.log("showError called with message:", message);
    if (errorMessage) {
        errorMessage.textContent = message || 'An unknown error occurred.';
        errorMessage.classList.remove('d-none');
    }
    if (noDataMessage) noDataMessage.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'none';
    try {
        if (plotlyChartDiv) Plotly.purge(plotlyChartDiv);
    } catch(e) { console.warn("Error purging Plotly chart:", e); }
}

function showNoData() {
    console.log("showNoData called");
     if (noDataMessage) {
        // --- Set a more specific message here ---
        noDataMessage.textContent = "No data available for the selected device and time range.";
        // --- End modification ---
        noDataMessage.classList.remove('d-none');
     }
    if (errorMessage) errorMessage.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'none';
    try {
        if (plotlyChartDiv) Plotly.purge(plotlyChartDiv);
    } catch(e) { console.warn("Error purging Plotly chart:", e); }
}


// --- Plotly Chart Logic ---
// ... (updatePlotlyChart function remains the same) ...
function updatePlotlyChart(plotData, deviceId) {
    // Keep the existing log here
    console.log("updatePlotlyChart called. Device:", deviceId, "Data points:", plotData.x.length);
    if (!plotlyChartDiv) {
        console.error("plotlyChartDiv element not found for plotting.");
        return;
    }
    plotlyChartDiv.style.display = 'block'; // Ensure div is visible

    const trace = {
        x: plotData.x, // Array of timestamps
        y: plotData.y, // Array of power values
        mode: 'lines+markers', // Show lines and markers
        type: 'scatter', // Use scatter type for time series
        name: `Power (Watts)`, // Legend entry
        line: {
            color: 'rgb(0, 123, 255)', // Bootstrap primary blue
            width: 1.5
        },
        marker: {
            size: plotData.x.length > 200 ? 2 : 4 // Smaller markers if lots of data
        },
        hovertemplate: '%{y:.2f} W<extra></extra>' // Customize hover text
    };

    const layout = {
        title: `Power Consumption - ${deviceId}`,
        xaxis: {
            title: 'Time',
            type: 'date', // Use date axis type
             tickformat: '%H:%M\n%b %d', // Example format
        },
        yaxis: {
            title: 'Power (Watts)',
            rangemode: 'tozero' // Ensure Y-axis starts at 0
        },
        margin: { l: 60, r: 30, b: 50, t: 80 }, // Adjust margins
        hovermode: 'x unified' // Show hover info for points with the same x-value
    };

    Plotly.react(plotlyChartDiv, [trace], layout, {responsive: true});
    console.log("Plotly chart updated/created.");
}


// --- Data Fetching ---
// ... (fetchDevices and fetchAndUpdateChart functions remain largely the same,
//      they will now use the globally scoped variables assigned in DOMContentLoaded) ...
async function fetchDevices() {
    console.log("fetchDevices function started");

    // --- More specific check ---
    let missingElements = [];
    if (!deviceSelect) missingElements.push('deviceSelect (ID: device-select)');
    if (!plotlyChartDiv) missingElements.push('plotlyChartDiv (ID: plotlyChartDiv)');
    if (!noDataMessage) missingElements.push('noDataMessage (ID: no-data-message)');

    if (missingElements.length > 0) {
        console.error("Required elements not found in fetchDevices:", missingElements.join(', '));
        showError("Page elements missing. Cannot load devices.");
        return;
    }
    // --- End specific check ---

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

        // Initial UI state
        plotlyChartDiv.style.display = 'none';
        noDataMessage.textContent = "Please select a device and time range.";
        noDataMessage.classList.remove('d-none');

    } catch (error) {
        console.error('Error fetching devices:', error);
        if (deviceSelect) deviceSelect.innerHTML = '<option value="" selected disabled>Error loading devices</option>';
        showError(`Could not load device list: ${error.message}`);
    }
    console.log("fetchDevices function finished");
}

async function fetchAndUpdateChart() {
    console.log("fetchAndUpdateChart function started");
     // Add check
    if (!deviceSelect || !timeRangeSelect || !plotlyChartDiv || !noDataMessage || !errorMessage || !loadingIndicator) {
        console.error("Required elements not found in fetchAndUpdateChart.");
        return;
    }
    const selectedDevice = deviceSelect.value;
    const selectedHours = timeRangeSelect.value;
    console.log(`Selected Device: ${selectedDevice}, Selected Hours: ${selectedHours}`);

    if (!selectedDevice) {
        console.log("fetchAndUpdateChart: No device selected, exiting.");
        plotlyChartDiv.style.display = 'none';
        noDataMessage.textContent = "Please select a device.";
        noDataMessage.classList.remove('d-none');
        errorMessage.classList.add('d-none');
        loadingIndicator.classList.add('d-none');
        try { Plotly.purge(plotlyChartDiv); } catch(e) {}
        return;
    }

    showLoading();

    try {
        const url = `${HISTORY_API_URL}?device_id=${encodeURIComponent(selectedDevice)}&hours=${selectedHours}`;
        console.log("fetchAndUpdateChart: Fetching URL:", url);
        const response = await fetch(url);
        console.log("fetchAndUpdateChart: API response status:", response.status);

        if (!response.ok) {
            let errorMsg = `HTTP error! status: ${response.status}`;
             try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore */ }
            throw new Error(errorMsg);
        }

        const data = await response.json();
        console.log("fetchAndUpdateChart: Received data count:", data.length);

        if (!Array.isArray(data)) {
            throw new Error("Received invalid data format from server.");
        }

        if (data.length === 0) {
            showNoData();
            return;
        }

        // Prepare data
        const plotData = { x: [], y: [] };
        data.forEach(item => {
            plotData.x.push(item.timestamp);
            plotData.y.push(item.power);
        });
        console.log("Data being sent to Plotly:", plotData);

        updatePlotlyChart(plotData, selectedDevice);

    } catch (error) {
        console.error('Error fetching or processing historical data:', error);
        showError(`Error loading chart data: ${error.message}`);
    } finally {
        hideLoading();
    }
    console.log("fetchAndUpdateChart function finished");
}


// --- Event Listeners & Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMContentLoaded event fired");

    // --- Assign elements AFTER DOM is loaded ---
    deviceSelect = document.getElementById('device-select');
    timeRangeSelect = document.getElementById('time-range-select');
    plotlyChartDiv = document.getElementById('plotlyChartDiv');
    console.log("Result of getElementById('plotlyChartDiv'):", plotlyChartDiv);
    loadingIndicator = document.getElementById('loading-indicator');
    errorMessage = document.getElementById('error-message');
    noDataMessage = document.getElementById('no-data-message');
    // --- End assignment ---

    // Check if elements were found before adding listeners/calling functions
    if (deviceSelect && timeRangeSelect) {
        deviceSelect.addEventListener('change', () => {
            console.log("Device selection changed!");
            fetchAndUpdateChart();
        });
        timeRangeSelect.addEventListener('change', () => {
            console.log("Time range selection changed!");
            fetchAndUpdateChart();
        });

        // Now safe to call fetchDevices
        fetchDevices();
    } else {
        console.error("Could not find essential dropdown elements (device-select or time-range-select).");
        // Optionally display an error to the user on the page
        if(errorMessage) {
            errorMessage.textContent = "Error initializing page controls.";
            errorMessage.classList.remove('d-none');
        }
    }
});
