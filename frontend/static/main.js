// Get elements from the DOM
const searchForm = document.getElementById('searchForm');
const subredditButtonsContainer = document.getElementById('subredditButtonsContainer');
const subredditButtonsDiv = document.getElementById('subredditButtons');

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
    // Here, you can modify this to create specific buttons based on the input
    const relatedSubreddits = [`r/${query}`, `r/${query}news`, `r/${query}tech`]; // Example subreddit generation

    // Dynamically create subreddit buttons
    relatedSubreddits.forEach(subreddit => {
        const button = document.createElement('button');
        button.textContent = subreddit;
        button.classList.add('subreddit-button');

        // Add click event listener for each button
        button.addEventListener('click', function () {
            // Fetch subreddit data from the server (you can modify the URL logic)
            fetch(`/subreddit/${subreddit.replace('r/', '')}`)
                .then(response => response.json())
                .then(data => {
                    console.log(data.message); // Process the data returned from Flask
                    alert(data.message); // Optionally display it
                })
                .catch(error => console.error('Error:', error));
        });

        subredditButtonsDiv.appendChild(button);
    });

    // Show the container with the subreddit buttons
    subredditButtonsContainer.classList.remove('hidden');
});
