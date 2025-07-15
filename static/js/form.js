// File upload handling
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');
    const uploadArea = document.getElementById('uploadArea');
    
    // Handle file selection
    fileInput.addEventListener('change', function() {
        updateFileList();
    });
    
    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        uploadArea.classList.add('border-primary', 'bg-primary/5');
    }
    
    function unhighlight() {
        uploadArea.classList.remove('border-primary', 'bg-primary/5');
    }
    
    // Handle dropped files
    uploadArea.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        fileInput.files = dt.files;
        updateFileList();
    });
    
    // Update the file list display
    function updateFileList() {
        const files = fileInput.files;
        if (files.length > 0) {
            // Hide upload area and show file list
            uploadArea.classList.add('hidden');
            fileList.classList.remove('hidden');
            
            fileList.innerHTML = ''; // Clear previous list
            
            Array.from(files).forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'flex items-center justify-between bg-gray-50 p-3 rounded-lg border border-gray-200';
                fileItem.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <i class="ri-file-text-line text-gray-500"></i>
                        <span class="text-sm text-gray-700 truncate max-w-xs">${file.name}</span>
                        <span class="text-xs text-gray-400">${formatFileSize(file.size)}</span>
                    </div>
                    <button type="button" class="text-gray-400 hover:text-red-500" data-index="${index}">
                        <i class="ri-close-line"></i>
                    </button>
                `;
                fileList.appendChild(fileItem);
            });
            
            // Add event listeners to remove buttons
            document.querySelectorAll('#fileList button').forEach(button => {
                button.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.getAttribute('data-index'));
                    removeFile(index);
                });
            });
        } else {
            // No files, show upload area and hide file list
            uploadArea.classList.remove('hidden');
            fileList.classList.add('hidden');
        }
    }
    
    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Remove file from the list
    function removeFile(index) {
        const dt = new DataTransfer();
        const input = fileInput;
        const { files } = input;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (index !== i) {
                dt.items.add(file);
            }
        }
        
        input.files = dt.files;
        updateFileList();
    }
});