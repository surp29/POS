/**
 * Utility functions chung cho toàn bộ ứng dụng
 */

/** Lấy message lỗi từ response Backend (FastAPI: detail hoặc error). */
function parseApiError(data, fallback = 'Có lỗi xảy ra') {
    if (!data) return fallback;
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.error === 'string') return data.error;
    if (data.message) return data.message;
    return fallback;
}

/** Chuẩn hóa danh sách đơn hàng — Backend trả { orders: [...] } hoặc mảng. */
function normalizeOrdersList(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.orders)) return data.orders;
    return [];
}

/** Chuẩn hóa danh sách sản phẩm — Backend trả { products: [...] }. */
function normalizeProductsList(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.products)) return data.products;
    return [];
}

/** URL ảnh/static từ Backend (image_url thường là /static/...). */
function backendAssetUrl(path) {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    const base = (typeof window !== 'undefined' && window.BACKEND_URL) || '';
    return base + (path.startsWith('/') ? path : '/' + path);
}

// Format money input with commas
function formatMoneyTyping(sourceInput, hiddenInput) {
    const raw = (sourceInput.value || '').replace(/[^0-9]/g, '');
    if (!raw) {
        sourceInput.value = '';
        if (hiddenInput) hiddenInput.value = '';
        return;
    }
    if (hiddenInput) hiddenInput.value = raw;
    sourceInput.value = raw.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show success message
function showSuccessMessage(message) {
    if (typeof showSuccessModal === 'function') {
        showSuccessModal('Thành công', message);
    } else {
        alert('Thành công: ' + message);
    }
}

// Show error message
function showErrorMessage(message) {
    if (typeof showErrorModal === 'function') {
        showErrorModal('Lỗi', message);
    } else {
        alert('Lỗi: ' + message);
    }
}

// Validate positive integer
function validatePositiveInteger(input) {
    let value = input.value;
    value = value.replace(/[^\d]/g, '');
    if (value === '') {
        input.value = '';
        return;
    }
    let num = parseInt(value);
    if (num < 0) {
        num = 0;
    }
    input.value = num;
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN');
}

// Format time
function formatTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

// Format datetime for input
function formatDateTimeForInput(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().slice(0, 16);
}

// Format number input with commas
function formatNumberInput(input) {
    let value = input.value.replace(/[^0-9.]/g, '');
    const parts = value.split('.');
    if (parts.length > 2) {
        value = parts[0] + '.' + parts.slice(1).join('');
    }
    if (parts[0]) {
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        value = parts.join('.');
    }
    input.value = value;
}

// Check if key is number
function isNumberKey(evt) {
    const charCode = (evt.which) ? evt.which : evt.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
        evt.preventDefault();
        return false;
    }
    return true;
}

// Get status badge HTML
function getStatusBadge(status) {
    const badges = {
        'Đã thanh toán': '<span class="badge badge-success">Đã thanh toán</span>',
        'Chưa thanh toán': '<span class="badge badge-warning">Chưa thanh toán</span>',
        'Hoàn thành': '<span class="badge badge-success">Hoàn thành</span>',
        'Đang xử lý': '<span class="badge badge-info">Đang xử lý</span>',
        'Đã hủy': '<span class="badge badge-danger">Đã hủy</span>',
        'Còn hàng': '<span class="badge badge-success">Còn hàng</span>',
        'Hết hàng': '<span class="badge badge-danger">Hết hàng</span>',
        'Hoạt động': '<span class="badge badge-success">Hoạt động</span>',
        'Không hoạt động': '<span class="badge badge-secondary">Không hoạt động</span>'
    };
    return badges[status] || '<span class="badge badge-secondary">' + (status || 'Không xác định') + '</span>';
}

/**
 * Pagination utility functions
 * Sử dụng chung cho tất cả các giao diện
 */

/**
 * Generate pagination HTML
 * @param {number} currentPage - Trang hiện tại
 * @param {number} totalPages - Tổng số trang
 * @returns {string} HTML cho pagination
 */
function generatePaginationHTML(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `
        <button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="window.goToPage(${currentPage - 1})">
            <i class="fas fa-chevron-left"></i>
        </button>
    `;
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHTML += `<button class="pagination-btn" onclick="window.goToPage(1)">1</button>`;
        if (startPage > 2) {
            paginationHTML += `<span class="text-gray-500">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="window.goToPage(${i})">
                ${i}
            </button>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span class="text-gray-500">...</span>`;
        }
        paginationHTML += `<button class="pagination-btn" onclick="window.goToPage(${totalPages})">${totalPages}</button>`;
    }
    
    // Next button
    paginationHTML += `
        <button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="window.goToPage(${currentPage + 1})">
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    return paginationHTML;
}

/**
 * Update pagination display
 * @param {string} paginationElementId - ID của element chứa pagination
 * @param {number} currentPage - Trang hiện tại
 * @param {number} totalItems - Tổng số items
 * @param {number} itemsPerPage - Số items mỗi trang
 */
function updatePagination(paginationElementId, currentPage, totalItems, itemsPerPage) {
    const pagination = document.getElementById(paginationElementId);
    if (!pagination) return;
    
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    pagination.innerHTML = generatePaginationHTML(currentPage, totalPages);
}

