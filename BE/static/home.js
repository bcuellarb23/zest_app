document.addEventListener('DOMContentLoaded' , async() => {

    // Dropdown Menu Logic
    const profileImg = document.querySelector('.profile-image');
    const dropdownMenu = document.querySelector('.dropdown-menu');

    if (profileImg && dropdownMenu) {
        profileImg.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('active');
        });

        document.addEventListener('click', () => {
            dropdownMenu.classList.remove('active');
        });
    }

    const userNameDiv = document.querySelector('#user-name-link');
    const foodInput = document.getElementById('foodInput');
    const searchButton = document.getElementById('searchButton');
    const resultsDiv = document.getElementById('results');

    async function fetchUserName() {
        try {
            const response = await fetch(`${API_BASE_URL}/get_info`, {
                credentials: 'include'
            });
            const data = await response.json();

            if (data.status === 'success' && userNameDiv) {
                // User is logged in, display their name
                userNameDiv.textContent = data.user_name;
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
    
    async function performSearch() {
        const foodInput = document.getElementById('foodInput');
        const resultsDiv = document.getElementById('results');
        const foodItem = foodInput.value;

        if (!foodItem) return;

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
                    
                    clone.querySelector('h4').textContent = product.product_name;
                    clone.querySelector('.p-cals').textContent = `Calories: ${product.calories} kcal`;
                    clone.querySelector('.p-prot').textContent = `Proteins: ${product.proteins}g`;
                    clone.querySelector('.p-carbs').textContent = `Carbohydrates: ${product.carbohydrates}g`;
                    clone.querySelector('.p-fats').textContent = `Fats: ${product.fat}g`;
                    
                    const input = clone.querySelector('#serving-size');
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
                resultsDiv.textContent = 'No food items found.';
            }
        } catch (error) {
            console.error('Error fetching food data:', error);
            resultsDiv.textContent = 'An error occurred while searching.';
        }
    }

    const initialSearchButton = document.getElementById('initialSearchButton');
    if (initialSearchButton) {
        initialSearchButton.addEventListener('click', () => {
            const initialButtons = document.getElementById('initial-buttons');
            if (initialButtons) initialButtons.style.display = 'none';
            
            const template = document.getElementById('searchbar-template');
            const clone = template.content.cloneNode(true);
            document.querySelector('.tracker').appendChild(clone);
            
            // Attach listener to the NEW search button from the template
            const newSearchButton = document.getElementById('searchButton');
            if (newSearchButton) {
                newSearchButton.addEventListener('click', performSearch);
            }
        });
    }

    fetchUserName();
    setDates();
    fetchDailyTotals();
});
