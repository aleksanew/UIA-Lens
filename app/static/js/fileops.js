// File operations for editor: New/Open/Save/Save As
(function(){
  function $(sel){ return document.querySelector(sel); }

  async function postJSON(url, body){
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
    const text = await res.text();
    let json;
    try { json = JSON.parse(text); } catch {_=>{}}
    if (!res.ok) {
      throw new Error(json?.message || text || `HTTP ${res.status}`);
    }
    return json || {};
  }

  async function getJSON(url){
    const res = await fetch(url, { method: 'GET' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function reloadEditor(){
    // Ensure we are on editor after operations that change pid
    window.location.assign('/api/v1/editor');
  }

  // New Project
  const btnNew = $('#file-new');
  btnNew?.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      await postJSON('/api/v1/files/new');
      reloadEditor();
    } catch (err) {
      alert('New project failed: ' + err.message);
    }
  });

  // Open Local
  const inputOpen = $('#file-open-input');
  const btnOpenLocal = $('#file-open-local');
  btnOpenLocal?.addEventListener('click', (e) => {
    e.preventDefault();
    inputOpen?.click();
  });
  function isImageFile(file){
    if (!file || !file.name) return false;
    return /\.(png|jpe?g|bmp|tiff?|webp)$/i.test(file.name);
  }

  inputOpen?.addEventListener('change', async () => {
    if (!inputOpen.files || inputOpen.files.length === 0) return;
    const file = inputOpen.files[0];
    const fd = new FormData();
    fd.append('file', file);
    const url = isImageFile(file) ? '/api/v1/files/import-layer' : '/api/v1/files/open';
    try {
      const res = await fetch(url, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      reloadEditor();
    } catch (err) {
      alert('Open failed: ' + err.message);
    } finally {
      inputOpen.value = '';
    }
  });

  // Open from storage
  const btnOpenStorage = $('#file-open-storage');
  btnOpenStorage?.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      const data = await getJSON('/api/v1/files/recent');
      const projects = Array.isArray(data.projects) ? data.projects : [];
      if (projects.length === 0){
        alert('No projects found in storage.');
        return;
      }

      // Build quick selection list
      const lines = projects.map((p, i) => {
        const id = p.id || p.pid || 'unknown';
        const name = p.name || '(untitled)';
        return `${i+1}. ${name}`;
      });
      const answer = prompt('Open project by number or pid:\n' + lines.join('\n'));
      if (answer === null) return;

      let pid = answer.trim();
      const idx = parseInt(pid, 10);
      if (!isNaN(idx) && idx >= 1 && idx <= projects.length){
        const chosen = projects[idx - 1];
        pid = chosen.id || chosen.pid;
      }
      if (!pid){
        alert('Invalid selection.');
        return;
      }

      await postJSON('/api/v1/files/open_by_pid', { pid });
      reloadEditor();
    } catch (err) {
      alert('Open from storage failed: ' + err.message);
    }
  });

  // Save removed (autosave via layer/tool routes). Use Save As or Export instead.

  // Save As
  const btnSaveAs = $('#file-save-as');
  btnSaveAs?.addEventListener('click', async (e) => {
    e.preventDefault();
    const name = prompt('Save as (name):', 'copy');
    if (name === null) return;
    try {
      await postJSON('/api/v1/files/save-as', { name });
      reloadEditor();
    } catch (err) {
      alert('Save As failed: ' + err.message);
    }
  });

  const btnProps = $('#file-properties');
  btnProps?.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      const data = await getJSON('/api/v1/files/properties');
      const project = data.project || {};
      const dims = project.canvas;
      const layerCount = project.layer_count ?? 'unknown';
      const sizeBytes = project.file_size_bytes;
      const pixel = project.pixel_stats;
      const sizeText = typeof sizeBytes === 'number' ? formatBytes(sizeBytes) : 'unknown';
      const lines = [
        `Name: ${project.name || '(unnamed)'}`,
        `Layers: ${layerCount}`,
        dims ? `Canvas: ${dims.width} × ${dims.height}px` : 'Canvas: unknown',
        `Project size: ${sizeText}`,
      ];
      if (pixel){
        lines.push(
          `Pixel mean (RGBA): ${pixel.mean?.join(', ')}`,
          `Pixel min (RGBA): ${pixel.min?.join(', ')}`,
          `Pixel max (RGBA): ${pixel.max?.join(', ')}`
        );
      }
      alert(lines.join('\n'));
    } catch (err){
      alert('Properties failed: ' + err.message);
    }
  });

  // Projects list in editor window
  const listEl = $('#projects-list');
  const refreshBtn = $('#projects-refresh');

  function projectLabel(p){
    const id = p.id || p.pid || 'unknown';
    const name = p.name || '(untitled)';
    return { id, name };
  }

  function renderProjects(projects){
    if (!listEl) return;
    listEl.innerHTML = '';
    if (!Array.isArray(projects) || projects.length === 0){
      const empty = document.createElement('div');
      empty.className = 'projects-empty';
      empty.textContent = 'No projects';
      listEl.appendChild(empty);
      return;
    }
    projects.forEach(p => {
      const { id, name } = projectLabel(p);
      const item = document.createElement('button');
      item.className = 'project-item';
      item.title = `${name} (${id})`;
      item.textContent = name;
      item.addEventListener('click', async () => {
        try {
          await postJSON('/api/v1/files/open_by_pid', { pid: id });
          reloadEditor();
        } catch (err){
          alert('Open failed: ' + err.message);
        }
      });
      listEl.appendChild(item);
    });
  }

  async function loadProjects(){
    try {
      const data = await getJSON('/api/v1/files/recent');
      renderProjects(data.projects || []);
    } catch (err){
      if (listEl){
        listEl.innerHTML = '<div class="projects-error">Failed to load projects</div>';
      }
    }
  }

  refreshBtn?.addEventListener('click', (e) => { e.preventDefault(); loadProjects(); });
  // Load on first paint
  if (listEl) loadProjects();

  function formatBytes(bytes){
    if (typeof bytes !== 'number' || bytes < 0) return 'unknown';
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
  }
})();
