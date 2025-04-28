// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/dashboard.js

const API_URL = '/api/data';
const REFRESH_INTERVAL = 5000; // 5 seconds
const ACTIVE_THRESHOLD_SECONDS = 60; // Device considered active if data received within this period

// Element references
let activeDevicesValueEl, dashboardCardsEl, errorMessageEl, activeDevicesCardEl, refreshButtonEl;

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

// Function to determine if a device is active
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
    // Base classes + height consistency
    card.className = 'card shadow-sm h-100';
    card.style.cursor = 'pointer'; // Indicate it's clickable

    // Add border based on active status
    if (isActive) {
        card.classList.add('border-success', 'border-2'); // Green border for active
    } else {
        card.classList.add('border-secondary'); // Grey border for inactive
        card.classList.add('opacity-75'); // Slightly faded for inactive
    }

    const cardBody = document.createElement('div');
    // Use flexbox to push time ago to the bottom
    cardBody.className = 'card-body d-flex flex-column';

    // Device Title
    const title = document.createElement('h5');
    title.className = 'card-title mb-2';
    title.textContent = deviceId;

    // Status Badge
    const statusBadge = document.createElement('span');
    statusBadge.className = `badge ${isActive ? 'bg-success' : 'bg-secondary'} mb-2 align-self-start`; // Align badge left
    statusBadge.textContent = isActive ? 'Active' : 'Inactive';

    // Latest Power Reading
    const latestPowerText = document.createElement('p');
    latestPowerText.className = 'card-text fs-5 fw-bold mb-1'; // Slightly smaller than total power was
    const latestPower = (stats && stats.latest !== undefined && stats.latest !== null) ? stats.latest : 0;
    latestPowerText.textContent = `${latestPower.toFixed(2)} W`;

    // Time Since Update (pushed to bottom)
    const timeAgoText = document.createElement('p');
    timeAgoText.className = 'card-text text-muted small mt-auto'; // mt-auto pushes it down
    const timeAgo = formatTimeAgo(stats?.timestamp_unix); // Use optional chaining
    timeAgoText.textContent = `Updated: ${timeAgo}`;

    // Append elements to card body
    cardBody.appendChild(title);
    cardBody.appendChild(statusBadge);
    cardBody.appendChild(latestPowerText);
    cardBody.appendChild(timeAgoText); // Add time ago text last

    card.appendChild(cardBody);

    // Make card clickable
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
    if (refreshButtonEl) refreshButtonEl.disabled = true; // Disable refresh button while loading

    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            let errorMsg = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore JSON parsing error */ }
            throw new Error(errorMsg);
        }
        const data = await response.json();

        // Clear previous state
        dashboardCardsEl.innerHTML = ''; // Clear existing cards/placeholders
        errorMessageEl.classList.add('d-none'); // Hide error message
        activeDevicesCardEl.classList.remove('bg-secondary'); // Ensure card is not greyed out
        activeDevicesCardEl.classList.add('bg-primary'); // Set default color

        let activeCount = 0;
        let totalDevices = 0;

        // Sort devices alphabetically for consistent order
        const deviceIds = Object.keys(data).filter(id => id !== 'Total' && id !== 'error').sort();
        totalDevices = deviceIds.length;

        for (const deviceId of deviceIds) {
            const stats = data[deviceId];
            const isActive = isDeviceActive(stats?.timestamp_unix);
            if (isActive) {
                activeCount++;
            }
            const cardElement = createDeviceCard(deviceId, stats, isActive);
            dashboardCardsEl.appendChild(cardElement);
        }

        // Update Active Devices Count
        activeDevicesValueEl.textContent = `${activeCount} / ${totalDevices}`;

        // Handle case where no devices are found
        if (totalDevices === 0) {
             dashboardCardsEl.innerHTML = '<p class="text-center text-muted w-100">No device data available yet.</p>';
             activeDevicesValueEl.textContent = '0 / 0';
        }

        console.log("Data refreshed successfully.");

    } catch (error) {
        console.error('Error fetching or processing data:', error);
        errorMessageEl.textContent = `Error loading data: ${error.message}. Please check connection or server logs.`;
        errorMessageEl.classList.remove('d-none'); // Show error message
        // Update UI to reflect error state
        activeDevicesValueEl.textContent = 'Error';
        activeDevicesCardEl.classList.remove('bg-primary');
        activeDevicesCardEl.classList.add('bg-secondary'); // Grey out the card
        dashboardCardsEl.innerHTML = ''; // Clear cards area on error
    } finally {
        if (refreshButtonEl) refreshButtonEl.disabled = false; // Re-enable refresh button
    }
}

// --- Initial Load & Interval ---
document.addEventListener('DOMContentLoaded', () => {
    // Assign elements after DOM is ready
    activeDevicesValueEl = document.getElementById('active-devices-value');
    dashboardCardsEl = document.getElementById('dashboard-cards');
    errorMessageEl = document.getElementById('error-message');
    activeDevicesCardEl = document.getElementById('active-devices-card');
    refreshButtonEl = document.getElementById('refresh-button');

    // Check if all required elements were found
    if (!activeDevicesValueEl || !dashboardCardsEl || !errorMessageEl || !activeDevicesCardEl || !refreshButtonEl) {
         console.error("One or more essential dashboard elements are missing!");
         if(errorMessageEl) { // Display error if possible
             errorMessageEl.textContent = "Dashboard UI elements failed to load correctly.";
             errorMessageEl.classList.remove('d-none');
         }
         return; // Stop execution if elements are missing
    }

    // Add event listener for the refresh button
    refreshButtonEl.addEventListener('click', () => {
        console.log("Refresh button clicked!");
        loadData(); // Manually trigger data load
    });

    // Initial data load
    loadData();

    // Set interval for automatic refresh
    setInterval(loadData, REFRESH_INTERVAL);
});
