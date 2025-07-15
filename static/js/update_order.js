function updateOrder() {
    const form = document.getElementById('orderForm');
    const formData = new FormData();
    const orderId = document.getElementById('orderId').value;
    const status = document.getElementById('status').value;
    const harga = document.getElementById('harga').value;
    const fileInput = document.getElementById('finishedFile');
    
    // Add all necessary data to formData
    formData.append('orderId', orderId);
    formData.append('status', status);
    formData.append('harga', harga);
    
    // Add file if exists
    if (fileInput.files.length > 0) {
        formData.append('finishedFile', fileInput.files[0]);
    }

    // Validation
    if (status === 'Selesai' && fileInput.files.length === 0 && !document.getElementById('fileInfo').querySelector('a[href*="finish/"]')) {
        alert('Harap unggah file tugas selesai');
        return;
    }

    // Show loading state
    const saveButton = document.querySelector('button[onclick="updateOrder()"]');
    const originalText = saveButton.innerHTML;
    saveButton.disabled = true;
    saveButton.innerHTML = '<i class="ri-loader-4-line animate-spin"></i> Menyimpan...';

    fetch(`/admin/orders/${orderId}/update`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header, let the browser set it with the boundary
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.message || 'Gagal memperbarui data');
        }
        return data;
    })
    .then(data => {
        if (data.status === 'success') {
            alert('Data berhasil diperbarui');
            window.location.reload();
        } else {
            throw new Error(data.message || 'Gagal memperbarui data');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Terjadi kesalahan: ' + (error.message || 'Tidak dapat terhubung ke server'));
    })
    .finally(() => {
        saveButton.disabled = false;
        saveButton.innerHTML = originalText;
    });
}