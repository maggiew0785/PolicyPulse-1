// Get elements from the DOM
const searchForm = document.getElementById('searchForm');
const subredditButtonsContainer = document.getElementById('subredditButtonsContainer');
const subredditButtonsDiv = document.getElementById('subredditButtons');
const themeSection = document.getElementById('themeSection');
const themesContainer = document.getElementById('themesContainer');
const searchBar = document.querySelector('.search-bar');
const reportContainer = document.getElementById('reportContainer');
const reportContent = document.getElementById('reportContent');
const closeReportButton = document.getElementById('closeReportButton');

// Add loading indicator elements
const loadingIndicator = document.createElement('div');
loadingIndicator.className = 'loading-indicator hidden';
loadingIndicator.innerHTML = `
    <div class="loading-spinner"></div>
    <div class="loading-status">Processing data...</div>
    <div class="loading-progress">0%</div>
`;
document.body.appendChild(loadingIndicator);

// Status checking interval
let statusCheckInterval;

async function startProcessing() {
    try {
        const response = await fetch('/api/start-processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to start processing');
        }

        // Show loading indicator
        loadingIndicator.classList.remove('hidden');
        
        // Start checking status
        startStatusChecking();

    } catch (error) {
        console.error('Error starting processing:', error);
        alert('Failed to start data processing. Please try again.');
    }
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        // Update loading indicator
        const statusText = document.querySelector('.loading-status');
        const progressText = document.querySelector('.loading-progress');
        
        statusText.textContent = status.current_stage === 'reddit_quotes' 
            ? 'Collecting Reddit data...'
            : 'Generating themes...';
        progressText.textContent = `${status.progress}%`;

        if (!status.is_processing) {
            // Processing completed
            clearInterval(statusCheckInterval);
            loadingIndicator.classList.add('hidden');
            
            if (status.error) {
                alert('Processing failed: ' + status.error);
            } else {
                // Fetch and display results
                fetchAndDisplayResults();
            }
        }

    } catch (error) {
        console.error('Error checking status:', error);
        clearInterval(statusCheckInterval);
        loadingIndicator.classList.add('hidden');
        alert('Error checking processing status');
    }
}

function startStatusChecking() {
    // Check status every 2 seconds
    statusCheckInterval = setInterval(checkStatus, 2000);
}

async function fetchAndDisplayResults() {
    try {
        const response = await fetch('/api/results');
        if (!response.ok) {
            throw new Error('Failed to fetch results');
        }
        
        const data = await response.json();
        generateThemes(data.codes);
        
        // Show themes section
        themeSection.classList.remove('hidden');
        
    } catch (error) {
        console.error('Error fetching results:', error);
        alert('Failed to fetch analysis results');
    }
}

// Handle form submission
searchForm.addEventListener('submit', async function (event) {
    console.log("Go button clicked, search query is being processed...");
    event.preventDefault();

    const query = document.getElementById('searchQuery').value.trim();
    if (!query) {
        alert('Please enter a search term!');
        return;
    }

    // Clear out any existing buttons
    subredditButtonsDiv.innerHTML = '';

    try {
        const response = await fetch('/get_related_subreddits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ topic: query })
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch related subreddits');
        }

        const data = await response.json();
        console.log('Related Subreddits:', data.related_subreddits);

        // Create buttons for each subreddit
        data.related_subreddits.forEach(subreddit => {
            const button = document.createElement('button');
            button.textContent = subreddit;
            button.classList.add('subreddit-button');
            
            // When a subreddit is selected, start the processing
            button.addEventListener('click', async () => {
                console.log("Selected subreddit:", subreddit);
                await startProcessing();
            });
            
            subredditButtonsDiv.appendChild(button);
        });

        // Show the subreddit buttons container
        subredditButtonsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to fetch related subreddits. Please try again.');
    }
});

function generateThemes(themes) {
    themesContainer.innerHTML = '';

    themes.forEach(theme => {
        const themeBox = document.createElement('div');
        themeBox.classList.add('theme-box');

        const themeIcon = document.createElement('div');
        themeIcon.classList.add('theme-icon');
        themeIcon.innerHTML = '&#128101;';

        const themeTitle = document.createElement('h2');
        themeTitle.textContent = theme.name;

        const themePercentage = document.createElement('div');
        themePercentage.classList.add('theme-percentage');
        themePercentage.textContent = theme.percentage;

        const themeDescription = document.createElement('p');
        themeDescription.textContent = theme.description;

        themeBox.appendChild(themeIcon);
        themeBox.appendChild(themeTitle);
        themeBox.appendChild(themePercentage);
        themeBox.appendChild(themeDescription);

        themesContainer.appendChild(themeBox);
    });
}

// Add close report functionality
if (closeReportButton) {
    closeReportButton.addEventListener('click', () => {
        reportContainer.classList.add('hidden');
    });
}

// Add CSS for loading indicator
const style = document.createElement('style');
style.textContent = `
    .loading-indicator {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        z-index: 1000;
    }

    .loading-spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto 10px;
    }

    .loading-status {
        margin-bottom: 10px;
        font-weight: bold;
    }

    .loading-progress {
        color: #666;
    }

    .hidden {
        display: none;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
