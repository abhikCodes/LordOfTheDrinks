// frontend/script.js

document.getElementById('pair-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = document.getElementById('food-query').value.trim();
    if (!query) return;
    
    toggleVisibility('loading', true);
    toggleVisibility('error', false);
    toggleVisibility('results', false);
  
    try {
      const res = await fetch('/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ food_query: query })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      displayResults(data);
    } catch (err) {
      showError(err.message);
    } finally {
      toggleVisibility('loading', false);
    }
  });
  
  function displayResults({ food, drinks, explanation }) {
    document.getElementById('food-details').innerHTML =
      `<h3>${food.title} <small>(${food.cuisine})</small></h3>`;
  
    // Render the Markdown into HTML
    document.getElementById('explanation').innerHTML =
      marked.parse(explanation);
  
    const container = document.getElementById('drinks-list');
    container.innerHTML = '';
    drinks.forEach(d => {
      const card = document.createElement('div');
      card.className = 'card drink-card';
      card.innerHTML = `
        <h4>${d.name} <small>(${d.drink_type})</small></h4>
        <button class="btn-toggle">View Recipe</button>
        <div class="details">
          <p><strong>Instructions:</strong> ${d.instructions}</p>
          <p><strong>Ingredients:</strong> ${d.ingredients.join(', ')}</p>
        </div>`;
      card.querySelector('.btn-toggle')
          .addEventListener('click', () => {
            const det = card.querySelector('.details');
            det.style.display = det.style.display === 'block' ? 'none' : 'block';
          });
      container.appendChild(card);
    });
  
    toggleVisibility('results', true);
  }
  
  function showError(msg) {
    const e = document.getElementById('error');
    e.textContent = msg;
    toggleVisibility('error', true);
  }
  
  function toggleVisibility(id, show) {
    document.getElementById(id).hidden = !show;
  }
  