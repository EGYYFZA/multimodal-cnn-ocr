const form = document.getElementById('f');
const imgInput = document.getElementById('img');
const vidInput = document.getElementById('vid');
const imgName = document.getElementById('imgname');
const vidName = document.getElementById('vidname');
const imgPrev = document.getElementById('imgprev');
const imgUploadBtn = document.getElementById('imgUploadBtn');
const vidUploadBtn = document.getElementById('vidUploadBtn');
const imgFileInput = document.getElementById('imgFileInput');
const vidFileInput = document.getElementById('vidFileInput');

const loading = document.getElementById('loading');
const result = document.getElementById('result');
const probText = document.getElementById('probtext');
const bar = document.getElementById('bar');
const ocrInfo = document.getElementById('ocrInfo');
const ocrTextBox = document.getElementById('ocrTextBox');
const mode = document.getElementById('mode');
const modeInfo = document.getElementById('modeInfo');
const evidenceList = document.getElementById('evidenceList');

function esc(s){
  return (s || '').toString()
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function num(x, fallback=0){
  const v = Number(x);
  return Number.isFinite(v) ? v : fallback;
}

function badge(label){
  const cls = (label === 'HOAKS') ? 'badge-hoax' : (label === 'VALID' ? 'badge-valid' : 'badge-error');
  return `<span class="badge ${cls}">${esc(label)}</span>`;
}

function setBar(p){
  const pct = Math.max(0, Math.min(1, p)) * 100;
  bar.style.width = pct.toFixed(2) + '%';
}

function renderEvidence(items){
  if (!evidenceList) return;
  if (!items || !items.length){
    evidenceList.innerHTML = '<div class="small">Tidak ada berita yang mirip pada dataset.</div>';
    return;
  }
  evidenceList.innerHTML = '<ul class="ev-list-compact">' + items.map((it, idx) => {
    const score = num(it.score, 0);
    const pct = (score * 100).toFixed(0);
    const title = esc(it.title || '(tanpa judul)');
    const url = (it.url || '').toString().trim();

    const titleHTML = url
      ? `<a href="${esc(url)}" target="_blank" rel="noopener" class="ev-link-compact">${title}</a>`
      : `<span class="ev-text-compact">${title}</span>`;

    return `
      <li class="ev-item-compact">
        <div class="ev-num">${idx + 1}</div>
        <div class="ev-content">
          <div class="ev-title-compact">${titleHTML}</div>
          <div class="ev-score">${pct}% mirip</div>
        </div>
      </li>
    `;
  }).join('') + '</ul>';
}

// File input UI
imgInput.addEventListener('change', () => {
  const f = imgInput.files && imgInput.files[0];
  if (f) {
    imgName.textContent = f.name;
    imgUploadBtn.textContent = '✕';
    imgUploadBtn.classList.add('btn-remove');
    imgUploadBtn.classList.remove('btn-subtle');
    imgFileInput.style.cursor = 'default';

    const url = URL.createObjectURL(f);
    imgPrev.src = url;
    imgPrev.style.display = 'block';
  } else {
    imgName.textContent = '(tidak ada file)';
    imgUploadBtn.textContent = 'Pilih';
    imgUploadBtn.classList.remove('btn-remove');
    imgUploadBtn.classList.add('btn-subtle');
    imgFileInput.style.cursor = 'pointer';
    imgPrev.style.display = 'none';
  }
});

vidInput.addEventListener('change', () => {
  const f = vidInput.files && vidInput.files[0];
  if (f) {
    vidName.textContent = f.name;
    vidUploadBtn.textContent = '✕';
    vidUploadBtn.classList.add('btn-remove');
    vidUploadBtn.classList.remove('btn-subtle');
    vidFileInput.style.cursor = 'default';
  } else {
    vidName.textContent = '(tidak ada file)';
    vidUploadBtn.textContent = 'Pilih';
    vidUploadBtn.classList.remove('btn-remove');
    vidUploadBtn.classList.add('btn-subtle');
    vidFileInput.style.cursor = 'pointer';
  }
});

imgUploadBtn.addEventListener('click', (e) => {
  if (imgUploadBtn.textContent === '✕') {
    e.preventDefault();
    e.stopPropagation();
    imgInput.value = '';
    imgName.textContent = '(tidak ada file)';
    imgUploadBtn.textContent = 'Pilih';
    imgUploadBtn.classList.remove('btn-remove');
    imgUploadBtn.classList.add('btn-subtle');
    imgFileInput.style.cursor = 'pointer';
    imgPrev.style.display = 'none';
  }
});

vidUploadBtn.addEventListener('click', (e) => {
  if (vidUploadBtn.textContent === '✕') {
    e.preventDefault();
    e.stopPropagation();
    vidInput.value = '';
    vidName.textContent = '(tidak ada file)';
    vidUploadBtn.textContent = 'Pilih';
    vidUploadBtn.classList.remove('btn-remove');
    vidUploadBtn.classList.add('btn-subtle');
    vidFileInput.style.cursor = 'pointer';
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const hasText = (form.title.value.trim() || form.body.value.trim());
  const hasImage = imgInput.files && imgInput.files.length > 0;
  const hasVideo = vidInput.files && vidInput.files.length > 0;

  if (!hasText && !hasImage && !hasVideo) {
    result.innerHTML = `${badge('ERROR')} <b>Masukkan minimal satu input: teks, gambar, atau video.</b>`;
    return;
  }

  loading.style.display = 'inline';
  result.innerHTML = 'Memproses…';
  setBar(0);
  probText.textContent = '0.0000';
  ocrInfo.style.display = 'none';
  ocrTextBox.textContent = '(tidak ada teks)';
  mode.textContent = '';
  if (evidenceList) evidenceList.innerHTML = '<div class="small">Mencari bukti dari dataset…</div>';

  const fd = new FormData(form);

  try {
    const r = await fetch('/api/predict', { method: 'POST', body: fd });
    const data = await r.json();

    if (!r.ok) {
      const msg = data && (data.detail || data.message) ? (data.detail || data.message) : 'Gagal memproses input.';
      result.innerHTML = `${badge('ERROR')} <b>${esc(msg)}</b>`;
      loading.style.display = 'none';
      return;
    }

    const pHoax = num(data.prob_hoax, 0);
    const thr = num(data.threshold_used ?? data.tau, 0.5);

    // Badge dengan warning jika ada
    let resultHTML = `${badge(data.label)}`;
    
    // Tambahkan warning untuk teks pendek
    if (data.warning) {
      resultHTML += `<div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; font-size: 14px; color: #856404;">${esc(data.warning)}</div>`;
    }
    
    result.innerHTML = resultHTML;

    // Progress bar & text dengan mode info
    setBar(pHoax);
    const modeText = data.mode === 'HYBRID-EVIDENCE' ? ' (Hybrid)' : '';
    probText.textContent = `${pHoax.toFixed(4)} • thr ${thr.toFixed(2)} • ${(pHoax*100).toFixed(1)}%${modeText}`;

    // OCR info - tampilkan jika digunakan
    if (data.used_ocr && data.ocr_snippet) {
      ocrInfo.style.display = 'block';
      ocrTextBox.textContent = data.ocr_snippet;
    } else {
      ocrInfo.style.display = 'none';
    }

    // Mode info
    const parts = [];
    if (data.mode) parts.push(data.mode);
    if (data.output_mode) parts.push(data.output_mode);
    parts.push(`thr=${thr.toFixed(2)}`);
    mode.textContent = parts.length ? `${parts.join(' • ')}` : '';

    renderEvidence(data.evidence);
  } catch (err) {
    result.innerHTML = `${badge('ERROR')} <b>Terjadi error koneksi / server.</b>`;
  } finally {
    loading.style.display = 'none';
  }
});

// Modal guide
const bd = document.getElementById('guideBackdrop');
const openers = [document.getElementById('btnGuide'), document.getElementById('btnGuideTop')].filter(Boolean);
const closer = document.getElementById('closeGuide');

function openGuide(){ bd.style.display = 'flex'; }
function closeGuide(){ bd.style.display = 'none'; }

openers.forEach(el => el.addEventListener('click', openGuide));
closer.addEventListener('click', closeGuide);
bd.addEventListener('click', (e) => { if (e.target === bd) closeGuide(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && bd.style.display === 'flex') closeGuide(); });

// Header scroll effect
const topbar = document.querySelector('.topbar');
window.addEventListener('scroll', () => {
  if (window.scrollY > 50) topbar.classList.add('scrolled');
  else topbar.classList.remove('scrolled');
});