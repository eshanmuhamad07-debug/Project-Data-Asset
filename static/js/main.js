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
// (modal konfirmasi hapus 2-tahap punya animasi sendiri, jadi di-skip di sini
// supaya tidak menutup mendadak/kaku -- lihat handler khusus di bagian bawah file)
document.addEventListener('click', function (e) {
  if (e.target.id === 'deleteConfirmModal') return;
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
  // Modal konfirmasi hapus ditutup lewat fungsinya sendiri biar animasinya smooth
  const deleteModal = document.getElementById('deleteConfirmModal');
  if (deleteModal && deleteModal.classList.contains('modal-open')) {
    closeDeleteModal();
  }
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
        label.className = 'flex items-center gap-2 text-sm text-slate-600 px-1.5 py-1 rounded-lg hover:bg-slate-50 cursor-pointer';
        label.innerHTML = `
          <input type="radio" name="aset_ids" value="${a.id}" class="rounded-full border-slate-300 text-indigo-600 focus:ring-indigo-500">
          <span class="font-mono text-[11px] text-slate-400">${a.kode}</span> ${a.nama}
        `;
        asetEl.appendChild(label);
      });
    });
};

// =============================================================
// LOADING SCREEN UNTUK IMPORT EXCEL (Tidak mencolok)
// =============================================================
let importProgressInterval = null;

function showImportLoading() {
  const overlay = document.getElementById('importLoadingOverlay');
  const progressBar = document.getElementById('importProgressBar');
  const progressText = document.getElementById('importProgressText');
  
  if (!overlay) return;
  
  // Reset progress
  if (progressBar) progressBar.style.width = '0%';
  if (progressText) progressText.textContent = 'Mohon tunggu, proses ini bisa memakan waktu beberapa saat';
  
  // Tampilkan overlay
  overlay.classList.remove('hidden');
  overlay.style.opacity = '0';
  
  // Animasi fade in
  setTimeout(() => {
    overlay.style.opacity = '1';
  }, 50);
  
  // Simulasi progress (visual saja)
  let progress = 0;
  if (importProgressInterval) clearInterval(importProgressInterval);
  
  importProgressInterval = setInterval(() => {
    if (progress < 90) {
      progress += Math.random() * 6 + 1;
      if (progress > 90) progress = 90;
      if (progressBar) progressBar.style.width = progress + '%';
    }
    
    // Update teks
    if (progressText) {
      const messages = [
        'Memproses data...',
        'Menganalisis file Excel...',
        'Menyimpan data ke database...',
        'Hampir selesai...'
      ];
      const idx = Math.min(Math.floor(progress / 25), messages.length - 1);
      progressText.textContent = messages[idx] || 'Memproses data...';
    }
  }, 300);
  
  // Simpan waktu mulai untuk fallback
  window._importStartTime = Date.now();
}

function hideImportLoading() {
  const overlay = document.getElementById('importLoadingOverlay');
  if (!overlay) return;
  
  // Animasi fade out
  overlay.style.opacity = '0';
  
  setTimeout(() => {
    overlay.classList.add('hidden');
    // Reset progress
    const progressBar = document.getElementById('importProgressBar');
    if (progressBar) progressBar.style.width = '0%';
    
    // Clear interval
    if (importProgressInterval) {
      clearInterval(importProgressInterval);
      importProgressInterval = null;
    }
  }, 300);
}

// =============================================================
// EVENT LISTENER UNTUK DETECT PAGE UNLOAD & LOAD
// =============================================================

// 1. Saat form submit (sebelum halaman berubah), loading tetap jalan
//    Tapi kita perlu mendeteksi kapan halaman selesai load (redirect kembali)
//    Menggunakan event 'pageshow' yang selalu terpanggil saat halaman muncul
//    (termasuk dari cache)

// 2. Gunakan 'beforeunload' untuk membersihkan interval jika user keluar
window.addEventListener('beforeunload', function() {
  if (importProgressInterval) {
    clearInterval(importProgressInterval);
    importProgressInterval = null;
  }
});

// 3. Gunakan 'pageshow' untuk mendeteksi halaman selesai load (termasuk redirect)
window.addEventListener('pageshow', function(event) {
  // Jika halaman muncul (setelah redirect dari import), sembunyikan loading
  // Cek apakah ada flash message dari import (berarti proses selesai)
  const toastContainer = document.getElementById('toastContainer');
  if (toastContainer && toastContainer.children.length > 0) {
    // Ada flash message → import selesai
    setTimeout(hideImportLoading, 500);
  } else {
    // Tidak ada flash message → cek apakah loading masih aktif
    const overlay = document.getElementById('importLoadingOverlay');
    if (overlay && !overlay.classList.contains('hidden')) {
      // Jika loading masih aktif dan tidak ada flash message, mungkin error
      // Tapi kita tunggu sebentar, bisa jadi flash muncul belakangan
      setTimeout(() => {
        const toastContainer2 = document.getElementById('toastContainer');
        if (toastContainer2 && toastContainer2.children.length > 0) {
          hideImportLoading();
        } else {
          // Jika setelah 2 detik masih tidak ada flash, sembunyikan loading
          // (berarti proses selesai tanpa flash, atau ada error)
          setTimeout(hideImportLoading, 2000);
        }
      }, 1000);
    }
  }
});

// 4. Jika user menekan tombol Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    hideImportLoading();
  }
});

// 5. Double click untuk membatalkan (dengan konfirmasi)
let cancelClickCount = 0;
document.addEventListener('dblclick', function(e) {
  const overlay = document.getElementById('importLoadingOverlay');
  if (overlay && !overlay.classList.contains('hidden')) {
    cancelClickCount++;
    if (cancelClickCount >= 2) {
      if (confirm('Batalkan proses import? (Data yang sudah terproses mungkin tetap tersimpan)')) {
        hideImportLoading();
        cancelClickCount = 0;
      }
    }
    setTimeout(() => { cancelClickCount = 0; }, 3000);
  }
});

// 6. Fallback: jika loading masih muncul setelah 10 detik (tanpa flash)
//    Cek setiap 3 detik apakah ada flash message
setInterval(() => {
  const overlay = document.getElementById('importLoadingOverlay');
  if (overlay && !overlay.classList.contains('hidden')) {
    const toastContainer = document.getElementById('toastContainer');
    if (toastContainer && toastContainer.children.length > 0) {
      hideImportLoading();
    }
  }
}, 3000);

// =============================================================
// KONFIRMASI HAPUS 2 TAHAP (REUSABLE)
// =============================================================
let deleteContext = {};

function openDeleteModal(config) {
  // config = {
  //   title: "Hapus Aset",
  //   message: "Yakin ingin menghapus aset 'TV Samsung'?",
  //   onConfirm: function(reason) { ... }  // fungsi yang dipanggil saat final confirm
  // }
  
  deleteContext = {
    onConfirm: config.onConfirm || function() {},
    reason: ''
  };
  
  // Reset modal ke tahap 1
  document.getElementById('deleteStep1').classList.remove('hidden');
  document.getElementById('deleteStep2').classList.add('hidden');
  document.getElementById('deleteLoading').classList.add('hidden');
  document.getElementById('deleteReason').value = '';
  document.getElementById('deleteReasonPreview').innerHTML = '';  // <-- PAKAI innerHTML
  
  // Set judul & pesan
  document.getElementById('deleteConfirmTitle').textContent = config.title || 'Hapus Data';
  document.getElementById('deleteConfirmSubtitle').textContent = config.subtitle || 'Konfirmasi penghapusan';
  document.getElementById('deleteConfirmMessage').innerHTML = config.message || 'Anda yakin ingin menghapus data ini?';  // <-- PAKAI innerHTML
  
  // Tampilkan modal dengan animasi
  const modal = document.getElementById('deleteConfirmModal');
  modal.style.display = 'flex';
  modal.style.opacity = '0';
  
  // Trigger reflow untuk animasi
  void modal.offsetHeight;
  
  modal.classList.add('modal-open');
  modal.style.opacity = '1';
  
  // Focus ke textarea
  setTimeout(() => {
    document.getElementById('deleteReason').focus();
  }, 300);
}

function closeDeleteModal() {
  const modal = document.getElementById('deleteConfirmModal');
  modal.classList.remove('modal-open');
  modal.style.opacity = '0';
  
  setTimeout(() => {
    modal.style.display = 'none';
  }, 300);
}

// Klik area gelap di luar kotak modal (bukan tombol X/Batal) -> tutup dengan animasi smooth
document.addEventListener('DOMContentLoaded', function () {
  const deleteModalEl = document.getElementById('deleteConfirmModal');
  if (deleteModalEl) {
    deleteModalEl.addEventListener('click', function (e) {
      if (e.target === deleteModalEl) {
        closeDeleteModal();
      }
    });
  }
});

function confirmDeleteStep2() {
  const reason = document.getElementById('deleteReason').value.trim();
  deleteContext.reason = reason || 'Tidak ada alasan';
  
  // Tampilkan alasan di preview
  document.getElementById('deleteReasonPreview').textContent = reason ? `Alasan: "${reason}"` : '(Tidak ada alasan)';
  
  // Pindah ke tahap 2
  document.getElementById('deleteStep1').classList.add('hidden');
  document.getElementById('deleteStep2').classList.remove('hidden');
  
  // Animasi smooth transisi
  const content = document.getElementById('deleteConfirmContent');
  content.style.transition = 'transform 0.2s ease';
  content.style.transform = 'scale(0.97)';
  setTimeout(() => {
    content.style.transform = 'scale(1)';
  }, 50);
}

// Event listener untuk tombol "Ya, Hapus!" (tahap 2)
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('deleteFinalConfirmBtn').addEventListener('click', function() {
    // Pindah ke loading
    document.getElementById('deleteStep2').classList.add('hidden');
    document.getElementById('deleteLoading').classList.remove('hidden');
    
    // Panggil fungsi onConfirm dengan alasan
    if (typeof deleteContext.onConfirm === 'function') {
      deleteContext.onConfirm(deleteContext.reason);
    }
  });
  
  // Enter key di textarea -> lanjut ke step 2
  document.getElementById('deleteReason').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      confirmDeleteStep2();
    }
  });
});

// Fungsi helper untuk menghapus dengan konfirmasi
function confirmDelete(url, data, config) {
  // data = { 
  //   nama: "TV Samsung",
  //   id: 1,
  //   formSelector: "#formDeleteAset" // optional, jika pakai form
  // }
  
  openDeleteModal({
    title: config?.title || 'Hapus Data',
    subtitle: config?.subtitle || 'Konfirmasi penghapusan',
    message: config?.message || `Yakin ingin menghapus data ini?`,
    onConfirm: function(reason) {
      // Submit form atau fetch
      if (data.formSelector) {
        // Pakai form submit
        const form = document.querySelector(data.formSelector);
        if (form) {
          // Tambah input hidden untuk alasan
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = 'delete_reason';
          input.value = reason;
          form.appendChild(input);
          form.submit();
        } else {
          // Fallback: fetch
          fetch(url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: new URLSearchParams({
              'delete_reason': reason
            })
          }).then(() => {
            window.location.reload();
          });
        }
      } else {
        // Fetch langsung
        fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
          },
          body: new URLSearchParams({
            'delete_reason': reason
          })
        }).then(() => {
          window.location.reload();
        });
      }
    }
  });
}

// =============================================================
// KONFIRMASI HAPUS ASET (Reusable)
// =============================================================
function confirmDeleteAset(id, nama) {
  const formId = 'deleteForm_' + id;
  const reasonId = 'deleteReason_' + id;
  
  openDeleteModal({
    title: 'Hapus Aset',
    subtitle: 'Konfirmasi penghapusan',
    message: `Yakin ingin menghapus aset <strong>"${nama}"</strong>?`,
    onConfirm: function(reason) {
      // Isi alasan ke form
      document.getElementById(reasonId).value = reason;
      // Submit form
      document.getElementById(formId).submit();
    }
  });
}