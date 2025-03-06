document.addEventListener('DOMContentLoaded', function() {
    // Location selector functionality
    const locationSearch = document.getElementById('locationSearch');
    if (locationSearch) {
        locationSearch.addEventListener('input', function(e) {
            // Add location search functionality here
            console.log('Searching for location:', e.target.value);
        });
    }

    // Category selection functionality
    const categorySelect = document.querySelector('select[aria-label="Select category"]');
    if (categorySelect) {
        categorySelect.addEventListener('change', function(e) {
            // Add category selection functionality here
            console.log('Selected category:', e.target.value);
        });
    }

    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});