// Oneiric — gallery logic
// Loads dreams.json, builds card grid, handles lightbox.

const DATA_URL = 'data/dreams.json';
const ASSET_BASE = 'public/dreams';

async function loadDreams() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to load dreams.json:', err);
    return [];
  }
}

function createCard(dream) {
  const thumbPath = `${ASSET_BASE}/${dream.id}/${dream.thumbnail || 'card.png'}`;

  const card = document.createElement('article');
  card.className = 'dream-card rounded-xl overflow-hidden bg-oneiric-surface border border-oneiric-muted/10';
  card.dataset.src = thumbPath;
  card.dataset.title = dream.title;

  card.innerHTML = `
    <div class="aspect-[9/16] relative overflow-hidden bg-black">
      <img
        src="${thumbPath}"
        alt="${escapeHtml(dream.title)}"
        loading="lazy"
        class="w-full h-full object-cover"
      >
    </div>
    <div class="p-4">
      <h3 class="serif text-lg text-oneiric-text mb-2 leading-tight">
        ${escapeHtml(dream.title)}
      </h3>
      <div class="flex flex-wrap gap-2 text-xs">
        ${dream.mood ? `<span class="px-2 py-1 rounded-full bg-oneiric-accent/20 text-oneiric-accent">${escapeHtml(dream.mood)}</span>` : ''}
        ${dream.archetype ? `<span class="px-2 py-1 rounded-full bg-oneiric-muted/20 text-oneiric-muted">${escapeHtml(dream.archetype)}</span>` : ''}
        ${dream.is_fictional ? `<span class="px-2 py-1 rounded-full bg-purple-500/20 text-purple-300">fictional</span>` : ''}
      </div>
      <div class="mt-3 text-xs text-oneiric-muted flex justify-between">
        <span>${dream.dreamer || 'anonymous'}</span>
        <span>${dream.date || ''}</span>
      </div>
    </div>
  `;

  card.addEventListener('click', () => openLightbox(thumbPath, dream.title));
  return card;
}

function escapeHtml(str) {
  return String(str || '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[c]);
}

const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxClose = document.getElementById('lightbox-close');

function openLightbox(src, alt) {
  lightboxImg.src = src;
  lightboxImg.alt = alt;
  lightbox.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  lightbox.classList.remove('active');
  document.body.style.overflow = '';
  setTimeout(() => { lightboxImg.src = ''; }, 300);
}

lightboxClose.addEventListener('click', closeLightbox);
lightbox.addEventListener('click', e => {
  if (e.target === lightbox) closeLightbox();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && lightbox.classList.contains('active')) closeLightbox();
});

async function init() {
  const dreams = await loadDreams();
  const grid = document.getElementById('dream-grid');
  const countEl = document.getElementById('dream-count');
  const empty = document.getElementById('empty-state');

  if (!dreams.length) {
    empty.classList.remove('hidden');
    countEl.textContent = '0 dreams';
    return;
  }

  // Sort: newest first
  dreams.sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  dreams.forEach(d => grid.appendChild(createCard(d)));
  countEl.textContent = `${dreams.length} dream${dreams.length !== 1 ? 's' : ''}`;
}

init();
