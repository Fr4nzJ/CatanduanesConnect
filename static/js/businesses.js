document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const categoryFilter = document.getElementById('categoryFilter');
    const locationFilter = document.getElementById('locationFilter');
    const listings = document.getElementById('businessListings');
    const viewMapButtons = () => document.querySelectorAll('.view-map-btn');

    let map = null;
    let currentMarker = null;

    function openMapModal(name, lat, lng, desc) {
        const modalEl = document.getElementById('mapModal');
        const modal = new bootstrap.Modal(modalEl);
        document.getElementById('mapModalTitle').textContent = name;
        modal.show();

        setTimeout(() => {
            if (!map) {
                map = L.map('mapContainer');
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19
                }).addTo(map);
            }

            if (currentMarker) {
                map.removeLayer(currentMarker);
            }

            if (!lat || !lng) {
                map.setView([12.5, 124.0], 7); // default region if coords absent
                return;
            }

            map.setView([lat, lng], 14);
            currentMarker = L.marker([lat, lng]).addTo(map).bindPopup(`<strong>${name}</strong><br>${desc || ''}`).openPopup();
        }, 250);
    }

    function applyClientFilters() {
        const q = searchInput.value.trim().toLowerCase();
        const cat = categoryFilter.value;
        const loc = locationFilter.value;

        const cards = document.querySelectorAll('.business-card');
        let visibleCount = 0;
        cards.forEach(card => {
            const name = card.dataset.name || '';
            const category = card.dataset.category || '';
            const location = card.dataset.location || '';

            const matchesSearch = !q || name.includes(q) || (card.textContent || '').toLowerCase().includes(q);
            const matchesCategory = !cat || category === cat;
            const matchesLocation = !loc || location === loc;

            if (matchesSearch && matchesCategory && matchesLocation) {
                card.style.display = '';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        if (visibleCount === 0) {
            listings.innerHTML = '<div class="col-12"><div class="alert alert-info">No businesses found.</div></div>';
        }
    }

    // Attach events
    searchBtn.addEventListener('click', applyClientFilters);
    searchInput.addEventListener('keyup', function (e) {
        if (e.key === 'Enter') applyClientFilters();
    });
    categoryFilter.addEventListener('change', applyClientFilters);
    locationFilter.addEventListener('change', applyClientFilters);

    document.body.addEventListener('click', function (e) {
        const target = e.target.closest('.view-map-btn');
        if (target) {
            const lat = parseFloat(target.dataset.lat);
            const lng = parseFloat(target.dataset.lng);
            const name = target.dataset.name;
            const desc = target.dataset.desc;
            openMapModal(name, lat, lng, desc);
        }
    });
});
