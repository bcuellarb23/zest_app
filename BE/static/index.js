document.addEventListener('DOMContentLoaded', async() => {

    const logoContainer = document.querySelector('.logo-index');
    
    if (logoContainer) {
        window.addEventListener('scroll', () => {
            const scrollY = window.scrollY;
            const vh = window.innerHeight;

            const scrollDistance = vh * 0.6;
            let progress = Math.min(scrollY / scrollDistance, 1);

            const currentHeight = 100 - (progress * 93);
            const currentWidth = 300 - (progress * 180);
            const currentPadding = 0 - (progress * 44);

            logoContainer.style.setProperty('--header-height', `${currentHeight}vh`);
            logoContainer.style.setProperty('--logo-width', `${currentWidth}px`);
            logoContainer.style.setProperty('--logo-top-padding', `${currentPadding}vh`);

            if (progress > 0.95){
                logoContainer.classList.add('scrolled');
            } else {
                logoContainer.classList.remove('scrolled');
            }

            const scrollArrow = document.getElementById('scrollArrow');

            if(scrollArrow) {
                scrollArrow.style.opacity = Math.max(1 - (progress *5), 0);

                if (progress > 0.9) {
                    scrollArrow.style.display = 'none';
                } else {
                    scrollArrow.style.display = 'block';
                }
            }
        });
    }

    const dropdown = document.querySelector('.dropdown-menu');

    dropdown.addEventListener('click', function(event) {
        event.stopPropagation();
        this.classList.toggle('is-active');
    });

    document.addEventListener('click', function() {
        dropdown.classList.remove('is-active');
    });
    
    const searchButton = document.getElementById('searchButton');
    const foodInput = document.getElementById('foodInput');
    const resultsDiv = document.getElementById('results');

    if (searchButton) {
        searchButton.addEventListener('click', performSearch);
    }

    async function performSearch() {

        const foodItem = foodInput.value;
        if (!foodItem) return;
        
        resultsDiv.innerHTML = 'Searching...';
        console.log(`Searching for: ${foodItem} at ${API_BASE_URL}/search_food`);

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
});
