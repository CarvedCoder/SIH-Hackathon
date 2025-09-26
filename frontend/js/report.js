// Modern Report.js - Enhanced version with improved UI integration
document.addEventListener('DOMContentLoaded', function () {
    // Configuration
    const API_BASE_URL = 'http://127.0.0.1:8001';
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    const MAX_FILES = 5;
    
    // DOM Elements
    const reportForm = document.getElementById('hazardReportForm');
    const severitySlider = document.getElementById('severity');
    const severityValue = document.getElementById('severityValue');
    const getCurrentLocationBtn = document.getElementById('getCurrentLocationBtn');
    const statusDiv = document.getElementById('reportStatus');
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    const locationNameInput = document.getElementById('locationName');
    const mediaInput = document.getElementById('mediaFiles');
    const mediaPreview = document.getElementById('mediaPreview');
    const header = document.getElementById('header');
    
    // State
    let map;
    let marker;
    let selectedFiles = [];
    let currentWeatherData = null;
    
    // Initialize page
    initializeHeader();
    initializeMap();
    initializeSeveritySlider();
    initializeFormValidation();
    
    // --- Header Effects ---
    function initializeHeader() {
        if (!header) return;
        
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }
    
    // --- Initialize Map ---
    function initializeMap() {
        const mapElement = document.getElementById('locationMap');
        if (!mapElement || typeof L === 'undefined') {
            console.error('Leaflet map not available');
            return;
        }
        
        // Initialize map centered on India
        map = L.map('locationMap').setView([20.5937, 78.9629], 5);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(map);
        
        // Add search control
        addSearchControl();
        
        // Map click handler
        map.on('click', handleMapClick);
        
        // If the form already has coordinates (prefilled), show them
        const preLat = parseFloat(latInput.value || NaN);
        const preLng = parseFloat(lngInput.value || NaN);
        if (!Number.isNaN(preLat) && !Number.isNaN(preLng)) {
            map.setView([preLat, preLng], 13);
            updateMarker(preLat, preLng);
            fetchWeatherData(preLat, preLng).catch(() => {});
        }
    }
    
    function addSearchControl() {
        if (!map) return;
        
        const searchControl = L.control({ position: 'topright' });
        
        searchControl.onAdd = function(map) {
            const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            div.style.cssText = 'background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 8px;';
            div.innerHTML = `
                <div style="display: flex; gap: 8px; align-items: center;">
                    <input type="text" id="mapSearch" placeholder="Search location..." 
                           style="padding: 6px 8px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); width: 180px; font-size: 12px;">
                    <button type="button" id="searchBtn" class="btn" style="padding: 6px 12px; font-size: 12px;">
                        <i class="fas fa-search"></i>
                    </button>
                </div>
            `;
            
            L.DomEvent.disableClickPropagation(div);
            return div;
        };
        
        searchControl.addTo(map);
        
        // Add search functionality after control is added
        setTimeout(() => {
            const searchBtn = document.getElementById('searchBtn');
            const searchInput = document.getElementById('mapSearch');
            
            if (searchBtn) searchBtn.addEventListener('click', searchLocation);
            if (searchInput) {
                searchInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') searchLocation();
                });
            }
        }, 100);
    }
    
    async function searchLocation() {
        const searchInput = document.getElementById('mapSearch');
        if (!searchInput) return;
        
        const query = searchInput.value.trim();
        if (!query) return;
        
        const searchBtn = document.getElementById('searchBtn');
        if (searchBtn) {
            searchBtn.disabled = true;
            searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&countrycodes=in`);
            const data = await response.json();
            
            if (data && data.length > 0) {
                const result = data[0];
                const lat = parseFloat(result.lat);
                const lon = parseFloat(result.lon);
                
                // Update map and marker
                map.setView([lat, lon], 13);
                updateMarker(lat, lon);
                
                // Update form inputs
                latInput.value = lat.toFixed(6);
                lngInput.value = lon.toFixed(6);
                locationNameInput.value = result.display_name.split(',')[0] || '';
                
                // Fetch weather
                await fetchWeatherData(lat, lon);
                
                showAlert('Location found and selected', 'success');
            } else {
                showAlert('Location not found. Try searching with more specific terms.', 'warning');
            }
        } catch (error) {
            console.error('Search error:', error);
            showAlert('Error searching location. Please try again.', 'danger');
        } finally {
            if (searchBtn) {
                searchBtn.disabled = false;
                searchBtn.innerHTML = '<i class="fas fa-search"></i>';
            }
        }
    }
    
    function handleMapClick(e) {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        
        updateMarker(lat, lng);
        
        // Update form inputs
        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);
        
        // Remove validation classes
        latInput.classList.remove('is-invalid');
        lngInput.classList.remove('is-invalid');
        
        // Reverse geocode to get location name
        reverseGeocode(lat, lng);
        
        // Fetch weather data
        fetchWeatherData(lat, lng).catch(() => {});
        
        showAlert('Location selected successfully', 'success', 2000);
    }
    
    function updateMarker(lat, lng) {
        if (!map) return;
        
        if (marker) {
            marker.setLatLng([lat, lng]);
        } else {
            // Create custom marker icon
            const customIcon = L.divIcon({
                html: '<i class="fas fa-map-marker-alt" style="color: #667eea; font-size: 24px;"></i>',
                iconSize: [24, 24],
                className: 'custom-div-icon'
            });
            
            marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
            marker.bindPopup(`
                <div style="color: #0f172a; font-weight: 500;">
                    <i class="fas fa-map-marker-alt" style="color: #667eea;"></i> Selected Location<br>
                    <small>Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}</small>
                </div>
            `).openPopup();
        }
    }
    
    async function reverseGeocode(lat, lng) {
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1`);
            const data = await response.json();
            
            if (data && data.display_name) {
                const address = data.address || {};
                const locationName = address.village || address.town || address.city || 
                                   address.state_district || address.state || 
                                   data.display_name.split(',')[0] || '';
                locationNameInput.value = locationName;
            }
        } catch (error) {
            console.error('Reverse geocoding error:', error);
        }
    }
    
    // --- Weather Data ---
    async function fetchWeatherData(lat, lng) {
        const weatherDiv = document.getElementById('weatherData');
        if (!weatherDiv) return;
        
        weatherDiv.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner spinner"></i>
                Fetching current weather conditions...
            </div>
        `;
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/weather?lat=${lat}&lon=${lng}`);
            if (!response.ok) throw new Error('Weather service temporarily unavailable');
            
            const data = await response.json();
            currentWeatherData = data;
            
            renderWeatherData(data);
            
            // Store weather data in hidden field
            const weatherInput = document.getElementById('weatherConditions');
            if (weatherInput) {
                weatherInput.value = JSON.stringify(data);
            }
        } catch (error) {
            console.error('Weather fetch error:', error);
            weatherDiv.innerHTML = `
                <div style="text-align: center; color: var(--text-muted);">
                    <i class="fas fa-exclamation-triangle"></i>
                    Weather data temporarily unavailable
                </div>
            `;
            currentWeatherData = null;
        }
    }
    
    function renderWeatherData(data) {
        const weatherDiv = document.getElementById('weatherData');
        if (!weatherDiv) return;
        
        weatherDiv.innerHTML = `
            <div class="weather-data-grid">
                <div class="weather-item">
                    <div><i class="fas fa-thermometer-half"></i> Temperature</div>
                    <strong>${data.temperature || 'N/A'}°C</strong>
                </div>
                <div class="weather-item">
                    <div><i class="fas fa-wind"></i> Wind Speed</div>
                    <strong>${data.wind_speed || 'N/A'} m/s</strong>
                </div>
                <div class="weather-item">
                    <div><i class="fas fa-tint"></i> Humidity</div>
                    <strong>${data.humidity || 'N/A'}%</strong>
                </div>
                <div class="weather-item">
                    <div><i class="fas fa-water"></i> Wave Height</div>
                    <strong>${data.wave_height ? data.wave_height + 'm' : 'N/A'}</strong>
                </div>
                <div class="weather-item">
                    <div><i class="fas fa-eye"></i> Visibility</div>
                    <strong>${data.visibility || 'N/A'} km</strong>
                </div>
                <div class="weather-item">
                    <div><i class="fas fa-cloud"></i> Conditions</div>
                    <strong>${data.weather_description || 'N/A'}</strong>
                </div>
            </div>
        `;
    }
    
    // --- Severity Slider ---
    function initializeSeveritySlider() {
        if (!severitySlider || !severityValue) return;
        
        updateSeverityDisplay(severitySlider.value);
        
        severitySlider.addEventListener('input', function() {
            updateSeverityDisplay(this.value);
        });
    }
    
    function updateSeverityDisplay(value) {
        severityValue.textContent = value;
        
        // Update color and text based on severity
        const severityLabels = {
            1: { label: '1 - Low', color: '#10b981' },
            2: { label: '2 - Mild', color: '#3b82f6' },
            3: { label: '3 - Moderate', color: '#f59e0b' },
            4: { label: '4 - High', color: '#ef4444' },
            5: { label: '5 - Critical', color: '#dc2626' }
        };
        
        const config = severityLabels[value];
        if (config) {
            severityValue.textContent = config.label;
            severityValue.style.background = config.color;
        }
    }
    
    // --- Get Current Location ---
    if (getCurrentLocationBtn) {
        getCurrentLocationBtn.addEventListener('click', function() {
            if (!navigator.geolocation) {
                showAlert('Geolocation is not supported by your browser', 'warning');
                return;
            }
            
            // Update button state
            getCurrentLocationBtn.disabled = true;
            const originalText = getCurrentLocationBtn.innerHTML;
            getCurrentLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting location...';
            
            const options = {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 60000
            };
            
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    // Validate if location is near Indian coastline
                    if (!isNearIndianCoast(lat, lng)) {
                        showAlert('Please select a location near the Indian coastline for ocean hazard reporting', 'warning');
                        getCurrentLocationBtn.disabled = false;
                        getCurrentLocationBtn.innerHTML = originalText;
                        return;
                    }
                    
                    // Update map and marker
                    if (map) map.setView([lat, lng], 13);
                    updateMarker(lat, lng);
                    
                    // Update form inputs
                    latInput.value = lat.toFixed(6);
                    lngInput.value = lng.toFixed(6);
                    
                    // Remove validation classes
                    latInput.classList.remove('is-invalid');
                    lngInput.classList.remove('is-invalid');
                    
                    // Get location name and weather
                    await Promise.all([
                        reverseGeocode(lat, lng),
                        fetchWeatherData(lat, lng)
                    ]);
                    
                    showAlert('Current location retrieved successfully', 'success');
                    getCurrentLocationBtn.disabled = false;
                    getCurrentLocationBtn.innerHTML = originalText;
                },
                (error) => {
                    let message = 'Unable to retrieve your current location.';
                    if (error.code === error.PERMISSION_DENIED) {
                        message = 'Location access denied. Please enable location services and try again.';
                    } else if (error.code === error.TIMEOUT) {
                        message = 'Location request timed out. Please try again or select location manually on the map.';
                    } else if (error.code === error.POSITION_UNAVAILABLE) {
                        message = 'Location information unavailable. Please select location manually on the map.';
                    }
                    
                    showAlert(message, 'danger');
                    getCurrentLocationBtn.disabled = false;
                    getCurrentLocationBtn.innerHTML = originalText;
                },
                options
            );
        });
    }
    
    // --- Media Handling ---
    if (mediaInput && mediaPreview) {
        mediaInput.addEventListener('change', handleMediaSelection);
    }
    
    function handleMediaSelection(e) {
        const files = Array.from(e.target.files);
        
        if (files.length === 0) return;
        
        // Validate file count
        if (selectedFiles.length + files.length > MAX_FILES) {
            showAlert(`Maximum ${MAX_FILES} files allowed. Please remove some files before adding more.`, 'warning');
            return;
        }
        
        files.forEach(file => {
            // Validate file size
            if (file.size > MAX_FILE_SIZE) {
                showAlert(`${file.name} is too large (maximum 10MB allowed)`, 'warning');
                return;
            }
            
            // Validate file type
            if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
                showAlert(`${file.name} is not a valid image or video file`, 'warning');
                return;
            }
            
            // Check for duplicates
            if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                showAlert(`${file.name} is already added`, 'warning');
                return;
            }
            
            // Add to selected files
            selectedFiles.push(file);
            createMediaPreview(file);
        });
        
        updateFileInput();
        updateMediaLabel();
    }
    
    function createMediaPreview(file) {
        const reader = new FileReader();
        const div = document.createElement('div');
        div.className = 'media-preview-item';
        div.setAttribute('data-filename', file.name);
        
        reader.onload = function(e) {
            const displayName = file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name;
            
            if (file.type.startsWith('image/')) {
                div.innerHTML = `
                    <img src="${e.target.result}" alt="${escapeHtml(file.name)}">
                    <button type="button" class="remove-media" title="Remove ${escapeHtml(file.name)}">
                        <i class="fas fa-times"></i>
                    </button>
                    <div style="position: absolute; bottom: 4px; left: 4px; right: 4px; background: rgba(0,0,0,0.7); color: white; font-size: 11px; padding: 2px 4px; border-radius: 4px; text-align: center;">
                        ${escapeHtml(displayName)}
                    </div>
                `;
            } else if (file.type.startsWith('video/')) {
                div.innerHTML = `
                    <video src="${e.target.result}" muted style="pointer-events: none;"></video>
                    <button type="button" class="remove-media" title="Remove ${escapeHtml(file.name)}">
                        <i class="fas fa-times"></i>
                    </button>
                    <div style="position: absolute; bottom: 4px; left: 4px; right: 4px; background: rgba(0,0,0,0.7); color: white; font-size: 11px; padding: 2px 4px; border-radius: 4px; text-align: center;">
                        <i class="fas fa-video"></i> ${escapeHtml(displayName)}
                    </div>
                `;
            }
            
            // Attach remove listener
            const removeBtn = div.querySelector('.remove-media');
            if (removeBtn) {
                removeBtn.addEventListener('click', () => removeMedia(file.name));
            }
            
            mediaPreview.appendChild(div);
        };
        
        reader.readAsDataURL(file);
    }
    
    function removeMedia(fileName) {
        selectedFiles = selectedFiles.filter(f => f.name !== fileName);
        updateFileInput();
        updateMediaLabel();
        
        // Remove preview element
        const preview = mediaPreview.querySelector(`[data-filename="${fileName}"]`);
        if (preview) {
            preview.remove();
        }
        
        showAlert('File removed successfully', 'info', 2000);
    }
    
    function updateFileInput() {
        const dataTransfer = new DataTransfer();
        selectedFiles.forEach(file => dataTransfer.items.add(file));
        mediaInput.files = dataTransfer.files;
    }
    
    function updateMediaLabel() {
        const label = document.querySelector('.file-input-label');
        if (!label) return;
        
        if (selectedFiles.length === 0) {
            label.innerHTML = '<i class="fas fa-upload"></i> Click to upload images and videos';
        } else {
            label.innerHTML = `<i class="fas fa-check"></i> ${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`;
        }
    }
    
    // --- Form Validation ---
    function initializeFormValidation() {
        if (!reportForm) return;
        
        const inputs = reportForm.querySelectorAll('input[required], select[required], textarea[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', clearValidation);
        });
    }
    
    function validateField(e) {
        const field = e.target;
        const isValid = field.checkValidity();
        
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid);
    }
    
    function clearValidation(e) {
        const field = e.target;
        field.classList.remove('is-invalid', 'is-valid');
    }
    
    // --- Form Submission ---
    if (reportForm) {
        reportForm.addEventListener('submit', handleFormSubmit);
        reportForm.addEventListener('reset', handleFormReset);
    }
    
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        // Validate form
        if (!reportForm.checkValidity()) {
            reportForm.classList.add('was-validated');
            showAlert('Please fill in all required fields correctly', 'warning');
            
            // Focus on first invalid field
            const firstInvalid = reportForm.querySelector(':invalid');
            if (firstInvalid) {
                firstInvalid.focus();
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }
        
        // Validate location
        if (!marker || !latInput.value || !lngInput.value) {
            showAlert('Please select a location on the map', 'warning');
            document.getElementById('locationMap').scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        
        if (Number.isNaN(lat) || Number.isNaN(lng) || !isNearIndianCoast(lat, lng)) {
            showAlert('Please select a valid location near the Indian coastline', 'warning');
            return;
        }
        
        const formData = new FormData(reportForm);
        
        // Ensure user_id is set
        if (!formData.get('user_id')) {
            formData.set('user_id', 'anonymous_' + Date.now());
        }
        
        // Update submit button
        const submitBtn = reportForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting report...';
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/reports/submit`, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                
                showAlert('Report submitted successfully!', 'success');
                
                // Show detailed success message
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <h5><i class="fas fa-check-circle"></i> Report Submitted Successfully!</h5>
                        <div style="margin-top: 12px;">
                            <p><strong>Report ID:</strong> ${escapeHtml(data.report_id)}</p>
                            <p><strong>Priority Score:</strong> ${escapeHtml(String(data.priority_score || 'Calculating...'))}</p>
                            ${data.nearby_reports_count > 0 ? 
                                `<p><strong>Similar Reports:</strong> ${data.nearby_reports_count} reports found in nearby areas</p>` : ''}
                            <p style="margin-top: 12px; font-size: 14px; color: var(--success-color);">
                                <i class="fas fa-info-circle"></i> ${data.message || 'Your report has been received and will be processed by our team.'}
                            </p>
                        </div>
                    </div>
                `;
                
                // Scroll to success message
                statusDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Reset form after delay
                setTimeout(() => {
                    handleFormReset();
                }, 3000);
                
            } else {
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.detail || errorData.message || 'Failed to submit report';
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('Submission error:', error);
            showAlert(`Submission failed: ${error.message}`, 'danger');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        }
    }
    
    function handleFormReset() {
        // Reset form
        reportForm.reset();
        reportForm.classList.remove('was-validated');
        
        // Reset validation classes
        const fields = reportForm.querySelectorAll('.is-invalid, .is-valid');
        fields.forEach(field => field.classList.remove('is-invalid', 'is-valid'));
        
        // Reset severity display
        updateSeverityDisplay(3);
        
        // Clear selected files and preview
        selectedFiles = [];
        if (mediaPreview) mediaPreview.innerHTML = '';
        updateMediaLabel();
        
        // Clear marker
        if (marker && map) {
            map.removeLayer(marker);
            marker = null;
        }
        
        // Clear weather display
        const weatherDiv = document.getElementById('weatherData');
        if (weatherDiv) {
            weatherDiv.innerHTML = `
                <div style="text-align: center; color: var(--text-muted);">
                    <i class="fas fa-info-circle"></i>
                    Select a location to view weather conditions
                </div>
            `;
        }
        
        // Clear status messages
        statusDiv.innerHTML = '';
        
        // Reset map view
        if (map) map.setView([20.5937, 78.9629], 5);
        
        currentWeatherData = null;
        
        showAlert('Form reset successfully', 'info', 2000);
    }
    
    // --- Helper Functions ---
    function isNearIndianCoast(lat, lon) {
        // Extended coastal bounds for India including islands
        const bounds = {
            min_lat: 6.0,   // Covers southern islands
            max_lat: 25.0,  // Northern coastal regions
            min_lon: 68.0,  // Western coast
            max_lon: 98.0   // Eastern coast and islands
        };
        
        return lat >= bounds.min_lat && lat <= bounds.max_lat && 
               lon >= bounds.min_lon && lon <= bounds.max_lon;
    }
    
    function showAlert(message, type = 'info', timeout = 5000) {
        if (!statusDiv) {
            console.log(`[${type.toUpperCase()}] ${message}`);
            return;
        }
        
        const alertId = `alert-${Date.now()}`;
        const alertElement = document.createElement('div');
        alertElement.id = alertId;
        alertElement.innerHTML = `
            <div class="alert alert-${escapeHtml(type)} alert-dismissible fade show" role="alert">
                ${getAlertIcon(type)} ${escapeHtml(message)}
                <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        statusDiv.insertBefore(alertElement, statusDiv.firstChild);
        
        if (timeout > 0) {
            setTimeout(() => {
                const el = document.getElementById(alertId);
                if (el) el.remove();
            }, timeout);
        }
    }
    
    function getAlertIcon(type) {
        const icons = {
            success: '<i class="fas fa-check-circle"></i>',
            warning: '<i class="fas fa-exclamation-triangle"></i>',
            danger: '<i class="fas fa-times-circle"></i>',
            info: '<i class="fas fa-info-circle"></i>'
        };
        return icons[type] || icons.info;
    }
    
    function escapeHtml(unsafe) {
        if (unsafe === undefined || unsafe === null) return '';
        return String(unsafe)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }
    
    // --- Page Animations ---
    function initializeAnimations() {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            },
            { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
        );
        
        document.querySelectorAll('.fade-in').forEach(el => {
            observer.observe(el);
        });
    }
    
    // Initialize animations
    initializeAnimations();
    
    // Debug function for testing
    window.debugReport = {
        fetchWeather: () => {
            const lat = parseFloat(latInput.value);
            const lng = parseFloat(lngInput.value);
            if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
                fetchWeatherData(lat, lng);
            } else {
                console.log('No valid coordinates set');
            }
        },
        getSelectedFiles: () => selectedFiles,
        getCurrentWeather: () => currentWeatherData
    };
    
    console.log('🌊 Modern Report Form Initialized');
});