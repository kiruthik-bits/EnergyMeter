// /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/static/js/dashboard.js

const API_URL = '/api/data'; // Use the API endpoint defined in api/routes.py
const REFRESH_INTERVAL = 5000; // 5 seconds

let totalPowerValueEl, dashboardCardsEl, errorMessageEl, totalPowerCardEl, refreshButtonEl;

function createDeviceCard(deviceId, stats) {
    const col = document.createElement('div');
    col.className = 'col'; // Bootstrap column

    const card = document.createElement('div');
    card.className = 'card shadow-sm h-100'; // Added h-100 for equal height cards

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body d-flex flex-column'; // Use flex for content alignment

    const title = document.createElement('h5');
    title.className = 'card-title mb-2'; // Bootstrap card title
    title.textContent = deviceId;

    const latestPowerText = document.createElement('p');
    latestPowerText.className = 'card-text mb-auto'; // mb-auto pushes footer down if using flex
    let latestPower = 'N/A';
    if (stats && stats.latest !== undefined && stats.latest !== null) {
        latestPower = `${stats.latest.toFixed(2)} W`;
    }
    latestPowerText.textContent = `Latest Reading: ${latestPower}`;

    // Optional: Add a small footer for timestamp if available
    // const footer = document.createElement('small');
    // footer.className = 'text-muted';
    // footer.textContent = `Last updated: ...`; // Need timestamp data

    cardBody.appendChild(title);
    cardBody.appendChild(latestPowerText);
    // cardBody.appendChild(footer);
    card.appendChild(cardBody);
    col.appendChild(card);

    return col;
}


async function loadData() {
    console.log("Fetching data at", new Date().toLocaleTimeString());
    // Add check for elements
    if (!totalPowerValueEl || !dashboardCardsEl || !errorMessageEl || !totalPowerCardEl) {
        console.error("Dashboard elements not found, cannot load data.");
        return;
    }
    // Disable button while loading
    if (refreshButtonEl) refreshButtonEl.disabled = true;

    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            // Try to get error message from response body
            let errorMsg = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore if response is not JSON */ }
            throw new Error(errorMsg);
        }
        const data = await response.json();

        // Clear previous cards and hide error
        dashboardCardsEl.innerHTML = '';
        errorMessageEl.classList.add('d-none'); // Hide error message
        totalPowerCardEl.classList.remove('bg-secondary'); // Reset card color
        totalPowerCardEl.classList.add('bg-danger');

        // Display Total Power
        if (data.Total && data.Total.total_power !== undefined && data.Total.total_power !== null) {
            totalPowerValueEl.textContent = `${data.Total.total_power.toFixed(2)} W`;
        } else {
            totalPowerValueEl.textContent = 'N/A';
        }

        // Display Individual Device Cards
        let deviceCount = 0;
        for (const deviceId in data) {
            if (deviceId === 'Total' || deviceId === 'error') continue; // Skip meta keys
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
        // Show error message and update UI to reflect error state
        errorMessageEl.textContent = `Error loading data: ${error.message}. Please check connection or server logs.`;
        errorMessageEl.classList.remove('d-none');
        totalPowerValueEl.textContent = 'Error';
        totalPowerCardEl.classList.remove('bg-danger');
        totalPowerCardEl.classList.add('bg-secondary'); // Grey out total power card
        dashboardCardsEl.innerHTML = ''; // Clear potentially stale cards
    } finally {
        // Re-enable button after loading finishes
        if (refreshButtonEl) refreshButtonEl.disabled = false;
    }
}

// --- Initial Load & Interval ---
document.addEventListener('DOMContentLoaded', () => {
    // --- Assign elements here ---
    totalPowerValueEl = document.getElementById('total-power-value');
    dashboardCardsEl = document.getElementById('dashboard-cards');
    errorMessageEl = document.getElementById('error-message');
    totalPowerCardEl = document.getElementById('total-power-card');
    refreshButtonEl = document.getElementById('refresh-button'); // Get the button

    // Check if button exists before adding listener
    if (refreshButtonEl) {
        refreshButtonEl.addEventListener('click', () => {
            console.log("Refresh button clicked!");
            loadData(); // Call loadData immediately
        });
    } else {
        console.warn("Refresh button element not found.");
    }

    // Initial load
    loadData();
    // Set interval for periodic refreshing
    setInterval(loadData, REFRESH_INTERVAL);
});
