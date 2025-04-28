// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/dashboard.js

const API_URL = '/api/data';
const REFRESH_INTERVAL = 5000; // 5 seconds
const ACTIVE_THRESHOLD_SECONDS = 60; // Device considered active if data received within this period

// Element references
let activeDevicesValueEl, dashboardCardsEl, errorMessageEl, activeDevicesCardEl, refreshButtonEl;

// Helper function to format time difference (expects Unix epoch seconds)
function formatTimeAgo(unixTimestamp) {
    if (unixTimestamp === null || unixTimestamp === undefined) {
        return "never";
    }
    const now = Math.floor(Date.now() / 1000); // Current time in seconds
    const secondsAgo = now - unixTimestamp;

    if (secondsAgo < 0) return "in the future?";
    if (secondsAgo < 60) return `${Math.floor(secondsAgo)}s ago`;
    if (secondsAgo < 3600) return `${Math.floor(secondsAgo / 60)}m ago`;
    if (secondsAgo < 86400) return `${Math.floor(secondsAgo / 3600)}h ago`;
    return `${Math.floor(secondsAgo / 86400)}d ago`;
}

// Function to determine if a device is active (expects Unix epoch seconds)
function isDeviceActive(unixTimestamp) {
    if (unixTimestamp === null || unixTimestamp === undefined) {
        return false;
    }
    const now = Math.floor(Date.now() / 1000);
    const secondsAgo = now - unixTimestamp;
    return secondsAgo >= 0 && secondsAgo <= ACTIVE_THRESHOLD_SECONDS;
}

// Function to create a device card
function createDeviceCard(deviceId, stats, isActive) {
    const col = document.createElement('div');
    col.className = 'col';

    const card = document.createElement('div');
    card.className = 'card shadow-sm h-100';
    card.style.cursor = 'pointer';

    if (isActive) {
        card.classList.add('border-success', 'border-2');
    } else {
        card.classList.add('border-secondary');
        card.classList.add('opacity-75');
    }

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body d-flex flex-column';

    const title = document.createElement('h5');
    title.className = 'card-title mb-2';
    title.textContent = deviceId;

    const statusBadge = document.createElement('span');
    statusBadge.className = `badge ${isActive ? 'bg-success' : 'bg-secondary'} mb-2 align-self-start`;
    statusBadge.textContent = isActive ? 'Active' : 'Inactive';

    const latestPowerText = document.createElement('p');
    latestPowerText.className = 'card-text fs-5 fw-bold mb-1';
    const latestPower = (stats && stats.latest !== undefined && stats.latest !== null) ? stats.latest : 0;
    latestPowerText.textContent = `${latestPower.toFixed(2)} W`;

    const timeAgoText = document.createElement('p');
    timeAgoText.className = 'card-text text-muted small mt-auto';
    // Use latest_timestamp_unix from the API response
    const timeAgo = formatTimeAgo(stats?.latest_timestamp_unix);
    timeAgoText.textContent = `Updated: ${timeAgo}`;

    cardBody.appendChild(title);
    cardBody.appendChild(statusBadge);
    cardBody.appendChild(latestPowerText);
    cardBody.appendChild(timeAgoText);

    card.appendChild(cardBody);

    card.addEventListener('click', () => {
        window.location.href = `/history?device_id=${encodeURIComponent(deviceId)}`;
    });

    col.appendChild(card);
    return col;
}

// Main function to load and display data
async function loadData() {
    console.log("Fetching data at", new Date().toLocaleTimeString());
    if (!activeDevicesValueEl || !dashboardCardsEl || !errorMessageEl || !activeDevicesCardEl) {
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
        activeDevicesCardEl.classList.remove('bg-secondary');
        activeDevicesCardEl.classList.add('bg-primary');

        let activeCount = 0;
        let totalDevices = 0;

        const deviceIds = Object.keys(data).filter(id => id !== 'Total' && id !== 'error').sort();
        totalDevices = deviceIds.length;

        for (const deviceId of deviceIds) {
            const stats = data[deviceId];
            // Use latest_timestamp_unix to check activity
            const isActive = isDeviceActive(stats?.latest_timestamp_unix);
            if (isActive) {
                activeCount++;
            }
            const cardElement = createDeviceCard(deviceId, stats, isActive);
            dashboardCardsEl.appendChild(cardElement);
        }

        activeDevicesValueEl.textContent = `${activeCount} / ${totalDevices}`;

        if (totalDevices === 0) {
             dashboardCardsEl.innerHTML = '<p class="text-center text-muted w-100">No device data available yet.</p>';
             activeDevicesValueEl.textContent = '0 / 0';
        }

        console.log("Data refreshed successfully.");

    } catch (error) {
        console.error('Error fetching or processing data:', error);
        errorMessageEl.textContent = `Error loading data: ${error.message}. Please check connection or server logs.`;
        errorMessageEl.classList.remove('d-none');
        activeDevicesValueEl.textContent = 'Error';
        activeDevicesCardEl.classList.remove('bg-primary');
        activeDevicesCardEl.classList.add('bg-secondary');
        dashboardCardsEl.innerHTML = '';
    } finally {
        if (refreshButtonEl) refreshButtonEl.disabled = false;
    }
}

// --- Initial Load & Interval ---
document.addEventListener('DOMContentLoaded', () => {
    activeDevicesValueEl = document.getElementById('active-devices-value');
    dashboardCardsEl = document.getElementById('dashboard-cards');
    errorMessageEl = document.getElementById('error-message');
    activeDevicesCardEl = document.getElementById('active-devices-card');
    refreshButtonEl = document.getElementById('refresh-button');

    if (!activeDevicesValueEl || !dashboardCardsEl || !errorMessageEl || !activeDevicesCardEl || !refreshButtonEl) {
         console.error("One or more essential dashboard elements are missing!");
         if(errorMessageEl) {
             errorMessageEl.textContent = "Dashboard UI elements failed to load correctly.";
             errorMessageEl.classList.remove('d-none');
         }
         return;
    }

    refreshButtonEl.addEventListener('click', () => {
        console.log("Refresh button clicked!");
        loadData();
    });

    loadData();
    setInterval(loadData, REFRESH_INTERVAL);
});
