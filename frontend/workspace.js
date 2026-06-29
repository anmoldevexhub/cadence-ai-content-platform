/* ==========================================================================
   CADENCE — website workspace logic
   ========================================================================== */
(function () {
  const C = window.Cadence, M = window.MOCK, I = C.icon;
  const params = new URLSearchParams(location.search);
  let site = M.site(params.get("site")) || M.websites[0];

  /* ---------- hero ---------- */
  document.getElementById("bcName").textContent = site.name;
  document.getElementById("wsName").textContent = site.name;
  document.getElementById("wsFav").textContent = site.short;
  document.getElementById("wsFav").style.background = site.color;
  const urlEl = document.getElementById("wsUrl");
  urlEl.querySelector("span").textContent = site.url;
  urlEl.href = "https://" + site.url;
  const statusMap = { Active: ["badge-published", "circle-dot", "Active"], Paused: ["badge-scheduled", "pause", "Paused"], Draft: ["badge-draft", "circle-dashed", "Setup"] };
  const [sc, si, st] = statusMap[site.status] || statusMap.Active;
  document.getElementById("wsStatus").innerHTML = `<span class="badge ${sc}">${I(si)} ${st}</span>`;
  document.getElementById("wsStats").innerHTML = [
    ["Published", site.published], ["Scheduled", site.scheduled], ["Pending", site.pending], ["Pages", site.pages],
  ].map(([l, v]) => `<div class="hs"><div class="v mono">${v}</div><div class="l">${l}</div></div>`).join("");
  document.getElementById("visitBtn").addEventListener("click", () => window.open("https://" + site.url, "_blank"));

  /* ---------- overview ---------- */
  const ovStats = [
    { l: "Posts published", v: site.published, d: site.engagement, icon: "send", tile: "blog" },
    { l: "Scheduled", v: site.scheduled, d: "this week", icon: "calendar-clock", tile: "linkedin" },
    { l: "Pending approval", v: site.pending, d: "needs review", icon: "clock", tile: "youtube" },
    { l: "Total posts", v: site.posts, d: "all time", icon: "layers", tile: "instagram" },
  ];
  document.getElementById("ovStats").innerHTML = ovStats.map(s => `
    <div class="stat"><div class="stat-top"><span class="stat-label">${s.l}</span><span class="stat-ic icon-tile tile-${s.tile}">${I(s.icon)}</span></div>
      <div class="stat-val mono">${s.v}</div><div class="stat-delta delta-up muted" style="font-weight:500">${s.d}</div></div>`).join("");

  const siteContent = M.content.filter(c => c.site === site.id);
  document.getElementById("ovPipeline").innerHTML = siteContent.length ? siteContent.map(c => {
    const p = M.platMeta(c.platform);
    return `<div class="pipe-row"><span class="icon-tile tile-${p.tile}">${I(p.icon)}</span>
      <span class="pr-t">${c.title}</span><span class="badge badge-${c.status.toLowerCase()}">${c.status}</span></div>`;
  }).join("") : `<div class="empty"><div class="empty-art">${I("file-plus")}</div><h3>No content yet</h3><p>Generate your first drafts to get started.</p></div>`;

  const chanData = [["Blog","blog",96,"var(--blog)"],["LinkedIn","linkedin",142,"var(--linkedin)"],["YouTube","youtube",58,"var(--youtube)"],["Instagram","instagram",188,"var(--instagram)"]];
  const chanMax = 188;
  document.getElementById("ovChannels").innerHTML = chanData.map(([n,t,v,col]) => `
    <div><div class="row-between mb2"><span class="row gap2"><span class="icon-tile tile-${t}" style="width:24px;height:24px;border-radius:6px">${I(M.platMeta(n).icon,"style='width:13px;height:13px'")}</span> ${n}</span><span class="fw6 mono">${v}</span></div>
      <div class="chan-bar"><i style="width:${Math.round(v/chanMax*100)}%;background:${col}"></i></div></div>`).join("");

  /* ---------- calendar week ---------- */
  const todayIndex = new Date().getDay();
  const days = M.schedule.days;
  const today = days[todayIndex === 0 ? 6 : todayIndex - 1];

  window.previewDraftFromWeekChip = function(draftId) {
    const d = siteContent.find(x => String(x.id) === String(draftId));
    if (!d) return;
    document.getElementById("largePreviewTitle").textContent = d.title;
    document.getElementById("largePreviewSub").textContent = `${d.platform} · Draft details`;
    const bodyContainer = document.getElementById("largePreviewBody");
    if (bodyContainer) {
      bodyContainer.innerHTML = previewHTML(d.platform, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date);
    }
    C.openModal("largePreviewModal");
  };

  document.getElementById("wsWeek").innerHTML = days.map(d => {
    const items = siteContent.filter(c => c.day === d && c.status !== "Draft");
    return `<div class="week-col ${d===today?'is-today':''}"><div class="week-day"><span>${d}</span>${d===today?'<span class="badge badge-primary txs">Today</span>':''}</div>
      <div class="week-items">${items.length ? items.map(c => { const p = M.platMeta(c.platform);
        return `<div class="week-chip" title="${c.title}" style="border-left: 3px solid ${p.color}; cursor: pointer;" onclick="window.previewDraftFromWeekChip('${c.id}')"><span class="icon-tile tile-${p.tile}" style="width:20px;height:20px;border-radius:4px">${I(p.icon,"style='width:11px;height:11px'")}</span>
          <span class="wc-txt"><span class="wc-time">${c.time}</span><span class="wc-site">${c.platform}</span></span></div>`; }).join("") : '<div class="week-empty">—</div>'}</div></div>`;
  }).join("");

  /* ---------- published grid ---------- */
  const published = siteContent.filter(c => c.status === "Published").concat(
    siteContent.filter(c => c.status === "Approved" || c.status === "Scheduled")
  );
  function coverGrad(plat) { return ({Blog:"linear-gradient(135deg,#095075,#053046)",LinkedIn:"linear-gradient(135deg,#0a66c2,#063b73)",YouTube:"linear-gradient(135deg,#dc2626,#7f1d1d)",Instagram:"linear-gradient(135deg,#f09433,#bc1888)"})[plat]; }
  function renderPub(filter) {
    const list = published.filter(c => filter === "all" || c.platform === filter);
    const grid = document.getElementById("pubGrid");
    if (!list.length) { grid.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="empty-art">${I("inbox")}</div><h3>Nothing here yet</h3><p>Published content for this channel will appear here.</p></div>`; C.refreshIcons(); return; }
    grid.innerHTML = list.map(c => { const p = M.platMeta(c.platform);
      const coverStyle = c.cover_image ? `background-image: url('${c.cover_image}'); background-size: cover; background-position: center;` : `background:${coverGrad(c.platform)}`;
      const coverContent = c.cover_image ? '' : I(p.icon,"style='width:30px;height:30px'");
      return `<div class="pub-card"><div class="pub-cover" style="${coverStyle}">${coverContent}</div>
        <div class="pub-body"><div class="row gap2 mb3"><span class="badge badge-${c.status.toLowerCase()}">${c.status}</span><span class="muted txs">${c.platform}</span></div>
          <div class="pub-title">${c.title}</div><div class="pub-foot"><span>${c.day} · ${c.time}</span><span class="row gap2">${I("eye","style='width:14px;height:14px'")} ${(Math.random()*4+1).toFixed(1)}k</span></div></div></div>`;
    }).join("");
    document.getElementById("pubCount").textContent = `${list.length} item${list.length>1?'s':''}`;
    C.refreshIcons();
  }
  renderPub("all");
  document.querySelectorAll("#pubFilter button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#pubFilter button").forEach(x => x.classList.remove("active")); b.classList.add("active"); renderPub(b.dataset.p);
  }));

  /* ---------- settings channels ---------- */
  document.getElementById("setName").value = site.name;
  document.getElementById("setUrl").value = site.url;
  
  if (document.getElementById("setEmail")) {
    document.getElementById("setEmail").value = site.contact_email || "";
  }
  if (document.getElementById("setPhone")) {
    document.getElementById("setPhone").value = site.contact_phone || "";
  }
  if (document.getElementById("setLogoUrl")) {
    document.getElementById("setLogoUrl").value = site.logo_url || "";
  }
  if (document.getElementById("setTone")) {
    const select = document.getElementById("setTone");
    for (let opt of select.options) {
      if (opt.text.toLowerCase().includes((site.tone || "").toLowerCase())) {
        opt.selected = true;
        break;
      }
    }
  }

  function updateLogoPreview(url) {
    const preview = document.getElementById("logoPreview");
    if (!preview) return;
    if (url) {
      preview.innerHTML = `<img src="${url}" style="width:100%;height:100%;object-fit:contain"/>`;
    } else {
      preview.innerHTML = `<i data-lucide="image" class="muted" style="width:24px;height:24px"></i>`;
      if (window.lucide) {
        window.lucide.createIcons({
          attrs: { class: 'muted', style: 'width:24px;height:24px' },
          nameList: ['image']
        });
      }
    }
  }
  updateLogoPreview(site.logo_url);

  if (document.getElementById("logoUpload")) {
    document.getElementById("logoUpload").addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          updateLogoPreview(event.target.result);
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (document.getElementById("setLogoUrl")) {
    document.getElementById("setLogoUrl").addEventListener("input", (e) => {
      updateLogoPreview(e.target.value.trim());
    });
  }

  if (document.getElementById("saveDetailsBtn")) {
    document.getElementById("saveDetailsBtn").addEventListener("click", async () => {
      const name = document.getElementById("setName").value.trim();
      const urlVal = document.getElementById("setUrl").value.trim();
      const email = document.getElementById("setEmail").value.trim();
      const phone = document.getElementById("setPhone").value.trim();
      const logoUrl = document.getElementById("setLogoUrl").value.trim();
      
      const toneSelect = document.getElementById("setTone");
      const tone = toneSelect ? toneSelect.options[toneSelect.selectedIndex].text : site.tone;
      
      const saveBtn = document.getElementById("saveDetailsBtn");
      saveBtn.disabled = true;
      const originalText = saveBtn.innerHTML;
      saveBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Saving...`;
      C.refreshIcons();

      const saveSettings = async (logoUploadBase64) => {
        try {
          const data = {
            name: name,
            url: urlVal.startsWith('http') ? urlVal : 'https://' + urlVal,
            domain: urlVal.replace('https://', '').replace('http://', '').split('/')[0],
            tone: tone,
            contact_email: email,
            contact_phone: phone,
            logo_url: logoUrl
          };
          if (logoUploadBase64) {
            data.logo_upload = logoUploadBase64;
          }
          
          await CadenceAPI.updateWebsite(site.id, data);
          
          // Sync local mock data
          await window.MOCK.syncMockData(site.id);
          
          // Update site reference
          site = window.MOCK.site(site.id);
          
          // Clear file upload input
          document.getElementById("logoUpload").value = "";
          
          // Update fields and preview
          document.getElementById("setLogoUrl").value = site.logo_url || "";
          updateLogoPreview(site.logo_url);
          
          C.toast({ type: "success", title: "Settings saved", desc: "Website details updated successfully!" });
        } catch (err) {
          C.toast({ type: "error", title: "Save failed", desc: err.message });
        } finally {
          saveBtn.disabled = false;
          saveBtn.innerHTML = originalText;
          C.refreshIcons();
        }
      };

      const logoUploadFile = document.getElementById("logoUpload").files[0];
      if (logoUploadFile) {
        const reader = new FileReader();
        reader.onloadend = async () => {
          await saveSettings(reader.result);
        };
        reader.readAsDataURL(logoUploadFile);
      } else {
        await saveSettings(null);
      }
    });
  }

  /* ---------- Pause/Resume & Delete Website ---------- */
  const pauseBtn = document.getElementById("pauseSiteBtn");
  if (pauseBtn) {
    function updatePauseBtnState() {
      if (site.status === "Paused") {
        pauseBtn.innerHTML = `${I("play")} Resume website`;
      } else {
        pauseBtn.innerHTML = `${I("pause")} Pause website`;
      }
      C.refreshIcons();
    }
    updatePauseBtnState();

    pauseBtn.addEventListener("click", async () => {
      const nextStatus = site.status === "Paused" ? "active" : "paused";
      pauseBtn.disabled = true;
      try {
        await CadenceAPI.updateWebsite(site.id, { status: nextStatus });
        await window.MOCK.syncMockData(site.id);
        site = window.MOCK.site(site.id);
        
        // update status badge
        const [sc, si, st] = statusMap[site.status] || statusMap.Active;
        document.getElementById("wsStatus").innerHTML = `<span class="badge ${sc}">${I(si)} ${st}</span>`;
        
        updatePauseBtnState();
        C.toast({ type: "success", title: nextStatus === "paused" ? "Website paused" : "Website resumed" });
      } catch (err) {
        C.toast({ type: "error", title: "Action failed", desc: err.message });
      } finally {
        pauseBtn.disabled = false;
      }
    });
  }

  const confirmDeleteSiteBtn = document.getElementById("confirmDeleteSiteBtn");
  if (confirmDeleteSiteBtn) {
    confirmDeleteSiteBtn.addEventListener("click", async () => {
      confirmDeleteSiteBtn.disabled = true;
      try {
        await CadenceAPI.deleteWebsite(site.id);
        C.toast({ type: "success", title: "Website removed", desc: "Successfully moved to Trash." });
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 1000);
      } catch (err) {
        C.toast({ type: "error", title: "Delete failed", desc: err.message });
        confirmDeleteSiteBtn.disabled = false;
      }
    });
  }

  /* ---------- Sample Content Management ---------- */
  let currentSamples = [];

  async function loadSamples() {
    try {
      currentSamples = await CadenceAPI.getSamples(site.id);
      renderSamplesList();
    } catch (err) {
      console.error("Failed to load samples:", err);
    }
  }

  function renderSamplesList() {
    const listEl = document.getElementById("sampleManagerList");
    if (!listEl) return;
    
    const platform = document.getElementById("samplePlatformSelect").value;
    const filtered = currentSamples.filter(s => s.platform === platform);
    
    if (filtered.length === 0) {
      listEl.innerHTML = `<div class="muted tsm" style="text-align:center;padding:var(--s4)">No samples uploaded for this platform yet.</div>`;
      return;
    }
    
    listEl.innerHTML = filtered.map(s => `
      <div class="row-between p3" style="background:var(--bg-subtle); border-radius:8px; border:1px solid var(--border);">
        <div class="col" style="flex:1; margin-right:var(--s3);">
          <strong style="font-size:var(--fs-sm)">${s.title || s.file_name || 'Untitled Sample'}</strong>
          <div class="muted txs" style="margin-top:2px">${s.file_name || 'Text entry'} · ${new Date(s.uploaded_at).toLocaleDateString()}</div>
        </div>
        <div class="row gap3" style="align-items:center">
          <label class="switch" title="Toggle active status">
            <input type="checkbox" data-sample-id="${s.id}" class="sample-active-toggle" ${s.is_active ? 'checked' : ''} />
            <span class="track"></span>
          </label>
          <button type="button" class="icon-btn btn-sm delete-sample-btn" data-sample-id="${s.id}" title="Delete sample" style="color:var(--error)">
            ${I("trash-2", "style='width:14px;height:14px'")}
          </button>
        </div>
      </div>
    `).join("");
    
    C.refreshIcons();
    wireSampleActions();
  }

  function wireSampleActions() {
    document.querySelectorAll(".sample-active-toggle").forEach(cb => {
      cb.addEventListener("change", async () => {
        const id = cb.dataset.sampleId;
        const isActive = cb.checked;
        try {
          await CadenceAPI.updateSample(site.id, id, { is_active: isActive });
          const sample = currentSamples.find(s => String(s.id) === String(id));
          if (sample) sample.is_active = isActive;
          C.toast({ type: "success", title: "Status updated", desc: `Sample is now ${isActive ? 'active' : 'inactive'}.` });
        } catch (err) {
          cb.checked = !isActive;
          C.toast({ type: "error", title: "Update failed", desc: err.message });
        }
      });
    });

    document.querySelectorAll(".delete-sample-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.sampleId;
        if (!confirm("Are you sure you want to delete this sample?")) return;
        try {
          await CadenceAPI.deleteSample(site.id, id);
          currentSamples = currentSamples.filter(s => String(s.id) !== String(id));
          renderSamplesList();
          C.toast({ type: "success", title: "Sample deleted" });
        } catch (err) {
          C.toast({ type: "error", title: "Delete failed", desc: err.message });
        }
      });
    });
  }

  // Bind dropdown change
  const selectEl = document.getElementById("samplePlatformSelect");
  if (selectEl) {
    selectEl.addEventListener("change", renderSamplesList);
  }

  // Bind upload button
  const uploadBtn = document.getElementById("uploadWorkspaceSampleBtn");
  if (uploadBtn) {
    uploadBtn.addEventListener("click", async () => {
      const fileInput = document.getElementById("workspaceSampleFile");
      const titleInput = document.getElementById("workspaceSampleTitle");
      const platform = document.getElementById("samplePlatformSelect").value;
      
      if (!fileInput.files || !fileInput.files[0]) {
        C.toast({ type: "error", title: "No file selected", desc: "Please choose a sample file first." });
        return;
      }
      
      const file = fileInput.files[0];
      const title = titleInput.value.trim();
      
      uploadBtn.disabled = true;
      const originalText = uploadBtn.innerHTML;
      uploadBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Uploading...`;
      C.refreshIcons();
      
      try {
        const content = await window.Cadence.readFileAsText(file);
        const newSample = await CadenceAPI.addSample(site.id, {
          platform: platform,
          title: title,
          content: content,
          file_name: file.name
        });
        
        currentSamples.unshift(newSample);
        fileInput.value = "";
        titleInput.value = "";
        renderSamplesList();
        C.toast({ type: "success", title: "Sample uploaded", desc: `Successfully added reference for ${platform}.` });
      } catch (err) {
        C.toast({ type: "error", title: "Upload failed", desc: err.message });
      } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = originalText;
        C.refreshIcons();
      }
    });
  }

  loadSamples();

  /* ---------- crawl action ---------- */
  const crawlBtn = document.getElementById("crawlBtn");
  let crawlInterval = null;

  async function checkCrawlStatus() {
    try {
      const res = await CadenceAPI.getCrawlStatus(site.id);
      if (res.status === "done") {
        clearInterval(crawlInterval);
        crawlInterval = null;
        
        // Refresh local mock data
        await window.MOCK.syncMockData(site.id);
        const updatedSite = window.MOCK.site(site.id);
        if (updatedSite) {
          site.style_guide = updatedSite.style_guide;
          site.needs_crawl = updatedSite.needs_crawl;
          site.scrape_status = updatedSite.scrape_status;
          populateStyleGuideFields();
        }
        
        crawlBtn.disabled = false;
        crawlBtn.innerHTML = `${I("refresh-cw")} Crawl website`;
        C.refreshIcons();
        C.toast({ type: "success", title: "Crawl completed", desc: "Website style guide successfully extracted!" });
      } else if (res.status === "failed") {
        clearInterval(crawlInterval);
        crawlInterval = null;
        crawlBtn.disabled = false;
        crawlBtn.innerHTML = `${I("refresh-cw")} Crawl website`;
        C.refreshIcons();
        C.toast({ type: "error", title: "Crawl failed", desc: "Unable to parse website content." });
      }
    } catch (err) {
      console.error(err);
    }
  }

  if (crawlBtn) {
    // If the site is already crawling when page loads, resume visual state
    if (site.scrape_status === "crawling") {
      crawlBtn.disabled = true;
      crawlBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Crawling...`;
      C.refreshIcons();
      crawlInterval = setInterval(checkCrawlStatus, 2000);
    }

    crawlBtn.addEventListener("click", async () => {
      crawlBtn.disabled = true;
      crawlBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Crawling...`;
      C.refreshIcons();
      try {
        await CadenceAPI.triggerCrawl(site.id);
        C.toast({ type: "info", title: "Crawl started", desc: "Analyzing website style and page structure..." });
        crawlInterval = setInterval(checkCrawlStatus, 2000);
      } catch (err) {
        crawlBtn.disabled = false;
        crawlBtn.innerHTML = `${I("refresh-cw")} Crawl website`;
        C.refreshIcons();
        C.toast({ type: "error", title: "Failed to start crawl", desc: err.message });
      }
    });
  }

  const conns = [["LinkedIn","linkedin",true,"company/"+site.id],["YouTube","youtube",true,"@"+site.id],["Instagram","instagram",false,""],["Blog (RSS)","blog",true,site.url+"/feed"]];
  document.getElementById("setChannels").innerHTML = conns.map(([n,t,on,h]) => `
    <div class="chan-conn"><span class="icon-tile tile-${t}">${I(M.platMeta(n==="Blog (RSS)"?"Blog":n).icon)}</span>
      <div class="cc-meta"><div class="cc-nm">${n}</div><div class="cc-st">${on?h:"Not connected"}</div></div>
      ${on?`<span class="badge badge-success">${I("check")} Connected</span>`:`<button class="btn btn-secondary btn-sm" onclick="Cadence.toast({type:'success',title:'${n} connected'})">Connect</button>`}</div>`).join("");

  /* ==========================================================================
     GENERATE — composer, drafts, previews
     ========================================================================== */
  let curChan = "Blog";
  document.querySelectorAll(".chan").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".chan").forEach(x => x.classList.remove("active")); b.classList.add("active"); curChan = b.dataset.chan;
  }));

  let ideaQueue = [];
  let ideaQueueLoading = false;

  async function loadIdeaQueue(showLoader = true) {
    if (ideaQueueLoading) return;
    ideaQueueLoading = true;
    const refreshBtn = document.getElementById("refreshIdeaQueue");
    if (refreshBtn) {
      refreshBtn.disabled = true;
      const refreshIcon = refreshBtn.querySelector("i") || refreshBtn.querySelector("svg");
      if (refreshIcon) {
        refreshIcon.style.animation = "spin 1s linear infinite";
      }
    }
    if (showLoader) {
      document.getElementById("ideaQueue").innerHTML = `
        <div style="display:flex;flex-direction:column;gap:var(--s2)">
          ${[1,2,3,4].map(() => `<div style="height:38px;border-radius:var(--radius-sm);background:var(--surface2);animation:pulse 1.5s ease-in-out infinite;opacity:0.6"></div>`).join("")}
        </div>`;
      document.getElementById("queueCount").textContent = "…";
    }
    try {
      const suggestions = await CadenceAPI.getIdeaSuggestions(site.id) || [];
      ideaQueue = suggestions.map(s => ({
        chan: s.platform.charAt(0).toUpperCase() + s.platform.slice(1),
        title: s.title,
        reason: s.reason || ""
      }));
      renderQueue();
    } catch (err) {
      console.error("Failed to load idea queue:", err);
      document.getElementById("ideaQueue").innerHTML = `<div class="muted tsm" style="text-align:center;padding:var(--s4)">Failed to load suggestions. Try refreshing.</div>`;
      document.getElementById("queueCount").textContent = "0";
    } finally {
      ideaQueueLoading = false;
      if (refreshBtn) {
        refreshBtn.disabled = false;
        const refreshIcon = refreshBtn.querySelector("i") || refreshBtn.querySelector("svg");
        if (refreshIcon) {
          refreshIcon.style.animation = "";
        }
      }
    }
  }

  function renderQueue() {
    document.getElementById("queueCount").textContent = ideaQueue.length;
    document.getElementById("ideaQueue").innerHTML = ideaQueue.length ? ideaQueue.map((q, i) => { const p = M.platMeta(q.chan);
      return `<div class="idea-q" title="${q.reason ? q.reason.replace(/"/g, '&quot;') : ''}" style="position:relative"><span class="icon-tile tile-${p.tile} iq-ic">${I(p.icon,"style='width:14px;height:14px'")}</span>
        <span class="iq-t">${q.title}</span><button class="icon-btn btn-sm" data-q="${i}" title="Use this suggestion">${I("sparkles","style='width:15px;height:15px'")}</button></div>`;
    }).join("") : `<div class="muted tsm" style="text-align:center;padding:var(--s4)">Click Refresh to generate AI suggestions for your brand.</div>`;
    C.refreshIcons();
    document.querySelectorAll("[data-q]").forEach(b => b.addEventListener("click", () => {
      const q = ideaQueue[+b.dataset.q];
      const titleInput = document.getElementById("ideaTitle");
      if (titleInput) {
        const currentVal = titleInput.value.trim();
        if (currentVal) {
          titleInput.value = currentVal + "\n" + q.title;
        } else {
          titleInput.value = q.title;
        }
        titleInput.focus();
      }
      curChan = q.chan;
      document.querySelectorAll(".chan").forEach(x => x.classList.toggle("active", x.dataset.chan === q.chan));
    }));
  }

  // Wire up the Refresh button
  const refreshIdeaQueueBtn = document.getElementById("refreshIdeaQueue");
  if (refreshIdeaQueueBtn) {
    refreshIdeaQueueBtn.addEventListener("click", () => loadIdeaQueue(true));
  }

  loadIdeaQueue();


  /* ----- sample generated bodies ----- */
  const SAMPLE = {
    Blog: { kicker: "Brewing Guide", body: ["Pour-over coffee rewards patience. The method looks simple — hot water, ground coffee, a paper filter — but three variables quietly decide whether your cup is bright and aromatic or flat and bitter.","The first is grind size. Too fine and water struggles through, over-extracting into bitterness; too coarse and it rushes past, leaving a thin, sour brew. Aim for the texture of coarse sea salt.","The second is the bloom. Pour just enough water to saturate the grounds, then wait thirty seconds as trapped CO₂ escapes. This single pause is the difference between amateur and café-quality."] },
    LinkedIn: "Motivation is a terrible training partner.\n\nIt shows up when conditions are perfect and ghosts you in February. Progressive overload doesn't care how you feel — it just asks for slightly more than last week.\n\nAdd 2.5kg. One more rep. A few seconds longer under tension. Boring? Yes. Effective? Relentlessly.\n\nThe people who get strong aren't more motivated. They're more consistent with something small.\n\nWhat's one tiny progression you can make this week? 👇",
    Instagram: { cap: "Stale beans? Here's how to tell 👇 Flat aroma · no bloom · oily surface · dull color · sour finish. Fresh coffee should smell alive the moment you open the bag.", tags: "#specialtycoffee #pourover #coffeelover #freshroast" },
    YouTube: { title: "Roasting at home: light vs. medium vs. dark (same beans)", dur: "8:42", desc: "We roasted the same Ethiopian beans three ways so you don't have to guess." },
  };

  function previewHTML(plat, title, body, coverImage, tags, category, createdAt, authorName, customDate) {
    const guide = site.style_guide || {};
    const primaryFont = guide.primary_font ? guide.primary_font : 'inherit';
    const headingFont = guide.heading_font ? guide.heading_font : primaryFont;
    const headingColor = guide.heading_color ? guide.heading_color : 'inherit';
    const textColor = guide.text_color ? guide.text_color : 'inherit';

    const isColorLight = (colorStr) => {
      if (!colorStr || colorStr === 'inherit' || colorStr === 'transparent') return false;
      const c = colorStr.replace(/!important/gi, '').trim().toLowerCase();
      if (['white', 'yellow', 'cyan', 'lightgray', 'lightblue', 'lightgreen', 'lime', '#fff', '#ffffff'].includes(c)) return true;
      if (['black', 'navy', 'darkblue', 'darkgray', 'maroon', 'purple', 'green'].includes(c)) return false;
      if (c.startsWith('#')) {
        let hex = c.substring(1);
        if (hex.length === 3 || hex.length === 4) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        if (hex.length >= 6) {
          const r = parseInt(hex.substring(0, 2), 16);
          const g = parseInt(hex.substring(2, 4), 16);
          const b = parseInt(hex.substring(4, 6), 16);
          return Math.sqrt(0.299*r*r + 0.587*g*g + 0.114*b*b) > 170;
        }
      }
      const rgb = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (rgb) {
        const r = parseInt(rgb[1], 10), g = parseInt(rgb[2], 10), b = parseInt(rgb[3], 10);
        return Math.sqrt(0.299*r*r + 0.587*g*g + 0.114*b*b) > 170;
      }
      return false;
    };

    const isColorDark = (colorStr) => {
      if (!colorStr || colorStr === 'inherit' || colorStr === 'transparent') return false;
      const c = colorStr.replace(/!important/gi, '').trim().toLowerCase();
      if (['black', 'navy', 'darkblue', 'darkgray', 'maroon', 'purple', 'green', 'indigo', 'slate', '#000', '#000000'].includes(c)) return true;
      if (['white', 'yellow', 'cyan', 'lightgray', 'lightblue', 'lightgreen', 'lime'].includes(c)) return false;
      if (c.startsWith('#')) {
        let hex = c.substring(1);
        if (hex.length === 3 || hex.length === 4) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        if (hex.length >= 6) {
          const r = parseInt(hex.substring(0, 2), 16);
          const g = parseInt(hex.substring(2, 4), 16);
          const b = parseInt(hex.substring(4, 6), 16);
          return Math.sqrt(0.299*r*r + 0.587*g*g + 0.114*b*b) < 100;
        }
      }
      const rgb = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (rgb) {
        const r = parseInt(rgb[1], 10), g = parseInt(rgb[2], 10), b = parseInt(rgb[3], 10);
        return Math.sqrt(0.299*r*r + 0.587*g*g + 0.114*b*b) < 100;
      }
      return false;
    };
    
    const styleId = `style-preview-${site.id}`;
    let styleTag = document.getElementById(styleId);
    if (!styleTag) {
      styleTag = document.createElement("style");
      styleTag.id = styleId;
      document.head.appendChild(styleTag);
    }
    styleTag.textContent = `
      .preview-wrapper-${site.id} {
        font-family: ${primaryFont}, sans-serif !important;
      }
      .preview-wrapper-${site.id} h2, 
      .preview-wrapper-${site.id} h3, 
      .preview-wrapper-${site.id} h4 {
        font-family: ${headingFont}, sans-serif !important;
      }

      /* Light Theme overrides */
      html[data-theme="light"] .preview-wrapper-${site.id},
      [data-theme="light"] .preview-wrapper-${site.id} {
        color: ${isColorLight(textColor) ? 'var(--text)' : textColor} !important;
      }
      html[data-theme="light"] .preview-wrapper-${site.id} h2,
      html[data-theme="light"] .preview-wrapper-${site.id} h3,
      html[data-theme="light"] .preview-wrapper-${site.id} h4,
      [data-theme="light"] .preview-wrapper-${site.id} h2,
      [data-theme="light"] .preview-wrapper-${site.id} h3,
      [data-theme="light"] .preview-wrapper-${site.id} h4 {
        color: ${isColorLight(headingColor) ? 'var(--text)' : headingColor} !important;
      }
      html[data-theme="light"] .preview-wrapper-${site.id} p,
      html[data-theme="light"] .preview-wrapper-${site.id} li,
      [data-theme="light"] .preview-wrapper-${site.id} p,
      [data-theme="light"] .preview-wrapper-${site.id} li {
        color: ${isColorLight(textColor) ? 'var(--text-secondary)' : textColor} !important;
      }

      /* Dark Theme overrides */
      html[data-theme="dark"] .preview-wrapper-${site.id},
      [data-theme="dark"] .preview-wrapper-${site.id} {
        color: ${isColorDark(textColor) ? 'var(--text)' : textColor} !important;
      }
      html[data-theme="dark"] .preview-wrapper-${site.id} h2,
      html[data-theme="dark"] .preview-wrapper-${site.id} h3,
      html[data-theme="dark"] .preview-wrapper-${site.id} h4,
      [data-theme="dark"] .preview-wrapper-${site.id} h2,
      [data-theme="dark"] .preview-wrapper-${site.id} h3,
      [data-theme="dark"] .preview-wrapper-${site.id} h4 {
        color: ${isColorDark(headingColor) ? 'var(--text)' : headingColor} !important;
      }
      html[data-theme="dark"] .preview-wrapper-${site.id} p,
      html[data-theme="dark"] .preview-wrapper-${site.id} li,
      [data-theme="dark"] .preview-wrapper-${site.id} p,
      [data-theme="dark"] .preview-wrapper-${site.id} li {
        color: ${isColorDark(textColor) ? 'var(--text-secondary)' : textColor} !important;
      }
    `;

    if (plat === "Blog") {
      let blogBody = "";
      if (typeof body === "string") {
        blogBody = body;
      } else {
        const b = body || SAMPLE.Blog;
        blogBody = (b.body || []).map(p => `<p>${p}</p>`).join("");
      }
      let tagsHTML = "";
      if (tags && tags.length > 0) {
        tagsHTML = `<div class="editor-tags-list mt4" style="border-top:1px solid var(--border); padding-top:var(--s3); margin-top:var(--s4); display:flex; flex-wrap:wrap; gap:6px;">` +
          tags.map(t => {
            const parts = t.split(':');
            const name = parts[0];
            const style = parts[1] || 'neutral';
            let styleClass = 'badge-neutral';
            if (style === 'primary') styleClass = 'badge-primary';
            else if (style === 'success') styleClass = 'badge-success';
            else if (style === 'danger') styleClass = 'badge-error';
            else if (style === 'warning') styleClass = 'badge-scheduled';
            return `<span class="badge ${styleClass}" style="text-transform:uppercase;font-size:10px">${name}</span>`;
          }).join(" ") + `</div>`;
      }
      const coverHTML = coverImage 
        ? `<img class="bp-cover-img" src="${coverImage}" style="width:100%; height:auto; border-radius:var(--r-md); margin-bottom:var(--s4); display:block; border:none;" />` 
        : `<div class="bp-cover">${I("image","style='width:28px;height:28px'")}</div>`;

      const dateObj = createdAt ? new Date(createdAt) : new Date();
      const formattedDate = dateObj.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
      
      const displayAuthor = authorName !== undefined ? authorName : site.name;
      const displayDate = customDate !== undefined ? customDate : formattedDate;
      const displayCategory = category !== undefined ? category : (site.industry || "Marketing");

      let bylineItems = [];
      if (displayAuthor) {
        bylineItems.push(`
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${I("user", "style='width:14px;height:14px;color:var(--text-muted)'")} By: ${displayAuthor}
          </span>
        `);
      }
      if (displayDate) {
        bylineItems.push(`
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${I("calendar", "style='width:14px;height:14px;color:var(--text-muted)'")} ${displayDate}
          </span>
        `);
      }
      if (displayCategory) {
        bylineItems.push(`
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${I("folder", "style='width:14px;height:14px;color:var(--text-muted)'")} ${displayCategory}
          </span>
        `);
      }
      bylineItems.push(`
        <span style="display: inline-flex; align-items: center; gap: 4px;">
          ${I("message-square", "style='width:14px;height:14px;color:var(--text-muted)'")} 0 Comments
        </span>
      `);

      const bylineHTML = bylineItems.length > 0 
        ? `<div class="bp-byline" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; color: var(--text-secondary); margin: var(--s2) 0 var(--s4) 0;">` +
          bylineItems.join(`<span style="color: var(--border)">/</span>`) +
          `</div>`
        : '';

      return `<div class="bp preview-wrapper-${site.id}"><div class="bp-kicker">Article</div><h2>${title}</h2>
        ${bylineHTML}
        ${coverHTML}
        ${blogBody}
        ${tagsHTML}</div>`;
    }
    if (plat === "LinkedIn") {
      const txt = (typeof body === "string" ? body : SAMPLE.LinkedIn);
      const coverHTML = coverImage 
        ? `<div class="li-cover" style="margin-top:var(--s3); border-radius:var(--r-sm); overflow:hidden; border:1px solid var(--border);"><img src="${coverImage}" style="width:100%; height:auto; display:block;" /></div>` 
        : "";
      return `<div class="li"><div class="li-top"><span class="avatar li-av" style="background:${site.color}">${site.short}</span>
        <div style="flex:1"><div class="li-nm">${site.name}</div><div class="li-hl">${site.industry}</div><div class="li-time">Just now · ${I("globe","style='width:11px;height:11px'")}</div></div>${I("more-horizontal")}</div>
        <div class="li-body" style="white-space: pre-wrap;">${txt}${coverHTML}</div>
        <div class="li-react"><span class="row" style="gap:2px"><span style="background:var(--linkedin);color:#fff;width:16px;height:16px;border-radius:99px;display:grid;place-items:center;font-size:9px">👍</span></span> 248 · 32 comments</div>
        <div class="li-bar"><button>${I("thumbs-up")} Like</button><button>${I("message-circle")} Comment</button><button>${I("repeat-2")} Repost</button><button>${I("send")} Send</button></div></div>`;
    }
    if (plat === "Instagram") {
      const txt = (typeof body === "string" ? body : SAMPLE.Instagram.cap);
      const imgStyle = coverImage 
        ? `style="background-image: url('${coverImage}'); background-size: contain; background-repeat: no-repeat; background-position: center; background-color: var(--bg-subtle);"`
        : "";
      const imgContent = coverImage 
        ? "" 
        : I("image", "style='width:32px;height:32px'");
      return `<div class="ig"><div class="ig-top"><span class="ig-av"><span style="color:${site.color}">${site.short}</span></span><span class="ig-nm">${site.id}</span>${I("more-horizontal")}</div>
        <div class="ig-img" ${imgStyle}>${imgContent}<span class="ig-tag">${title.slice(0,28)}</span></div>
        <div class="ig-actions">${I("heart")}${I("message-circle")}${I("send")}<span class="sp">${I("bookmark")}</span></div>
        <div class="ig-likes">1,204 likes</div><div class="ig-cap"><b>${site.id}</b> ${txt}</div></div>`;
    }
    if (plat === "YouTube") {
      const txt = (typeof body === "string" ? body : SAMPLE.YouTube.desc);
      const thumbStyle = coverImage 
        ? `style="background-image: url('${coverImage}'); background-size: cover; background-position: center;"`
        : "";
      return `<div class="yt"><div class="yt-thumb" ${thumbStyle}><span class="play">${I("play")}</span><span class="dur">8:42</span></div>
        <div class="yt-info"><span class="avatar yt-av" style="background:${site.color}">${site.short}</span>
        <div><div class="yt-t">${title}</div><div class="yt-ch">${site.name} · ${txt.substring(0, 80)}...</div></div></div></div>`;
    }
  }

  /* ----- draft model ----- */
  let drafts = M.content.filter(c => c.site === site.id);
  let filter = "all";
  let selectedDraftId = null;

  function statusPill(s) { return `<span class="badge badge-${s.toLowerCase()}">${s}</span>`; }

  function draftListItem(d, isActive) {
    const p = M.platMeta(d.chan);
    const activeClass = isActive ? "active" : "";
    const displayTitle = d.title.length > 40 ? d.title.substring(0, 37) + "..." : d.title;
    
    return `<div class="draft-list-item ${activeClass}" data-list-id="${d.id}">
      <span class="icon-tile tile-${p.tile}">${I(p.icon)}</span>
      <div class="dli-meta">
        <div class="dli-title" title="${d.title}">${displayTitle}</div>
        <div class="dli-sub">
          <span>${d.chan}</span>
          <span class="dli-dot">·</span>
          ${statusPill(d.status)}
        </div>
      </div>
    </div>`;
  }

  function draftPreviewContent(d) {
    const p = M.platMeta(d.chan);
    const actions = d.status === "Draft"
      ? `<button class="btn btn-ghost btn-sm" data-act="reject" data-id="${d.id}">${I("x")} Reject</button>
         <button class="btn btn-ghost btn-sm" data-act="regen" data-id="${d.id}">${I("rotate-cw")} Regenerate</button>
         <span class="spacer"></span>
         <button class="btn btn-secondary btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button>
         <button class="btn btn-success btn-sm" data-act="approve" data-id="${d.id}">${I("check")} Approve</button>`
      : d.status === "Approved"
      ? `<button class="btn btn-ghost btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button><span class="spacer"></span>
         <button class="btn btn-primary btn-sm" data-act="schedule" data-id="${d.id}">${I("calendar-plus")} Schedule</button>`
      : `<span class="muted tsm row gap2">${I("check-check","style='width:15px;height:15px;color:var(--success)'")} ${d.status==='Scheduled'?'Scheduled':'Live'}</span><span class="spacer"></span>
         <button class="btn btn-ghost btn-sm" data-act="view" data-id="${d.id}">${I("eye")} View</button>`;
         
    return `<div class="draft-preview-card" data-card="${d.id}">
      <div class="draft-preview-head">
        <span class="icon-tile tile-${p.tile}">${I(p.icon)}</span>
        <div class="dp-meta">
          <div class="dp-title">${d.title}</div>
          <div class="dp-sub">${d.chan} · AI draft ${statusPill(d.status)}</div>
        </div>
        <button class="icon-btn btn-sm" data-act="maximize" data-id="${d.id}" title="View in large screen" style="margin-right:4px;">${I("maximize-2")}</button>
        <button class="icon-btn btn-sm" data-act="more" data-id="${d.id}">${I("more-vertical")}</button>
      </div>
      <div class="draft-preview-body draft__body">
        ${previewHTML(d.chan, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date)}
      </div>
      <div class="draft-preview-foot draft__foot">
        ${actions}
      </div>
    </div>`;
  }

  function renderDrafts() {
    const list = drafts.filter(d => filter === "all" || d.status === filter);
    const wrap = document.getElementById("draftList");
    const previewContainer = document.getElementById("draftPreviewContent");
    
    if (!list.length) {
      wrap.innerHTML = `<div class="empty card" style="padding:var(--s9)"><div class="empty-art">${I("sparkles")}</div><h3>No ${filter==='all'?'':filter.toLowerCase()+' '}drafts</h3><p>Use the composer to generate AI content for this website.</p></div>`;
      if (previewContainer) {
        previewContainer.innerHTML = `<div class="empty card" style="padding:var(--s9); border-style:dashed;"><div class="empty-art">${I("sparkles")}</div><h3>No draft selected</h3><p>Create a draft first or change filter to see preview.</p></div>`;
      }
      C.refreshIcons();
      return;
    }

    // Determine active draft selection
    let activeDraft = list.find(d => d.id === selectedDraftId);
    if (!activeDraft) {
      // Default to first item of list
      activeDraft = list[0];
      selectedDraftId = activeDraft ? activeDraft.id : null;
    }

    wrap.innerHTML = list.map(d => draftListItem(d, d.id === selectedDraftId)).join("");
    
    if (previewContainer) {
      if (activeDraft) {
        previewContainer.innerHTML = draftPreviewContent(activeDraft);
      } else {
        previewContainer.innerHTML = `<div class="empty card" style="padding:var(--s9); border-style:dashed;"><div class="empty-art">${I("sparkles")}</div><h3>No draft selected</h3><p>Select a draft from the list to preview its details.</p></div>`;
      }
    }
    
    C.refreshIcons();
    wireDraftActions();
  }

  function wireDraftActions() {
    document.querySelectorAll("[data-act]").forEach(b => {
      if (b._wired) return; b._wired = true;
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = b.dataset.id, act = b.dataset.act, d = drafts.find(x => x.id === id);
        if (!d) return;
        if (act === "approve") {
          try {
            await CadenceAPI.approveDraft(d.id);
            d.status = "Approved";
            C.toast({ type: "success", title: "Draft approved", desc: "Ready to schedule" });
            await M.syncMockData(site.id);
            if (C.mountShell) C.mountShell();
            renderDrafts();
          } catch (err) {
            C.toast({ type: "error", title: "Approval failed", desc: err.message });
          }
        }
        else if (act === "reject") {
          try {
            await CadenceAPI.rejectDraft(d.id, "Rejected by administrator");
            drafts = drafts.filter(x => x.id !== id);
            C.toast({ type: "info", title: "Draft rejected" });
            await M.syncMockData(site.id);
            if (C.mountShell) C.mountShell();
            if (selectedDraftId === id) selectedDraftId = null;
            renderDrafts();
          } catch (err) {
            C.toast({ type: "error", title: "Rejection failed", desc: err.message });
          }
        }
        else if (act === "schedule") {
          document.getElementById("schedDraftId").value = d.id;
          
          // Default to tomorrow at the current time
          const tomorrow = new Date();
          tomorrow.setDate(tomorrow.getDate() + 1);
          
          const yyyy = tomorrow.getFullYear();
          const mm = String(tomorrow.getMonth() + 1).padStart(2, '0');
          const dd = String(tomorrow.getDate()).padStart(2, '0');
          const hh = String(tomorrow.getHours()).padStart(2, '0');
          const min = String(tomorrow.getMinutes()).padStart(2, '0');
          
          document.getElementById("schedDate").value = `${yyyy}-${mm}-${dd}`;
          document.getElementById("schedTime").value = `${hh}:${min}`;
          
          C.openModal("scheduleModal");
        }
        else if (act === "regen") {
          await regenerate(d);
        }
        else if (act === "edit" || act === "view") {
          openEdit(d);
        }
        else if (act === "maximize") {
          document.getElementById("largePreviewTitle").textContent = d.title;
          document.getElementById("largePreviewSub").textContent = `${d.chan} · AI draft preview`;
          
          const bodyContainer = document.getElementById("largePreviewBody");
          if (bodyContainer) {
            bodyContainer.innerHTML = previewHTML(d.chan, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date);
          }
          C.openModal("largePreviewModal");
        }
        else if (act === "more") {
          if (confirm("Move this draft to trash?")) {
            try {
              await CadenceAPI.deleteDraft(d.id);
              drafts = drafts.filter(x => x.id !== id);
              C.toast({ type: "success", title: "Draft moved to trash" });
              await M.syncMockData(site.id);
              if (C.mountShell) C.mountShell();
              if (selectedDraftId === id) selectedDraftId = null;
              renderDrafts();
            } catch (err) {
              C.toast({ type: "error", title: "Delete failed", desc: err.message });
            }
          }
        }
      });
    });

    document.querySelectorAll(".draft-list-item").forEach(item => {
      if (item._wired) return;
      item._wired = true;
      item.addEventListener("click", () => {
        selectedDraftId = item.dataset.listId;
        renderDrafts();
      });
    });
  }

  async function regenerate(d) {
    const card = document.querySelector(`[data-card="${d.id}"] .draft__body`);
    if (card) {
      card.innerHTML = genLoadingHTML(); C.refreshIcons();
    }
    try {
      await CadenceAPI.regenerateDraft(d.id);
      await window.MOCK.syncMockData(site.id);
      drafts = window.MOCK.content.filter(x => x.site === site.id);
      renderDrafts();
      C.toast({ type: "success", title: "Regenerated a fresh draft" });
    } catch (err) {
      C.toast({ type: "error", title: "Regeneration failed", desc: err.message });
      renderDrafts();
    }
  }

  function genLoadingHTML() {
    return `<div class="gen-loading"><div class="gl-head">${I("loader-circle","class='spin'")} Cadence is writing…</div>
      <div class="sk-line w80"></div><div class="sk-line"></div><div class="sk-line w60"></div><div class="sk-line"></div><div class="sk-line w40"></div></div>`;
  }

  /* ----- generate new draft ----- */
  async function startGenerate() {
    const rawVal = document.getElementById("ideaTitle").value.trim();
    const titles = rawVal.split('\n').map(t => t.trim()).filter(t => t.length > 0);
    
    if (titles.length === 0) {
      titles.push(`New ${curChan} post about ${site.name}`);
    }
    
    const btn = document.getElementById("genBtn");
    btn.disabled = true; btn.innerHTML = '<i data-lucide="loader-circle" class="spin"></i> Generating…'; C.refreshIcons();
    
    // Switch to generate panel visibly first
    document.querySelectorAll(".ws-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === "generate"));
    document.querySelectorAll("#wsPanels .tab-panel").forEach(pp => pp.classList.toggle("active", pp.dataset.panel === "generate"));

    try {
      // Generate each title sequentially
      for (const title of titles) {
        const idea = await CadenceAPI.submitIdea(site.id, title, curChan.toLowerCase());
        await CadenceAPI.generateContent(idea.id);
      }
      
      await window.MOCK.syncMockData(site.id);
      drafts = window.MOCK.content.filter(x => x.site === site.id);
      
      if (drafts.length > 0) {
        let maxIdDraft = drafts[0];
        drafts.forEach(d => {
          if (parseInt(d.id) > parseInt(maxIdDraft.id)) {
            maxIdDraft = d;
          }
        });
        selectedDraftId = maxIdDraft.id;
      }
      
      filter = "all";
      document.querySelectorAll("#draftFilter button").forEach(x => x.classList.toggle("active", x.dataset.f === "all"));
      renderDrafts();
      await loadIdeaQueue();
      
      const successMsg = titles.length > 1 ? `${titles.length} drafts generated` : `${curChan} content generated`;
      C.toast({ type: "success", title: "Draft ready", desc: successMsg });
      document.getElementById("ideaTitle").value = "";
    } catch (err) {
      console.error(err);
      C.toast({ type: "error", title: "Generation failed", desc: err.message });
    } finally {
      btn.disabled = false; btn.innerHTML = I("sparkles") + " Generate with AI"; C.refreshIcons();
    }
  }
  document.getElementById("genBtn").addEventListener("click", startGenerate);

  document.querySelectorAll("#draftFilter button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#draftFilter button").forEach(x => x.classList.remove("active")); b.classList.add("active"); filter = b.dataset.f; renderDrafts();
  }));

  /* ----- edit modal ----- */
  let editing = null;
  let activeEditorTags = [];

  function renderEditorTags() {
    const list = document.getElementById("tagsList");
    if (!list) return;
    
    list.innerHTML = activeEditorTags.map((t, idx) => {
      const parts = t.split(':');
      const name = parts[0];
      const style = parts[1] || 'neutral';
      
      let badgeClass = 'badge-neutral';
      if (style === 'primary') badgeClass = 'badge-primary';
      else if (style === 'success') badgeClass = 'badge-success';
      else if (style === 'danger') badgeClass = 'badge-error';
      else if (style === 'warning') badgeClass = 'badge-scheduled';
      
      return `
        <span class="editor-tag-pill badge ${badgeClass}" data-idx="${idx}" title="Click to cycle style">
          ${name}
          <span class="remove-tag" data-idx="${idx}">&times;</span>
        </span>
      `;
    }).join("");
    
    // Wire remove tag buttons
    list.querySelectorAll(".remove-tag").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.dataset.idx);
        activeEditorTags.splice(idx, 1);
        renderEditorTags();
      });
    });
    
    // Wire click on pills to toggle styles
    list.querySelectorAll(".editor-tag-pill").forEach(pill => {
      pill.addEventListener("click", () => {
        const idx = parseInt(pill.dataset.idx);
        const parts = activeEditorTags[idx].split(':');
        const name = parts[0];
        const style = parts[1] || 'neutral';
        
        // Cycle styles: neutral -> primary -> success -> danger -> warning -> neutral
        const styles = ['neutral', 'primary', 'success', 'danger', 'warning'];
        const nextIdx = (styles.indexOf(style) + 1) % styles.length;
        const nextStyle = styles[nextIdx];
        
        activeEditorTags[idx] = `${name}:${nextStyle}`;
        renderEditorTags();
      });
    });
  }

  // Cover Image Inputs and Change Listeners
  const coverUrlInput = document.getElementById("editCoverUrl");
  if (coverUrlInput) {
    coverUrlInput.addEventListener("input", (e) => {
      const url = e.target.value.trim();
      const coverPreview = document.getElementById("editCoverPreview");
      if (coverPreview) {
        if (url) {
          coverPreview.style.backgroundImage = `url('${url}')`;
          coverPreview.style.border = "none";
          coverPreview.innerHTML = "";
        } else {
          coverPreview.style.backgroundImage = "none";
          coverPreview.style.border = "1.5px dashed var(--border)";
          coverPreview.innerHTML = `<i data-lucide="image" class="muted" style="width:32px;height:32px"></i>`;
          if (window.lucide) window.lucide.createIcons();
        }
      }
    });
  }

  const uploadCoverBtn = document.getElementById("uploadCoverBtn");
  const uploadCoverFileInput = document.getElementById("editCoverFile");
  if (uploadCoverBtn && uploadCoverFileInput) {
    uploadCoverBtn.addEventListener("click", () => uploadCoverFileInput.click());
    uploadCoverFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const base64 = event.target.result;
          const coverPreview = document.getElementById("editCoverPreview");
          document.getElementById("editCoverUrl").value = base64;
          if (coverPreview) {
            coverPreview.style.backgroundImage = `url('${base64}')`;
            coverPreview.style.border = "none";
            coverPreview.innerHTML = "";
          }
        };
        reader.readAsDataURL(file);
      }
    });
  }

  const removeCoverBtn = document.getElementById("removeCoverBtn");
  if (removeCoverBtn) {
    removeCoverBtn.addEventListener("click", () => {
      document.getElementById("editCoverUrl").value = "";
      const coverPreview = document.getElementById("editCoverPreview");
      if (coverPreview) {
        coverPreview.style.backgroundImage = "none";
        coverPreview.style.border = "1.5px dashed var(--border)";
        coverPreview.innerHTML = `<i data-lucide="image" class="muted" style="width:32px;height:32px"></i>`;
        if (window.lucide) window.lucide.createIcons();
      }
      document.getElementById("editCoverFile").value = "";
    });
  }

  // Tag Input Addition Listener
  const newTagInput = document.getElementById("newTagInput");
  if (newTagInput) {
    newTagInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const val = newTagInput.value.trim();
        if (val) {
          const lowerVal = val.toLowerCase();
          const exists = activeEditorTags.some(t => t.split(':')[0].toLowerCase() === lowerVal);
          if (!exists) {
            activeEditorTags.push(`${val}:neutral`);
            renderEditorTags();
          }
          newTagInput.value = "";
        }
      }
    });
  }

  // Rich Text Editor Toolbar Listeners
  const editorToolbar = document.getElementById("editorToolbar");
  if (editorToolbar) {
    editorToolbar.querySelectorAll("[data-cmd]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const cmd = btn.dataset.cmd;
        document.execCommand(cmd, false, null);
        document.getElementById("editBodyRich").focus();
      });
    });

    editorToolbar.querySelectorAll("[data-block]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const block = btn.dataset.block;
        document.execCommand("formatBlock", false, block);
        document.getElementById("editBodyRich").focus();
      });
    });

    let savedRange = null;
    const saveSelection = () => {
      const selection = window.getSelection();
      if (selection.rangeCount > 0) {
        savedRange = selection.getRangeAt(0);
      }
    };
    const restoreSelection = () => {
      if (savedRange) {
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(savedRange);
      }
    };

    const richBody = document.getElementById("editBodyRich");
    if (richBody) {
      richBody.addEventListener("mouseup", saveSelection);
      richBody.addEventListener("keyup", saveSelection);
    }

    const foreColorInput = document.getElementById("tb-forecolor");
    if (foreColorInput) {
      foreColorInput.addEventListener("input", (e) => {
        restoreSelection();
        const color = e.target.value;
        document.execCommand("foreColor", false, color);
      });
    }

    const backColorInput = document.getElementById("tb-backcolor");
    if (backColorInput) {
      backColorInput.addEventListener("input", (e) => {
        restoreSelection();
        const color = e.target.value;
        if (!document.execCommand("hiliteColor", false, color)) {
          document.execCommand("backColor", false, color);
        }
      });
    }
    
    const tbLink = document.getElementById("tb-link");
    if (tbLink) {
      tbLink.addEventListener("click", (e) => {
        e.preventDefault();
        restoreSelection();
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          const selectedText = range.toString().trim();
          
          if (selectedText.length > 0) {
            const url = prompt("Enter the link URL (e.g., https://google.com):");
            if (url) {
              restoreSelection();
              document.execCommand("createLink", false, url);
            }
          } else {
            const linkText = prompt("Enter link text:");
            if (linkText) {
              const url = prompt("Enter the link URL (e.g., https://google.com):");
              if (url) {
                restoreSelection();
                const a = document.createElement("a");
                a.href = url;
                a.textContent = linkText;
                a.target = "_blank";
                range.insertNode(a);
                // Move cursor after the inserted link
                range.setStartAfter(a);
                range.setEndAfter(a);
                selection.removeAllRanges();
                selection.addRange(range);
              }
            }
          }
        }
        document.getElementById("editBodyRich").focus();
      });
    }
    
    const tbImg = document.getElementById("tb-image");
    if (tbImg) {
      tbImg.addEventListener("click", (e) => {
        e.preventDefault();
        restoreSelection();
        const url = prompt("Enter the image URL (or leave blank to select a file from your computer):");
        if (url) {
          restoreSelection();
          document.execCommand("insertImage", false, url);
          document.getElementById("editBodyRich").focus();
        } else if (url === "") {
          const inlineFileInput = document.getElementById("inlineImageFile");
          if (inlineFileInput) inlineFileInput.click();
        }
      });
    }

    const inlineFileInput = document.getElementById("inlineImageFile");
    if (inlineFileInput) {
      inlineFileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (event) => {
            restoreSelection();
            const base64 = event.target.result;
            document.execCommand("insertImage", false, base64);
            document.getElementById("editBodyRich").focus();
          };
          reader.readAsDataURL(file);
        }
      });
    }
  }

  function openEdit(d) {
    editing = d;
    document.getElementById("editSub").textContent = `${d.chan} · ${d.title}`;
    document.getElementById("editTitle").value = d.title;
    
    // Load body into rich editor
    const richBody = document.getElementById("editBodyRich");
    if (richBody) {
      richBody.innerHTML = d.body || "";
    }
    
    // Load cover image
    const coverPreview = document.getElementById("editCoverPreview");
    const coverUrlInput = document.getElementById("editCoverUrl");
    if (coverPreview && coverUrlInput) {
      coverUrlInput.value = d.cover_image || "";
      if (d.cover_image) {
        coverPreview.style.backgroundImage = `url('${d.cover_image}')`;
        coverPreview.style.border = "none";
        coverPreview.innerHTML = "";
      } else {
        coverPreview.style.backgroundImage = "none";
        coverPreview.style.border = "1.5px dashed var(--border)";
        coverPreview.innerHTML = `<i data-lucide="image" class="muted" style="width:32px;height:32px"></i>`;
        if (window.lucide) window.lucide.createIcons();
      }
    }
    
    // Load tags
    activeEditorTags = Array.isArray(d.tags) ? [...d.tags] : [];
    renderEditorTags();

    // Load metadata settings
    const editAuthor = document.getElementById("editAuthor");
    if (editAuthor) {
      editAuthor.value = d.author_name || site.name || "";
    }
    const editDate = document.getElementById("editDate");
    if (editDate) {
      editDate.value = d.custom_date || (d.created_at ? new Date(d.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }));
    }
    const editCategory = document.getElementById("editCategory");
    if (editCategory) {
      editCategory.value = d.category || site.industry || "Marketing";
    }
    
    C.openModal("editModal");
  }

  document.getElementById("saveEdit").addEventListener("click", async () => {
    if (editing) {
      const title = document.getElementById("editTitle").value.trim();
      const body = document.getElementById("editBodyRich").innerHTML;
      const cover_image = document.getElementById("editCoverUrl").value.trim();
      const tags = activeEditorTags;
      const author_name = document.getElementById("editAuthor") ? document.getElementById("editAuthor").value.trim() : "";
      const custom_date = document.getElementById("editDate") ? document.getElementById("editDate").value.trim() : "";
      const category = document.getElementById("editCategory") ? document.getElementById("editCategory").value.trim() : "";
      
      try {
        await CadenceAPI.updateDraft(editing.id, { title, body, cover_image, tags, author_name, custom_date, category });
        editing.title = title;
        editing.body = body;
        editing.cover_image = cover_image;
        editing.tags = tags;
        editing.author_name = author_name;
        editing.custom_date = custom_date;
        editing.category = category;
        
        await window.MOCK.syncMockData(site.id);
        drafts = window.MOCK.content.filter(x => x.site === site.id);
        renderDrafts();
        C.toast({ type: "success", title: "Changes saved" });
      } catch (err) {
        C.toast({ type: "error", title: "Save failed", desc: err.message });
      }
    }
    C.closeModal("editModal");
  });

  const confirmScheduleBtn = document.getElementById("confirmSchedule");
  if (confirmScheduleBtn) {
    confirmScheduleBtn.addEventListener("click", async () => {
      const draftId = document.getElementById("schedDraftId").value;
      const dateVal = document.getElementById("schedDate").value;
      const timeVal = document.getElementById("schedTime").value || "09:00";
      
      if (!draftId) {
        C.toast({ type: "warning", title: "No draft selected" });
        return;
      }
      if (!dateVal) {
        C.toast({ type: "warning", title: "Please select a date" });
        return;
      }
      
      const [yyyy, mm, dd] = dateVal.split("-").map(Number);
      const [hh, min] = timeVal.split(":").map(Number);
      const targetDate = new Date(yyyy, mm - 1, dd, hh, min, 0, 0);
      
      confirmScheduleBtn.disabled = true;
      try {
        await CadenceAPI.scheduleDraft(draftId, targetDate.toISOString());
        
        // Find draft in our local drafts list and update status
        const d = drafts.find(x => x.id == draftId);
        if (d) {
          d.status = "Scheduled";
        }
        
        await window.MOCK.syncMockData(site.id);
        drafts = window.MOCK.content.filter(x => x.site === site.id);
        renderDrafts();
        C.toast({ type: "success", title: "Draft scheduled", desc: `Scheduled for ${dateVal} at ${timeVal}` });
        C.closeModal("scheduleModal");
      } catch (err) {
        C.toast({ type: "error", title: "Scheduling failed", desc: err.message });
      } finally {
        confirmScheduleBtn.disabled = false;
      }
    });
  }

  /* ----- hero / tab buttons that jump to generate ----- */
  document.querySelectorAll("[data-tab=generate]").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".ws-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === "generate"));
    document.querySelectorAll("#wsPanels .tab-panel").forEach(pp => pp.classList.toggle("active", pp.dataset.panel === "generate"));
    document.getElementById("ideaTitle")?.focus();
  }));

  function openImageLightbox(src) {
    let overlay = document.getElementById("imageLightboxOverlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "imageLightboxOverlay";
      overlay.style = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        cursor: zoom-out;
        opacity: 0;
        transition: opacity 0.25s ease;
      `;
      overlay.innerHTML = `
        <img id="lightboxImg" style="max-width: 90%; max-height: 90%; border-radius: var(--r-md); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); object-fit: contain; width: 1000px; height: 1200px; transition: transform 0.25s ease;" />
      `;
      overlay.addEventListener("click", () => {
        overlay.style.opacity = "0";
        setTimeout(() => overlay.remove(), 250);
      });
      document.body.appendChild(overlay);
    }
    const img = overlay.querySelector("#lightboxImg");
    img.src = src;
    setTimeout(() => {
      overlay.style.opacity = "1";
    }, 10);
  }

  document.body.addEventListener("click", (e) => {
    if (e.target.closest("#editCoverPreview")) {
      const bg = e.target.closest("#editCoverPreview").style.backgroundImage;
      if (bg && bg !== "none") {
        const src = bg.replace(/^url\(['"]?/, "").replace(/['"]?\)$/, "");
        openImageLightbox(src);
      }
    }
    else if (e.target.closest(".bp-cover")) {
      const bg = e.target.closest(".bp-cover").style.backgroundImage;
      if (bg && bg !== "none") {
        const src = bg.replace(/^url\(['"]?/, "").replace(/['"]?\)$/, "");
        openImageLightbox(src);
      }
    }
    else if (e.target.closest(".ig-img")) {
      const bg = e.target.closest(".ig-img").style.backgroundImage;
      if (bg && bg !== "none") {
        const src = bg.replace(/^url\(['"]?/, "").replace(/['"]?\)$/, "");
        openImageLightbox(src);
      }
    }
    else if (e.target.closest(".yt-thumb")) {
      const bg = e.target.closest(".yt-thumb").style.backgroundImage;
      if (bg && bg !== "none") {
        const src = bg.replace(/^url\(['"]?/, "").replace(/['"]?\)$/, "");
        openImageLightbox(src);
      }
    }
    else if (e.target.tagName === "IMG" && (e.target.closest("#editBodyRich") || e.target.closest(".draft__body"))) {
      openImageLightbox(e.target.src);
    }
  });

  renderDrafts();
  C.refreshIcons();
})();
