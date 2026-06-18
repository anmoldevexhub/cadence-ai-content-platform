/* ==========================================================================
   CADENCE — website workspace logic
   ========================================================================== */
(function () {
  const C = window.Cadence, M = window.MOCK, I = C.icon;
  const params = new URLSearchParams(location.search);
  const site = M.site(params.get("site")) || M.websites[0];

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
  const days = M.schedule.days, today = "Wed";
  document.getElementById("wsWeek").innerHTML = days.map(d => {
    const items = siteContent.filter(c => c.day === d && c.status !== "Draft");
    return `<div class="week-col ${d===today?'is-today':''}"><div class="week-day"><span>${d}</span>${d===today?'<span class="badge badge-primary txs">Today</span>':''}</div>
      <div class="week-items">${items.length ? items.map(c => { const p = M.platMeta(c.platform);
        return `<div class="week-chip" title="${c.title}"><span class="icon-tile tile-${p.tile}" style="width:22px;height:22px;border-radius:6px">${I(p.icon,"style='width:12px;height:12px'")}</span>
          <span class="wc-txt"><span class="wc-time">${c.time}</span><span class="wc-site">${c.platform}</span></span></div>`; }).join("") : '<div class="week-empty">—</div>'}</div></div>`;
  }).join("");

  /* ---------- published grid ---------- */
  const published = siteContent.filter(c => c.status === "Published").concat(
    siteContent.filter(c => c.status === "Approved" || c.status === "Scheduled")
  );
  function coverGrad(plat) { return ({Blog:"linear-gradient(135deg,#6366f1,#4338ca)",LinkedIn:"linear-gradient(135deg,#0a66c2,#063b73)",YouTube:"linear-gradient(135deg,#dc2626,#7f1d1d)",Instagram:"linear-gradient(135deg,#f09433,#bc1888)"})[plat]; }
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

  /* ---------- style guide population ---------- */
  function populateStyleGuideFields() {
    const guide = site.style_guide || {};
    document.getElementById("styleTone").value = (guide.primary_tone || "Pending crawl...") + (guide.average_sentence_length ? ` (Avg: ${guide.average_sentence_length})` : "");
    document.getElementById("styleHeadings").value = guide.heading_pattern || "Pending crawl...";
    document.getElementById("styleVocab").value = (guide.recurring_vocabulary && guide.recurring_vocabulary.length) ? guide.recurring_vocabulary.join(", ") : "Pending crawl...";
    document.getElementById("styleCTAs").value = (guide.call_to_action_examples && guide.call_to_action_examples.length) ? guide.call_to_action_examples.join("\n") : "Pending crawl...";
  }
  populateStyleGuideFields();

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

  const ideaQueue = [
    { chan: "Blog", title: "How to store coffee beans for peak freshness" },
    { chan: "Instagram", title: "Behind the roast: a 15-second reel" },
    { chan: "LinkedIn", title: "Why we switched to compostable bags" },
  ];
  function renderQueue() {
    document.getElementById("queueCount").textContent = ideaQueue.length;
    document.getElementById("ideaQueue").innerHTML = ideaQueue.length ? ideaQueue.map((q, i) => { const p = M.platMeta(q.chan);
      return `<div class="idea-q"><span class="icon-tile tile-${p.tile} iq-ic">${I(p.icon,"style='width:14px;height:14px'")}</span>
        <span class="iq-t">${q.title}</span><button class="icon-btn btn-sm" data-q="${i}" title="Generate this">${I("sparkles","style='width:15px;height:15px'")}</button></div>`;
    }).join("") : `<div class="muted tsm" style="text-align:center;padding:var(--s4)">Queue is empty</div>`;
    C.refreshIcons();
    document.querySelectorAll("[data-q]").forEach(b => b.addEventListener("click", () => {
      const q = ideaQueue[+b.dataset.q]; document.getElementById("ideaTitle").value = q.title; curChan = q.chan;
      document.querySelectorAll(".chan").forEach(x => x.classList.toggle("active", x.dataset.chan === q.chan));
      startGenerate();
    }));
  }
  renderQueue();

  /* ----- sample generated bodies ----- */
  const SAMPLE = {
    Blog: { kicker: "Brewing Guide", body: ["Pour-over coffee rewards patience. The method looks simple — hot water, ground coffee, a paper filter — but three variables quietly decide whether your cup is bright and aromatic or flat and bitter.","The first is grind size. Too fine and water struggles through, over-extracting into bitterness; too coarse and it rushes past, leaving a thin, sour brew. Aim for the texture of coarse sea salt.","The second is the bloom. Pour just enough water to saturate the grounds, then wait thirty seconds as trapped CO₂ escapes. This single pause is the difference between amateur and café-quality."] },
    LinkedIn: "Motivation is a terrible training partner.\n\nIt shows up when conditions are perfect and ghosts you in February. Progressive overload doesn't care how you feel — it just asks for slightly more than last week.\n\nAdd 2.5kg. One more rep. A few seconds longer under tension. Boring? Yes. Effective? Relentlessly.\n\nThe people who get strong aren't more motivated. They're more consistent with something small.\n\nWhat's one tiny progression you can make this week? 👇",
    Instagram: { cap: "Stale beans? Here's how to tell 👇 Flat aroma · no bloom · oily surface · dull color · sour finish. Fresh coffee should smell alive the moment you open the bag.", tags: "#specialtycoffee #pourover #coffeelover #freshroast" },
    YouTube: { title: "Roasting at home: light vs. medium vs. dark (same beans)", dur: "8:42", desc: "We roasted the same Ethiopian beans three ways so you don't have to guess." },
  };

  function previewHTML(plat, title, body, coverImage) {
    const guide = site.style_guide || {};
    const primaryFont = guide.primary_font ? guide.primary_font : 'inherit';
    const headingFont = guide.heading_font ? guide.heading_font : primaryFont;
    const headingColor = guide.heading_color ? guide.heading_color : 'inherit';
    const textColor = guide.text_color ? guide.text_color : 'inherit';

    const isColorLight = (colorStr) => {
      if (!colorStr || colorStr === 'inherit' || colorStr === 'transparent') return false;
      const c = colorStr.trim().toLowerCase();
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
      const c = colorStr.trim().toLowerCase();
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
      const coverStyle = coverImage ? ` style="background-image: url('${coverImage}'); background-size: cover; background-position: center; border: none; height: 220px;"` : '';
      const coverContent = coverImage ? '' : I("image","style='width:28px;height:28px'");
      return `<div class="bp preview-wrapper-${site.id}"><div class="bp-kicker">Article</div><h2>${title}</h2>
        <div class="bp-byline"><span class="avatar avatar-sm" style="background:${site.color}">${site.short}</span> ${site.name} · 5 min read</div>
        <div class="bp-cover"${coverStyle}>${coverContent}</div>
        ${blogBody}</div>`;
    }
    if (plat === "LinkedIn") {
      const txt = (typeof body === "string" ? body : SAMPLE.LinkedIn);
      return `<div class="li"><div class="li-top"><span class="avatar li-av" style="background:${site.color}">${site.short}</span>
        <div style="flex:1"><div class="li-nm">${site.name}</div><div class="li-hl">${site.industry}</div><div class="li-time">Just now · ${I("globe","style='width:11px;height:11px'")}</div></div>${I("more-horizontal")}</div>
        <div class="li-body" style="white-space: pre-wrap;">${txt}</div>
        <div class="li-react"><span class="row" style="gap:2px"><span style="background:var(--linkedin);color:#fff;width:16px;height:16px;border-radius:99px;display:grid;place-items:center;font-size:9px">👍</span></span> 248 · 32 comments</div>
        <div class="li-bar"><button>${I("thumbs-up")} Like</button><button>${I("message-circle")} Comment</button><button>${I("repeat-2")} Repost</button><button>${I("send")} Send</button></div></div>`;
    }
    if (plat === "Instagram") {
      const txt = (typeof body === "string" ? body : SAMPLE.Instagram.cap);
      return `<div class="ig"><div class="ig-top"><span class="ig-av"><span style="color:${site.color}">${site.short}</span></span><span class="ig-nm">${site.id}</span>${I("more-horizontal")}</div>
        <div class="ig-img">${I("image","style='width:32px;height:32px'")}<span class="ig-tag">${title.slice(0,28)}</span></div>
        <div class="ig-actions">${I("heart")}${I("message-circle")}${I("send")}<span class="sp">${I("bookmark")}</span></div>
        <div class="ig-likes">1,204 likes</div><div class="ig-cap"><b>${site.id}</b> ${txt}</div></div>`;
    }
    if (plat === "YouTube") {
      const txt = (typeof body === "string" ? body : SAMPLE.YouTube.desc);
      return `<div class="yt"><div class="yt-thumb"><span class="play">${I("play")}</span><span class="dur">8:42</span></div>
        <div class="yt-info"><span class="avatar yt-av" style="background:${site.color}">${site.short}</span>
        <div><div class="yt-t">${title}</div><div class="yt-ch">${site.name} · ${txt.substring(0, 80)}...</div></div></div></div>`;
    }
  }

  /* ----- draft model ----- */
  let drafts = M.content.filter(c => c.site === site.id);
  let filter = "all";

  function statusPill(s) { return `<span class="badge badge-${s.toLowerCase()}">${s}</span>`; }

  function draftCard(d) {
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
    return `<div class="draft" data-card="${d.id}">
      <div class="draft__head"><span class="icon-tile tile-${p.tile}">${I(p.icon)}</span>
        <div class="d-meta"><div class="d-title">${d.title}</div><div class="d-sub">${d.chan} · AI draft ${statusPill(d.status)}</div></div>
        <button class="icon-btn btn-sm" data-act="more" data-id="${d.id}">${I("more-vertical")}</button></div>
      <div class="draft__body">${previewHTML(d.chan, d.title, d.body, d.cover_image)}</div>
      <div class="draft__foot">${actions}</div></div>`;
  }

  function renderDrafts() {
    const list = drafts.filter(d => filter === "all" || d.status === filter);
    const wrap = document.getElementById("draftList");
    if (!list.length) { wrap.innerHTML = `<div class="empty card" style="padding:var(--s9)"><div class="empty-art">${I("sparkles")}</div><h3>No ${filter==='all'?'':filter.toLowerCase()+' '}drafts</h3><p>Use the composer to generate AI content for this website.</p></div>`; C.refreshIcons(); return; }
    wrap.innerHTML = list.map(draftCard).join("");
    C.refreshIcons();
    wireDraftActions();
  }

  function wireDraftActions() {
    document.querySelectorAll("[data-act]").forEach(b => {
      if (b._wired) return; b._wired = true;
      b.addEventListener("click", async () => {
        const id = b.dataset.id, act = b.dataset.act, d = drafts.find(x => x.id === id);
        if (!d) return;
        if (act === "approve") {
          try {
            await CadenceAPI.approveDraft(d.id);
            d.status = "Approved";
            C.toast({ type: "success", title: "Draft approved", desc: "Ready to schedule" });
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
            renderDrafts();
          } catch (err) {
            C.toast({ type: "error", title: "Rejection failed", desc: err.message });
          }
        }
        else if (act === "schedule") {
          try {
            const schedDate = new Date();
            schedDate.setDate(schedDate.getDate() + 1); // schedule for tomorrow
            await CadenceAPI.scheduleDraft(d.id, schedDate.toISOString());
            d.status = "Scheduled";
            C.toast({ type: "success", title: "Scheduled for tomorrow" });
            renderDrafts();
          } catch (err) {
            C.toast({ type: "error", title: "Scheduling failed", desc: err.message });
          }
        }
        else if (act === "regen") {
          await regenerate(d);
        }
        else if (act === "edit" || act === "view") {
          openEdit(d);
        }
        else if (act === "more") {
          C.toast({ type: "info", title: "Duplicate · Move · Delete" });
        }
      });
    });
  }

  async function regenerate(d) {
    const card = document.querySelector(`[data-card="${d.id}"] .draft__body`);
    card.innerHTML = genLoadingHTML(); C.refreshIcons();
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
    const title = document.getElementById("ideaTitle").value.trim() || `New ${curChan} post about ${site.name}`;
    const btn = document.getElementById("genBtn");
    btn.disabled = true; btn.innerHTML = '<i data-lucide="loader-circle" class="spin"></i> Generating…'; C.refreshIcons();
    
    // Switch to generate panel visibly first
    document.querySelectorAll(".ws-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === "generate"));
    document.querySelectorAll("#wsPanels .tab-panel").forEach(pp => pp.classList.toggle("active", pp.dataset.panel === "generate"));

    try {
      const idea = await CadenceAPI.submitIdea(site.id, title, curChan.toLowerCase());
      await CadenceAPI.generateContent(idea.id);
      
      await window.MOCK.syncMockData(site.id);
      drafts = window.MOCK.content.filter(x => x.site === site.id);
      
      filter = "all";
      document.querySelectorAll("#draftFilter button").forEach(x => x.classList.toggle("active", x.dataset.f === "all"));
      renderDrafts();
      
      C.toast({ type: "success", title: "Draft ready", desc: `${curChan} content generated` });
      document.getElementById("ideaTitle").value = "";
    } catch (err) {
      console.error(err);
      C.toast({ type: "error", title: "Generation failed", desc: err.message });
    } finally {
      btn.disabled = false; btn.innerHTML = I("sparkles") + "Generate"; C.refreshIcons();
    }
  }
  document.getElementById("genBtn").addEventListener("click", startGenerate);

  document.querySelectorAll("#draftFilter button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#draftFilter button").forEach(x => x.classList.remove("active")); b.classList.add("active"); filter = b.dataset.f; renderDrafts();
  }));

  /* ----- edit modal ----- */
  let editing = null;
  function openEdit(d) {
    editing = d;
    document.getElementById("editSub").textContent = `${d.chan} · ${d.title}`;
    document.getElementById("editTitle").value = d.title;
    document.getElementById("editBody").value = d.body || "";
    C.openModal("editModal");
  }
  document.getElementById("saveEdit").addEventListener("click", async () => {
    if (editing) {
      const title = document.getElementById("editTitle").value;
      const body = document.getElementById("editBody").value;
      try {
        await CadenceAPI.updateDraft(editing.id, { title, body });
        editing.title = title;
        editing.body = body;
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

  /* ----- hero / tab buttons that jump to generate ----- */
  document.querySelectorAll("[data-tab=generate]").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".ws-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === "generate"));
    document.querySelectorAll("#wsPanels .tab-panel").forEach(pp => pp.classList.toggle("active", pp.dataset.panel === "generate"));
    document.getElementById("ideaTitle")?.focus();
  }));

  renderDrafts();
  C.refreshIcons();
})();
