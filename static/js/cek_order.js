// Deklarasikan fungsi-fungsi di level global
function openCekOrderModal() {
    const modal = document.getElementById('cekOrderModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        // document.body.style.overflow = 'hidden';
    }
}

function closeCekOrderModal() {
    const modal = document.getElementById('cekOrderModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        // document.body.style.overflow = 'auto';
    }
}

function closeOrderDetailModal() {
    const modal = document.getElementById('orderDetailModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        // document.body.style.overflow = 'auto';
    }
}

// Inisialisasi event listener
document.addEventListener('DOMContentLoaded', function () {
    // Close modal when clicking outside
    const cekOrderModal = document.getElementById('cekOrderModal');
    if (cekOrderModal) {
        cekOrderModal.addEventListener('click', function (e) {
            if (e.target === this) {
                closeCekOrderModal();
            }
        });
    }

    const orderDetailModal = document.getElementById('orderDetailModal');
    if (orderDetailModal) {
        orderDetailModal.addEventListener('click', function (e) {
            if (e.target === this) {
                closeOrderDetailModal();
            }
        });
    }

    // Handle form submission
    const cekOrderForm = document.getElementById('cekOrderForm');
    if (cekOrderForm) {
        cekOrderForm.addEventListener('submit', handleCekOrderSubmit);
    }
});

async function handleCekOrderSubmit(e) {
    e.preventDefault();

    const kodeOrder = document.getElementById('kode_order')?.value.trim();
    const submitButton = this.querySelector('button[type="submit"]');

    if (!kodeOrder || !submitButton) return;

    const originalButtonText = submitButton.innerHTML;

    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="ri-loader-4-line animate-spin mr-2"></i> Memeriksa...';

    try {
        const response = await fetch('/cek-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `kode_order=${encodeURIComponent(kodeOrder)}`
        });

        const data = await response.json();

        if (data.status === 'success') {
            closeCekOrderModal();
            openOrderDetailModal(data.order);
        } else {
            alert(data.message || 'Terjadi kesalahan. Silakan coba lagi.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Terjadi kesalahan. Silakan coba lagi.');
    } finally {
        // Reset button
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    }
}

// Function to open order detail modal
window.openOrderDetailModal = function (orderData) {
    console.log('Order Data:', orderData); // Debug: Lihat data yang diterima
    const modal = document.getElementById('orderDetailModal');
    if (!modal) return;

    // Fill in the order details
    console.log('Status:', orderData.status); // Debug: Lihat status order
    console.log('Completed File:', orderData.completed_file); // Debug: Lihat completed_file

    document.getElementById('orderCode').textContent = `Kode: ${orderData.order_code}`;
    document.getElementById('orderStatus').textContent = orderData.status;
    document.getElementById('orderNama').textContent = orderData.nama;
    document.getElementById('orderJenis').textContent = orderData.jenis;
    document.getElementById('orderWa').textContent = orderData.wa_pengguna;
    document.getElementById('orderDeadline').textContent = orderData.deadline;
    document.getElementById('orderCreatedAt').textContent = orderData.created_at;
    document.getElementById('orderDeskripsi').textContent = orderData.deskripsi;

    // Update price display
    const priceElement = document.getElementById('orderHarga');
    if (priceElement) {
        if (orderData.harga && orderData.harga > 0) {
            // Format price to Indonesian Rupiah
            const formattedPrice = new Intl.NumberFormat('id-ID', {
                style: 'currency',
                currency: 'IDR',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(orderData.harga);
            priceElement.textContent = `${formattedPrice}`;
        } else {
            priceElement.textContent = 'Belum disepakati dengan admin';
        }
    }

    // Update the status display
    const statusElement = document.getElementById('orderStatus');
    if (statusElement) {
        statusElement.textContent = orderData.status;
        statusElement.className = 'px-3 py-1 rounded-full text-sm font-medium';

        const status = orderData.status.toLowerCase();
        if (status.includes('menunggu')) {
            statusElement.classList.add('bg-yellow-100', 'text-yellow-800');
        } else if (status.includes('proses')) {
            statusElement.classList.add('bg-blue-100', 'text-blue-800');
        } else if (status.includes('selesai')) {
            statusElement.classList.add('bg-green-100', 'text-green-800');
        } else if (status.includes('batal')) {
            statusElement.classList.add('bg-red-100', 'text-red-800');
        } else {
            statusElement.classList.add('bg-gray-100', 'text-gray-800');
        }
    }

    // Show file if exists
    const fileElement = document.getElementById('orderFile');
    if (fileElement) {
        if (orderData.file_name) {
            fileElement.innerHTML = `
                <a href="/${orderData.file_path}" target="_blank" 
                   class="text-primary hover:underline flex items-center">
                    <i class="ri-download-line mr-1"></i> ${orderData.file_name}
                </a>
            `;
        } else {
            fileElement.textContent = 'Tidak ada file';
        }
    }

    // Handle completed file display
    const completedFileContainer = document.getElementById('completedFile');
    if (completedFileContainer) {
        if (orderData.status.toLowerCase().includes('selesai') && orderData.finished_file) {
            completedFileContainer.innerHTML = `
                <a href="/${orderData.finished_file}" target="_blank" 
                   class="text-primary hover:underline flex items-center">
                    <i class="ri-download-line mr-1"></i> ${orderData.finished_file.split('/').pop()}
                </a>
            `;
        } else {
            completedFileContainer.textContent = 'Tidak ada file';
        }
    }

    // Show the modal
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    // document.body.style.overflow = 'hidden';
};