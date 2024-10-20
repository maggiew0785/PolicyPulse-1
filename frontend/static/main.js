// Get elements from the DOM
const searchForm = document.getElementById('searchForm');
const subredditButtonsContainer = document.getElementById('subredditButtonsContainer');
const subredditButtonsDiv = document.getElementById('subredditButtons');
const themeSection = document.getElementById('themeSection'); // Get the theme section
const themesContainer = document.getElementById('themesContainer');
const searchBar = document.querySelector('.search-bar'); // Get the search bar for themes

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

// Handle form submission
searchForm.addEventListener('submit', function (event) {
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
    const relatedSubreddits = [`r/${query}`, `r/${query}news`, `r/${query}tech`]; // Example subreddit generation

    // Dynamically create subreddit buttons
    relatedSubreddits.forEach(subreddit => {
        const button = document.createElement('button');
        button.textContent = subreddit;
        button.classList.add('subreddit-button');

        // Add click event listener for each button
        button.addEventListener('click', function () {
            console.log(`You selected subreddit ${subreddit}`);

            // Show the theme section and generate the theme boxes
            themeSection.classList.remove('hidden');
            generateThemes();

            // Move the theme search bar below the themes after themes are displayed
            themesContainer.after(searchBar);
            searchBar.classList.remove('hidden'); // Ensure search bar is visible
        });

        subredditButtonsDiv.appendChild(button);
    });

    // Show the subreddit buttons container
    subredditButtonsContainer.classList.remove('hidden');
});

// Function to generate theme boxes when subreddit is clicked
function generateThemes() {
    // Clear out the themes container in case there are old themes
    themesContainer.innerHTML = '';

    // Dynamically create theme boxes based on placeholder data
    themes.forEach(theme => {
        // Create the theme box div
        const themeBox = document.createElement('div');
        themeBox.classList.add('theme-box');

        // Create the percentage element
        const themePercentage = document.createElement('div');
        themePercentage.classList.add('theme-percentage');
        themePercentage.textContent = theme.percentage;

        // Create the icon element (replace with an actual icon if needed)
        const themeIcon = document.createElement('div');
        themeIcon.classList.add('theme-icon');
        themeIcon.innerHTML = '&#128101;';  // People icon

        // Create the title
        const themeTitle = document.createElement('h2');
        themeTitle.textContent = theme.title;

        // Create the description
        const themeDescription = document.createElement('p');
        themeDescription.textContent = theme.description;

        // Append elements to the theme box
        themeBox.appendChild(themePercentage);
        themeBox.appendChild(themeIcon);
        themeBox.appendChild(themeTitle);
        themeBox.appendChild(themeDescription);

        // Append theme box to the container
        themesContainer.appendChild(themeBox);
    });
}
