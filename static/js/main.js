// =============================================================
// Sidebar toggle (mobile)
// =============================================================
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');
const openBtn = document.getElementById('openSidebarBtn');
const closeBtn = document.getElementById('closeSidebarBtn');

function openSidebar() {
  sidebar.classList.remove('-translate-x-full');
  overlay.classList.remove('hidden');
}
function closeSidebar() {
  sidebar.classList.add('-translate-x-full');
  overlay.classList.add('hidden');
}
if (openBtn) openBtn.addEventListener('click', openSidebar);
if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
if (overlay) overlay.addEventListener('click', closeSidebar);

// =============================================================
// Modal helper (dipakai semua halaman)
// =============================================================
function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}
function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}
// Klik area gelap di luar modal untuk menutup
document.addEventListener('click', function (e) {
  if (e.target.classList.contains('fixed') && e.target.classList.contains('modal-backdrop')) {
    e.target.classList.add('hidden');
    e.target.classList.remove('flex');
  }
});

// Tombol Esc untuk menutup modal yang sedang terbuka
document.addEventListener('keydown', function (e) {
  if (e.key !== 'Escape') return;
  document.querySelectorAll('.fixed.modal-backdrop.flex').forEach(function (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  });
});

// =============================================================
// Toast: auto-hilang setelah beberapa detik
// =============================================================
document.querySelectorAll('#toastContainer .toast').forEach(function (toast, i) {
  setTimeout(function () {
    toast.style.transition = 'opacity .3s ease, transform .3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(8px)';
    setTimeout(function () { toast.remove(); }, 300);
  }, 4500 + i * 300);
});

// =============================================================
// Chained Dropdown Kategori -> Sub Kategori (vanilla JS, fetch API)
// =============================================================
async function loadSubKategori(selectKategoriEl, targetSelectId, selectedSubId) {
  const targetSelect = document.getElementById(targetSelectId);
  const kategoriId = selectKategoriEl.value;
  targetSelect.innerHTML = '<option value="">Memuat...</option>';

  if (!kategoriId) {
    targetSelect.innerHTML = '<option value="">Pilih Kategori dulu</option>';
    return;
  }

  try {
    const res = await fetch(`/api/sub-kategori/${kategoriId}`);
    const data = await res.json();
    targetSelect.innerHTML = '<option value="">Pilih Sub Kategori</option>';
    data.forEach(sub => {
      const opt = document.createElement('option');
      opt.value = sub.id;
      opt.textContent = sub.nama;
      if (selectedSubId && String(selectedSubId) === String(sub.id)) opt.selected = true;
      targetSelect.appendChild(opt);
    });
  } catch (err) {
    targetSelect.innerHTML = '<option value="">Gagal memuat sub-kategori</option>';
  }
}

// Pasang listener ke semua select kategori yang ada class .kategoriSelect
document.addEventListener('change', function (e) {
  if (e.target.classList.contains('kategoriSelect')) {
    loadSubKategori(e.target, e.target.dataset.target);
  }
});

// =============================================================
// Chained Dropdown Gedung -> Lantai -> Ruangan (filter lanjutan Data Aset)
// =============================================================
async function loadLantai(selectGedungEl, targetSelectId, selectedLantai) {
  const targetSelect = document.getElementById(targetSelectId);
  if (!targetSelect) return;
  const gedung = selectGedungEl.value;
  targetSelect.innerHTML = '<option value="">Memuat...</option>';

  if (!gedung) {
    targetSelect.innerHTML = '<option value="">Pilih Gedung dulu</option>';
    return;
  }

  try {
    const res = await fetch(`/api/lantai?gedung=${encodeURIComponent(gedung)}`);
    const data = await res.json();
    targetSelect.innerHTML = '<option value="">Semua Lantai</option>';
    data.forEach(lt => {
      const opt = document.createElement('option');
      opt.value = lt;
      opt.textContent = `Lantai ${lt}`;
      if (selectedLantai && String(selectedLantai) === String(lt)) opt.selected = true;
      targetSelect.appendChild(opt);
    });
  } catch (err) {
    targetSelect.innerHTML = '<option value="">Gagal memuat lantai</option>';
  }
}

async function loadRuangan(selectGedungEl, lantaiSelectId, targetSelectId, selectedRuangan) {
  const targetSelect = document.getElementById(targetSelectId);
  if (!targetSelect) return;
  const gedung = selectGedungEl.value;
  const lantaiEl = document.getElementById(lantaiSelectId);
  const lantai = lantaiEl ? lantaiEl.value : '';
  targetSelect.innerHTML = '<option value="">Memuat...</option>';

  if (!gedung) {
    targetSelect.innerHTML = '<option value="">Pilih Gedung dulu</option>';
    return;
  }

  try {
    const params = new URLSearchParams({ gedung });
    if (lantai) params.set('lantai', lantai);
    const res = await fetch(`/api/ruangan?${params.toString()}`);
    const data = await res.json();
    targetSelect.innerHTML = '<option value="">Semua Ruangan</option>';
    data.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r;
      opt.textContent = r;
      if (selectedRuangan && String(selectedRuangan) === String(r)) opt.selected = true;
      targetSelect.appendChild(opt);
    });
  } catch (err) {
    targetSelect.innerHTML = '<option value="">Gagal memuat ruangan</option>';
  }
}

// =============================================================
// Polling jumlah notifikasi setiap 30 detik (opsional, ringan)
// =============================================================
setInterval(async () => {
  const bellBadge = document.querySelector('header a[title="Notifikasi"] span');
  try {
    const res = await fetch('/api/notifikasi/count');
    const data = await res.json();
    if (bellBadge) {
      if (data.count > 0) {
        bellBadge.textContent = data.count;
        bellBadge.classList.remove('hidden');
      } else {
        bellBadge.classList.add('hidden');
      }
    }
  } catch (err) { /* diamkan jika gagal, tidak kritikal */ }
}, 30000);

// =============================================================
// FUNGSI UNTUK DROPDOWN DINAMIS (untuk form tiket)
// =============================================================

// Fungsi load lantai berdasarkan gedung (khusus form TIKET, bukan filter Data Aset).
// PENTING: nama fungsi ini SENGAJA dibuat beda (loadLantaiTiket) dari loadLantai()
// di atas -- sebelumnya sama-sama bernama loadLantai dan keduanya menempel ke
// `window`, jadi fungsi ini menimpa fungsi loadLantai() versi filter Data Aset
// (karena dieksekusi belakangan). Akibatnya filter Lantai di Data Aset selalu
// gagal/kosong walau Gedung sudah dipilih.
window.loadLantaiTiket = function(gedung, lantaiTargetId, ruanganTargetId, asetTargetId) {
  const lantaiEl = document.getElementById(lantaiTargetId);
  if (!lantaiEl) return;
  
  if (!gedung) {
    lantaiEl.innerHTML = '<option value="">Pilih Gedung</option>';
    return;
  }
  
  fetch(`/api/lantai?gedung=${encodeURIComponent(gedung)}`)
    .then(res => res.json())
    .then(data => {
      lantaiEl.innerHTML = '<option value="">Pilih Lantai</option>';
      data.forEach(lt => {
        const opt = document.createElement('option');
        opt.value = lt;
        opt.textContent = `Lantai ${lt}`;
        lantaiEl.appendChild(opt);
      });
      // Reset ruangan & aset
      if (ruanganTargetId) {
        const ruanganEl = document.getElementById(ruanganTargetId);
        if (ruanganEl) ruanganEl.innerHTML = '<option value="">Pilih Lantai dulu</option>';
      }
      if (asetTargetId) {
        const asetEl = document.getElementById(asetTargetId);
        if (asetEl) asetEl.innerHTML = '<p class="text-xs text-slate-400">Pilih lokasi terlebih dahulu</p>';
      }
    });
};

// Fungsi load ruangan berdasarkan gedung + lantai
window.loadRuanganByGedungLantai = function(gedungId, lantaiId, ruanganTargetId, asetTargetId) {
  const gedungEl = document.getElementById(gedungId);
  const lantaiEl = document.getElementById(lantaiId);
  const ruanganEl = document.getElementById(ruanganTargetId);
  if (!ruanganEl || !gedungEl) return;
  
  const gedung = gedungEl.value;
  const lantai = lantaiEl ? lantaiEl.value : '';
  
  if (!gedung) {
    ruanganEl.innerHTML = '<option value="">Pilih Gedung</option>';
    return;
  }
  
  let url = `/api/ruangan?gedung=${encodeURIComponent(gedung)}`;
  if (lantai) url += `&lantai=${encodeURIComponent(lantai)}`;
  
  fetch(url)
    .then(res => res.json())
    .then(data => {
      ruanganEl.innerHTML = '<option value="">Pilih Ruangan</option>';
      data.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r;
        opt.textContent = r;
        ruanganEl.appendChild(opt);
      });
      // Reset aset
      if (asetTargetId) {
        const asetEl = document.getElementById(asetTargetId);
        if (asetEl) asetEl.innerHTML = '<p class="text-xs text-slate-400">Pilih ruangan terlebih dahulu</p>';
      }
    });
};

// Fungsi load aset berdasarkan lokasi
window.loadAsetByLokasi = function(gedungId, lantaiId, ruanganId, asetTargetId) {
  const gedungEl = document.getElementById(gedungId);
  const lantaiEl = document.getElementById(lantaiId);
  const ruanganEl = document.getElementById(ruanganId);
  const asetEl = document.getElementById(asetTargetId);
  if (!asetEl || !gedungEl) return;
  
  const gedung = gedungEl.value;
  const lantai = lantaiEl ? lantaiEl.value : '';
  const ruangan = ruanganEl ? ruanganEl.value : '';
  
  if (!gedung || !ruangan) {
    asetEl.innerHTML = '<p class="text-xs text-slate-400">Pilih ruangan terlebih dahulu</p>';
    return;
  }
  
  let url = `/api/aset-by-lokasi?gedung=${encodeURIComponent(gedung)}`;
  if (lantai) url += `&lantai=${encodeURIComponent(lantai)}`;
  if (ruangan) url += `&ruangan=${encodeURIComponent(ruangan)}`;
  
  fetch(url)
    .then(res => res.json())
    .then(data => {
      if (data.length === 0) {
        asetEl.innerHTML = '<p class="text-xs text-slate-400">Tidak ada aset di lokasi ini</p>';
        return;
      }
      asetEl.innerHTML = '';
      data.forEach(a => {
        const label = document.createElement('label');
        label.className = 'flex items-center gap-2 text-sm text-slate-600 px-1.5 py-1 rounded-lg hover:bg-slate-50';
        label.innerHTML = `
          <input type="checkbox" name="aset_ids[]" value="${a.id}" class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500">
          <span class="font-mono text-[11px] text-slate-400">${a.kode}</span> ${a.nama}
        `;
        asetEl.appendChild(label);
      });
    });
};
