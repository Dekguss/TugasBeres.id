document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const statusFilter = document.getElementById('statusFilter');
    const searchInput = document.getElementById('searchInput');
    const ordersTable = document.getElementById('ordersTable');
    const rows = ordersTable.getElementsByTagName('tr');

    // Add event listeners
    statusFilter.addEventListener('change', filterOrders);
    searchInput.addEventListener('input', filterOrders);

    // Initial filter
    filterOrders();

    // Format date for comparison
    function formatDate(dateString) {
        if (!dateString) return '';
        const [day, month, year] = dateString.split('/');
        return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }

    // Filter orders based on status and search query
    function filterOrders() {
        const status = statusFilter.value.toLowerCase();
        const searchQuery = searchInput.value.toLowerCase();
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            if (!row.dataset.status) continue; // Skip header row and no-data row

            const statusMatch = status === 'all' || 
                              (row.dataset.status && row.dataset.status.toLowerCase() === status);
            
            // Get all text content from the row for searching
            const rowText = row.textContent.toLowerCase();
            const searchMatch = !searchQuery || rowText.includes(searchQuery);

            // Check if the order is due today or past due
            const dateCell = row.querySelector('.order-date');
            let isDue = true;
            
            if (dateCell) {
                const dateStr = dateCell.textContent.trim();
                if (dateStr) {
                    const [day, month, year] = dateStr.split('/').map(Number);
                    const orderDate = new Date(year, month - 1, day);
                    orderDate.setHours(0, 0, 0, 0);
                    
                    // Add warning class if due date is today or in the past and status is not completed/cancelled/rejected
                    const statusCell = row.querySelector('td:nth-child(4)');
                    if (statusCell) {
                        const statusText = statusCell.textContent.trim().toLowerCase();
                        const isCompleted = ['selesai', 'dibatalkan', 'ditolak'].includes(statusText);
                        
                        if (orderDate <= today && !isCompleted) {
                            row.classList.add('bg-yellow-50');
                        } else {
                            row.classList.remove('bg-yellow-50');
                        }
                    }
                }
            }

            // Show/hide row based on filters
            if (statusMatch && searchMatch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    }
});
