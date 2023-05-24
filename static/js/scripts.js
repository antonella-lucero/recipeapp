// Event listener for the search form
document.getElementById('search-form').addEventListener('submit', async (event) => {
  event.preventDefault();

  const formData = new FormData(event.target);
  const ingredients = formData.get('ingredients');
  const response = await fetch('/search', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ingredients })
  });

  if (response.ok) {
      const data = await response.json();
      document.getElementById('recipe-results').innerHTML = data.search_results_html;
  } else {
      alert('Error: Unable to fetch search results');
  }
});


// Event listener for the save recipe buttons
document.addEventListener('click', async (event) => {
  if (event.target.classList.contains('save-recipe-button')) {
      const recipeId = event.target.dataset.recipeId;
      const title = event.target.dataset.title;
      const response = await fetch('/save_recipe', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify({ recipe_id: recipeId, title })
      });

      if (response.ok) {
          toggleSaveRecipeButton(event.target);
          alert('Recipe saved successfully!');
      } else {
          alert('Error: Unable to save the recipe');
      }
  }
});

// Function to toggle the save recipe button state
function toggleSaveRecipeButton(button) {
  button.disabled = !button.disabled;
  button.textContent = button.disabled ? 'Saved' : 'Save';
}
