// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/dashboard.js

const API_URL = '/api/data';
const REFRESH_INTERVAL = 5000;

// Define thresholds for background colors (adjust as needed)
const HIGH_USAGE_THRESHOLD = 300; // Watts
const MEDIUM_USAGE_THRESHOLD = 50; // Watts
const STALE_DATA_THRESHOLD_SECONDS = 300; // 5 minutes

let totalPowerValueEl, dashboardCardsEl, errorMessageEl, totalPowerCardEl, refreshButtonEl;

// Helper function to format time difference
function formatTimeAgo(unixTimestamp) {
    if (unixTimestamp === null || unixTimestamp === undefined) {
        return "never";
    }
    const now = Math.floor(Date.now() / 1000); // Current time in seconds
    const secondsAgo = now - unixTimestamp;

    if (secondsAgo < 0) return "in the future?"; // Should not happen
    if (secondsAgo < 60) return `${Math.floor(secondsAgo)}s ago`;
    if (secondsAgo < 3600) return `${Math.floor(secondsAgo / 60)}m ago`;
    if (secondsAgo < 86400) return `${Math.floor(secondsAgo / 3600)}h ago`;
    return `${Math.floor(secondsAgo / 86400)}d ago`;
}

function createDeviceCard(deviceId, stats) {
    const col = document.createElement('div');
    col.className = 'col';

    const card = document.createElement('div');
    // Base classes
    card.className = 'card shadow-sm h-100';
    card.style.cursor = 'pointer'; // Indicate it's clickable

    // Add background based on usage
    let latestPower = 0; // Default to 0
    if (stats && stats.latest !== undefined && stats.latest !== null) {
        latestPower = stats.latest;
        if (latestPower >= HIGH_USAGE_THRESHOLD) {
            card.classList.add('border-danger', 'border-2'); // Red border for high usage
        } else if (latestPower >= MEDIUM_USAGE_THRESHOLD) {
            card.classList.add('border-warning', 'border-2'); // Yellow border for medium usage
        } else {
             card.classList.add('border-success'); // Green border for low usage
        }
    } else {
         card.classList.add('border-secondary'); // Grey border if no data
    }

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body d-flex flex-column';

    const title = document.createElement('h5');
    title.className = 'card-title mb-2';
    title.textContent = deviceId;

    const latestPowerText = document.createElement('p');
    latestPowerText.className = 'card-text fs-4 fw-bold mb-1'; // Larger font for power
    latestPowerText.textContent = `${latestPower.toFixed(2)} W`;

    // --- Add Time Since Update ---
    const timeAgoText = document.createElement('p');
    timeAgoText.className = 'card-text text-muted small mt-auto'; // Push to bottom
    const timeAgo = formatTimeAgo(stats?.timestamp_unix); // Use optional chaining
    timeAgoText.textContent = `Updated: ${timeAgo}`;

    // Check if data is stale
    if (stats?.timestamp_unix && (Math.floor(Date.now() / 1000) - stats.timestamp_unix) > STALE_DATA_THRESHOLD_SECONDS) {
        timeAgoText.classList.add('text-danger', 'fw-bold'); // Highlight stale data
        card.classList.remove('border-success', 'border-warning', 'border-danger');
        card.classList.add('border-secondary', 'opacity-75'); // Make stale cards grey and slightly transparent
    }
     // --- End Add Time Since Update ---


    cardBody.appendChild(title);
    cardBody.appendChild(latestPowerText);
    cardBody.appendChild(timeAgoText); // Add time ago text
    card.appendChild(cardBody);

    // --- Make card clickable ---
    card.addEventListener('click', () => {
        // Redirect to history page for this device
        window.location.href = `/history?device_id=${encodeURIComponent(deviceId)}`;
    });
    // --- End Make card clickable ---

    col.appendChild(card);
    return col;
}


async function loadData() {
    console.log("Fetching data at", new Date().toLocaleTimeString());
    if (!totalPowerValueEl || !dashboardCardsEl || !errorMessageEl || !totalPowerCardEl) {
        console.error("Dashboard elements not found, cannot load data.");
        return;
    }
    if (refreshButtonEl) refreshButtonEl.disabled = true;

    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            let errorMsg = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore */ }
            throw new Error(errorMsg);
        }
        const data = await response.json();

        dashboardCardsEl.innerHTML = '';
        errorMessageEl.classList.add('d-none');
        totalPowerCardEl.classList.remove('bg-secondary');
        totalPowerCardEl.classList.add('bg-danger');

        if (data.Total && data.Total.total_power !== undefined && data.Total.total_power !== null) {
            totalPowerValueEl.textContent = `${data.Total.total_power.toFixed(2)} W`;
        } else {
            totalPowerValueEl.textContent = 'N/A';
        }

        let deviceCount = 0;
        // Sort devices alphabetically for consistent order
        const deviceIds = Object.keys(data).filter(id => id !== 'Total' && id !== 'error').sort();

        for (const deviceId of deviceIds) {
            // if (deviceId === 'Total' || deviceId === 'error') continue; // Already filtered
            deviceCount++;
            const stats = data[deviceId];
            const cardElement = createDeviceCard(deviceId, stats);
            dashboardCardsEl.appendChild(cardElement);
        }

        if (deviceCount === 0) {
             dashboardCardsEl.innerHTML = '<p class="text-center text-muted w-100">No device data available yet.</p>';
        }

        console.log("Data refreshed successfully.");

    } catch (error) {
        console.error('Error fetching or processing data:', error);
        errorMessageEl.textContent = `Error loading data: ${error.message}. Please check connection or server logs.`;
        errorMessageEl.classList.remove('d-none');
        totalPowerValueEl.textContent = 'Error';
        totalPowerCardEl.classList.remove('bg-danger');
        totalPowerCardEl.classList.add('bg-secondary');
        dashboardCardsEl.innerHTML = '';
    } finally {
        if (refreshButtonEl) refreshButtonEl.disabled = false;
    }
}

// --- Initial Load & Interval ---
document.addEventListener('DOMContentLoaded', () => {
    totalPowerValueEl = document.getElementById('total-power-value');
    dashboardCardsEl = document.getElementById('dashboard-cards');
    errorMessageEl = document.getElementById('error-message');
    totalPowerCardEl = document.getElementById('total-power-card');
    refreshButtonEl = document.getElementById('refresh-button');

    if (refreshButtonEl) {
        refreshButtonEl.addEventListener('click', () => {
            console.log("Refresh button clicked!");
            loadData();
        });
    } else {
        console.warn("Refresh button element not found.");
    }

    loadData();
    setInterval(loadData, REFRESH_INTERVAL);
});
