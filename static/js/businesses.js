(() => {
  const searchInput = document.getElementById('searchInput');
  const categorySelect = document.getElementById('categorySelect');
  const locationSelect = document.getElementById('locationSelect');
  const cards = document.getElementById('cards');
  const emptyState = document.getElementById('emptyState');

  const mapModal = document.getElementById('mapModal');
  const closeMapBtn = document.getElementById('closeMap');
  const mapTitle = document.getElementById('mapTitle');
  let leafletMap = null;
  let currentMarker = null;

  function normalize(str) {
    return (str || '').toString().trim().toLowerCase();
  }

  function filterCards() {
    const q = normalize(searchInput?.value);
    const cat = normalize(categorySelect?.value);
    const loc = normalize(locationSelect?.value);

    let visible = 0;
    Array.from(cards.children).forEach((card) => {
      const name = normalize(card.dataset.name);
      const desc = normalize(card.dataset.desc);
      const category = normalize(card.dataset.category);
      const location = normalize(card.dataset.location);

      const matchesQ = !q || name.includes(q) || desc.includes(q);
      const matchesCat = !cat || category === cat;
      const matchesLoc = !loc || location.includes(loc);

      const show = matchesQ && matchesCat && matchesLoc;
      card.style.display = show ? '' : 'none';
      if (show) visible += 1;
    });

    if (emptyState) emptyState.style.display = visible === 0 ? '' : 'none';
  }

  function setupFilters() {
    if (searchInput) searchInput.addEventListener('input', filterCards);
    if (categorySelect) categorySelect.addEventListener('change', filterCards);
    if (locationSelect) locationSelect.addEventListener('change', filterCards);
  }

  function openMap({ name, desc, lat, lng }) {
    if (!mapModal) return;
    mapModal.classList.add('open');
    if (mapTitle) mapTitle.textContent = name || 'Location';

    const latNum = Number(lat);
    const lngNum = Number(lng);
    if (Number.isNaN(latNum) || Number.isNaN(lngNum)) return;

    setTimeout(() => {
      if (!leafletMap) {
        leafletMap = L.map('map');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(leafletMap);
      }

      leafletMap.setView([latNum, lngNum], 15);
      if (currentMarker) {
        currentMarker.remove();
      }
      currentMarker = L.marker([latNum, lngNum]).addTo(leafletMap);
      currentMarker.bindPopup(`<strong>${name || ''}</strong><br/>${desc || ''}`).openPopup();
      leafletMap.invalidateSize();
    }, 0);
  }

  function closeMap() {
    if (!mapModal) return;
    mapModal.classList.remove('open');
  }

  function setupMapButtons() {
    if (!cards) return;
    cards.addEventListener('click', (e) => {
      const btn = e.target.closest('.view-map');
      if (!btn) return;
      const lat = btn.dataset.lat;
      const lng = btn.dataset.lng;
      const name = btn.dataset.name;
      const desc = btn.dataset.desc;
      openMap({ name, desc, lat, lng });
    });
    if (closeMapBtn) closeMapBtn.addEventListener('click', closeMap);
    if (mapModal) mapModal.addEventListener('click', (e) => {
      // click outside content closes
      if (e.target === mapModal) closeMap();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMap();
    });
  }

  // init
  if (cards) {
    setupFilters();
    setupMapButtons();
    filterCards();
  }
})();

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
