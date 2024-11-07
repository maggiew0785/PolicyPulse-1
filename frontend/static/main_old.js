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

// Example placeholder themes data
const themes = [
    {
        title: 'Noise Complaints',
        percentage: '20%',
        description: '“Just try living with the noise of a restaurant in front of your window”'
    },
    {
        title: 'Sidewalk Space',
        percentage: '15%',
        description: '“I don’t mind the sidewalk dining if they leave enough space for pedestrians”'
    },
    {
        title: 'Business Restrictions',
        percentage: '15%',
        description: '“The financial burden we’re putting on small businesses feels unnecessary”'
    }
];

const reportData = {
    title: "Noise Complaints",
    percentage: "20%",
    postsCount: "898",
    description: "Just try living with the noise of a restaurant in front of your window.",
    items: [
        {
            count: 354,
            title: "Noise Ordinance Regulations",
            description: "Policies governing acceptable noise levels and hours during which outdoor seating areas must comply...",
            details: "More information on noise ordinance regulations and community responses."
        },
        {
            count: 255,
            title: "Permitting and Zoning Requirements",
            description: "Local regulations that determine where outdoor seating can be established...",
            details: "Details about zoning requirements and noise mitigation measures."
        },
        // Add more items as needed
    ]
};

// Handle form submission
searchForm.addEventListener('submit', async function (event){
    console.log("Go button clicked, search query is being processed...");
    event.preventDefault(); // Prevent the form from refreshing the page

    // Get the search query from the input field
    const query = document.getElementById('searchQuery').value.trim();

    // If the input is empty, do nothing
    if (!query) {
        alert('Please enter a search term!');
        return;
    }

    // Clear out any existing buttons
    subredditButtonsDiv.innerHTML = '';

    // Create some buttons based on the query (this is a placeholder logic)
    try {
        const response = await fetch('/get_related_subreddits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ topic: query })
        });
        
        // Parse the JSON response from the server
        const data = await response.json();
        const relatedSubreddits = data.related_subreddits;
        console.log('Related Subreddits:', relatedSubreddits);

    // Dynamically create subreddit buttons
        relatedSubreddits.forEach(subreddit => {
            const button = document.createElement('button');
            button.textContent = subreddit;
            button.classList.add('subreddit-button');

            // Add click event listener for each button
            button.addEventListener('click', async function () {
                console.log("Button clicked for subreddit:", subreddit);
                // Show the theme section
                themeSection.classList.remove('hidden');

                // Fetch themes based on the selected subreddit
                try {
                    const cleanedSubreddit = subreddit.trim().replace(/^r\//, ''); // Clean subreddit name
                    // alert("Fetching themes from: " + `/get_themes/${subreddit}`); // Log the URL
                    // alert("Fetching themes from: " + `/get_themes/${cleanedSubreddit}`); // Log the URL

                    // Fetch themes based on the selected subreddit
                    const themeResponse = await fetch(`/get_themes/${cleanedSubreddit}`, {
                        method: 'GET',  // Method is GET for this request
                        headers: {
                            'Content-Type': 'application/json' // Optional for GET, but can be included
                        }
                    });  

                    alert(themeResponse)

                    if (!themeResponse.ok) {
                        throw new Error('Failed to retrieve themes');
                    }
                    const themeData = await themeResponse.json();

                    // Generate theme boxes with the fetched theme data
                    generateThemes(themeData);

                    // Move the theme search bar below the themes after themes are displayed
                    themesContainer.after(searchBar);
                    searchBar.classList.remove('hidden'); // Ensure search bar is visible
                } catch (error) {
                    console.error('Error fetching themes:', error);
                    alert('Failed to retrieve themes. Please tryy again.');
                }
            });

            subredditButtonsDiv.appendChild(button);
            console.log('Button created for subreddit:', subreddit);

        });

        // Show the subreddit buttons container
        subredditButtonsContainer.classList.remove('hidden');
    } catch (error) {
        console.error('Error fetching related subreddits:', error);
        alert('Failed to retrieve related subreddits. Please try again.')
    }
});

function generateThemes(themeData) {
    themesContainer.innerHTML = ''; // Clear previous themes

    themeData.forEach(theme => {
        const themeBox = document.createElement('div');
        themeBox.classList.add('theme-box');

        // const themePercentage = document.createElement('div');
        // themePercentage.classList.add('theme-percentage');
        // themePercentage.textContent = theme.percentage;

        const themeIcon = document.createElement('div');
        themeIcon.classList.add('theme-icon');
        themeIcon.innerHTML = '&#128101;';  // People icon

        const themeTitle = document.createElement('h2');
        themeTitle.textContent = theme.title;

        const themeDescription = document.createElement('p');
        themeDescription.textContent = theme.description;

        // themeBox.appendChild(themePercentage);
        themeBox.appendChild(themeIcon);
        themeBox.appendChild(themeTitle);
        themeBox.appendChild(themeDescription);

        // Add click event listener to display report when theme is clicked
        themeBox.addEventListener('click', () => generateReport(reportData));

        themesContainer.appendChild(themeBox);
    });
}


function generateReport(data) {
    console.log("Generating report...");
    
    reportContent.innerHTML = ''; // Clear previous content in reportContent

    // Populate report content
    const reportHeader = document.createElement('div');
    reportHeader.classList.add('report-header');
    reportHeader.innerHTML = `
        <div class="report-percentage">${data.percentage}</div>
        <div class="report-posts">${data.postsCount} Posts</div>
        <div class="report-icon">&#128101;</div>
        <h2 class="report-title">${data.title}</h2>
        <p class="report-description">"${data.description}"</p>
    `;

    // Create items container
    const reportItems = document.createElement('div');
    reportItems.classList.add('report-items');

    data.items.forEach(item => {
        const reportItem = document.createElement('div');
        reportItem.classList.add('report-item');
        
        reportItem.innerHTML = `
            <span class="item-count">${item.count} posts</span>
            <span class="item-title">${item.title}:</span>
            <span class="item-description">${item.description}</span>
            <button class="toggle-details">&#x25BC;</button>
        `;

        const itemDetails = document.createElement('div');
        itemDetails.classList.add('item-details', 'hidden');
        itemDetails.innerHTML = `<p>${item.details}</p>`;

        const toggleButton = reportItem.querySelector('.toggle-details');
        toggleButton.addEventListener('click', () => {
            itemDetails.classList.toggle('hidden');
            toggleButton.innerHTML = itemDetails.classList.contains('hidden') ? '&#x25BC;' : '&#x25B2;';
        });

        reportItem.appendChild(itemDetails);
        reportItems.appendChild(reportItem);
    });
    closeReportButton.addEventListener('click', () => {
        reportContainer.classList.add('hidden'); // Hide the report container on close
    });

    reportContent.appendChild(reportHeader);
    reportContent.appendChild(reportItems);

    // Show the report container
    reportContainer.classList.remove('hidden');
}