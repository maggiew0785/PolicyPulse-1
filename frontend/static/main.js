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
    <div class="loading-overlay"></div>
    <div class="loading-content">
        <div class="loading-spinner"></div>
        <div class="loading-status">Processing data...</div>
        <div class="loading-progress">0%</div>
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

// async function checkStatus() {
//     try {
//         const response = await fetch('/api/status');
//         const status = await response.json();

//         // Update loading indicator
//         const statusText = document.querySelector('.loading-status');
//         const progressText = document.querySelector('.loading-progress');
        
//         statusText.textContent = status.current_stage === 'reddit_quotes' 
//             ? 'Collecting Reddit data...'
//             : 'Generating themes...';
//         progressText.textContent = `${status.progress}%`;

//         if (!status.is_processing) {
//             // Processing completed
//             clearInterval(statusCheckInterval);
//             loadingIndicator.classList.add('hidden');
            
//             if (status.error) {
//                 alert('Processing failed: ' + status.error);
//             } else {
//                 // Fetch and display results
//                 fetchAndDisplayResults();
//             }
//         }

//     } catch (error) {
//         console.error('Error checking status:', error);
//         clearInterval(statusCheckInterval);
//         loadingIndicator.classList.add('hidden');
//         alert('Error checking processing status');
//     }
// }

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        
        const statusData = await response.json();

        // Update loading indicator
        const statusText = document.querySelector('.loading-status');
        const progressText = document.querySelector('.loading-progress');
        
        if (statusData.current_stage) {
            statusText.textContent = statusData.current_stage === 'reddit_quotes' 
                ? 'Collecting Reddit data...'
                : 'Generating themes...';
            progressText.textContent = `${statusData.progress}%`;
        }

        if (!statusData.is_processing) {
            clearInterval(statusCheckInterval);
            loadingIndicator.classList.add('hidden');
            isProcessing = false;
            
            if (statusData.error) {
                console.error('Processing error:', statusData.error);
                alert('Processing failed: ' + statusData.error);
            } else {
                // Now directly call generateReport with the stored theme title
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
    
                // Clean the subreddit name by removing 'r/' prefix if present
                const cleanedSubreddit = subreddit.trim().replace(/^r\//, '');
                try {
                    const themeResponse = await fetch(`/get_themes/${cleanedSubreddit}`);
            
                    if (!themeResponse.ok) {
                        throw new Error('Failed to retrieve themes');
                    }
                    
                    const themeData = await themeResponse.json();
                    console.log('Received theme data:', themeData); // Debug log
                    
                    // Make sure themeSection is visible
                    themeSection.classList.remove('hidden');
                    
                    // Generate theme boxes with the fetched theme data
                    generateThemes(themeData);
                    
                    // Move the theme search bar below the themes
                    themesContainer.after(searchBar);
                    searchBar.classList.remove('hidden'); // Ensure search bar is visible
            
                } catch (error) {
                    console.error('Error fetching themes:', error);
                    alert('Failed to fetch themes. Please try again.');
                }            });
            
            subredditButtonsDiv.appendChild(button);
        });

        // Show the container
        subredditButtonsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to fetch related subreddits');
    }
});

// function generateThemes(themeData) {
//     themesContainer.innerHTML = ''; // Clear previous themes
    
//     console.log('Generating themes with data:', themeData); // Add this debug log

//     themeData.forEach((theme, index) => { // Added index for debugging
//         console.log(`Creating theme box ${index}:`, theme); // Debug each theme

//         const themeBox = document.createElement('div');
//         themeBox.classList.add('theme-box');

//         const themeIcon = document.createElement('div');
//         themeIcon.classList.add('theme-icon');
//         themeIcon.innerHTML = '&#128101;';  // People icon

//         const themeTitle = document.createElement('h2');
//         themeTitle.textContent = theme.title || theme.name; // Try both title or name

//         const themeDescription = document.createElement('p');
//         themeDescription.textContent = theme.description;

//         themeBox.appendChild(themeIcon);
//         themeBox.appendChild(themeTitle);
//         themeBox.appendChild(themeDescription);

//         // Add a click event listener with debugging
//         themeBox.addEventListener('click', () => {
//             console.log('Theme box clicked!');
//             console.log('Clicked theme data:', theme);
            
//             // Start processing regardless of theme.report
//             startProcessing();
//             generateReport(theme.name || theme.title); // Pass the theme name/title
//         });

//         // Add some visual feedback for clickability
//         themeBox.style.cursor = 'pointer';
        
//         themesContainer.appendChild(themeBox);
//     });

//     // Verify themes were added
//     console.log('Total theme boxes created:', themesContainer.children.length);
// }

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
                            <button class="expand-button" 
                                    onclick="toggleQuotes(this)" 
                                    data-subtopic="${code.name}">▼</button>
                        </div>
                        <p class="description">${code.description}</p>
                        <div class="quotes-container hidden">
                            Loading quotes...
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Show the report container
        reportContainer.classList.remove('hidden');
        console.log("Report container should now be visible");

    } catch (error) {
        console.error('Error generating report:', error);
        alert('Failed to generate report. Please try again.');
    }
}

// Helper function to calculate total posts
function calculateTotalPosts(codes) {
    return codes.reduce((total, code) => {
        const [count] = code.percentage.split('/');
        return total + parseInt(count);
    }, 0);
}

// Function to toggle quotes visibility and load them if needed
async function toggleQuotes(button) {
    const quotesContainer = button.closest('.subtopic-item').querySelector('.quotes-container');
    const subtopicName = button.closest('.subtopic-item').querySelector('h3').textContent;
    
    console.log("Toggling quotes for subtopic:", subtopicName); // Add this log

    if (quotesContainer.classList.contains('hidden')) {
        // Load quotes if not already loaded
        if (quotesContainer.textContent.trim() === 'Loading quotes...') {
            try {
                console.log("Fetching quotes from:", `/api/quotes/${encodeURIComponent(subtopicName)}`); // Add this log
                const response = await fetch(`/api/quotes/${encodeURIComponent(subtopicName)}`);
                console.log("Quote response status:", response.status); // Add this log
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch quotes: ${response.status}`);
                }
                
                const quotes = await response.json();
                console.log("Received quotes:", quotes); // Add this log

                if (quotes.length === 0) {
                    quotesContainer.innerHTML = 'No quotes found for this subtopic.';
                } else {
                    quotesContainer.innerHTML = quotes.map(quote => `
                        <div class="quote">
                            <p>${quote.text}</p>
                            <div class="quote-meta">
                                <span class="subreddit">r/${quote.subreddit}</span>
                                <span class="score">↑ ${quote.score}</span>
                            </div>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Error loading quotes:', error);
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
// Add CSS for the report
const reportStyles = document.createElement('style');
reportStyles.textContent = `
    .report-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        background: #f5f5f5;
        border-bottom: 1px solid #ddd;
    }

    .stats {
        text-align: center;
    }

    .total-posts {
        display: flex;
        flex-direction: column;
    }

    .percentage {
        font-size: 24px;
        font-weight: bold;
    }

    .subtopic-item {
        margin: 15px;
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 8px;
    }

    .subtopic-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .posts-count {
        color: #666;
        font-size: 14px;
    }

    .expand-button {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 18px;
    }

    .quotes-container {
        margin-top: 10px;
        padding: 10px;
        background: #f9f9f9;
    }

    .quote {
        padding: 10px;
        margin: 10px 0;
        border-left: 3px solid #007bff;
        background: white;
    }

    .quote-meta {
        margin-top: 5px;
        font-size: 12px;
        color: #666;
    }

    .hidden {
        display: none;
    }
`;

// Add the styles to the document
const style = document.createElement(reportStyles);
style.textContent += reportStyles;
document.head.appendChild(style);