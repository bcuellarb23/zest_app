document.addEventListener('DOMContentLoaded' , async() => {

    const userNameDiv = document.querySelector('.user-name');
    

    
        async function fetchUserName() {
        try {
            const response = await fetch(`${API_BASE_URL}/get_info`, {
                credentials: 'include'
            });
            const data = await response.json();

            if (data.status === 'success' && userNameDiv) {
                // User is logged in, display their name
                userNameDiv.textContent = data.user_name;
                if (data.profile_pic) {
                  document.getElementById('profile-display').src = data.profile_pic;
                }
            } else {
                // User is NOT logged in, display "Guest" and make it a clickable link
                console.error('Failed to retrieve username:', data.message);
                userNameDiv.textContent = "Guest";
                userNameDiv.style.cursor = "pointer";

                // Add the click event listener ONLY if the user is a guest
                userNameDiv.addEventListener('click', () => {
                    window.location.href = '/login';
                });
            }
        } catch (error) {
            console.error('Error fetching user name:', error);
            
            // Handle network or server errors by treating the user as a guest
            userNameDiv.textContent = "Guest";
            userNameDiv.style.cursor = "pointer";
            userNameDiv.addEventListener('click', () => {
                window.location.href = '/login';
            });
        }
    }

    function setDates() {
        // Get the current date
        const today = new Date();
	const dayName = today.toLocaleDateString('en-US', { weekday: 'long' });
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0'); // Months are 0-based
        const day = String(today.getDate()).padStart(2, '0');
        
        const formattedDate = `${month}/${day}/${year}`;
        document.getElementById('today-date').textContent = `${dayName}, ${formattedDate}`;
    }

    async function fetchDailyTotals() {
        try {
            const response = await fetch(`${API_BASE_URL}/get_daily_totals`, {
                credentials: 'include'
            });
            const result = await response.json();

            if (result.status === 'success') {
                const data = result.data;
                
                
                // Update each macro progress bar and percentage
                updateProgress('calories', data.consumed.calories, data.tdee);
                updateProgress('protein', data.consumed.proteins, data.proteins_goal);
                updateProgress('carb', data.consumed.carbs, data.carbs_goal);
                updateProgress('fat', data.consumed.fats || 0, data.fats_goal); 
            } else {
                console.error(result.message);
            }
        } catch (error) {
            console.error('Error fetching daily totals:', error);
        }
    }

    async function addFoodEntry(foodData) {
        try { 
            const saveResponse = await fetch(`${API_BASE_URL}/add_food`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(foodData),
                credentials: 'include'
            });
            const saveResult = await saveResponse.json();
            
            if (saveResponse.ok) {
                alert('Food added successfully!');
                fetchDailyTotals(); // Re-fetch totals after adding food
            } else {
                alert(`Error: ${saveResult.message}`);
            }
        } catch (error) {
            console.error('Error adding food:', error);
            alert(' An unexpected error has occurred while adding food.');
        }

    }

    function updateProgress(macro, consumed, goal) {
        
        const percentage = goal > 0 ? (consumed / goal) * 100 : 0;
        const displayPercent = Math.min(Math.round(percentage), 100);

        const percentDiv = document.getElementById(`${macro}-percent`);

        if (percentDiv) {
            percentDiv.textContent = `${displayPercent}%`;
        }

        const barCircle = document.getElementById(`${macro}-bar`);
        if (barCircle) {
            const radius = 25;
            const circumference = 2 * Math.PI * radius;
            barCircle.style.strokeDasharray = circumference;
    
            const offset = circumference - (Math.min(percentage, 100) / 100) * circumference;
            barCircle.style.strokeDashoffset = offset;
        }
    }
    
    // Search button logic
    const searchButton = document.getElementById('searchButton');
    const foodInput = document.getElementById('foodInput');
    const resultsDiv = document.getElementById('results');
    
    // Click the button for search
    if (searchButton) {
        searchButton.addEventListener('click', performSearch);
        foodInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
            });
    }

    async function performSearch() {
        const foodItem = foodInput.value;
        if (!foodItem) return;

        // Lock button to prevent double cclicks
        searchButton.disbled = true;
        const originalButtonText = searchButton.textContent;
        searchButton.textContent = '...';

        resultsDiv.innerHTML = '<p>Searching...</p>';

        try {
            const response = await fetch(`${API_BASE_URL}/search_food?food_item=${encodeURIComponent(foodItem)}`, {
                credentials: 'include'
            });

            const products = await response.json();
            resultsDiv.innerHTML = ''; // Clear previous results

            if (response.ok && products.length > 0) {
                const template = document.getElementById('result-template');

                products.forEach(product => {
                    const clone = template.content.cloneNode(true);

                    clone.querySelector('.p-name').textContent = product.product_name;
                    clone.querySelector('.p-cals').innerHTML = `Calories: <br>${product.calories} kcal`;
                    clone.querySelector('.p-prot').innerHTML = `Proteins: <br>${product.proteins}g`;
                    clone.querySelector('.p-carbs').innerHTML = `Carbs: <br>${product.carbohydrates}g`;
                    clone.querySelector('.p-fats').innerHTML = `Fats: <br>${product.fat}g`;

                    const input = clone.querySelector('.serving-size-input');
                    input.value = product.serving_size || 100;

                    const btn = clone.querySelector('.add-food-btn');
                    btn.addEventListener('click', async () => {
                        const servingSize = parseFloat(input.value);
                        const foodData = {
                            product_name: product.product_name,
                            calories: product.calories,
                            proteins: product.proteins,
                            carbohydrates: product.carbohydrates,
                            fat: product.fat,
                            serving_size: servingSize || 100,
                        };
                        await addFoodEntry(foodData);
                    });

                    resultsDiv.appendChild(clone);
                });
            } else {
                resultsDiv.innerHTML = `<p>No food items found for "${foodItem}".</p>`;
            }
        } catch (error) {
            console.error('Error fetching food data:', error);
            resultsDiv.textContent = 'An error occurred while searching. Please try again.';
        } finally {
            searchButton.disabled = false;
            searchButton.textContent = originalButtonText;
        }
    }

    fetchUserName();
    setDates();
    fetchDailyTotals();
});
