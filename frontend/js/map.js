// Map initialization and functionality
function initMap() {
    // Center map on India
    const map = L.map('map').setView([20.5937, 78.9629], 5);
    
    // Add base layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Add hazard markers (sample data)
    const hazards = [
        {lat: 13.0827, lng: 80.2707, type: 'tsunami', title: 'Chennai Tsunami Alert', severity: 'high'},
        {lat: 19.0760, lng: 72.8777, type: 'flood', title: 'Mumbai Flooding', severity: 'medium'},
        {lat: 19.8135, lng: 85.8312, type: 'cyclone', title: 'Puri Cyclone Warning', severity: 'high'},
        {lat: 8.5241, lng: 76.9366, type: 'tsunami', title: 'Kerala High Waves', severity: 'low'},
        {lat: 22.5726, lng: 88.3639, type: 'flood', title: 'Kolkata Water Logging', severity: 'medium'},
        {lat: 15.2993, lng: 74.1240, type: 'storm_surge', title: 'Goa Coastal Erosion', severity: 'low'},
        {lat: 16.5062, lng: 80.6480, type: 'flood', title: 'Vijayawada River Flood', severity: 'high'}
    ];
    
    // Create custom icons for different hazard types
    const iconColors = {
        tsunami: 'red',
        cyclone: 'orange',
        flood: 'blue',
        storm_surge: 'purple',
        default: 'gray'
    };
    
    // Create icon based on hazard type
    function createIcon(type) {
        const color = iconColors[type] || iconColors.default;
        return L.divIcon({
            className: `hazard-marker ${type}`,
            html: `<div style="background-color: ${color}; 
                              width: 20px; 
                              height: 20px; 
                              border-radius: 50%; 
                              border: 2px solid white;
                              box-shadow: 0 0 0 3px ${color}80"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
    }
    
    // Add markers to map
    hazards.forEach(hazard => {
        const marker = L.marker([hazard.lat, hazard.lng], {
            icon: createIcon(hazard.type)
        }).addTo(map);
        
        marker.bindPopup(`
            <div class="map-popup">
                <h3>${hazard.title}</h3>
                <p>Type: ${hazard.type}</p>
                <p>Severity: ${hazard.severity}</p>
                <button class="btn-primary view-details">View Details</button>
            </div>
        `);
    });
    
    // Add coastline highlighting
    // This would typically come from a GeoJSON file in a real implementation
    const coastlineCoords = [
        // Simplified Indian coastline coordinates
        [8.0883, 77.5385], [9.2833, 79.3000], [10.7667, 79.8333], 
        [13.0839, 80.2700], [15.9129, 80.4670], [18.9667, 72.8333],
        [20.4167, 72.8333], [22.0000, 69.0000], [23.0000, 68.0000]
    ];
    
    L.polyline(coastlineCoords, {color: 'blue', weight: 2}).addTo(map);
    
    // Add legend
    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'info legend');
        div.innerHTML = `
            <h4>Hazard Legend</h4>
            <div><span style="background-color: red"></span> Tsunami</div>
            <div><span style="background-color: orange"></span> Cyclone</div>
            <div><span style="background-color: blue"></span> Flood</div>
            <div><span style="background-color: purple"></span> Storm Surge</div>
        `;
        return div;
    };
    legend.addTo(map);
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    initMap();
});