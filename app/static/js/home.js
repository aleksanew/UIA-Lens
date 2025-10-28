// Home page: list projects and allow opening or local upload
(function(){
  function $(sel){ return document.querySelector(sel); }

  async function getJSON(url){
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
  async function postJSON(url, body){
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body||{})
    });
    const text = await res.text();
    let json; try { json = JSON.parse(text); } catch {}
    if (!res.ok) throw new Error(json?.message || text || `HTTP ${res.status}`);
    return json || {};
  }

  function reloadEditor(){ window.location.assign('/api/v1/editor'); }

  const listEl = $('#home-projects-list');
  const refreshBtn = $('#home-projects-refresh');

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
      const btn = document.createElement('button');
      btn.className = 'project-item';
      btn.textContent = name;
      btn.title = `${name} (${id})`;
      btn.addEventListener('click', async () => {
        try {
          await postJSON('/api/v1/files/open_by_pid', { pid: id });
          reloadEditor();
        } catch (err){
          alert('Open failed: ' + err.message);
        }
      });
      listEl.appendChild(btn);
    });
  }

  async function loadProjects(){
    try {
      const data = await getJSON('/api/v1/files/recent');
      renderProjects(data.projects || []);
    } catch (err){
      if (listEl) listEl.innerHTML = '<div class="projects-error">Failed to load projects</div>';
    }
  }

  refreshBtn?.addEventListener('click', (e)=>{ e.preventDefault(); loadProjects(); });
  if (listEl) loadProjects();

  // Local open
  const btnOpenLocal = $('#home-open-local');
  const inputOpen = $('#home-open-input');
  btnOpenLocal?.addEventListener('click', (e)=>{ e.preventDefault(); inputOpen?.click(); });
  inputOpen?.addEventListener('change', async ()=>{
    if (!inputOpen.files || inputOpen.files.length === 0) return;
    const file = inputOpen.files[0];
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/v1/files/open', { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      reloadEditor();
    } catch (err){
      alert('Open failed: ' + err.message);
    } finally {
      inputOpen.value = '';
    }
  });
})();

