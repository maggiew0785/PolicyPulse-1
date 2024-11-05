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

// Track selected themes
let selectedThemes = new Set();

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

// Create quotes container (initially hidden)
const quotesContainer = document.createElement('div');
quotesContainer.className = 'quotes-container hidden';
document.body.appendChild(quotesContainer);

// Create show quotes button (initially hidden)
const showQuotesButton = document.createElement('button');
showQuotesButton.className = 'show-quotes-button hidden';
showQuotesButton.textContent = 'Show Quotes for Selected Themes (0)';

function generateThemes(themes) {
    if (!themesContainer) {
        console.error('Themes container not found');
        return;
    }

    // Clear existing content
    themesContainer.innerHTML = '';
    selectedThemes.clear();
    quotesContainer.innerHTML = '';
    quotesContainer.classList.add('hidden');

    // Create a wrapper div for themes and button
    const themeWrapper = document.createElement('div');
    themeWrapper.className = 'theme-wrapper';

    // Create grid container for theme boxes
    const themeGrid = document.createElement('div');
    themeGrid.className = 'theme-grid';

    themes.forEach(theme => {
        const themeBox = document.createElement('div');
        themeBox.classList.add('theme-box');

        // Add checkbox container at the top right
        const headerContainer = document.createElement('div');
        headerContainer.classList.add('theme-header');
        
        const themeIcon = document.createElement('div');
        themeIcon.classList.add('theme-icon');
        themeIcon.innerHTML = '&#128101;';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('theme-checkbox');
        
        headerContainer.appendChild(themeIcon);
        headerContainer.appendChild(checkbox);

        const themeTitle = document.createElement('h2');
        themeTitle.textContent = theme.name;

        const themePercentage = document.createElement('div');
        themePercentage.classList.add('theme-percentage');
        themePercentage.textContent = theme.percentage;

        const themeDescription = document.createElement('p');
        themeDescription.textContent = theme.description;

        themeBox.appendChild(headerContainer);
        themeBox.appendChild(themeTitle);
        themeBox.appendChild(themePercentage);
        themeBox.appendChild(themeDescription);

        // Add click handlers
        const toggleTheme = () => {
            checkbox.checked = !checkbox.checked;
            if (checkbox.checked) {
                selectedThemes.add(theme.name);
                themeBox.classList.add('selected');
            } else {
                selectedThemes.delete(theme.name);
                themeBox.classList.remove('selected');
            }
            
            // Update show quotes button
            showQuotesButton.textContent = `Show Quotes for Selected Themes (${selectedThemes.size})`;
            showQuotesButton.classList.toggle('hidden', selectedThemes.size === 0);
            
            // Hide quotes container when no themes are selected
            if (selectedThemes.size === 0) {
                quotesContainer.classList.add('hidden');
            }
        };

        // Make the whole box clickable
        themeBox.addEventListener('click', (e) => {
            if (e.target !== checkbox) {
                toggleTheme();
            }
        });

        // Handle checkbox clicks separately
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            if (checkbox.checked) {
                selectedThemes.add(theme.name);
                themeBox.classList.add('selected');
            } else {
                selectedThemes.delete(theme.name);
                themeBox.classList.remove('selected');
            }
            
            showQuotesButton.textContent = `Show Quotes for Selected Themes (${selectedThemes.size})`;
            showQuotesButton.classList.toggle('hidden', selectedThemes.size === 0);
            
            if (selectedThemes.size === 0) {
                quotesContainer.classList.add('hidden');
            }
        });

        themeGrid.appendChild(themeBox);
    });

    // Add the grid to the wrapper
    themeWrapper.appendChild(themeGrid);
    themeWrapper.appendChild(showQuotesButton);
    themesContainer.appendChild(themeWrapper);
}

function displayQuotes(quotesData) {
    quotesContainer.innerHTML = '';
    
    // Create summary header
    const summaryHeader = document.createElement('div');
    summaryHeader.className = 'quotes-summary';
    summaryHeader.textContent = `Found ${quotesData.total_quotes} quotes across ${quotesData.themes.length} themes`;
    quotesContainer.appendChild(summaryHeader);

    // Create accordion for each theme
    Object.entries(quotesData.quotes_by_theme).forEach(([theme, quotes]) => {
        const themeSection = document.createElement('div');
        themeSection.className = 'theme-quotes-section';

        const themeHeader = document.createElement('div');
        themeHeader.className = 'theme-quotes-header';
        themeHeader.innerHTML = `
            <h3>${theme}</h3>
            <span class="quote-count">${quotes.length} quotes</span>
            <span class="expand-icon">▼</span>
        `;

        const quotesList = document.createElement('div');
        quotesList.className = 'quotes-list';

        quotes.forEach(quote => {
            const quoteBox = document.createElement('div');
            quoteBox.className = 'quote-box';
            
            const quoteText = document.createElement('p');
            quoteText.className = 'quote-text';
            quoteText.textContent = quote.text;
            
            const quoteMeta = document.createElement('div');
            quoteMeta.className = 'quote-metadata';
            quoteMeta.innerHTML = `
                <div class="quote-codes">
                    <strong>Codes:</strong> ${quote.codes.join(', ')}
                </div>
                <div class="quote-themes">
                    <strong>Themes:</strong> ${quote.themes.join(', ')}
                </div>
            `;
            
            quoteBox.appendChild(quoteText);
            quoteBox.appendChild(quoteMeta);
            quotesList.appendChild(quoteBox);
        });

        // Toggle expansion on header click
        themeHeader.addEventListener('click', () => {
            const isExpanded = themeSection.classList.toggle('expanded');
            themeHeader.querySelector('.expand-icon').textContent = isExpanded ? '▼' : '▶';
        });

        themeSection.appendChild(themeHeader);
        themeSection.appendChild(quotesList);
        quotesContainer.appendChild(themeSection);
    });

    quotesContainer.classList.remove('hidden');
}

// Add click handler for show quotes button
showQuotesButton.addEventListener('click', async () => {
    if (selectedThemes.size === 0) {
        alert('Please select at least one theme to view quotes');
        return;
    }

    try {
        showQuotesButton.disabled = true;
        showQuotesButton.textContent = 'Loading quotes...';
        
        const response = await fetch('/api/theme-quotes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                themes: Array.from(selectedThemes)
            })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch quotes');
        }

        const data = await response.json();
        if (data.status === 'success') {
            displayQuotes(data);
        } else {
            throw new Error(data.message || 'Failed to load quotes');
        }
        
    } catch (error) {
        console.error('Error fetching quotes:', error);
        alert('Failed to fetch quotes for selected themes');
    } finally {
        showQuotesButton.disabled = false;
        showQuotesButton.textContent = `Show Quotes for Selected Themes (${selectedThemes.size})`;
    }
});

// Add the necessary CSS
const style = document.createElement('style');
style.textContent = `
    .theme-wrapper {
        display: flex;
        flex-direction: column;
        gap: 20px;
        width: 100%;
        margin-bottom: 40px;
    }

    .theme-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
        width: 100%;
    }

    .theme-box {
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
        padding: 20px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background: white;
    }

    .theme-box.selected {
        border-color: #3b82f6;
        background-color: #eff6ff;
    }

    .theme-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .theme-checkbox {
        width: 20px;
        height: 20px;
        cursor: pointer;
    }

    .show-quotes-button {
        display: block;
        margin: 20px auto;
        padding: 10px 20px;
        background-color: #3b82f6;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .show-quotes-button:hover:not(:disabled) {
        background-color: #2563eb;
    }

    .show-quotes-button:disabled {
        background-color: #93c5fd;
        cursor: not-allowed;
    }

    .quotes-container {
        margin-top: 40px;
        padding: 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .quotes-summary {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e5e7eb;
    }

    .theme-quotes-section {
        margin-bottom: 20px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
    }

    .theme-quotes-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px 20px;
        background-color: #f8fafc;
        cursor: pointer;
        border-radius: 8px 8px 0 0;
    }

    .theme-quotes-header h3 {
        margin: 0;
        font-size: 1.1em;
    }

    .quote-count {
        color: #6b7280;
        font-size: 0.9em;
    }

    .expand-icon {
        font-size: 0.8em;
        color: #6b7280;
    }

    .quotes-list {
        display: none;
        padding: 20px;
    }

    .theme-quotes-section.expanded .quotes-list {
        display: block;
    }

    .quote-box {
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        background-color: #f9fafb;
    }

    .quote-text {
        margin: 0 0 10px 0;
        line-height: 1.5;
    }

    .quote-metadata {
        font-size: 0.9em;
        color: #6b7280;
    }

    .quote-codes, .quote-themes {
        margin-top: 5px;
    }

    .hidden {
        display: none;
    }
`;
document.head.appendChild(style);