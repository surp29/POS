/**
 * Phone Input Component with Country Selection and Validation
 * Supports multiple countries with specific validation rules
 */

// Country codes and validation rules
const PHONE_COUNTRIES = [
    { code: 'VN', name: 'Việt Nam', dialCode: '+84', flag: '🇻🇳', pattern: /^0\d{9}$/, length: 10, placeholder: '0XXXXXXXXX', prefix: '0' },
    { code: 'US', name: 'United States', dialCode: '+1', flag: '🇺🇸', pattern: /^\d{10}$/, length: 10, placeholder: 'XXXXXXXXXX', prefix: '' },
    { code: 'GB', name: 'United Kingdom', dialCode: '+44', flag: '🇬🇧', pattern: /^[1-9]\d{9,10}$/, length: 10, placeholder: '7XXXXXXXXX', prefix: '7' },
    { code: 'CN', name: 'China', dialCode: '+86', flag: '🇨🇳', pattern: /^1[3-9]\d{9}$/, length: 11, placeholder: '1XXXXXXXXXX', prefix: '1' },
    { code: 'JP', name: 'Japan', dialCode: '+81', flag: '🇯🇵', pattern: /^[789]0\d{8}$/, length: 11, placeholder: '90XXXXXXXXX', prefix: '9' },
    { code: 'KR', name: 'South Korea', dialCode: '+82', flag: '🇰🇷', pattern: /^1[0-9]\d{7,8}$/, length: 10, placeholder: '10XXXXXXXX', prefix: '1' },
    { code: 'TH', name: 'Thailand', dialCode: '+66', flag: '🇹🇭', pattern: /^[689]\d{8}$/, length: 9, placeholder: '8XXXXXXXX', prefix: '8' },
    { code: 'SG', name: 'Singapore', dialCode: '+65', flag: '🇸🇬', pattern: /^[689]\d{7}$/, length: 8, placeholder: '8XXXXXXX', prefix: '8' },
    { code: 'MY', name: 'Malaysia', dialCode: '+60', flag: '🇲🇾', pattern: /^1[0-9]\d{7,8}$/, length: 10, placeholder: '1XXXXXXXXX', prefix: '1' },
    { code: 'ID', name: 'Indonesia', dialCode: '+62', flag: '🇮🇩', pattern: /^8\d{9,10}$/, length: 11, placeholder: '8XXXXXXXXXX', prefix: '8' },
    { code: 'PH', name: 'Philippines', dialCode: '+63', flag: '🇵🇭', pattern: /^9\d{9}$/, length: 10, placeholder: '9XXXXXXXXX', prefix: '9' },
    { code: 'AU', name: 'Australia', dialCode: '+61', flag: '🇦🇺', pattern: /^4\d{8}$/, length: 9, placeholder: '4XXXXXXXX', prefix: '4' },
    { code: 'CA', name: 'Canada', dialCode: '+1', flag: '🇨🇦', pattern: /^\d{10}$/, length: 10, placeholder: 'XXXXXXXXXX', prefix: '' },
    { code: 'FR', name: 'France', dialCode: '+33', flag: '🇫🇷', pattern: /^[67]\d{8}$/, length: 9, placeholder: '6XXXXXXXX', prefix: '6' },
    { code: 'DE', name: 'Germany', dialCode: '+49', flag: '🇩🇪', pattern: /^1[5-7]\d{8,9}$/, length: 11, placeholder: '15XXXXXXXXX', prefix: '15' },
    { code: 'IN', name: 'India', dialCode: '+91', flag: '🇮🇳', pattern: /^[6-9]\d{9}$/, length: 10, placeholder: '9XXXXXXXXX', prefix: '9' },
];

// Default country (Vietnam)
const DEFAULT_COUNTRY = 'VN';

/**
 * Initialize phone input components
 */
function initializePhoneInputs() {
    // Remove any duplicate containers first
    document.querySelectorAll('.phone-input-container').forEach(container => {
        const formGroup = container.closest('.form-group');
        if (formGroup) {
            const containers = formGroup.querySelectorAll('.phone-input-container');
            if (containers.length > 1) {
                // Keep only the first one, remove the rest
                for (let i = 1; i < containers.length; i++) {
                    containers[i].remove();
                }
            }
        }
    });
    
    document.querySelectorAll('input[data-phone]').forEach(input => {
        // Skip if already wrapped
        if (input.closest('.phone-input-container')) {
            return;
        }
        
        // Check if there's already a container in the same form group
        const formGroup = input.closest('.form-group');
        if (formGroup) {
            const existingContainer = formGroup.querySelector('.phone-input-container');
            if (existingContainer) {
                // Container already exists, skip
                return;
            }
        }
        
        wrapPhoneInput(input);
    });
}

/**
 * Wrap a phone input with country selector
 */
function wrapPhoneInput(input) {
    // Skip if already wrapped
    if (input.closest('.phone-input-container')) {
        return;
    }
    
    // Check if there's already a container for this input (by name or id)
    const inputName = input.name;
    const inputId = input.id;
    
    // Check if container already exists in the same form group
    const formGroup = input.closest('.form-group');
    if (formGroup) {
        const existingContainer = formGroup.querySelector('.phone-input-container');
        if (existingContainer) {
            // Container already exists, don't create another one
            return;
        }
    }

    const container = document.createElement('div');
    container.className = 'phone-input-container';
    
    // Create country select
    const countrySelect = document.createElement('select');
    countrySelect.className = 'form-select phone-country-select';
    countrySelect.setAttribute('data-country-select', 'true');
    
    // Populate country options
    PHONE_COUNTRIES.forEach(country => {
        const option = document.createElement('option');
        option.value = country.code;
        option.textContent = `${country.flag} ${country.dialCode}`;
        option.setAttribute('data-dial-code', country.dialCode);
        option.setAttribute('data-pattern', country.pattern.source);
        option.setAttribute('data-length', country.length);
        option.setAttribute('data-placeholder', country.placeholder);
        if (country.code === DEFAULT_COUNTRY) {
            option.selected = true;
        }
        countrySelect.appendChild(option);
    });
    
    // Create number input
    const numberInput = document.createElement('input');
    numberInput.type = 'tel';
    numberInput.className = 'form-input phone-number-input';
    numberInput.setAttribute('data-phone-number', 'true');
    
    // Copy attributes from original input
    if (inputName) numberInput.name = inputName;
    if (inputId) {
        numberInput.id = inputId;
        // Remove ID from original input to avoid duplicate IDs
        input.removeAttribute('id');
    }
    if (input.placeholder) numberInput.placeholder = input.placeholder;
    if (input.required) numberInput.required = input.required;
    
    // Set initial placeholder
    const selectedCountry = PHONE_COUNTRIES.find(c => c.code === DEFAULT_COUNTRY);
    if (selectedCountry) {
        numberInput.placeholder = selectedCountry.placeholder;
    }
    
    // Hide original input completely
    input.style.display = 'none';
    input.style.visibility = 'hidden';
    input.style.position = 'absolute';
    input.style.width = '0';
    input.style.height = '0';
    input.style.opacity = '0';
    input.setAttribute('data-phone-hidden', 'true');
    
    // Insert container before original input
    input.parentNode.insertBefore(container, input);
    container.appendChild(countrySelect);
    container.appendChild(numberInput);
    
    // Setup event listeners
    setupPhoneInputEvents(countrySelect, numberInput, input);
    
    // Try to parse existing value
    if (input.value) {
        parseAndSetPhoneValue(input.value, countrySelect, numberInput);
    } else {
        // Auto-fill prefix if input is empty and country has prefix
        const selectedCountry = PHONE_COUNTRIES.find(c => c.code === DEFAULT_COUNTRY);
        if (selectedCountry && selectedCountry.prefix) {
            numberInput.value = selectedCountry.prefix;
            setTimeout(() => {
                numberInput.setSelectionRange(selectedCountry.prefix.length, selectedCountry.prefix.length);
            }, 0);
            updateHiddenInput(countrySelect, numberInput, input);
        }
    }
}

/**
 * Setup event listeners for phone input
 */
function setupPhoneInputEvents(countrySelect, numberInput, hiddenInput) {
    // Country change handler
    countrySelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        const countryCode = selectedOption.value;
        const country = PHONE_COUNTRIES.find(c => c.code === countryCode);
        const length = parseInt(selectedOption.getAttribute('data-length'));
        const placeholder = selectedOption.getAttribute('data-placeholder');
        
        numberInput.placeholder = placeholder;
        numberInput.maxLength = length;
        
        // Auto-fill prefix if country has one and input is empty
        if (country && country.prefix && numberInput.value === '') {
            numberInput.value = country.prefix;
            // Set cursor position after prefix
            setTimeout(() => {
                numberInput.setSelectionRange(country.prefix.length, country.prefix.length);
            }, 0);
        } else if (!country || !country.prefix) {
            numberInput.value = '';
        }
        
        // Clear validation
        numberInput.classList.remove('is-invalid');
        const container = numberInput.closest('.phone-input-container');
        if (container) {
            // Remove error from container
            const errorInContainer = container.querySelector('.phone-error');
            if (errorInContainer) errorInContainer.remove();
            
            // Also check if error is after container (sibling)
            const formGroup = container.closest('.form-group');
            if (formGroup) {
                const nextSibling = container.nextElementSibling;
                if (nextSibling && nextSibling.classList.contains('phone-error')) {
                    nextSibling.remove();
                }
            }
            
            container.classList.remove('has-error');
        }
        
        updateHiddenInput(countrySelect, numberInput, hiddenInput);
    });
    
    // Number input handlers
    numberInput.addEventListener('input', function() {
        const selectedOption = countrySelect.options[countrySelect.selectedIndex];
        const countryCode = selectedOption.value;
        const country = PHONE_COUNTRIES.find(c => c.code === countryCode);
        
        if (!country) return;
        
        // Format input based on country
        let value = this.value.replace(/\D/g, ''); // Remove non-digits
        
        // Special handling for Vietnam (must start with 0)
        if (countryCode === 'VN') {
            // Vietnam: must start with 0 and have exactly 10 digits
            if (value.length > 0 && !value.startsWith('0')) {
                // If user types a digit that's not 0, prepend 0
                value = '0' + value;
            }
            // Limit to 10 digits (including leading 0)
            if (value.length > country.length) {
                value = value.substring(0, country.length);
            }
            // Ensure it starts with 0 if not empty
            if (value.length > 0 && !value.startsWith('0')) {
                value = '0' + value.substring(0, country.length - 1);
            }
        } else if (country.prefix) {
            // Countries with prefix: ensure it starts with prefix
            if (value.length > 0 && !value.startsWith(country.prefix)) {
                // If user deleted prefix, restore it
                if (value.length < country.prefix.length) {
                    value = country.prefix;
                } else {
                    // If user typed different digit, replace with prefix + rest
                    value = country.prefix + value.substring(country.prefix.length);
                }
            }
            // Limit to country's max length
            if (value.length > country.length) {
                value = value.substring(0, country.length);
            }
        } else {
            // Other countries without prefix: Limit to country's max length
            if (value.length > country.length) {
                value = value.substring(0, country.length);
            }
        }
        
        this.value = value;
        updateHiddenInput(countrySelect, numberInput, hiddenInput);
        validatePhoneInput(countrySelect, numberInput);
    });
    
    // Focus handler: auto-fill prefix when input gets focus and is empty
    numberInput.addEventListener('focus', function() {
        const selectedOption = countrySelect.options[countrySelect.selectedIndex];
        const countryCode = selectedOption.value;
        const country = PHONE_COUNTRIES.find(c => c.code === countryCode);
        
        if (country && country.prefix && this.value === '') {
            this.value = country.prefix;
            setTimeout(() => {
                this.setSelectionRange(country.prefix.length, country.prefix.length);
            }, 0);
            updateHiddenInput(countrySelect, numberInput, hiddenInput);
        }
    });
    
    numberInput.addEventListener('blur', function() {
        validatePhoneInput(countrySelect, numberInput);
    });
    
    numberInput.addEventListener('keypress', function(e) {
        // Only allow digits
        if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'Tab', 'Enter'].includes(e.key)) {
            e.preventDefault();
        }
    });
}

/**
 * Validate phone input
 */
function validatePhoneInput(countrySelect, numberInput) {
    const selectedOption = countrySelect.options[countrySelect.selectedIndex];
    const countryCode = selectedOption.value;
    const country = PHONE_COUNTRIES.find(c => c.code === countryCode);
    
    if (!country) return true;
    
    const value = numberInput.value.trim();
    
    // Remove existing error
    numberInput.classList.remove('is-invalid');
    const container = numberInput.closest('.phone-input-container');
    if (container) {
        // Remove error from container
        const errorInContainer = container.querySelector('.phone-error');
        if (errorInContainer) errorInContainer.remove();
        
        // Also check if error is after container (sibling)
        const formGroup = container.closest('.form-group');
        if (formGroup) {
            const nextSibling = container.nextElementSibling;
            if (nextSibling && nextSibling.classList.contains('phone-error')) {
                nextSibling.remove();
            }
        }
        
        container.classList.remove('has-error');
    }
    
    // Skip validation if empty (unless required)
    if (!value) {
        if (numberInput.required) {
            showPhoneError(numberInput, 'Vui lòng nhập số điện thoại');
            return false;
        }
        return true;
    }
    
    // Check length
    if (value.length !== country.length) {
        showPhoneError(numberInput, `Số điện thoại ${country.name} phải có ${country.length} chữ số`);
        return false;
    }
    
    // Check pattern
    if (!country.pattern.test(value)) {
        let errorMsg = `Số điện thoại không hợp lệ cho ${country.name}`;
        if (countryCode === 'VN') {
            if (!value.startsWith('0')) {
                errorMsg = 'Số điện thoại Việt Nam phải bắt đầu bằng số 0';
            } else if (value.length !== 10) {
                errorMsg = 'Số điện thoại Việt Nam phải có đủ 10 chữ số';
            } else {
                errorMsg = 'Số điện thoại Việt Nam không hợp lệ. Ví dụ: 0912345678';
            }
        }
        showPhoneError(numberInput, errorMsg);
        return false;
    }
    
    return true;
}

/**
 * Show phone validation error
 */
function showPhoneError(numberInput, message) {
    numberInput.classList.add('is-invalid');
    
    // Remove existing error first
    const container = numberInput.closest('.phone-input-container');
    if (container) {
        const existingError = container.querySelector('.phone-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error after container (not inside) to avoid overlapping with next field
        const formGroup = container.closest('.form-group');
        if (formGroup) {
            // Check if error already exists after container
            const nextSibling = container.nextElementSibling;
            if (nextSibling && nextSibling.classList.contains('phone-error')) {
                nextSibling.remove();
            }
            
            // Create error div
            const errorDiv = document.createElement('div');
            errorDiv.className = 'phone-error';
            errorDiv.textContent = message;
            
            // Insert error after container
            container.parentNode.insertBefore(errorDiv, container.nextSibling);
            container.classList.add('has-error');
        } else {
            // Fallback: append to container if no form-group found
            const errorDiv = document.createElement('div');
            errorDiv.className = 'phone-error';
            errorDiv.textContent = message;
            container.appendChild(errorDiv);
            container.classList.add('has-error');
        }
    }
}

/**
 * Update hidden input with full phone number
 */
function updateHiddenInput(countrySelect, numberInput, hiddenInput) {
    const selectedOption = countrySelect.options[countrySelect.selectedIndex];
    const dialCode = selectedOption.getAttribute('data-dial-code');
    const number = numberInput.value.trim();
    
    if (number) {
        hiddenInput.value = dialCode + number;
    } else {
        hiddenInput.value = '';
    }
}

/**
 * Get phone value from input
 */
function getPhoneValue(input) {
    if (!input) return '';
    
    // If input is wrapped, get from hidden input
    if (input.hasAttribute('data-phone-hidden')) {
        return input.value || '';
    }
    
    // If input is in phone container, get from hidden input
    const container = input.closest('.phone-input-container');
    if (container) {
        const hiddenInput = container.previousElementSibling;
        if (hiddenInput && hiddenInput.hasAttribute('data-phone-hidden')) {
            return hiddenInput.value || '';
        }
        // Try to find hidden input by looking for input[data-phone-hidden] near the container
        const form = container.closest('form');
        if (form) {
            const hiddenInputs = form.querySelectorAll('input[data-phone-hidden]');
            for (let hidden of hiddenInputs) {
                const hiddenContainer = hidden.nextElementSibling;
                if (hiddenContainer === container) {
                    return hidden.value || '';
                }
            }
        }
    }
    
    // Fallback: try to construct from visible inputs
    if (container) {
        const countrySelect = container.querySelector('.phone-country-select');
        const numberInput = container.querySelector('.phone-number-input');
        if (countrySelect && numberInput) {
            const dialCode = countrySelect.options[countrySelect.selectedIndex].getAttribute('data-dial-code');
            const number = numberInput.value.trim();
            if (number) {
                return dialCode + number;
            }
        }
    }
    
    return input.value || '';
}

/**
 * Set phone value
 */
function setPhoneValue(input, value) {
    if (!input) return;
    
    // Handle empty value
    if (!value || value === '') {
        const container = input.closest('.phone-input-container') || 
                         (input.hasAttribute('data-phone') ? null : input.parentElement.querySelector('.phone-input-container'));
        
        if (container) {
            const countrySelect = container.querySelector('.phone-country-select');
            const numberInput = container.querySelector('.phone-number-input');
            if (countrySelect) countrySelect.value = DEFAULT_COUNTRY;
            if (numberInput) numberInput.value = '';
            
            // Update hidden input
            const hiddenInput = container.previousElementSibling;
            if (hiddenInput && hiddenInput.hasAttribute('data-phone-hidden')) {
                hiddenInput.value = '';
            }
        } else {
            // Try to find hidden input and its container
            const hiddenInput = document.querySelector(`input[data-phone-hidden][name="${input.name}"]`);
            if (hiddenInput) {
                const hiddenContainer = hiddenInput.nextElementSibling;
                if (hiddenContainer && hiddenContainer.classList.contains('phone-input-container')) {
                    const countrySelect = hiddenContainer.querySelector('.phone-country-select');
                    const numberInput = hiddenContainer.querySelector('.phone-number-input');
                    if (countrySelect) countrySelect.value = DEFAULT_COUNTRY;
                    if (numberInput) numberInput.value = '';
                    hiddenInput.value = '';
                }
            }
        }
        return;
    }
    
    const container = input.closest('.phone-input-container') || 
                     (input.hasAttribute('data-phone') ? null : input.parentElement.querySelector('.phone-input-container'));
    
    if (!container) {
        // Try to find hidden input and its container
        const hiddenInput = document.querySelector(`input[data-phone-hidden][name="${input.name}"]`);
        if (hiddenInput) {
            const hiddenContainer = hiddenInput.nextElementSibling;
            if (hiddenContainer && hiddenContainer.classList.contains('phone-input-container')) {
                parseAndSetPhoneValue(value, 
                    hiddenContainer.querySelector('.phone-country-select'),
                    hiddenContainer.querySelector('.phone-number-input'));
                return;
            }
        }
        return;
    }
    
    const countrySelect = container.querySelector('.phone-country-select');
    const numberInput = container.querySelector('.phone-number-input');
    
    if (countrySelect && numberInput) {
        parseAndSetPhoneValue(value, countrySelect, numberInput);
    }
}

/**
 * Parse phone value and set to inputs
 */
function parseAndSetPhoneValue(value, countrySelect, numberInput) {
    if (!value) {
        numberInput.value = '';
        return;
    }
    
    // Try to find matching country by dial code
    let matchedCountry = null;
    let phoneNumber = value;
    
    // Remove any non-digit characters except +
    const cleanValue = value.replace(/[^\d+]/g, '');
    
    // Try to match dial code
    for (const country of PHONE_COUNTRIES) {
        if (cleanValue.startsWith(country.dialCode)) {
            matchedCountry = country;
            phoneNumber = cleanValue.substring(country.dialCode.length);
            break;
        }
    }
    
    // If no match, default to Vietnam
    if (!matchedCountry) {
        matchedCountry = PHONE_COUNTRIES.find(c => c.code === DEFAULT_COUNTRY);
        // If value starts with 0, assume Vietnam
        if (value.startsWith('0')) {
            phoneNumber = value.replace(/\D/g, '');
        } else {
            phoneNumber = value.replace(/\D/g, '');
        }
    }
    
    // Set country
    if (matchedCountry) {
        countrySelect.value = matchedCountry.code;
        const event = new Event('change');
        countrySelect.dispatchEvent(event);
    }
    
    // Set number
    // For Vietnam: ensure it starts with 0
    if (matchedCountry && matchedCountry.code === 'VN') {
        if (phoneNumber && !phoneNumber.startsWith('0')) {
            phoneNumber = '0' + phoneNumber;
        }
        // Limit to 10 digits
        if (phoneNumber.length > matchedCountry.length) {
            phoneNumber = phoneNumber.substring(0, matchedCountry.length);
        }
    } else if (matchedCountry && matchedCountry.code !== 'VN') {
        // For other countries: remove leading 0 if present
        if (phoneNumber.startsWith('0')) {
            phoneNumber = phoneNumber.substring(1);
        }
        // Limit to country's max length
        if (phoneNumber.length > matchedCountry.length) {
            phoneNumber = phoneNumber.substring(0, matchedCountry.length);
        }
    }
    
    numberInput.value = phoneNumber;
    
    // Update hidden input
    const hiddenInput = countrySelect.closest('.phone-input-container').previousElementSibling;
    if (hiddenInput && hiddenInput.hasAttribute('data-phone-hidden')) {
        updateHiddenInput(countrySelect, numberInput, hiddenInput);
    }
}

// Make functions globally available
window.initializePhoneInputs = initializePhoneInputs;
window.getPhoneValue = getPhoneValue;
window.setPhoneValue = setPhoneValue;
window.wrapPhoneInput = wrapPhoneInput;

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePhoneInputs);
} else {
    initializePhoneInputs();
}
