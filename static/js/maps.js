// Leaflet Map Initialization and Controls
let map;
let markers = [];
const DEFAULT_CENTER = [13.3087, 124.0989]; // Catanduanes coordinates
const DEFAULT_ZOOM = 12;

function initMap(elementId, options = {}) {
    map = L.map(elementId).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add location picker if needed
    if (options.locationPicker) {
        let pickedLocation = null;
        map.on('click', function(e) {
            if (pickedLocation) {
                map.removeLayer(pickedLocation);
            }
            pickedLocation = L.marker(e.latlng).addTo(map);
            document.getElementById('latitude').value = e.latlng.lat.toFixed(6);
            document.getElementById('longitude').value = e.latlng.lng.toFixed(6);
        });
    }

    return map;
}

function clearMarkers() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
}

function addJobMarkers(jobs) {
    clearMarkers();
    jobs.forEach(job => {
        if (job.latitude && job.longitude) {
            const marker = L.marker([job.latitude, job.longitude])
                .bindPopup(`
                    <h5>${job.title}</h5>
                    <p><strong>${job.company_name}</strong></p>
                    <p>${job.description.substring(0, 100)}...</p>
                    <a href="/jobs/${job.id}" class="btn btn-sm btn-primary">View Details</a>
                `);
            markers.push(marker);
            marker.addTo(map);
        }
    });
    // Auto-fit bounds if there are markers
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function addServiceMarkers(services) {
    clearMarkers();
    services.forEach(service => {
        if (service.latitude && service.longitude) {
            const marker = L.marker([service.latitude, service.longitude])
                .bindPopup(`
                    <h5>${service.title}</h5>
                    <p>${service.description.substring(0, 100)}...</p>
                    <p><strong>Payment Offer:</strong> ₱${service.payment_offer}</p>
                    <a href="/services/${service.id}" class="btn btn-sm btn-primary">View Details</a>
                `);
            markers.push(marker);
            marker.addTo(map);
        }
    });
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function loadJobsData(filters = {}) {
    const params = new URLSearchParams(filters);
    fetch(`/dashboard/api/map/jobs?${params.toString()}`)
        .then(response => response.json())
        .then(jobs => addJobMarkers(jobs))
        .catch(error => console.error('Error loading jobs:', error));
}

function loadServicesData(filters = {}) {
    const params = new URLSearchParams(filters);
    fetch(`/dashboard/api/map/services?${params.toString()}`)
        .then(response => response.json())
        .then(services => addServiceMarkers(services))
        .catch(error => console.error('Error loading services:', error));
}

function zoomToMarker(lat, lng) {
    map.setView([lat, lng], 15);
    markers.forEach(marker => {
        const markerLatLng = marker.getLatLng();
        if (markerLatLng.lat === lat && markerLatLng.lng === lng) {
            marker.openPopup();
        }
    });
}

function addJobMarkers(jobs) {
    clearMarkers();
    jobs.forEach(job => {
        if (job.latitude && job.longitude) {
            const marker = L.marker([job.latitude, job.longitude])
                .bindPopup(`
                    <h5>${job.title}</h5>
                    <p><strong>${job.company_name}</strong></p>
                    <p>${job.description.substring(0, 100)}...</p>
                    <a href="/jobs/${job.id}" class="btn btn-sm btn-primary">View Details</a>
                `);
            markers.push(marker);
            marker.addTo(map);
        }
    });
    // Auto-fit bounds if there are markers
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function addServiceMarkers(services) {
    clearMarkers();
    services.forEach(service => {
        if (service.latitude && service.longitude) {
            const marker = L.marker([service.latitude, service.longitude])
                .bindPopup(`
                    <h5>${service.title}</h5>
                    <p>${service.description.substring(0, 100)}...</p>
                    <p><strong>Payment Offer:</strong> ₱${service.payment_offer}</p>
                    <a href="/services/${service.id}" class="btn btn-sm btn-primary">View Details</a>
                `);
            markers.push(marker);
            marker.addTo(map);
        }
    });
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function loadJobsData() {
    fetch('/api/map/jobs')
        .then(response => response.json())
        .then(jobs => addJobMarkers(jobs))
        .catch(error => console.error('Error loading jobs:', error));
}

function loadServicesData() {
    fetch('/api/map/services')
        .then(response => response.json())
        .then(services => addServiceMarkers(services))
        .catch(error => console.error('Error loading services:', error));
}

function zoomToMarker(lat, lng) {
    map.setView([lat, lng], 15);
    markers.forEach(marker => {
        const markerLatLng = marker.getLatLng();
        if (markerLatLng.lat === lat && markerLatLng.lng === lng) {
            marker.openPopup();
        }
    });
}