document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('backendStatus');
  try {
    const res = await fetch('http://127.0.0.1:8000/api/health');
    if (res.ok) {
      statusEl.textContent = 'Online (Ready)';
      statusEl.style.color = '#10b981';
    } else {
      statusEl.textContent = 'Server Error';
      statusEl.style.color = '#f59e0b';
    }
  } catch (e) {
    statusEl.textContent = 'Offline';
    statusEl.style.color = '#ef4444';
  }
});
