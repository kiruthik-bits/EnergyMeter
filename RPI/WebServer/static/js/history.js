// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/history.js

// --- Declare variables ---
let deviceSelect, timeRangeSelect, plotlyChartDiv, loadingIndicator, errorMessage, noDataMessage;

// --- API Endpoints ---
const DEVICES_API_URL = '/api/devices';
const HISTORY_API_URL = '/api/historical_data'; // Base URL

// --- Helper Functions ---
function showLoading() {
    if (loadingIndicator) loadingIndicator.classList.remove('d-none');
    if (errorMessage) errorMessage.classList.add('d-none');
    if (noDataMessage) noDataMessage.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'none';
}

function hideLoading() {
    if (loadingIndicator) loadingIndicator.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'block';
}

function showError(message) {
    // Keep console.error for actual errors
    console.error("Displaying error:", message);
    if (errorMessage) {
        errorMessage.textContent = message || 'An unknown error occurred.';
        errorMessage.classList.remove('d-none');
    }
    if (noDataMessage) noDataMessage.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'none';
    try {
        if (plotlyChartDiv) Plotly.purge(plotlyChartDiv);
    } catch(e) { console.warn("Error purging Plotly chart:", e); } // Keep warn for purge issues
}

function showNoData() {
     if (noDataMessage) {
        noDataMessage.textContent = "No data available for the selected device and time range.";
        noDataMessage.classList.remove('d-none');
     }
    if (errorMessage) errorMessage.classList.add('d-none');
    if (plotlyChartDiv) plotlyChartDiv.style.display = 'none';
    try {
        if (plotlyChartDiv) Plotly.purge(plotlyChartDiv);
    } catch(e) { console.warn("Error purging Plotly chart:", e); } // Keep warn for purge issues
}


// --- Plotly Chart Logic ---
function updatePlotlyChart(plotData, deviceId) {
    if (!plotlyChartDiv) {
        console.error("plotlyChartDiv element not found for plotting.");
        return;
    }
    plotlyChartDiv.style.display = 'block';

    const trace = {
        x: plotData.x, // Expecting JS Date objects or ISO strings
        y: plotData.y,
        mode: 'lines+markers',
        type: 'scatter',
        name: `Power (Watts)`,
        line: { color: 'rgb(0, 123, 255)', width: 1.5 },
        marker: { size: plotData.x.length > 200 ? 2 : 4 },
        hovertemplate: '%{y:.2f} W<extra></extra>'
    };

    const layout = {
        title: `Power Consumption - ${deviceId}`,
        xaxis: { title: 'Time', type: 'date', tickformat: '%H:%M\n%b %d' },
        yaxis: { title: 'Power (Watts)', rangemode: 'tozero' },
        margin: { l: 60, r: 30, b: 50, t: 80 },
        hovermode: 'x unified'
    };

    Plotly.react(plotlyChartDiv, [trace], layout, {responsive: true});
}


// --- Data Fetching ---
async function fetchDevices() {
    let devicesPopulated = false;
    if (!deviceSelect || !plotlyChartDiv || !noDataMessage) {
        console.error("Required elements not found in fetchDevices.");
        showError("Page elements missing. Cannot load devices.");
        return devicesPopulated;
    }
    try {
        const response = await fetch(DEVICES_API_URL);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const devices = await response.json();

        deviceSelect.innerHTML = ''; // Clear existing options

        if (!Array.isArray(devices) || devices.length === 0) {
             deviceSelect.innerHTML = '<option value="" selected disabled>No devices found</option>';
             showError('No devices found in the database.');
             return devicesPopulated;
        }

        // Add placeholder option
        const placeholderOption = document.createElement('option');
        placeholderOption.value = "";
        placeholderOption.textContent = "-- Select a Device --";
        placeholderOption.selected = true;
        deviceSelect.appendChild(placeholderOption);

        // Populate dropdown
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device;
            option.textContent = device;
            deviceSelect.appendChild(option);
        });
        devicesPopulated = true;

    } catch (error) {
        console.error('Error fetching devices:', error); // Keep essential error log
        if (deviceSelect) deviceSelect.innerHTML = '<option value="" selected disabled>Error loading devices</option>';
        showError(`Could not load device list: ${error.message}`);
    }
    return devicesPopulated;
}

async function fetchAndUpdateChart() {
    if (!deviceSelect || !timeRangeSelect || !plotlyChartDiv || !noDataMessage || !errorMessage || !loadingIndicator) {
        console.error("Required elements not found in fetchAndUpdateChart.");
        return;
    }
    const selectedDevice = deviceSelect.value;
    const selectedHours = timeRangeSelect.value;

    if (!selectedDevice || deviceSelect.selectedIndex === 0) {
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
        const response = await fetch(url);

        if (!response.ok) {
            let errorMsg = `HTTP error! status: ${response.status}`;
             try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore */ }
            throw new Error(errorMsg);
        }

        const data = await response.json(); // API now returns [{timestamp: unix_epoch_float, power: ...}, ...]

        if (!Array.isArray(data)) {
            throw new Error("Received invalid data format from server.");
        }

        if (data.length === 0) {
            showNoData();
            return;
        }

        // Prepare data for Plotly
        const plotData = { x: [], y: [] };
        data.forEach(item => {
            // Convert Unix epoch seconds to JavaScript Date object (needs milliseconds)
            if (item.timestamp !== null && item.timestamp !== undefined) {
                 plotData.x.push(new Date(item.timestamp * 1000));
                 plotData.y.push(item.power);
            }
        });

        updatePlotlyChart(plotData, selectedDevice);

    } catch (error) {
        console.error('Error fetching or processing historical data:', error);
        showError(`Error loading chart data: ${error.message}`);
    } finally {
        hideLoading();
    }
}



// --- Event Listeners & Initial Load ---
document.addEventListener('DOMContentLoaded', async () => {
    // Assign elements AFTER DOM is loaded
    deviceSelect = document.getElementById('device-select');
    timeRangeSelect = document.getElementById('time-range-select');
    plotlyChartDiv = document.getElementById('plotlyChartDiv');
    loadingIndicator = document.getElementById('loading-indicator');
    errorMessage = document.getElementById('error-message');
    noDataMessage = document.getElementById('no-data-message');

    // Check if elements were found before adding listeners/calling functions
    if (deviceSelect && timeRangeSelect) {
        deviceSelect.addEventListener('change', fetchAndUpdateChart);
        timeRangeSelect.addEventListener('change', fetchAndUpdateChart);

        // Fetch devices and wait for the dropdown to be populated
        const devicesLoaded = await fetchDevices();

        if (devicesLoaded) {
            // Check URL for device_id
            const urlParams = new URLSearchParams(window.location.search);
            const deviceIdFromUrl = urlParams.get('device_id');

            if (deviceIdFromUrl) {
                const options = Array.from(deviceSelect.options).map(opt => opt.value);
                if (options.includes(deviceIdFromUrl)) {
                    deviceSelect.value = deviceIdFromUrl;
                    fetchAndUpdateChart(); // Trigger the chart load
                } else {
                    console.warn("Device ID from URL not found in dropdown options."); // Keep this warning
                    noDataMessage.textContent = "Device specified in URL not found. Please select a device.";
                    noDataMessage.classList.remove('d-none');
                    plotlyChartDiv.style.display = 'none';
                }
            } else {
                 // Show prompt if no device in URL
                 noDataMessage.textContent = "Please select a device and time range.";
                 noDataMessage.classList.remove('d-none');
                 plotlyChartDiv.style.display = 'none';
            }
        } else {
             console.error("Device fetching failed, cannot proceed."); // Keep essential error log
        }

    } else {
        console.error("Could not find essential dropdown elements (device-select or time-range-select)."); // Keep essential error log
        if(errorMessage) {
            errorMessage.textContent = "Error initializing page controls.";
            errorMessage.classList.remove('d-none');
        }
    }
});
