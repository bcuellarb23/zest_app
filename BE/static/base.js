document.addEventListener('DOMContentLoaded', () => {
  const dropdown = document.querySelector('.dropdown-menu');

  if (dropdown) {
    dropdown.addEventListener('click', function(event) {
      event.stopPropagation();
      this.classList.toggle('is-active');
    });

    document.addEventListener('click', function() {
      dropdown.classList.remove('is-active');
    });
  }

});
