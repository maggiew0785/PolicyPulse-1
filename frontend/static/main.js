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

// Get the Go button and input field
const searchButton = document.getElementById('searchButton');
const themeSearchInput = document.getElementById('themeSearch');

// Add an event listener to the Go button
searchButton.addEventListener('click', async function () {
    const themeTitle = themeSearchInput.value.trim();

    if (!themeTitle) {
        alert('Please enter a theme!');
        return;
    }

    console.log("Searching for theme:", themeTitle);

    // Show the loading indicator
    loadingIndicator.classList.remove('hidden');
    await startProcessing();
   
});


// Add loading indicator elements
const loadingIndicator = document.createElement('div');
loadingIndicator.className = 'loading-indicator hidden';
loadingIndicator.innerHTML = `
    <div class="loading-overlay"></div>
    <div class="loading-content">
        <div class="loading-spinner"></div>
        <div class="loading-status">Processing data...</div>
    </div>
`;
document.body.appendChild(loadingIndicator);


// Status checking interval
let statusCheckInterval;

// Add a flag to track if processing is already running
let isProcessing = false;

async function startProcessing() {
    if (isProcessing) {
        console.log('Processing already in progress, skipping new request');
        return;
    }

    try {
        isProcessing = true;
        loadingIndicator.classList.remove('hidden');

        const response = await fetch('/api/start-processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            // Add any required data in the body if needed
            body: JSON.stringify({
                // Add any parameters your backend expects
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to start processing: ${response.status} - ${errorText}`);
        }

        // Start checking status
        startStatusChecking();

    } catch (error) {
        console.error('Error starting processing:', error);
        loadingIndicator.classList.add('hidden');
        alert('Failed to start data processing. Please try again.');
    } finally {
        isProcessing = false;
    }
}

function generateThemes(themeData) {
    themesContainer.innerHTML = ''; 
    
    console.log('Generating themes with data:', themeData);

    themeData.forEach(theme => {
        const themeBox = document.createElement('div');
        themeBox.classList.add('theme-box');

        const themeIcon = document.createElement('div');
        themeIcon.classList.add('theme-icon');
        themeIcon.innerHTML = '&#128101;';

        const themeTitle = document.createElement('h2');
        themeTitle.textContent = theme.title || theme.name;

        const themeDescription = document.createElement('p');
        themeDescription.textContent = theme.description;

        themeBox.appendChild(themeIcon);
        themeBox.appendChild(themeTitle);
        themeBox.appendChild(themeDescription);

        // Store the theme data for later use
        themeBox.addEventListener('click', async () => {
            console.log("Theme box clicked:", theme.title || theme.name);
            // Store the clicked theme title globally
            window.clickedThemeTitle = theme.title || theme.name;
            await startProcessing();
        });

        themesContainer.appendChild(themeBox);
    });
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        
        const statusData = await response.json();

        // Update loading indicator
        const statusText = document.querySelector('.loading-status');
        if (statusData.current_stage) {
            statusText.textContent = statusData.current_stage === 'reddit_quotes' 
                ? 'Collecting Reddit data...'
                : 'Generating themes...';
        }

        if (!statusData.is_processing) {
            clearInterval(statusCheckInterval);
            loadingIndicator.classList.add('hidden');
            isProcessing = false;
            
            if (statusData.error) {
                console.error('Processing error:', statusData.error);
                alert('Processing failed: ' + statusData.error);
            } else {
                console.log("Processing complete, generating report for:", window.clickedThemeTitle);
                await generateReport(window.clickedThemeTitle);
            }
        }

    } catch (error) {
        console.error('Error checking status:', error);
        clearInterval(statusCheckInterval);
        loadingIndicator.classList.add('hidden');
        isProcessing = false;
    }
}

function startStatusChecking() {
    // Check status every 2 seconds
    statusCheckInterval = setInterval(checkStatus, 2000);
}

// Remove the automatic report generation from fetchAndDisplayResults
async function fetchAndDisplayResults() {
    try {
        const response = await fetch('/api/results');
        if (!response.ok) {
            throw new Error('Failed to fetch results');
        }
        
        const data = await response.json();
        // Only update the report if we're actually showing it
        if (!reportContainer.classList.contains('hidden')) {
            generateReport(data.codes);
        }
        
    } catch (error) {
        console.error('Error fetching results:', error);
        alert('Failed to fetch analysis results');
    }
}

// Get form element
searchForm.addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent form from submitting normally
    
    console.log("Form submitted");
    
    const query = document.getElementById('searchQuery').value.trim();
    console.log("Search query:", query);
    
    if (!query) {
        alert('Please enter a search term!');
        return;
    }

    try {
        const response = await fetch('/get_related_subreddits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ topic: query })
        });

        console.log("Response status:", response.status);
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        console.log("Received data:", data);

        // Clear existing buttons
        subredditButtonsDiv.innerHTML = '';

        // Create buttons for each subreddit
        data.related_subreddits.forEach(subreddit => {
            const button = document.createElement('button');
            button.textContent = subreddit;
            button.classList.add('subreddit-button');
            
            button.addEventListener('click', async () => {
                console.log(`Clicked subreddit: ${subreddit}`);
                console.log("Fetching themes for selected subreddit:", subreddit);
            
                // Show the loading indicator
                loadingIndicator.classList.remove('hidden');
            
                // Clean the subreddit name by removing 'r/' prefix if present
                const cleanedSubreddit = subreddit.trim().replace(/^r\//, '');
                try {
                    const themeResponse = await fetch(`/get_themes/${cleanedSubreddit}`);
            
                    if (!themeResponse.ok) {
                        throw new Error('Failed to retrieve themes');
                    }
            
                    const themeData = await themeResponse.json();
                    console.log('Received theme data:', themeData);
            
                    // Make sure themeSection is visible
                    themeSection.classList.remove('hidden');
            
                    // Generate theme boxes with the fetched theme data
                    generateThemes(themeData);
            
                    // Move the theme search bar below the themes
                    themesContainer.after(searchBar);
                    searchBar.classList.remove('hidden');
            
                } catch (error) {
                    console.error('Error fetching themes:', error);
                    alert('Failed to fetch themes. Please try again.');
                } finally {
                    // Hide the loading indicator once themes are displayed
                    loadingIndicator.classList.add('hidden');
                }
            });

            subredditButtonsDiv.appendChild(button); // Add button to the container
        }); // <-- Missing closing parenthesis for forEach

        // Show the container
        subredditButtonsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to fetch related subreddits');
    }
});

const themeStyles = document.createElement('style');
themeStyles.textContent = `
    .theme-box {
        border: 1px solid #ccc;
        padding: 15px;
        margin: 10px;
        border-radius: 8px;
        cursor: pointer;
        background-color: white;
        transition: transform 0.2s, box-shadow 0.2s;
        min-width: 200px;
    }

    .theme-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    .theme-icon {
        font-size: 24px;
        margin-bottom: 10px;
    }

    #themesContainer {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        padding: 20px;
        justify-content: center;
    }

    .theme-box h2 {
        margin: 10px 0;
        font-size: 18px;
    }

    .theme-box p {
        margin: 0;
        color: #666;
    }
`;
document.head.appendChild(themeStyles);

// Add close report functionality
if (closeReportButton) {
    closeReportButton.addEventListener('click', () => {
        reportContainer.classList.add('hidden');
    });
}

// Add CSS for loading indicator
const loadingStyles = document.createElement('style');
loadingStyles.textContent = `
    .loading-indicator {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }

    .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
    }

    .loading-content {
        position: relative;
        background: white;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }

    .loading-spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto 15px;
    }

    .loading-status {
        margin-bottom: 10px;
        font-weight: bold;
        color: #333;
    }

    .loading-progress {
        color: #666;
    }

    .hidden {
        display: none !important;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(loadingStyles);

async function generateReport(themeTitle) {
    try {
        console.log("Generating report for theme:", themeTitle);
        const response = await fetch('/api/results');
        if (!response.ok) {
            throw new Error('Failed to fetch results');
        }
        
        const data = await response.json();
        console.log("Got results data:", data);
        
        // Create report content
        reportContent.innerHTML = `
            <div class="report-header">
                <h2>${themeTitle}</h2>
                <div class="stats">
                    <div class="total-posts">
                        <span class="percentage">${data.total_posts || calculateTotalPosts(data.codes)}</span>
                        <span>Posts</span>
                    </div>
                </div>
            </div>
           <div class="subtopics">
            ${data.codes.map(code => `
                <div class="subtopic-item" data-subtopic="${code.name}">
                    <div class="subtopic-header">
                        <div class="posts-count">
                            ${code.percentage} posts
                        </div>
                        <h3>${code.name}</h3>
                        <div class="expand-container">
                            <span class="see-real-quotes">See real quotes</span>
                            <button class="expand-button" 
                                    onclick="toggleQuotes(this)" 
                                    data-subtopic="${code.name}">▼</button>
                        </div>
                    </div>
                    <p class="description">${code.description}</p>
                    <div class="quotes-container hidden">
                        Loading quotes...
                    </div>
                </div>
            `).join('')}
        </div>
        <button id="downloadReport" class="download-button">Download Report</button>
        `;

        // Show the report container
        reportContainer.classList.remove('hidden');
        console.log("Report container should now be visible");

        // Add an event listener for the download button
        const downloadButton = document.getElementById('downloadReport');
        downloadButton.addEventListener('click', () => downloadReportAsJSON(data, themeTitle));

    } catch (error) {
        console.error('Error generating report:', error);
        alert('Failed to generate report. Please try again.');
    }
}
function downloadReportAsJSON(data, themeTitle) {
    // Create a JSON string from the data
    const jsonString = JSON.stringify(data, null, 2);

    // Create a Blob from the JSON string
    const blob = new Blob([jsonString], { type: 'application/json' });

    // Create a link element
    const link = document.createElement('a');

    // Set the download URL and filename
    link.href = URL.createObjectURL(blob);
    link.download = `${themeTitle.replace(/\s+/g, '_')}_Report.json`;

    // Append the link to the document body
    document.body.appendChild(link);

    // Trigger the download
    link.click();

    // Remove the link element from the document
    document.body.removeChild(link);
}


// Helper function to calculate total posts
function calculateTotalPosts(codes) {
    return codes.reduce((total, code) => {
        const [count] = code.percentage.split('/');
        return total + parseInt(count);
    }, 0);
}

// Add the styles to the document
// const style = document.createElement(reportStyles);
// style.textContent += reportStyles;
// document.head.appendChild(style);

/// Function to toggle quotes visibility and load them if needed
async function toggleQuotes(button) {
    const quotesContainer = button.closest('.subtopic-item').querySelector('.quotes-container');
    const subtopicName = button.closest('.subtopic-item').querySelector('h3').textContent;

    if (quotesContainer.classList.contains('hidden')) {
        // Load quotes if not already loaded
        if (!quotesContainer.dataset.loaded) {
            try {
                const response = await fetch(`/api/quotes/${encodeURIComponent(subtopicName)}`);
                if (!response.ok) throw new Error(`Failed to fetch quotes: ${response.status}`);

                const quotes = await response.json();
                quotesContainer.dataset.loaded = true;
                quotesContainer.dataset.currentIndex = 3; // Start with 3 quotes

                // Display initial 3 quotes
                quotesContainer.innerHTML = quotes.slice(0, 3).map(quote => `
                    <div class="quote">
                        <p>${quote.text}</p>
                        <div class="quote-meta">
                            <span class="subreddit">r/${quote.subreddit}</span>
                            <span class="score">↑ ${quote.score}</span>
                        </div>
                    </div>
                `).join('');

                // Add "Show More" button for pagination
                const showMoreButton = document.createElement('button');
                showMoreButton.textContent = 'Show More Quotes';
                showMoreButton.classList.add('show-more-button');
                showMoreButton.onclick = () => showMoreQuotes(quotes, quotesContainer);
                quotesContainer.appendChild(showMoreButton);

                // Add "Show Less" button
                const showLessButton = document.createElement('button');
                showLessButton.textContent = 'Show Less Quotes';
                showLessButton.classList.add('show-less-button');
                showLessButton.onclick = () => showLessQuotes(quotesContainer);
                showLessButton.style.display = 'none'; // Hide initially
                quotesContainer.appendChild(showLessButton);
            } catch (error) {
                quotesContainer.innerHTML = `Failed to load quotes: ${error.message}`;
            }
        }

        quotesContainer.classList.remove('hidden');
        button.textContent = '▲';
    } else {
        quotesContainer.classList.add('hidden');
        button.textContent = '▼';
    }
}

// Function to show more quotes (persistent Show More button at bottom)
function showMoreQuotes(quotes, quotesContainer) {
    const currentIndex = parseInt(quotesContainer.dataset.currentIndex);
    const nextIndex = currentIndex + 5;

    // Append 5 more quotes or as many as remain above the button
    const showMoreButton = quotesContainer.querySelector('.show-more-button');
    showMoreButton.insertAdjacentHTML('beforebegin', quotes.slice(currentIndex, nextIndex).map(quote => `
        <div class="quote">
            <p>${quote.text}</p>
            <div class="quote-meta">
                <span class="subreddit">r/${quote.subreddit}</span>
                <span class="score">↑ ${quote.score}</span>
            </div>
        </div>
    `).join(''));

    // Update the current index
    quotesContainer.dataset.currentIndex = nextIndex;

    // Show the "Show Less" button if hidden
    const showLessButton = quotesContainer.querySelector('.show-less-button');
    showLessButton.style.display = 'inline-block';

    // Disable "Show More" button if there are no more quotes to show
    if (nextIndex >= quotes.length) {
        showMoreButton.disabled = true;
        showMoreButton.textContent = 'No more quotes';
    }
}

// Function to show less quotes (remove the last batch displayed)
function showLessQuotes(quotesContainer) {
    const currentIndex = parseInt(quotesContainer.dataset.currentIndex);
    const newIndex = Math.max(currentIndex - 5, 3); // Ensure at least the initial 3 quotes remain

    // Remove the last batch of quotes
    const quotesToRemove = Array.from(quotesContainer.querySelectorAll('.quote')).slice(newIndex, currentIndex);
    quotesToRemove.forEach(quoteElement => quoteElement.remove());

    // Update the current index
    quotesContainer.dataset.currentIndex = newIndex;

    // Hide the "Show Less" button if only the initial quotes are visible
    if (newIndex <= 3) {
        const showLessButton = quotesContainer.querySelector('.show-less-button');
        showLessButton.style.display = 'none';
    }

    // Enable "Show More" button if it was disabled
    const showMoreButton = quotesContainer.querySelector('.show-more-button');
    showMoreButton.disabled = false;
    showMoreButton.textContent = 'Show More Quotes';
}
