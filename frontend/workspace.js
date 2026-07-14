/* ==========================================================================
   CADENCE — website workspace logic
   ========================================================================== */
(function () {
  const C = window.Candence, M = window.MOCK, I = C.icon;
  const params = new URLSearchParams(location.search);
  let site = M.site(params.get("site")) || M.websites[0];

  // Intercept relative domain links in content previews/editor to prevent local 404 redirects (e.g. www.devexhub.com -> https://www.devexhub.com)
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a");
    if (a && a.closest(".bp, .li, .ig, .yt, .rich-editor, #largePreviewBody, #draftPreviewContent")) {
      const href = a.getAttribute("href");
      if (href && href.trim() && !/^(https?:\/\/|mailto:|tel:|#|\/)/i.test(href.trim())) {
        e.preventDefault();
        window.open("https://" + href.trim(), "_blank");
      }
    }
  });

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
  const siteContent = M.content.filter(c => c.site === site.id);

  // Calculate live stats from actual content
  const publishedCount = siteContent.filter(c => c.status === "Published" || c.status === "published").length;
  const scheduledCount = siteContent.filter(c => c.status === "Scheduled" || c.status === "scheduled").length;
  const pendingCount = siteContent.filter(c => c.status === "Draft" || c.status === "draft").length;
  const totalCount = siteContent.length;

  const ovStats = [
    { l: "Posts published", v: publishedCount, d: site.engagement, icon: "send", tile: "blog" },
    { l: "Scheduled", v: scheduledCount, d: "this week", icon: "calendar-clock", tile: "linkedin" },
    { l: "Pending approval", v: pendingCount, d: "needs review", icon: "clock", tile: "youtube" },
    { l: "Total posts", v: totalCount, d: "all time", icon: "layers", tile: "instagram" },
  ];
  document.getElementById("ovStats").innerHTML = ovStats.map(s => `
    <div class="stat"><div class="stat-top"><span class="stat-label">${s.l}</span><span class="stat-ic icon-tile tile-${s.tile}">${I(s.icon)}</span></div>
      <div class="stat-val mono">${s.v}</div><div class="stat-delta delta-up muted" style="font-weight:500">${s.d}</div></div>`).join("");
  // Sort by created_at descending
  const sortedContent = [...siteContent].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  const recentContent = sortedContent.slice(0, 5);

  let pipelineHTML = recentContent.map(c => {
    const p = M.platMeta(c.platform);
    return `<div class="pipe-row" style="cursor: pointer; padding: 11px var(--s2); border-radius: var(--r-sm); transition: background 0.15s ease;" onclick="window.previewDraftFromWeekChip('${c.id}')" title="Click to view details">
      <span class="icon-tile tile-${p.tile}">${I(p.icon)}</span>
      <span class="pr-t" style="margin-left: 4px;">${c.title}</span>
      <span class="badge badge-${c.status.toLowerCase()}">${c.status}</span>
    </div>`;
  }).join("");

  if (siteContent.length > 5) {
    pipelineHTML += `
      <div style="padding: var(--s3) 0 var(--s1); text-align: center; border-top: 1px solid var(--border); margin-top: var(--s2);">
        <button class="btn btn-soft btn-sm" data-tab="drafts" style="font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: var(--r-sm);">
          View all ${siteContent.length} drafts
        </button>
      </div>`;
  }

  document.getElementById("ovPipeline").innerHTML = pipelineHTML || `<div class="empty"><div class="empty-art">${I("file-plus")}</div><h3>No content yet</h3><p>Generate your first drafts to get started.</p></div>`;

  const counts = { Blog: 0, LinkedIn: 0, YouTube: 0, Instagram: 0 };
  siteContent.forEach(c => {
    const platform = c.chan || c.platform;
    if (counts[platform] !== undefined) {
      counts[platform]++;
    }
  });

  const chanData = [
    ["Blog", "blog", counts.Blog, "var(--blog)"],
    ["LinkedIn", "linkedin", counts.LinkedIn, "var(--linkedin)"],
    ["YouTube", "youtube", counts.YouTube, "var(--youtube)"],
    ["Instagram", "instagram", counts.Instagram, "var(--instagram)"]
  ];
  const chanMax = Math.max(...Object.values(counts), 1);
  document.getElementById("ovChannels").innerHTML = chanData.map(([n,t,v,col]) => `
    <div><div class="row-between mb2"><span class="row gap2"><span class="icon-tile tile-${t}" style="width:24px;height:24px;border-radius:6px">${I(M.platMeta(n).icon,"style='width:13px;height:13px'")}</span> ${n}</span><span class="fw6 mono">${v}</span></div>
      <div class="chan-bar"><i style="width:${Math.round(v/chanMax*100)}%;background:${col}"></i></div></div>`).join("");

  /* ---------- calendar week (full cal-board, mirrors global calendar) ---------- */
  const todayIndex = new Date().getDay();
  const days = M.schedule.days;
  const today = days[todayIndex === 0 ? 6 : todayIndex - 1];

  let wsWeekOffset = 0;

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

  function renderWorkspaceCalendar() {
    const todayDate = new Date();
    todayDate.setDate(todayDate.getDate() + (wsWeekOffset * 7));
    const currentDayOfWeek = todayDate.getDay() === 0 ? 6 : todayDate.getDay() - 1;
    const startOfWeek = new Date(todayDate);
    startOfWeek.setDate(todayDate.getDate() - currentDayOfWeek);
    startOfWeek.setHours(0, 0, 0, 0);

    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    endOfWeek.setHours(23, 59, 59, 999);

    // Week dates array for each day
    const weekDates = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(startOfWeek);
      d.setDate(startOfWeek.getDate() + i);
      weekDates.push(d);
    }

    // Format week label
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const startStr = `${months[startOfWeek.getMonth()]} ${startOfWeek.getDate()}`;
    const endStr   = `${months[endOfWeek.getMonth()]} ${endOfWeek.getDate()}`;
    const yearStr  = endOfWeek.getFullYear();

    const weekLabelEl = document.getElementById("wsWeekLabel");
    if (weekLabelEl) {
      weekLabelEl.textContent = wsWeekOffset === 0
        ? `This week  ·  ${startStr} – ${endStr}, ${yearStr}`
        : `${startStr} – ${endStr}, ${yearStr}`;
    }

    // Active platform filter
    const wsCalPlatFilter = document.getElementById("wsCalPlatFilter");
    const activePlatBtn = wsCalPlatFilter ? wsCalPlatFilter.querySelector("button.active") : null;
    const activePlat = activePlatBtn ? activePlatBtn.dataset.p : "all";

    // Cards for this week from this site
    let wsCards = siteContent.filter(c => {
      if (c.status !== "Scheduled" && c.status !== "Published") return false;
      if (!c.scheduled_for) return false;
      const cardDate = new Date(c.scheduled_for);
      return cardDate >= startOfWeek && cardDate <= endOfWeek;
    });

    function visibleCard(c) {
      return activePlat === "all" || c.platform === activePlat;
    }

    const board = document.getElementById("wsCalBoard");
    if (!board) return;

    const actualToday = new Date();
    actualToday.setHours(0, 0, 0, 0);

    board.innerHTML = days.map((dayName, idx) => {
      const colDate = new Date(weekDates[idx]);
      colDate.setHours(0, 0, 0, 0);
      const isPastDate = colDate < actualToday;
      const isToday = colDate.getTime() === actualToday.getTime();

      const items = wsCards.filter(c => {
        if (!visibleCard(c)) return false;
        const cd = new Date(c.scheduled_for);
        const cdIdx = cd.getDay() === 0 ? 6 : cd.getDay() - 1;
        return days[cdIdx] === dayName;
      }).sort((a, b) => a.time.localeCompare(b.time));

      function cardHTML(c) {
        const p = M.platMeta(c.platform);
        const w = M.site(c.site);
        const isFrozen = c.status === "Published" || isPastDate;
        return `<div class="cal-card ${isFrozen ? 'frozen' : ''}" draggable="${!isFrozen}" data-id="${c.id}" style="border-left:3px solid ${p.color}; ${isFrozen ? 'cursor:default;' : 'cursor:grab;'}">
          ${!isFrozen ? `<button class="icon-btn btn-sm cal-card-delete" data-del-id="${c.id}" title="Remove slot"><i data-lucide="trash-2" style="width:12px;height:12px;"></i></button>` : ''}
          <div class="cc-top">
            <span class="icon-tile tile-${p.tile}" style="width:22px;height:22px;border-radius:6px">${I(p.icon, "style='width:12px;height:12px'")}</span>
            <span class="cc-time mono" ${!isFrozen ? 'style="cursor:pointer;text-decoration:underline;" title="Click to edit time"' : ''}>${c.time}</span>
            <span class="badge badge-${c.status.toLowerCase()}" style="margin-left:auto;margin-right:${!isFrozen ? '20px' : '4px'};">${c.status}</span>
          </div>
          <div class="cc-title">${c.title}</div>
          <div class="cc-foot"><span class="favicon" style="width:16px;height:16px;border-radius:4px;font-size:9px;background:${w ? w.color : 'var(--primary)'}">${w ? w.short : '?'}</span> ${w ? w.name : 'Site'}</div>
        </div>`;
      }

      const itemsHTML = items.length
        ? items.map(c => cardHTML(c)).join("")
        : (isPastDate
            ? `<div class="cal-empty frozen"><span>Passed</span></div>`
            : `<div class="cal-empty" data-add-day="${dayName}">${I("plus")}<span>Drop or add</span></div>`);

      const todayBadge = isToday ? `<span class="badge badge-primary txs">Today</span>` : '';
      const calDate = `${months[weekDates[idx].getMonth()]} ${weekDates[idx].getDate()}`;

      return `<div class="cal-col ${isPastDate ? 'cal-col-frozen' : ''}" data-day="${dayName}">
        <div class="cal-head">
          <div>
            <div class="cal-dow">${dayName} ${todayBadge}</div>
            <div class="cal-date">${calDate}</div>
          </div>
          <span class="cal-count">${items.length}</span>
        </div>
        <div class="cal-slots" data-day="${dayName}" style="${isPastDate ? 'background:var(--bg-subtle);opacity:0.85;' : ''}">
          ${itemsHTML}
        </div>
      </div>`;
    }).join("");

    C.refreshIcons();

    // Delete buttons
    board.querySelectorAll(".cal-card-delete").forEach(btn => {
      btn.addEventListener("click", async e => {
        e.stopPropagation();
        const id = btn.dataset.delId;
        try {
          await CandenceAPI.unscheduleDraft(id);
          C.toast({ type: "success", title: "Removed from calendar" });
          await M.syncMockData();
          renderWorkspaceCalendar();
        } catch (err) {
          C.toast({ type: "error", title: "Removal failed", desc: err.message });
        }
      });
    });

    // Card click → preview
    board.querySelectorAll(".cal-card").forEach(card => {
      card.addEventListener("click", e => {
        if (e.target.closest(".cal-card-delete") || e.target.closest(".cc-time")) return;
        const id = card.dataset.id;
        const d = wsCards.find(x => String(x.id) === String(id));
        if (!d) return;
        document.getElementById("largePreviewTitle").textContent = d.title;
        document.getElementById("largePreviewSub").textContent = `${d.platform} · ${d.status}`;
        const bodyContainer = document.getElementById("largePreviewBody");
        if (bodyContainer) {
          bodyContainer.innerHTML = previewHTML(d.platform, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date);
        }
        C.openModal("largePreviewModal");
      });
    });

    // Time click → edit schedule
    board.querySelectorAll(".cc-time").forEach(timeBtn => {
      const cardEl = timeBtn.closest(".cal-card");
      if (!cardEl || cardEl.classList.contains("frozen")) return;
      timeBtn.addEventListener("click", e => {
        e.stopPropagation();
        const id = cardEl.dataset.id;
        const c = wsCards.find(x => String(x.id) === String(id));
        if (!c) return;
        const sf = new Date(c.scheduled_for);
        const yyyy = sf.getFullYear();
        const mm = String(sf.getMonth()+1).padStart(2,'0');
        const dd2 = String(sf.getDate()).padStart(2,'0');
        const esDate = document.getElementById("esDate");
        const esTimeEl = document.getElementById("esTime");
        if (esDate) esDate.value = `${yyyy}-${mm}-${dd2}`;
        if (esTimeEl) esTimeEl.value = c.time;
        if (window.updateMinTime) window.updateMinTime();
        window.activeEditCard = c;
        C.openModal("editScheduleModal");
      });
    });

    // Drag and Drop
    let dragId = null;
    board.querySelectorAll(".cal-card").forEach(card => {
      if (card.classList.contains("frozen")) return;
      card.addEventListener("dragstart", e => {
        dragId = card.dataset.id;
        card.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", () => {
        dragId = null;
        board.querySelectorAll(".cal-card").forEach(c => c.classList.remove("dragging"));
        board.querySelectorAll(".cal-slots").forEach(s => s.classList.remove("drop-on"));
      });
    });

    board.querySelectorAll(".cal-slots").forEach(slot => {
      const slotDayIdx = days.indexOf(slot.dataset.day);
      const colDate2 = new Date(weekDates[slotDayIdx]);
      colDate2.setHours(0, 0, 0, 0);
      const isPast2 = colDate2 < actualToday;

      slot.addEventListener("dragover", e => {
        if (isPast2) return;
        e.preventDefault();
        slot.classList.add("drop-on");
      });
      slot.addEventListener("dragleave", () => slot.classList.remove("drop-on"));
      slot.addEventListener("drop", async e => {
        e.preventDefault();
        slot.classList.remove("drop-on");
        if (isPast2) {
          C.toast({ type: "warning", title: "Rescheduling blocked", desc: "Cannot schedule to past dates." });
          return;
        }
        const dragged = wsCards.find(c => c.id === dragId);
        if (!dragged) return;
        const targetDate = new Date(weekDates[slotDayIdx]);
        const tp = dragged.time.split(':');
        targetDate.setHours(parseInt(tp[0]), parseInt(tp[1] || 0), 0, 0);
        if (targetDate < new Date()) {
          C.toast({ type: "warning", title: "Rescheduling blocked", desc: `Today at ${dragged.time} has already passed.` });
          return;
        }
        try {
          await CandenceAPI.scheduleDraft(dragged.id, targetDate.toISOString());
          await M.syncMockData();
          renderWorkspaceCalendar();
          C.toast({ type: "success", title: "Rescheduled", desc: `Moved to ${slot.dataset.day}` });
        } catch (err) {
          C.toast({ type: "error", title: "Rescheduling failed", desc: err.message });
        }
      });
    });
  }

  // Initial render
  renderWorkspaceCalendar();

  // Week navigation
  const prevBtn = document.getElementById("wsPrevWeek");
  const nextBtn = document.getElementById("wsNextWeek");
  if (prevBtn) prevBtn.onclick = () => { wsWeekOffset--; renderWorkspaceCalendar(); };
  if (nextBtn) nextBtn.onclick = () => { wsWeekOffset++; renderWorkspaceCalendar(); };

  // Platform filter pills
  const wsCalPlatFilter2 = document.getElementById("wsCalPlatFilter");
  if (wsCalPlatFilter2) {
    wsCalPlatFilter2.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        wsCalPlatFilter2.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        renderWorkspaceCalendar();
      });
    });
  }



  // Edit-schedule modal save
  const wsEsSave = document.getElementById("esSave");
  if (wsEsSave && !wsEsSave._wsWired) {
    wsEsSave._wsWired = true;
    wsEsSave.addEventListener("click", async () => {
      const card = window.activeEditCard;
      if (!card) return;
      const dateVal = (document.getElementById("esDate") || {}).value || "";
      const timeVal = (document.getElementById("esTime") || {}).value || "";
      if (!dateVal || !timeVal) { C.toast({ type: "warning", title: "Date and Time are required" }); return; }
      const targetDate = new Date(`${dateVal}T${timeVal}:00`);
      if (targetDate < new Date()) { C.toast({ type: "warning", title: "Scheduling blocked", desc: "Cannot schedule in the past." }); return; }
      try {
        await CandenceAPI.scheduleDraft(card.id, targetDate.toISOString());
        C.closeModal("editScheduleModal");
        await M.syncMockData();
        renderWorkspaceCalendar();
        C.toast({ type: "success", title: "Schedule updated" });
      } catch(err) {
        C.toast({ type: "error", title: "Failed to update schedule", desc: err.message });
      }
    });
  }


  /* ---------- published grid ---------- */
  const published = siteContent.filter(c => c.status === "Published").concat(
    siteContent.filter(c => c.status === "Approved" || c.status === "Scheduled")
  );
  function coverGrad(plat) { return ({Blog:"linear-gradient(135deg,#095075,#053046)",LinkedIn:"linear-gradient(135deg,#0a66c2,#063b73)",YouTube:"linear-gradient(135deg,#dc2626,#7f1d1d)",Instagram:"linear-gradient(135deg,#f09433,#bc1888)"})[plat]; }
  let pubCurrentPage = 1;
  const pubPageSize = 6;
  let pubActiveFilter = "all";

  function renderPub(filter) {
    if (filter !== undefined) {
      pubActiveFilter = filter;
      pubCurrentPage = 1;
    }
    const list = published.filter(c => pubActiveFilter === "all" || c.platform === pubActiveFilter);
    const grid = document.getElementById("pubGrid");
    const pagWrap = document.getElementById("pubPagination");
    
    if (!list.length) {
      grid.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="empty-art">${I("inbox")}</div><h3>Nothing here yet</h3><p>Published content for this channel will appear here.</p></div>`;
      if (pagWrap) pagWrap.innerHTML = "";
      document.getElementById("pubCount").textContent = "0 items";
      C.refreshIcons();
      return;
    }
    
    const totalItems = list.length;
    const totalPages = Math.ceil(totalItems / pubPageSize);
    
    if (pubCurrentPage > totalPages) pubCurrentPage = totalPages;
    if (pubCurrentPage < 1) pubCurrentPage = 1;
    
    const startIdx = (pubCurrentPage - 1) * pubPageSize;
    const paginatedList = list.slice(startIdx, startIdx + pubPageSize);
    
    grid.innerHTML = paginatedList.map(c => {
      const p = M.platMeta(c.platform);
      const coverStyle = c.cover_image ? `background-image: url('${c.cover_image}'); background-size: cover; background-position: center;` : `background:${coverGrad(c.platform)}`;
      const coverContent = c.cover_image ? '' : I(p.icon,"style='width:30px;height:30px'");
      return `<div class="pub-card" onclick="window.previewPublishedCard('${c.id}')"><div class="pub-cover" style="${coverStyle}">${coverContent}</div>
        <div class="pub-body"><div class="row gap2 mb3"><span class="badge badge-${c.status.toLowerCase()}">${c.status}</span><span class="muted txs">${c.platform}</span></div>
          <div class="pub-title">${c.title}</div><div class="pub-foot"><span>${c.day} · ${c.time}</span></div></div></div>`;
    }).join("");
    
    document.getElementById("pubCount").textContent = `${totalItems} item${totalItems>1?'s':''}`;
    
    if (pagWrap) {
      if (totalPages <= 1) {
        pagWrap.innerHTML = "";
      } else {
        let pagHtml = "";
        pagHtml += `<button class="btn btn-secondary btn-sm" ${pubCurrentPage === 1 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''} onclick="window.changePubPage(${pubCurrentPage - 1})">${I("arrow-left")} Prev</button>`;
        for (let i = 1; i <= totalPages; i++) {
          pagHtml += `<button class="btn ${i === pubCurrentPage ? 'btn-primary' : 'btn-secondary'} btn-sm" onclick="window.changePubPage(${i})">${i}</button>`;
        }
        pagHtml += `<button class="btn btn-secondary btn-sm" ${pubCurrentPage === totalPages ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''} onclick="window.changePubPage(${pubCurrentPage + 1})">Next ${I("arrow-right")}</button>`;
        pagWrap.innerHTML = pagHtml;
      }
    }
    C.refreshIcons();
  }

  window.changePubPage = function(page) {
    pubCurrentPage = page;
    renderPub();
  };

  window.previewPublishedCard = function(itemId) {
    const item = M.content.find(x => String(x.id) === String(itemId));
    if (!item) return;
    document.getElementById("largePreviewTitle").textContent = item.title;
    document.getElementById("largePreviewSub").textContent = `${item.platform} · ${item.status} details`;
    const bodyContainer = document.getElementById("largePreviewBody");
    if (bodyContainer) {
      bodyContainer.innerHTML = previewHTML(
        item.platform,
        item.title,
        item.body || "No content available",
        item.cover_image,
        item.tags || [],
        item.category,
        item.created_at,
        item.author_name,
        item.custom_date
      );
    }
    const footContainer = document.getElementById("largePreviewFoot");
    if (footContainer) {
      footContainer.innerHTML = `
        <button class="btn btn-secondary btn-sm" id="editPublishedPostBtn">${I("edit-3")} Edit Published Post</button>
        ${item.platform === "Blog" ? `<button class="btn btn-success btn-sm" id="republishPostBtn">${I("rotate-cw")} Republish</button>` : ''}
        <span class="spacer"></span>
        <button class="btn btn-primary btn-sm" data-close-modal>Close preview</button>
      `;
      C.refreshIcons();
      document.getElementById("editPublishedPostBtn").addEventListener("click", () => {
        C.closeModal("largePreviewModal");
        openEdit(item);
      });
      const repubBtn = document.getElementById("republishPostBtn");
      if (repubBtn) {
        repubBtn.addEventListener("click", async () => {
          try {
            repubBtn.disabled = true;
            C.toast({ type: "info", title: "Updating Live Post", desc: "Pushing changes to the website..." });
            await CandenceAPI.republishDraft(item.id);
            C.toast({ type: "success", title: "Republish Succeeded", desc: "Your live blog has been updated!" });
            C.closeModal("largePreviewModal");
          } catch(err) {
            repubBtn.disabled = false;
            C.toast({ type: "error", title: "Republish Failed", desc: err.message });
          }
        });
      }
    }
    C.openModal("largePreviewModal");
  };

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

  // Wire the "Start crawl" button inside the style guide empty state
  const crawlBtnFromGuide = document.getElementById("crawlBtnFromGuide");
  if (crawlBtnFromGuide) {
    crawlBtnFromGuide.addEventListener("click", () => {
      const mainCrawlBtn = document.getElementById("crawlBtn");
      if (mainCrawlBtn) mainCrawlBtn.click();
    });
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
          
          await CandenceAPI.updateWebsite(site.id, data);
          
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
        await CandenceAPI.updateWebsite(site.id, { status: nextStatus });
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
        await CandenceAPI.deleteWebsite(site.id);
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
      currentSamples = await CandenceAPI.getSamples(site.id);
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
          await CandenceAPI.updateSample(site.id, id, { is_active: isActive });
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
          await CandenceAPI.deleteSample(site.id, id);
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
        const content = await window.Candence.readFileAsText(file);
        const newSample = await CandenceAPI.addSample(site.id, {
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
      const res = await CandenceAPI.getCrawlStatus(site.id);
      if (res.status === "done" || res.status === "failed") {
        clearInterval(crawlInterval);
        crawlInterval = null;
        
        crawlBtn.disabled = false;
        crawlBtn.innerHTML = `${I("refresh-cw")} Crawl website`;
        C.refreshIcons();
        C.closeModal("crawlProgressModal");
        
        if (res.status === "done") {
          C.toast({ type: "success", title: "Crawl completed", desc: "Website style guide successfully extracted!" });
        } else {
          C.toast({ type: "error", title: "Crawl failed", desc: "Unable to parse website content." });
        }
        
        // Refresh local mock data in background
        try {
          await window.MOCK.syncMockData(site.id);
          const updatedSite = window.MOCK.site(site.id);
          if (updatedSite) {
            site.style_guide = updatedSite.style_guide;
            site.needs_crawl = updatedSite.needs_crawl;
            site.scrape_status = updatedSite.scrape_status;
            populateStyleGuideFields();
          }
        } catch (syncErr) {
          console.error("Failed to sync mock data in background:", syncErr);
        }
      } else {
        const pBar = document.getElementById("crawlProgressBar");
        if (pBar) {
          let curWidth = parseFloat(pBar.style.width) || 25;
          if (curWidth < 90) {
            pBar.style.width = (curWidth + 15) + "%";
          }
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  if (crawlBtn) {
    if (site.scrape_status === "crawling") {
      crawlBtn.disabled = true;
      crawlBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Crawling...`;
      C.refreshIcons();
      
      const pBar = document.getElementById("crawlProgressBar");
      if (pBar) pBar.style.width = "40%";
      C.openModal("crawlProgressModal");
      
      crawlInterval = setInterval(async () => {
        await checkCrawlStatus();
        if (site.scrape_status === "done") {
          loadCrawledPages();
        }
      }, 2000);
    }

    crawlBtn.addEventListener("click", async () => {
      crawlBtn.disabled = true;
      crawlBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Crawling...`;
      C.refreshIcons();
      
      const pBar = document.getElementById("crawlProgressBar");
      if (pBar) pBar.style.width = "25%";
      C.openModal("crawlProgressModal");
      
      try {
        await CandenceAPI.triggerCrawl(site.id);
        C.toast({ type: "info", title: "Crawl started", desc: "Analyzing website style and page structure..." });
        crawlInterval = setInterval(async () => {
          await checkCrawlStatus();
          if (site.scrape_status === "done") {
            loadCrawledPages();
          }
        }, 2000);
      } catch (err) {
        crawlBtn.disabled = false;
        crawlBtn.innerHTML = `${I("refresh-cw")} Crawl website`;
        C.refreshIcons();
        C.closeModal("crawlProgressModal");
        C.toast({ type: "error", title: "Failed to start crawl", desc: err.message });
      }
    });
  }

  /* ---------- Crawled Data & Style Guide Editor Logic ---------- */
  let crawledPagesList = [];
  
  // Helper: extract a clean hex color from a raw CSS color string
  function cleanHex(raw) {
    if (!raw) return null;
    // Strip !important, whitespace, quotes
    const str = raw.replace(/!important/gi, "").replace(/['"]/g, "").trim();
    // Match 3 or 6 digit hex
    const m = str.match(/#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/);
    if (!m) return null;
    let hex = m[0];
    // Expand 3-digit to 6-digit
    if (hex.length === 4) {
      hex = "#" + hex[1]+hex[1]+hex[2]+hex[2]+hex[3]+hex[3];
    }
    return hex;
  }

  function populateStyleGuideFields() {
    const guide = site.style_guide || {};
    const brandColors = Array.isArray(site.brand_colors) ? site.brand_colors : [];
    const hasData = !!(guide.heading_color || guide.text_color || guide.primary_tone || guide.heading_pattern || site.tone || brandColors.length);

    const noCrawlMsg = document.getElementById("noCrawlDataMsg");
    const crawlFields = document.getElementById("crawlDataFields");
    const statusBadge = document.getElementById("crawlStatusBadge");

    if (noCrawlMsg && crawlFields) {
      noCrawlMsg.style.display = hasData ? "none" : "block";
      crawlFields.style.display = hasData ? "block" : "none";
    }

    if (statusBadge) {
      if (site.scrape_status === "done") {
        statusBadge.className = "badge badge-published";
        statusBadge.style.cssText = "font-size:11px;background:#dcfce7;color:#166534";
        statusBadge.textContent = "Crawled";
      } else if (site.scrape_status === "crawling") {
        statusBadge.className = "badge badge-scheduled";
        statusBadge.style.cssText = "font-size:11px";
        statusBadge.textContent = "Crawling...";
      } else if (hasData) {
        statusBadge.className = "badge badge-neutral";
        statusBadge.style.cssText = "font-size:11px";
        statusBadge.textContent = "From crawl";
      } else {
        statusBadge.className = "";
        statusBadge.textContent = "";
      }
    }

    if (!hasData) return;

    // --- Brand Color Swatches ---
    const swatchContainer = document.getElementById("brandColorSwatches");
    const noBrandColorsMsg = document.getElementById("noBrandColors");

    // Collect all color sources: brand_colors array + heading_color + text_color from style_guide
    const rawColors = [...brandColors];
    if (guide.heading_color) rawColors.push(guide.heading_color);
    if (guide.text_color) rawColors.push(guide.text_color);

    // Clean and deduplicate
    const cleanColors = [...new Set(
      rawColors.map(c => cleanHex(c)).filter(Boolean)
    )];

    if (swatchContainer) {
      if (cleanColors.length === 0) {
        swatchContainer.innerHTML = "";
        if (noBrandColorsMsg) noBrandColorsMsg.style.display = "block";
      } else {
        if (noBrandColorsMsg) noBrandColorsMsg.style.display = "none";
        swatchContainer.innerHTML = cleanColors.map((hex, i) => {
          const label = i === 0 ? "Primary" : i === 1 ? "Secondary" : i === 2 ? "Accent" : `Color ${i+1}`;
          // Determine if color is light or dark for label contrast
          const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
          const luminance = (0.299*r + 0.587*g + 0.114*b) / 255;
          const textCol = luminance > 0.55 ? "#374151" : "#ffffff";
          return `
            <div style="display:flex;flex-direction:column;align-items:center;gap:4px;cursor:default" title="${hex}">
              <div style="width:44px;height:44px;border-radius:8px;background:${hex};border:1px solid rgba(0,0,0,0.08);display:flex;align-items:flex-end;justify-content:center;padding-bottom:3px;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
                <span style="font-size:8px;font-weight:700;color:${textCol};letter-spacing:-0.3px;font-family:monospace">${hex.toUpperCase()}</span>
              </div>
              <span style="font-size:10px;color:var(--text-muted);font-weight:500">${label}</span>
            </div>
          `;
        }).join("") + `
          <button id="editColorsBtn" style="width:44px;height:44px;border-radius:8px;border:1px dashed var(--border);background:var(--bg-subtle);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text-muted);transition:all 0.15s" title="Edit colors">
            <i data-lucide="pencil" style="width:14px;height:14px"></i>
          </button>
        `;
        C.refreshIcons();

        // Wire edit button to open inline color editor
        const editBtn = document.getElementById("editColorsBtn");
        if (editBtn) {
          editBtn.addEventListener("click", () => {
            const currentVal = cleanColors.join(", ");
            const inp = document.createElement("input");
            inp.className = "input";
            inp.value = currentVal;
            inp.style.marginTop = "8px";
            inp.placeholder = "#hex1, #hex2, ...";
            swatchContainer.after(inp);
            inp.focus();
            editBtn.style.display = "none";
            inp.addEventListener("blur", () => {
              // Parse and refresh swatches
              site.brand_colors = inp.value.split(",").map(s => s.trim()).filter(Boolean);
              inp.remove();
              populateStyleGuideFields();
            });
          });
        }
      }
    }

    // --- Text fields ---
    const toneEl = document.getElementById("setGuideTone");
    if (toneEl) toneEl.value = guide.primary_tone || site.tone || "";

    const vocabEl = document.getElementById("setGuideVocabulary");
    if (vocabEl) {
      const vocab = guide.recurring_vocabulary || [];
      // Filter out any hex-like junk words (< 2 real letters)
      const cleanVocab = Array.isArray(vocab) ? vocab.filter(v => /[a-zA-Z]{2,}/.test(v) && !/^[0-9a-fA-F]{3,8}$/.test(v)) : [];
      vocabEl.value = cleanVocab.length ? cleanVocab.join(", ") : (Array.isArray(vocab) ? vocab.join(", ") : vocab);
    }

    const patternEl = document.getElementById("setGuideHeadingPattern");
    if (patternEl) patternEl.value = guide.heading_pattern || "";

    // --- New Crawl Style fields ---
    const headingFontEl = document.getElementById("styleHeadingFont");
    if (headingFontEl) headingFontEl.value = guide.heading_font || "";

    const styleToneEl = document.getElementById("styleTone");
    if (styleToneEl) styleToneEl.value = guide.primary_tone || site.tone || "";

    const styleVocabEl = document.getElementById("styleVocabulary");
    if (styleVocabEl) {
      const vocab = guide.recurring_vocabulary || [];
      const cleanVocab = Array.isArray(vocab) ? vocab.filter(v => /[a-zA-Z]{2,}/.test(v) && !/^[0-9a-fA-F]{3,8}$/.test(v)) : [];
      styleVocabEl.value = cleanVocab.length ? cleanVocab.join(", ") : (Array.isArray(vocab) ? vocab.join(", ") : vocab);
    }
  }

  // Populate immediately on page load
  populateStyleGuideFields();

  // Edit Style Guide Button Action
  const editStyleGuideBtn = document.getElementById("editStyleGuideBtn");
  if (editStyleGuideBtn) {
    editStyleGuideBtn.addEventListener("click", () => {
      // Make fields editable
      const fields = ["styleHeadingFont", "styleTone", "styleVocabulary"];
      fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.removeAttribute("readonly");
          el.style.background = "var(--surface)";
          el.style.border = "1px solid var(--border)";
        }
      });
      
      // Change button to Save
      editStyleGuideBtn.innerHTML = `<i data-lucide="check"></i> Save Changes`;
      editStyleGuideBtn.classList.remove("btn-secondary");
      editStyleGuideBtn.classList.add("btn-primary");
      C.refreshIcons();
      
      // Change button action to save
      editStyleGuideBtn.onclick = async () => {
        editStyleGuideBtn.disabled = true;
        const originalText = editStyleGuideBtn.innerHTML;
        editStyleGuideBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Saving...`;
        C.refreshIcons();

        const guide = site.style_guide || {};
        const updatedGuide = {
          ...guide,
          heading_font: document.getElementById("styleHeadingFont").value.trim(),
          primary_tone: document.getElementById("styleTone").value.trim(),
          recurring_vocabulary: document.getElementById("styleVocabulary").value.split(",").map(v => v.trim()).filter(v => v.length > 0)
        };

        try {
          await CandenceAPI.updateWebsite(site.id, {
            style_guide: updatedGuide,
            tone: updatedGuide.primary_tone
          });
          
          await window.MOCK.syncMockData(site.id);
          site = window.MOCK.site(site.id);
          populateStyleGuideFields();
          
          // Make fields readonly again
          fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
              el.setAttribute("readonly", true);
              el.style.background = "var(--bg-subtle)";
              el.style.border = "";
            }
          });
          
          // Reset button
          editStyleGuideBtn.innerHTML = `<i data-lucide="edit-3"></i> Edit Style Guide`;
          editStyleGuideBtn.classList.remove("btn-primary");
          editStyleGuideBtn.classList.add("btn-secondary");
          editStyleGuideBtn.disabled = false;
          C.refreshIcons();
          
          C.toast({ type: "success", title: "Style Guide saved", desc: "Successfully updated!" });
        } catch (err) {
          editStyleGuideBtn.disabled = false;
          editStyleGuideBtn.innerHTML = originalText;
          C.refreshIcons();
          C.toast({ type: "error", title: "Save failed", desc: err.message });
        }
      };
    });
  }

  // Save Style Guide Button Action
  const saveStyleGuideBtn = document.getElementById("saveStyleGuideBtn");
  if (saveStyleGuideBtn) {
    saveStyleGuideBtn.addEventListener("click", async () => {
      saveStyleGuideBtn.disabled = true;
      const originalText = saveStyleGuideBtn.innerHTML;
      saveStyleGuideBtn.innerHTML = `<i data-lucide="loader-circle" class="spin" style="width:14px;height:14px;margin-right:6px"></i> Saving...`;
      C.refreshIcons();

      const tone = document.getElementById("setGuideTone").value.trim();
      const vocabRaw = document.getElementById("setGuideVocabulary").value.trim();
      const vocab = vocabRaw ? vocabRaw.split(",").map(v => v.trim()).filter(v => v.length > 0) : [];
      const headingPattern = document.getElementById("setGuideHeadingPattern").value.trim();

      const guide = site.style_guide || {};
      const updatedGuide = {
        ...guide,
        primary_tone: tone,
        recurring_vocabulary: vocab,
        heading_pattern: headingPattern
      };

      try {
        await CandenceAPI.updateWebsite(site.id, {
          style_guide: updatedGuide,
          brand_colors: site.brand_colors || [],
          tone: tone
        });
        
        await window.MOCK.syncMockData(site.id);
        site = window.MOCK.site(site.id);
        populateStyleGuideFields();
        
        C.toast({ type: "success", title: "Style Guide saved", desc: "Successfully updated!" });
      } catch (err) {
        C.toast({ type: "error", title: "Save failed", desc: err.message });
      } finally {
        saveStyleGuideBtn.disabled = false;
        saveStyleGuideBtn.innerHTML = originalText;
        C.refreshIcons();
      }
    });
  }

  // Load crawled pages
  async function loadCrawledPages() {
    const tableBody = document.getElementById("crawledPagesTableBody");
    if (!tableBody) return;

    try {
      crawledPagesList = await CandenceAPI.getWebsitePages(site.id) || [];
      renderCrawledPages();
    } catch (err) {
      console.error("Failed to load crawled pages:", err);
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align:center; padding:var(--s5); color:var(--error)">
            Failed to load crawled pages.
          </td>
        </tr>
      `;
    }
  }

  function renderCrawledPages() {
    const tableBody = document.getElementById("crawledPagesTableBody");
    if (!tableBody) return;

    const searchQuery = document.getElementById("crawlPageSearch").value.toLowerCase().trim();
    
    const filtered = crawledPagesList.filter(p => {
      const title = (p.page_title || "").toLowerCase();
      const url = (p.page_url || "").toLowerCase();
      return title.includes(searchQuery) || url.includes(searchQuery);
    });

    if (filtered.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align:center; padding:var(--s5); color:var(--text-muted)">
            No crawled pages found.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = filtered.map(p => {
      const wordCount = p.raw_text ? p.raw_text.split(/\s+/).length : 0;
      let type = p.page_type || "Page";
      if (type === "other") type = "Page";
      type = type.charAt(0).toUpperCase() + type.slice(1);

      const titleOrUrl = p.page_title || p.page_url;
      const displayTitle = titleOrUrl.length > 50 ? titleOrUrl.substring(0, 47) + "..." : titleOrUrl;

      return `
        <tr style="border-bottom:1px solid var(--border)">
          <td style="padding:10px var(--s3); font-weight:550; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" title="${p.page_url}">
            <div style="font-weight:600; color:var(--text)">${displayTitle}</div>
            <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono); overflow:hidden; text-overflow:ellipsis">${p.page_url}</div>
          </td>
          <td style="padding:10px var(--s3)"><span class="badge badge-neutral">${type}</span></td>
          <td style="padding:10px var(--s3); text-align:right" class="mono">${wordCount}</td>
          <td style="padding:10px var(--s3); text-align:center">
            <button class="btn btn-secondary btn-sm btn-view-page-details" data-page-id="${p.id}" style="padding:4px 8px; font-size:12px;">
              View Details
            </button>
          </td>
        </tr>
      `;
    }).join("");

    // Wire up details button
    tableBody.querySelectorAll(".btn-view-page-details").forEach(btn => {
      btn.addEventListener("click", () => {
        const pageId = btn.dataset.pageId;
        const pageObj = crawledPagesList.find(p => String(p.id) === String(pageId));
        if (pageObj) {
          openPageDetailsModal(pageObj);
        }
      });
    });
  }

  // Open Scraped Page Details Modal
  function openPageDetailsModal(page) {
    document.getElementById("pageDetailsTitle").textContent = page.page_title || "Page details";
    document.getElementById("pageDetailsUrl").textContent = page.page_url;
    document.getElementById("pageMetaTitle").textContent = page.meta_title || page.page_title || "—";
    document.getElementById("pageMetaDesc").textContent = page.meta_description || "—";
    document.getElementById("pageAuthor").textContent = page.author || "—";
    
    const typeBadge = document.getElementById("pageTypeBadge");
    if (typeBadge) {
      let type = page.page_type || "Page";
      if (type === "other") type = "Page";
      typeBadge.textContent = type.toUpperCase();
    }

    const dateObj = new Date(page.crawled_at);
    document.getElementById("pageCrawledDate").textContent = dateObj.toLocaleString();

    // CTAs
    const ctasListEl = document.getElementById("pageCTAList");
    if (ctasListEl) {
      const ctas = page.ctas || [];
      if (ctas.length > 0) {
        ctasListEl.innerHTML = ctas.map(c => {
          let text = c;
          if (typeof c === 'object') {
            text = c.text || c.label || JSON.stringify(c);
          }
          return `<div style="padding:4px 8px; background:var(--surface); border-radius:4px; border:1px solid var(--border)">${text}</div>`;
        }).join("");
      } else {
        ctasListEl.innerHTML = `<span class="muted" style="font-size:12px">No CTAs detected on this page.</span>`;
      }
    }

    // Heading structure
    const headingsEl = document.getElementById("pageHeadingStructure");
    if (headingsEl) {
      const headings = page.heading_structure || [];
      if (headings.length > 0) {
        headingsEl.innerHTML = headings.map(h => {
          let lvl = "H";
          let txt = "";
          if (typeof h === 'object') {
            lvl = (h.level || "H").toUpperCase();
            txt = h.text || "";
          } else {
            txt = h;
          }
          const indent = lvl === 'H1' ? '0px' : lvl === 'H2' ? '12px' : lvl === 'H3' ? '24px' : '36px';
          return `<div style="margin-left:${indent}; padding:2px 0;"><span class="badge badge-neutral" style="font-size:9px; padding:1px 3px; margin-right:6px">${lvl}</span>${txt}</div>`;
        }).join("");
      } else {
        headingsEl.innerHTML = `<span class="muted" style="font-size:12px">No headings detected.</span>`;
      }
    }

    // Main Content text
    const textEl = document.getElementById("pageMainContentText");
    if (textEl) {
      textEl.textContent = page.main_content || page.raw_text || "No text content available.";
    }

    C.openModal("pageDetailsModal");
  }

  // Bind Search & Refresh button listeners
  const crawlPageSearch = document.getElementById("crawlPageSearch");
  if (crawlPageSearch) {
    crawlPageSearch.addEventListener("input", renderCrawledPages);
  }

  const btnRefreshCrawlPagesList = document.getElementById("btnRefreshCrawlPagesList");
  if (btnRefreshCrawlPagesList) {
    btnRefreshCrawlPagesList.addEventListener("click", () => {
      btnRefreshCrawlPagesList.disabled = true;
      loadCrawledPages().finally(() => {
        btnRefreshCrawlPagesList.disabled = false;
      });
    });
  }

  // Load Style Guide and Crawled Pages initially
  populateStyleGuideFields();
  loadCrawledPages();
  /* ------------------------------------------------------------- */

  let activeConns = [];

  async function loadConnections() {
    try {
      activeConns = await CandenceAPI.getSocialConnections(site.id) || [];
    } catch(e) {
      console.error("Failed to load connections:", e);
      activeConns = [];
    }
    renderConnections();
  }

  window.showWorkspaceBlogAuthFields = function() {
    const authType = document.getElementById('connectAuthType').value;
    document.getElementById('connect_auth_fields_api_key').classList.toggle('hide', authType !== 'api_key');
    document.getElementById('connect_auth_fields_bearer_token').classList.toggle('hide', authType !== 'bearer_token');
    document.getElementById('connect_auth_fields_basic_auth').classList.toggle('hide', authType !== 'basic_auth');
  };

  const authSelect = document.getElementById('connectAuthType');
  if (authSelect) {
    authSelect.addEventListener('change', window.showWorkspaceBlogAuthFields);
  }

  function truncateUrl(url) {
    if (!url) return '';
    try {
      const urlObj = new URL(url);
      const host = urlObj.hostname;
      const path = urlObj.pathname;
      if (path.length > 15) {
        return urlObj.protocol + "//" + host + path.substring(0, 8) + "..." + path.substring(path.length - 6);
      }
      return url;
    } catch(e) {
      if (url.length > 30) {
        return url.substring(0, 15) + "..." + url.substring(url.length - 8);
      }
      return url;
    }
  }

  function renderConnections() {
    const list = document.getElementById("setChannels");
    if (!list) return;

    const platforms = [
      { name: "LinkedIn", key: "linkedin", defaultHandle: "company/" + site.id },
      { name: "YouTube", key: "youtube", defaultHandle: "@" + site.id },
      { name: "Instagram", key: "instagram", defaultHandle: "Not connected" },
      { name: "Blog (RSS)", key: "blog", defaultHandle: site.url + "/feed" }
    ];

    list.innerHTML = platforms.map(p => {
      const conn = activeConns.find(c => c.platform === p.key && c.is_active);
      const pm = M.platMeta(p.name === "Blog (RSS)" ? "Blog" : p.name);
      
      let badgeHTML = "";
      let detailsHTML = "";
      let disconnectHTML = "";

      badgeHTML = conn 
        ? `<span class="badge badge-success" style="display:inline-flex; align-items:center; gap:4px; margin-right:8px;">${I("check")} Connected</span>
           <button class="btn btn-secondary btn-sm btn-connect-platform" data-plat="${p.key}" data-name="${p.name}" title="Edit connection details" style="padding:4px 8px;">${I("settings")}</button>`
        : `<button class="btn btn-secondary btn-sm btn-connect-platform" data-plat="${p.key}" data-name="${p.name}">Connect</button>`;

      detailsHTML = conn 
        ? `<div class="cc-st" style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted); word-break:break-all; margin-top:2px;">
             ${conn.platform === 'blog' ? 'Endpoint' : 'Webhook'}: ${truncateUrl(conn.make_webhook_url) || 'No URL'}
             ${conn.platform === 'blog' ? `(${conn.auth_type === 'none' ? 'No Auth' : conn.auth_type.replace('_', ' ')})` : ''}
           </div>`
        : `<div class="cc-st">${p.defaultHandle}</div>`;

      disconnectHTML = conn 
        ? `<button class="icon-btn btn-sm btn-disconnect-platform" data-conn-id="${conn.id}" title="Disconnect" style="margin-left:8px; color:var(--text-muted);"><i data-lucide="trash-2" style="width:14px;height:14px"></i></button>`
        : '';

      return `
        <div class="chan-conn" style="display:flex; align-items:center; padding:12px; border:1px solid var(--border); border-radius:var(--r-md); background:var(--surface); margin-bottom:8px;">
          <span class="icon-tile tile-${p.key}" style="width:32px; height:32px; border-radius:8px; display:grid; place-items:center; flex-shrink:0; background:${pm.color}15; color:${pm.color};">${I(pm.icon)}</span>
          <div class="cc-meta" style="flex:1; min-width:0; margin-left:12px;">
            <div class="cc-nm" style="font-weight:600; color:var(--text);">${p.name}</div>
            ${detailsHTML}
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            ${badgeHTML}
            ${disconnectHTML}
          </div>
        </div>`;
    }).join("");

    C.refreshIcons();

    // Wire up Connect / Edit buttons
    document.querySelectorAll(".btn-connect-platform").forEach(btn => {
      btn.addEventListener("click", () => {
        const plat = btn.dataset.plat;
        const name = btn.dataset.name;
        
        // Reset modal fields
        document.getElementById("connectModalPlatName").textContent = name;
        document.getElementById("connectWebhookUrl").value = "";
        document.getElementById("connectAuthType").value = "none";
        document.getElementById("connectBlogFormat").value = "json";
        document.getElementById("connect_api_key_name").value = "X-API-Key";
        document.getElementById("connect_api_key_value").value = "";
        document.getElementById("connect_bearer_token_value").value = "";
        document.getElementById("connect_username").value = "";
        document.getElementById("connect_password").value = "";
        document.getElementById("connectModalTestStatus").innerHTML = "";

        // Toggle labels and custom blog fields
        const isBlog = plat === 'blog';
        document.getElementById("connectUrlLabel").textContent = isBlog ? "Publishing Endpoint URL" : "Webhook URL (Make.com, Zapier, or API Endpoint)";
        document.getElementById("blogSettingsFields").classList.toggle("hide", !isBlog);

        // Find existing connection to pre-populate
        const existing = activeConns.find(c => c.platform === plat);
        if (existing) {
          document.getElementById("connectWebhookUrl").value = existing.make_webhook_url || "";
          if (isBlog) {
            document.getElementById("connectAuthType").value = existing.auth_type || "none";
            const payload = existing.auth_payload || {};
            document.getElementById("connectBlogFormat").value = payload.payload_format || "json";
            if (existing.auth_type === 'api_key') {
              document.getElementById("connect_api_key_name").value = payload.api_key_name || "X-API-Key";
              document.getElementById("connect_api_key_value").value = payload.api_key_value || "";
            } else if (existing.auth_type === 'bearer_token') {
              document.getElementById("connect_bearer_token_value").value = payload.token_value || "";
            } else if (existing.auth_type === 'basic_auth') {
              document.getElementById("connect_username").value = payload.username || "";
              document.getElementById("connect_password").value = payload.password || "";
            }
          }
        }

        if (isBlog) {
          window.showWorkspaceBlogAuthFields();
        }

        const saveBtn = document.getElementById("btnSaveSocialConn");
        if (saveBtn) saveBtn.dataset.plat = plat;

        C.openModal("connectSocialModal");
      });
    });

    // Wire up Disconnect buttons
    document.querySelectorAll(".btn-disconnect-platform").forEach(btn => {
      btn.addEventListener("click", async () => {
        const connId = btn.dataset.connId;
        if (confirm("Are you sure you want to disconnect this platform?")) {
          try {
            await CandenceAPI.disconnectSocial(site.id, connId);
            C.toast({ type: "info", title: "Channel disconnected", desc: "Configuration removed successfully" });
            await loadConnections();
          } catch(err) {
            C.toast({ type: "error", title: "Disconnection failed", desc: err.message });
          }
        }
      });
    });
  }

  // Bind Connect Social Modal Save Action
  const btnSaveSocialConn = document.getElementById("btnSaveSocialConn");
  if (btnSaveSocialConn) {
    btnSaveSocialConn.addEventListener("click", async () => {
      const plat = btnSaveSocialConn.dataset.plat;
      const url = document.getElementById("connectWebhookUrl").value.trim();
      if (!url) {
        C.toast({ type: "error", title: "URL required", desc: "Please enter a valid URL" });
        return;
      }

      let authType = 'none';
      let authPayload = {};

      if (plat === 'blog') {
        authType = document.getElementById('connectAuthType').value;
        const payload_format = document.getElementById('connectBlogFormat').value;
        if (authType === 'api_key') {
          const api_key_name = document.getElementById('connect_api_key_name').value.trim();
          const api_key_value = document.getElementById('connect_api_key_value').value.trim();
          if (!api_key_name || !api_key_value) {
            C.toast({ type: "error", title: "API Key required", desc: "Please fill in both key name and key value" });
            return;
          }
          authPayload = { api_key_name, api_key_value, payload_format };
        } else if (authType === 'bearer_token') {
          const token_value = document.getElementById('connect_bearer_token_value').value.trim();
          if (!token_value) {
            C.toast({ type: "error", title: "Token required", desc: "Please enter the bearer token" });
            return;
          }
          authPayload = { token_value, payload_format };
        } else if (authType === 'basic_auth') {
          const username = document.getElementById('connect_username').value.trim();
          const password = document.getElementById('connect_password').value.trim();
          if (!username || !password) {
            C.toast({ type: "error", title: "Credentials required", desc: "Please enter both username and password" });
            return;
          }
          authPayload = { username, password, payload_format };
        } else {
          authPayload = { payload_format };
        }
      }

      btnSaveSocialConn.disabled = true;
      btnSaveSocialConn.textContent = "Connecting...";
      try {
        await CandenceAPI.connectSocial(site.id, plat, url, authType, authPayload);
        C.closeModal("connectSocialModal");
        C.toast({ type: "success", title: "Platform connected", desc: "Webhook configured successfully!" });
        await loadConnections();
      } catch (err) {
        C.toast({ type: "error", title: "Connection failed", desc: err.message });
      } finally {
        btnSaveSocialConn.disabled = false;
        btnSaveSocialConn.textContent = "Connect Channel";
      }
    });
  }



  loadConnections();

  /* ==========================================================================
     GENERATE — composer, drafts, previews
     ========================================================================== */
  let curChan = "Blog";
  let sessionGeneratedDrafts = [];
  document.querySelectorAll(".chan").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".chan").forEach(x => x.classList.remove("active")); b.classList.add("active"); curChan = b.dataset.chan;
    
    // Toggle composer inputs based on channel
    const stdFields = document.getElementById("standardIdeaFields");
    const ytFields = document.getElementById("youtubeUploadFields");
    const titleHeader = document.getElementById("composerHeaderTitle");
    const subHeader = document.getElementById("composerHeaderSub");
    const iconHeader = document.getElementById("composerHeaderIcon");
    const genBtn = document.getElementById("genBtn");
    
    if (curChan === "YouTube") {
      if (stdFields) stdFields.style.display = "none";
      if (ytFields) ytFields.style.display = "block";
      if (titleHeader) titleHeader.textContent = "Upload new video";
      if (subHeader) subHeader.textContent = "Upload your video file and caption directly to draft queue.";
      if (iconHeader) {
        iconHeader.className = "icon-tile tile-youtube";
        iconHeader.innerHTML = `<i data-lucide="video"></i>`;
      }
      if (genBtn) {
        genBtn.innerHTML = `<i data-lucide="plus-circle"></i> Create Video Draft`;
      }
    } else {
      if (stdFields) stdFields.style.display = "block";
      if (ytFields) ytFields.style.display = "none";
      if (titleHeader) titleHeader.textContent = "New content idea";
      if (subHeader) subHeader.textContent = "Pick a channel, give a topic — Candence drafts it.";
      if (iconHeader) {
        const pm = M.platMeta(curChan);
        iconHeader.className = `icon-tile tile-${pm.tile}`;
        iconHeader.innerHTML = `<i data-lucide="${pm.icon}"></i>`;
      }
      if (genBtn) {
        genBtn.innerHTML = `<i data-lucide="sparkles"></i> Generate with AI`;
      }
    }
    const infoCheckboxCont = document.getElementById("infographicsCheckboxContainer");
    if (infoCheckboxCont) {
      infoCheckboxCont.style.display = (curChan === "Blog") ? "flex" : "none";
    }
    renderQueue();
    if (window.lucide) window.lucide.createIcons();
  }));

  // Composer YouTube video upload wiring
  const composerYtBtn = document.getElementById("ytVideoUploadBtn");
  const composerYtFileInput = document.getElementById("ytVideoFile");
  if (composerYtBtn && composerYtFileInput) {
    composerYtBtn.addEventListener("click", () => composerYtFileInput.click());
    composerYtFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      const fileNameSpan = document.getElementById("ytVideoFileName");
      const base64Input = document.getElementById("ytVideoBase64");
      if (file) {
        if (fileNameSpan) fileNameSpan.textContent = file.name;
        const reader = new FileReader();
        reader.onload = (event) => {
          if (base64Input) base64Input.value = event.target.result;
        };
        reader.readAsDataURL(file);
      } else {
        if (fileNameSpan) fileNameSpan.textContent = "No video file selected";
        if (base64Input) base64Input.value = "";
      }
    });
  }

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
          ${[1,2,3,4].map(() => `<div style="height:76px;border-radius:var(--r-md);background:var(--surface-2);animation:pulse 1.5s ease-in-out infinite;opacity:0.6"></div>`).join("")}
        </div>`;
      document.getElementById("queueCount").textContent = "…";
    }
    try {
      const suggestions = await CandenceAPI.getIdeaSuggestions(site.id) || [];
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
    const filteredQueue = ideaQueue.filter(q => q.chan.toLowerCase() === curChan.toLowerCase());
    document.getElementById("queueCount").textContent = filteredQueue.length;
    document.getElementById("ideaQueue").innerHTML = filteredQueue.length ? filteredQueue.map((q) => { 
      const originalIdx = ideaQueue.indexOf(q);
      const p = M.platMeta(q.chan);
      const reasonHTML = q.reason ? `<div class="iq-reason" style="font-size:12px; color:var(--text-muted); margin-top:3px; line-height:1.4;">${q.reason}</div>` : '';
      return `<div class="idea-q" style="display:flex; gap:12px; padding:12px; border:1px solid var(--border); border-radius:var(--r-md); background:var(--surface); transition:all 0.2s ease; position:relative;" data-index="${originalIdx}">
        <span class="icon-tile tile-${p.tile} iq-ic" style="width:32px; height:32px; border-radius:8px; display:grid; place-items:center; flex-shrink:0; background:${p.color}15; color:${p.color};">${I(p.icon,"style='width:16px;height:16px'")}</span>
        <div style="flex:1; min-width:0;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="badge badge-neutral" style="font-size:9px; padding:1px 5px; text-transform:uppercase; font-weight:700;">${q.chan}</span>
          </div>
          <div class="iq-t" style="font-weight:600; font-size:14px; color:var(--text); margin-top:4px; line-height:1.3; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; white-space:normal;">${q.title}</div>
          ${reasonHTML}
        </div>
        <div style="display:flex; flex-direction:column; gap:6px; justify-content:center; align-items:flex-end; flex-shrink:0;">
          <button class="btn btn-primary btn-sm btn-use-idea" data-q="${originalIdx}" title="Use this suggestion" style="padding:6px 10px; border-radius:var(--r-sm); display:flex; align-items:center; gap:4px; font-size:12px;">
            ${I("sparkles","style='width:12px;height:12px'")}
            <span>Draft</span>
          </button>
          <button class="icon-btn btn-sm btn-dismiss-idea" data-dismiss="${originalIdx}" title="Dismiss suggestion" style="color:var(--text-muted); opacity:0.6; padding:4px; border-radius:4px; transition:all 0.15s ease;">
            ${I("x", "style='width:14px;height:14px'")}
          </button>
        </div>
      </div>`;
    }).join("") : `<div class="muted tsm" style="text-align:center;padding:var(--s4)">No suggestions available for ${curChan}. Click Refresh to generate new suggestions.</div>`;
    
    C.refreshIcons();
    
    document.querySelectorAll(".btn-use-idea").forEach(b => b.addEventListener("click", () => {
      const q = ideaQueue[+b.dataset.q];
      const titleInput = document.getElementById("ideaTitle");
      if (titleInput) {
        titleInput.value = q.title;
        titleInput.focus();
      }
      curChan = q.chan;
      document.querySelectorAll(".chan").forEach(x => x.classList.toggle("active", x.dataset.chan === q.chan));
      renderQueue();
      C.toast({ type: "success", title: "Idea applied", desc: `Loaded suggestion into the ${q.chan} composer!` });
    }));

    document.querySelectorAll(".btn-dismiss-idea").forEach(b => b.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = +b.dataset.dismiss;
      ideaQueue.splice(idx, 1);
      renderQueue();
      C.toast({ type: "info", title: "Idea dismissed", desc: "Suggestion removed from queue" });
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
    let headingColor = guide.heading_color ? guide.heading_color : 'inherit';
    let textColor = guide.text_color ? guide.text_color : 'inherit';

    if (headingColor.toLowerCase() === 'transparent') headingColor = 'inherit';
    if (textColor.toLowerCase() === 'transparent') textColor = 'inherit';

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
        <div class="ig-cap"><b>${site.id}</b> ${txt}</div></div>`;
    }
    if (plat === "YouTube") {
      const txt = (typeof body === "string" ? body : SAMPLE.YouTube.desc);
      const isVid = coverImage && (coverImage.toLowerCase().endsWith(".mp4") || coverImage.toLowerCase().endsWith(".webm") || coverImage.startsWith("data:video/"));
      
      let mediaHTML = "";
      if (isVid) {
        mediaHTML = `<video src="${coverImage}" controls style="width:100%; border-radius:8px; display:block; margin-bottom:var(--s2); max-height:200px; object-fit:cover;"></video>`;
      } else {
        const thumbStyle = coverImage 
          ? `style="background-image: url('${coverImage}'); background-size: cover; background-position: center;"`
          : "";
        mediaHTML = `<div class="yt-thumb" ${thumbStyle}><span class="play">${I("play")}</span><span class="dur">Video</span></div>`;
      }
      return `<div class="yt">${mediaHTML}
        <div class="yt-info"><span class="avatar yt-av" style="background:${site.color}">${site.short}</span>
        <div><div class="yt-t">${title}</div><div class="yt-ch">${site.name} · ${txt.substring(0, 80)}...</div></div></div></div>`;
    }
  }

  /* ----- draft model ----- */
  let drafts = M.content.filter(c => c.site === site.id);
  let filter = "all";
  let channelFilter = "all";
  let selectedDraftId = null;
  let activeWsDraftId = null;
  let draftsPage = 1;
  const DRAFTS_PER_PAGE = 5;

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
         <button class="btn btn-ghost btn-sm" data-act="regen-content" data-id="${d.id}">${I("file-text")} Regen Content</button>
         ${d.chan === "Blog" ? `<button class="btn btn-ghost btn-sm" data-act="regen-image" data-id="${d.id}">${I("image")} Regen Image</button>` : ''}
         ${d.chan === "Blog" ? `
            <button class="btn btn-ghost btn-sm" data-act="internal-links" data-id="${d.id}">${I("link")} Link References</button>
            <button class="btn btn-ghost btn-sm" data-act="remove-links" data-id="${d.id}">${I("link-2-off")} Remove Links</button>
          ` : ''}
         <span class="spacer"></span>
         <button class="btn btn-secondary btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button>
         <button class="btn btn-success btn-sm" data-act="approve" data-id="${d.id}">${I("check")} Approve</button>`
      : d.status === "Approved"
      ? `<button class="btn btn-ghost btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button><span class="spacer"></span>
         <button class="btn btn-primary btn-sm" data-act="schedule" data-id="${d.id}">${I("calendar-plus")} Schedule</button>`
      : d.status === "Scheduled"
      ? `<button class="btn btn-ghost btn-sm" data-act="unschedule" data-id="${d.id}">${I("calendar-x")} Unschedule</button><span class="spacer"></span>
         <button class="btn btn-ghost btn-sm" data-act="view" data-id="${d.id}">${I("eye")} View</button>`
      : `<span class="muted tsm row gap2">${I("check-check","style='width:15px;height:15px;color:var(--success)'")} Published</span><span class="spacer"></span>
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

  function openBigPreview(d) {
    document.getElementById("largePreviewTitle").textContent = d.title;
    document.getElementById("largePreviewSub").textContent = `${d.chan} · AI draft preview`;
    
    const bodyContainer = document.getElementById("largePreviewBody");
    if (bodyContainer) {
      bodyContainer.innerHTML = previewHTML(d.chan, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date);
    }
    
    const footContainer = document.getElementById("largePreviewFoot");
    if (footContainer) {
      const isYouTube = d.chan === "YouTube";
      const actions = d.status === "Draft"
        ? `<button class="btn btn-ghost btn-sm" data-act="reject" data-id="${d.id}">${I("x")} Reject</button>
           <button class="btn btn-ghost btn-sm" data-act="regen-content" data-id="${d.id}">${I("file-text")} Regen Content</button>
           ${isYouTube 
             ? `<button class="btn btn-ghost btn-sm" data-act="regen-image" data-id="${d.id}">${I("video")} Regen Video</button>`
             : `<button class="btn btn-ghost btn-sm" data-act="regen-image" data-id="${d.id}">${I("image")} Regen Image</button>`
           }
           ${d.chan === "Blog" ? `
            <button class="btn btn-ghost btn-sm" data-act="internal-links" data-id="${d.id}">${I("link")} Link References</button>
            <button class="btn btn-ghost btn-sm" data-act="remove-links" data-id="${d.id}">${I("link-2-off")} Remove Links</button>
          ` : ''}
           <span class="spacer"></span>
           <button class="btn btn-secondary btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button>
           <button class="btn btn-success btn-sm" data-act="approve" data-id="${d.id}">${I("check")} Approve</button>`
        : d.status === "Approved"
        ? `<button class="btn btn-ghost btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button><span class="spacer"></span>
           <button class="btn btn-primary btn-sm" data-act="schedule" data-id="${d.id}">${I("calendar-plus")} Schedule</button>`
        : d.status === "Scheduled"
        ? `<button class="btn btn-ghost btn-sm" data-act="unschedule" data-id="${d.id}">${I("calendar-x")} Unschedule</button><span class="spacer"></span>
           <button class="btn btn-ghost btn-sm" data-act="view" data-id="${d.id}">${I("eye")} View</button>`
        : `<span class="muted tsm row gap2">${I("check-check","style='width:15px;height:15px;color:var(--success)'")} Published</span><span class="spacer"></span>
           <button class="btn btn-ghost btn-sm" data-act="view" data-id="${d.id}">${I("eye")} View</button>`;
      footContainer.innerHTML = actions;
    }
    C.openModal("largePreviewModal");
    C.refreshIcons();
    wireDraftActions();
  }

  function renderWsDraftPreview(d) {
    const el = document.getElementById("wsDraftPreview");
    if (!el) return;
    if (!d) {
      el.innerHTML = `<div class="empty card" style="padding:var(--s9); border:none; display:grid; place-content:center; text-align:center;"><div class="empty-art">${I("sparkles")}</div><h3>No draft selected</h3><p>Select a draft from the list to preview details.</p></div>`;
      return;
    }
    
    const p = M.platMeta(d.chan);
    const isApproved = d.status === "Approved";
    const isDraft = d.status === "Draft";
    const isScheduled = d.status === "Scheduled";

    const isYouTube = d.chan === "YouTube";
    const actionsLeft = isDraft
      ? `<button class="btn btn-ghost btn-sm" data-act="reject" data-id="${d.id}">${I("x")} Reject</button>
         <button class="btn btn-ghost btn-sm" data-act="regen-content" data-id="${d.id}">${I("file-text")} Regen Content</button>
         ${isYouTube 
           ? `<button class="btn btn-ghost btn-sm" data-act="regen-image" data-id="${d.id}">${I("video")} Regen Video</button>`
           : `<button class="btn btn-ghost btn-sm" data-act="regen-image" data-id="${d.id}">${I("image")} Regen Image</button>`
         }
         ${d.chan === "Blog" ? `
            <button class="btn btn-ghost btn-sm" data-act="internal-links" data-id="${d.id}">${I("link")} Link References</button>
            <button class="btn btn-ghost btn-sm" data-act="remove-links" data-id="${d.id}">${I("link-2-off")} Remove Links</button>
          ` : ''}`
      : isScheduled
      ? `<button class="btn btn-ghost btn-sm" data-act="unschedule" data-id="${d.id}">${I("calendar-x")} Unschedule</button>`
      : '';

    const actionsRight = isDraft
      ? `<button class="btn btn-secondary btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button>
         <button class="btn btn-success btn-sm" data-act="approve" data-id="${d.id}">${I("check")} Approve</button>`
      : isApproved
      ? `<button class="btn btn-secondary btn-sm" data-act="edit" data-id="${d.id}">${I("pencil")} Edit</button>
         <button class="btn btn-primary btn-sm" data-act="schedule" data-id="${d.id}">${I("calendar-plus")} Schedule</button>`
      : `<button class="btn btn-ghost btn-sm" data-act="view" data-id="${d.id}">${I("eye")} View</button>`;

    el.innerHTML = `
      <div class="card__header" style="display:flex; align-items:center; justify-content:space-between; padding: 12px var(--s5);">
        <span class="icon-tile tile-${p.tile}">${I(p.icon)}</span>
        <div style="flex:1;min-width:0;margin-left:10px;">
          <h3 style="font-size:var(--fs-md);margin-bottom:2px;">${d.chan} draft</h3>
          <div class="sub">${site.name} · status: <b>${d.status}</b></div>
        </div>
        <button class="icon-btn btn-sm" id="maximizeWsDraft" title="Full screen view" style="margin-right:4px;">${I("maximize-2")}</button>
        <button class="icon-btn btn-sm" data-act="more" data-id="${d.id}" title="Move to trash">${I("more-vertical")}</button>
      </div>
      <div class="card__body" id="wsPrevBody" style="max-height:480px;overflow-y:auto;padding:var(--s5);">${previewHTML(d.chan, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date)}</div>
      <div class="card__footer" style="display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; padding: 12px var(--s5);">
        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          ${actionsLeft}
        </div>
        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          ${actionsRight}
        </div>
      </div>`;

    const maxBtn = document.getElementById("maximizeWsDraft");
    if (maxBtn) {
      maxBtn.addEventListener("click", () => openBigPreview(d));
    }

    C.refreshIcons();
    wireDraftActions();
  }

  function renderDrafts() {
    // 1. Render main Drafts Tab Panel list
    const wsWrap = document.getElementById("wsDraftList");
    const wsPagWrap = document.getElementById("wsDraftListPagination");
    
    if (wsWrap) {
      const list = drafts.filter(d => {
        const matchesStatus = filter === "all" || d.status === filter;
        const matchesChannel = channelFilter === "all" || d.chan.toLowerCase() === channelFilter.toLowerCase();
        return matchesStatus && matchesChannel;
      });
      list.sort((a, b) => parseInt(b.id) - parseInt(a.id));
      
      const totalPages = Math.ceil(list.length / DRAFTS_PER_PAGE);
      if (draftsPage > totalPages) draftsPage = Math.max(1, totalPages);
      
      let activeWsDraft = null;
      if (list.length > 0) {
        activeWsDraft = list.find(d => d.id === activeWsDraftId);
        if (!activeWsDraft) {
          activeWsDraft = list[0];
          activeWsDraftId = activeWsDraft.id;
        }
      } else {
        activeWsDraftId = null;
      }
      
      renderWsDraftPreview(activeWsDraft);
      
      if (!list.length) {
        wsWrap.innerHTML = `<div class="empty card" style="padding:var(--s9)"><div class="empty-art">${I("sparkles")}</div><h3>No ${filter==='all'?'':filter.toLowerCase()+' '}drafts</h3><p>Use the composer to generate AI content for this website.</p></div>`;
        if (wsPagWrap) wsPagWrap.innerHTML = "";
      } else {
        const pageItems = list.slice((draftsPage - 1) * DRAFTS_PER_PAGE, draftsPage * DRAFTS_PER_PAGE);
        wsWrap.innerHTML = pageItems.map(d => draftListItem(d, d.id === activeWsDraftId)).join("");
        
        if (wsPagWrap) {
          if (totalPages > 1) {
            wsPagWrap.innerHTML = `
              <button class="btn btn-secondary btn-sm" id="prevDraftPage" ${draftsPage === 1 ? 'disabled' : ''} style="padding: 4px 8px; font-size: 11px;">
                ${I("chevron-left", "style='width:12px;height:12px'")} Prev
              </button>
              <span class="tsm muted" style="font-size: 12px; font-weight: 550; min-width: 60px; text-align: center;">
                ${draftsPage} / ${totalPages}
              </span>
              <button class="btn btn-secondary btn-sm" id="nextDraftPage" ${draftsPage === totalPages ? 'disabled' : ''} style="padding: 4px 8px; font-size: 11px;">
                Next ${I("chevron-right", "style='width:12px;height:12px'")}
              </button>
            `;
            
            document.getElementById("prevDraftPage").addEventListener("click", () => {
              if (draftsPage > 1) {
                draftsPage--;
                renderDrafts();
              }
            });
            document.getElementById("nextDraftPage").addEventListener("click", () => {
              if (draftsPage < totalPages) {
                draftsPage++;
                renderDrafts();
              }
            });
          } else {
            wsPagWrap.innerHTML = "";
          }
        }
      }
    }

    // 2. Render Session Generated Drafts in Generate Panel
    const sessionSection = document.getElementById("sessionDraftsSection");
    const sessionWrap = document.getElementById("sessionDraftList");
    
    if (sessionSection && sessionWrap) {
      const sessionList = drafts.filter(d => sessionGeneratedDrafts.includes(String(d.id)));
      sessionList.sort((a, b) => parseInt(b.id) - parseInt(a.id));
      
      if (sessionList.length > 0) {
        sessionSection.style.display = "block";
        sessionWrap.innerHTML = sessionList.map(d => draftListItem(d, false)).join("");
      } else {
        sessionSection.style.display = "none";
        sessionWrap.innerHTML = "";
      }
    }
    
    // Wire draft list click listeners
    document.querySelectorAll(".draft-list-item").forEach(item => {
      // Don't flag as wired here, wire fresh list clicks each render
      item.addEventListener("click", () => {
        const id = item.dataset.listId;
        // If clicking in the main drafts tab, update split screen view
        if (wsWrap && wsWrap.contains(item)) {
          activeWsDraftId = id;
          renderDrafts();
        } else {
          // If clicking in the session drafts list, open full modal
          const d = drafts.find(x => x.id === id);
          if (d) openBigPreview(d);
        }
      });
    });

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
        
        if (["approve", "reject", "schedule", "unschedule", "edit", "view", "more", "regen-content", "regen-image"].includes(act)) {
          C.closeModal("largePreviewModal");
        }
        
        if (act === "approve") {
          try {
            await CandenceAPI.approveDraft(d.id);
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
            await CandenceAPI.rejectDraft(d.id, "Rejected by administrator");
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
          
          if (window.updateWorkspaceMinTime) window.updateWorkspaceMinTime();
          C.openModal("scheduleModal");
        }
        else if (act === "regen-content") {
          await regenerate(d, "content");
        }
        else if (act === "regen-image") {
          await regenerate(d, "image");
        }
        else if (act === "unschedule") {
          try {
            await CandenceAPI.updateDraft(d.id, { status: "draft" });
            d.status = "Draft";
            C.toast({ type: "success", title: "Unscheduled", desc: "Draft moved back to Draft status" });
            await M.syncMockData(site.id);
            if (C.mountShell) C.mountShell();
            renderDrafts();
          } catch (err) {
            C.toast({ type: "error", title: "Unschedule failed", desc: err.message });
          }
        }
        else if (act === "internal-links") {
          try {
            b.disabled = true;
            b.innerHTML = `${I("loader-circle", "class='spin' style='width:12px;height:12px'")} Linking...`;
            C.refreshIcons();
            const updated = await CandenceAPI.injectInternalLinks(d.id);
            d.body = updated.body;
            C.toast({ type: "success", title: "Links added", desc: "Successfully linked keywords to old posts!" });
            
            // Update preview body directly
            const bodyContainer = document.querySelector(".draft-preview-body");
            if (bodyContainer) {
              bodyContainer.innerHTML = previewHTML(d.chan, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date);
            }
          } catch (err) {
            C.toast({ type: "error", title: "Linking failed", desc: err.message });
          } finally {
            b.disabled = false;
            b.innerHTML = `${I("link")} Link References`;
            C.refreshIcons();
          }
        }
        else if (act === "remove-links") {
          try {
            b.disabled = true;
            b.innerHTML = `${I("loader-circle", "class='spin' style='width:12px;height:12px'")} Removing...`;
            C.refreshIcons();
            const updated = await CandenceAPI.removeInternalLinks(d.id);
            d.body = updated.body;
            C.toast({ type: "success", title: "Links removed", desc: "Successfully removed all hyperlinks from the draft!" });
            
            // Update preview body directly
            const bodyContainer = document.querySelector(".draft-preview-body");
            if (bodyContainer) {
              bodyContainer.innerHTML = previewHTML(d.chan, d.title, d.body, d.cover_image, d.tags, d.category, d.created_at, d.author_name, d.custom_date);
            }
          } catch (err) {
            C.toast({ type: "error", title: "Failed to remove links", desc: err.message });
          } finally {
            b.disabled = false;
            b.innerHTML = `${I("link-2-off")} Remove Links`;
            C.refreshIcons();
          }
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
              await CandenceAPI.deleteDraft(d.id);
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

  }

  /* ----- Global Task Polling & UI Indicators ----- */
  function getActiveTasks() {
    let ideas = [];
    let draftsList = [];
    try {
      ideas = JSON.parse(localStorage.getItem("candence.active_ideas")) || [];
    } catch(e){}
    try {
      draftsList = JSON.parse(localStorage.getItem("candence.active_drafts")) || [];
    } catch(e){}
    return { ideas, drafts: draftsList };
  }

  function saveActiveTasks(ideas, draftsList) {
    localStorage.setItem("candence.active_ideas", JSON.stringify(ideas));
    localStorage.setItem("candence.active_drafts", JSON.stringify(draftsList));
  }

  // IOS-Style Floating Progress Widget position state variables
  let widgetCollapsed = false;
  let widgetCustomX = null;
  let widgetCustomY = null;

  function updateGlobalTaskWidget() {
    const { ideas, drafts: draftsList } = getActiveTasks();
    const total = ideas.length + draftsList.length;
    
    let widget = document.getElementById("globalTaskWidget");
    if (total === 0) {
      if (widget) widget.remove();
      return;
    }
    
    if (!widget) {
      widget = document.createElement("div");
      widget.id = "globalTaskWidget";
      widget.style.position = "fixed";
      widget.style.zIndex = "100000";
      widget.style.cursor = "grab";
      widget.style.userSelect = "none";
      widget.style.transition = "width 0.2s cubic-bezier(0.4, 0, 0.2, 1), height 0.2s, padding 0.2s, border-radius 0.2s";
      
      // Load custom position or default to top right
      widget.style.top = widgetCustomY !== null ? `${widgetCustomY}px` : "76px";
      if (widgetCustomX !== null) {
        widget.style.left = `${widgetCustomX}px`;
      } else {
        widget.style.right = "24px";
      }
      
      document.body.appendChild(widget);

      // Drag and drop event listeners
      let isDragging = false;
      let dragStartX = 0;
      let dragStartY = 0;
      let dragStartLeft = 0;
      let dragStartTop = 0;
      let hasMovedSignificant = false;

      widget.addEventListener("mousedown", (e) => {
        if (e.target.closest("button")) return;
        
        isDragging = true;
        hasMovedSignificant = false;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        
        const rect = widget.getBoundingClientRect();
        dragStartLeft = rect.left;
        dragStartTop = rect.top;
        
        widget.style.cursor = "grabbing";
        e.preventDefault();
      });

      window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const dx = e.clientX - dragStartX;
        const dy = e.clientY - dragStartY;
        
        if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
          hasMovedSignificant = true;
        }
        
        let newX = dragStartLeft + dx;
        let newY = dragStartTop + dy;
        
        newX = Math.max(10, Math.min(window.innerWidth - widget.offsetWidth - 10, newX));
        newY = Math.max(10, Math.min(window.innerHeight - widget.offsetHeight - 10, newY));
        
        widgetCustomX = newX;
        widgetCustomY = newY;
        
        widget.style.left = `${newX}px`;
        widget.style.top = `${newY}px`;
        widget.style.right = "auto";
      });

      window.addEventListener("mouseup", () => {
        if (!isDragging) return;
        isDragging = false;
        widget.style.cursor = "grab";
        
        if (!hasMovedSignificant) {
          widgetCollapsed = !widgetCollapsed;
          updateGlobalTaskWidget();
        }
      });
    }
    
    const taskName = ideas.length > 0 ? `AI writing: "${ideas[0].title}"` : `Regenerating: "${draftsList[0].title}"`;
    const label = total > 1 ? `${taskName} (+${total - 1} more)` : taskName;
    
    if (widgetCollapsed) {
      widget.style.padding = "10px";
      widget.style.borderRadius = "99px";
      widget.style.background = "var(--primary)";
      widget.style.border = "2px solid #ffffff";
      widget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.25)";
      widget.style.display = "flex";
      widget.style.alignItems = "center";
      widget.style.justifyContent = "center";
      widget.style.borderLeft = "none";
      
      widget.innerHTML = `
        <div style="position:relative; width:28px; height:28px; display:flex; align-items:center; justify-content:center;">
          <i data-lucide="loader-circle" class="spin" style="color:#ffffff; width:20px; height:20px;"></i>
          <span style="position:absolute; top:-6px; right:-6px; background:#ef4444; color:#ffffff; font-size:9px; font-weight:bold; border-radius:99px; padding:1px 5px; border:1px solid #ffffff; box-shadow:0 2px 4px rgba(0,0,0,0.2);">${total}</span>
        </div>
      `;
    } else {
      widget.style.padding = "12px 18px";
      widget.style.borderRadius = "var(--r-md)";
      widget.style.background = "var(--surface)";
      widget.style.border = "1px solid var(--border-strong)";
      widget.style.boxShadow = "var(--sh-lg)";
      widget.style.display = "flex";
      widget.style.alignItems = "center";
      widget.style.justifyContent = "flex-start";
      widget.style.borderLeft = "4px solid var(--primary)";
      
      widget.innerHTML = `
        <i data-lucide="loader-circle" class="spin" style="color:var(--primary); width:16px; height:16px; margin-right:12px;"></i>
        <span style="font-weight:600; font-size:13px; color:var(--text); max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-right:10px;">${label}</span>
        <button title="Collapse to Pill" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:11px; padding:2px; display:flex; align-items:center; opacity:0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6">
          <i data-lucide="minimize-2" style="width:12px; height:12px;"></i>
        </button>
      `;
    }
    
    C.refreshIcons();
  }

  let globalTaskPollerInterval = null;
  
  function initGlobalTaskPoller() {
    if (globalTaskPollerInterval) return;
    
    updateGlobalTaskWidget();
    const { ideas, drafts: draftsList } = getActiveTasks();
    if (ideas.length === 0 && draftsList.length === 0) return;
    
    globalTaskPollerInterval = setInterval(async () => {
      try {
        const { ideas: curIdeas, drafts: curDraftsList } = getActiveTasks();
        if (curIdeas.length === 0 && curDraftsList.length === 0) {
          clearInterval(globalTaskPollerInterval);
          globalTaskPollerInterval = null;
          updateGlobalTaskWidget();
          return;
        }
        
        let changed = false;
        
        // 1. Poll Active Ideas
        const remainingIdeas = [];
        for (const idea of curIdeas) {
          try {
            const updated = await CandenceAPI.getIdeaDetail(idea.id);
            if (updated && updated.status === 'done') {
              C.toast({ type: "success", title: "Content Generated", desc: `"${idea.title}" draft is now ready!` });
              changed = true;
            } else if (updated && updated.status === 'failed') {
              C.toast({ type: "error", title: "Generation Failed", desc: `Failed to generate "${idea.title}".` });
              changed = true;
            } else {
              remainingIdeas.push(idea);
            }
          } catch(e) {
            console.error("Error polling global task idea:", e);
            remainingIdeas.push(idea); // Keep trying
          }
        }
        
        // 2. Poll Active Drafts
        const remainingDrafts = [];
        let currentDrafts = [];
        if (curDraftsList.length > 0 && site?.id) {
          try {
            await window.MOCK.syncMockData(site.id);
            currentDrafts = window.MOCK.content.filter(x => x.site === site.id);
          } catch(e) {
            console.error("Failed to sync mock data during global poll:", e);
          }
        }
        
        for (const d of curDraftsList) {
          if (currentDrafts.length === 0) {
            remainingDrafts.push(d);
            continue;
          }
          
          if (d.type === "image") {
            const updated = currentDrafts.find(x => x.id === d.id);
            if (updated && updated.cover_image !== d.oldCover) {
              C.toast({ type: "success", title: "Cover Image Ready", desc: `Regenerated cover image for "${d.title}"` });
              changed = true;
            } else {
              remainingDrafts.push(d);
            }
          } else {
            const updatedOld = currentDrafts.find(x => x.id === d.id);
            const hasNewDraft = currentDrafts.some(x => parseInt(x.id) > parseInt(d.id) && x.body && x.body !== "");
            
            if (hasNewDraft || (updatedOld && updatedOld.body && updatedOld.body !== "" && updatedOld.body !== d.oldBody)) {
              C.toast({ type: "success", title: "Draft Regenerated", desc: `"${d.title}" content regenerated successfully!` });
              changed = true;
            } else {
              remainingDrafts.push(d);
            }
          }
        }
        
        if (changed || curIdeas.length !== remainingIdeas.length || curDraftsList.length !== remainingDrafts.length) {
          saveActiveTasks(remainingIdeas, remainingDrafts);
          updateGlobalTaskWidget();
          
          // Refresh the drafts list view automatically if present
          if (site?.id) {
            const oldDraftIds = drafts.map(d => parseInt(d.id));
            const maxOldId = oldDraftIds.length > 0 ? Math.max(...oldDraftIds) : 0;
            
            await window.MOCK.syncMockData(site.id);
            drafts = window.MOCK.content.filter(x => x.site === site.id);
            
            // If we completed an idea generation task
            if (curIdeas.length > remainingIdeas.length) {
              // Finish the progress bar
              if (window._genProgressInterval) {
                clearInterval(window._genProgressInterval);
                window._genProgressInterval = null;
              }
              const progressBar = document.getElementById("generationProgressBar");
              const progressPercent = document.getElementById("generationProgressPercent");
              if (progressBar && progressPercent) {
                progressBar.style.width = "100%";
                progressPercent.textContent = "100%";
              }
              setTimeout(() => {
                const progressContainer = document.getElementById("generationProgressContainer");
                if (progressContainer) progressContainer.style.display = "none";
              }, 1500);

              // Map newly created drafts to sessionGeneratedDrafts based on maxOldId
              drafts.forEach(d => {
                const idNum = parseInt(d.id);
                if (idNum > maxOldId && !sessionGeneratedDrafts.includes(String(d.id))) {
                  sessionGeneratedDrafts.push(String(d.id));
                }
              });

              // Auto-select the newly generated draft
              const sorted = [...drafts].sort((a, b) => parseInt(b.id) - parseInt(a.id));
              if (sorted.length > 0) {
                selectedDraftId = sorted[0].id;
              }
            }
            
            renderDrafts();
            await loadIdeaQueue();
          }
        }
      } catch (globalErr) {
        console.error("Error in global task poller tick:", globalErr);
      }
    }, 4000);
  }

  async function regenerate(d, type = "all") {
    C.toast({ type: "info", title: "Regeneration Started", desc: "AI is rewriting draft in the background..." });
    const card = document.querySelector(`[data-card="${d.id}"] .draft__body`);
    if (card) {
      card.innerHTML = genLoadingHTML(); C.refreshIcons();
    }
    
    try {
      const res = await CandenceAPI.regenerateDraft(d.id, type);
      
      // Save to localStorage active registry
      const { ideas: existingIdeas, drafts: existingDrafts } = getActiveTasks();
      const newActiveDraft = {
        id: d.id,
        title: d.title,
        type: type,
        oldCover: d.cover_image,
        oldBody: d.body
      };
      
      saveActiveTasks(existingIdeas, [...existingDrafts, newActiveDraft]);
      initGlobalTaskPoller();
    } catch (err) {
      C.toast({ type: "error", title: "Regeneration failed", desc: err.message });
      renderDrafts();
    }
  }

  function genLoadingHTML() {
    return `<div class="gen-loading"><div class="gl-head">${I("loader-circle","class='spin'")} Candence is writing…</div>
      <div class="sk-line w80"></div><div class="sk-line"></div><div class="sk-line w60"></div><div class="sk-line"></div><div class="sk-line w40"></div></div>`;
  }

  /* ----- generate new draft ----- */
  async function startGenerate() {
    const btn = document.getElementById("genBtn");
    
    if (curChan === "YouTube") {
      const ytTitle = document.getElementById("ytTitle").value.trim();
      const ytCaption = document.getElementById("ytCaption").value.trim();
      const ytVideoBase64 = document.getElementById("ytVideoBase64").value;
      
      if (!ytTitle) {
        C.toast({ type: "error", title: "Title Required", desc: "Please enter a video title." });
        return;
      }
      if (!ytVideoBase64) {
        C.toast({ type: "error", title: "Video Required", desc: "Please upload a video file." });
        return;
      }
      
      btn.disabled = true;
      btn.innerHTML = '<i data-lucide="loader-circle" class="spin"></i> Creating Draft…';
      C.refreshIcons();
      
      try {
        const draft = await CandenceAPI.createDraft({
          website: site.id,
          platform: "youtube",
          title: ytTitle,
          body: ytCaption,
          cover_image: ytVideoBase64,
          status: "draft"
        });
        
        await window.MOCK.syncMockData(site.id);
        drafts = window.MOCK.content.filter(x => x.site === site.id);
        selectedDraftId = draft.id;
        sessionGeneratedDrafts.push(String(draft.id));
        
        // Reset composer values
        document.getElementById("ytTitle").value = "";
        document.getElementById("ytCaption").value = "";
        document.getElementById("ytVideoFile").value = "";
        document.getElementById("ytVideoBase64").value = "";
        document.getElementById("ytVideoFileName").textContent = "No video file selected";
        
        filter = "all";
        document.querySelectorAll("#draftFilter button").forEach(x => x.classList.toggle("active", x.dataset.f === "all"));
        renderDrafts();
        
        C.toast({ type: "success", title: "Draft Created", desc: "Successfully saved video draft to queue." });
      } catch (err) {
        console.error(err);
        C.toast({ type: "error", title: "Failed to create draft", desc: err.message });
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="plus-circle"></i> Create Video Draft`;
        C.refreshIcons();
      }
      return;
    }

    const rawVal = document.getElementById("ideaTitle").value.trim();
    const titles = rawVal.split('\n').map(t => t.trim()).filter(t => t.length > 0);
    
    const notesEl = document.getElementById("ideaNotes");
    const notesVal = notesEl ? notesEl.value.trim() : "";
    
    if (titles.length === 0) {
      titles.push(`New ${curChan} post about ${site.name}`);
    }
    
    btn.disabled = true; btn.innerHTML = '<i data-lucide="loader-circle" class="spin"></i> Submitting…'; C.refreshIcons();
    
    // Switch to generate panel visibly first
    document.querySelectorAll(".ws-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === "generate"));
    document.querySelectorAll("#wsPanels .tab-panel").forEach(pp => pp.classList.toggle("active", pp.dataset.panel === "generate"));

    const addInfographicsEl = document.getElementById("addInfographics");
    const includeInfographics = addInfographicsEl ? addInfographicsEl.checked : false;
    const addCTAEl = document.getElementById("addCTA");
    const includeCTA = addCTAEl ? addCTAEl.checked : false;

    try {
      const generatedIdeas = [];
      // Generate each title sequentially
      for (const title of titles) {
        const idea = await CandenceAPI.submitIdea(site.id, title, curChan.toLowerCase(), notesVal);
        await CandenceAPI.generateContent(idea.id, includeInfographics, includeCTA);
        generatedIdeas.push({ id: idea.id, title: idea.title });
      }

      C.toast({ 
        type: "info", 
        title: "AI Generation Started", 
        desc: `Started generating ${titles.length} draft(s) in the background...` 
      });

      // Show progress bar
      const progressContainer = document.getElementById("generationProgressContainer");
      const progressBar = document.getElementById("generationProgressBar");
      const progressPercent = document.getElementById("generationProgressPercent");
      if (progressContainer && progressBar && progressPercent) {
        progressContainer.style.display = "block";
        progressBar.style.width = "0%";
        progressPercent.textContent = "0%";
        let currentProgress = 0;
        if (window._genProgressInterval) {
          clearInterval(window._genProgressInterval);
        }
        window._genProgressInterval = setInterval(() => {
          if (currentProgress < 90) {
            currentProgress += Math.floor(Math.random() * 6) + 3;
            if (currentProgress > 90) currentProgress = 90;
            progressBar.style.width = `${currentProgress}%`;
            progressPercent.textContent = `${currentProgress}%`;
          }
        }, 600);
      }

      // Save to localStorage active registry
      const { ideas: existingIdeas, drafts: existingDrafts } = getActiveTasks();
      saveActiveTasks([...existingIdeas, ...generatedIdeas], existingDrafts);
      
      // Start global polling
      initGlobalTaskPoller();

      document.getElementById("ideaTitle").value = "";
      if (document.getElementById("ideaNotes")) document.getElementById("ideaNotes").value = "";
    } catch (err) {
      console.error(err);
      C.toast({ type: "error", title: "Generation failed", desc: err.message });
      if (window._genProgressInterval) {
        clearInterval(window._genProgressInterval);
        window._genProgressInterval = null;
      }
      const progressContainer = document.getElementById("generationProgressContainer");
      if (progressContainer) progressContainer.style.display = "none";
    } finally {
      btn.disabled = false; btn.innerHTML = I("sparkles") + " Generate with AI"; C.refreshIcons();
    }
  }
  document.getElementById("genBtn").addEventListener("click", startGenerate);

  // Layout Toggle controls
  const layoutToggle = document.getElementById("genLayoutToggle");
  const layoutEl = document.getElementById("generateLayoutEl");
  if (layoutToggle && layoutEl) {
    layoutToggle.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        layoutToggle.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        
        const mode = btn.dataset.layout;
        if (mode === "focus") {
          layoutEl.classList.add("focus-mode");
        } else {
          layoutEl.classList.remove("focus-mode");
        }
      });
    });
  }

  document.querySelectorAll("#draftFilter button, #wsDraftFilter button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#draftFilter button, #wsDraftFilter button").forEach(x => {
      if (x.dataset.f === b.dataset.f) x.classList.add("active"); else x.classList.remove("active");
    });
    filter = b.dataset.f; draftsPage = 1; renderDrafts();
  }));

  const channelFilterGroup = document.getElementById("wsDraftChannelFilter");
  if (channelFilterGroup) {
    channelFilterGroup.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      channelFilterGroup.querySelectorAll("button").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
      channelFilter = b.dataset.c;
      draftsPage = 1;
      renderDrafts();
    }));
  }

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
            const isVid = file.type.startsWith("video/") || base64.startsWith("data:video/");
            if (isVid) {
              coverPreview.style.backgroundImage = "none";
              coverPreview.style.border = "none";
              coverPreview.innerHTML = `<video src="${base64}" controls style="width:100%; height:100%; object-fit:cover; border-radius:6px;"></video>`;
            } else {
              coverPreview.style.backgroundImage = `url('${base64}')`;
              coverPreview.style.border = "none";
              coverPreview.innerHTML = "";
            }
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

  function initPremiumEditor() {
    const editModal = document.getElementById("editModal");
    if (!editModal) return;

    // 1. Sidebar Tab Switcher
    const btnSettings = document.getElementById("tabBtnSettings");
    const btnAI = document.getElementById("tabBtnAI");
    const contentSettings = document.getElementById("tabContentSettings");
    const contentAI = document.getElementById("tabContentAI");

    if (btnSettings && btnAI) {
      btnSettings.addEventListener("click", () => {
        btnSettings.classList.add("active");
        btnAI.classList.remove("active");
        contentSettings.style.display = "flex";
        contentAI.style.display = "none";
      });
      btnAI.addEventListener("click", () => {
        btnAI.classList.add("active");
        btnSettings.classList.remove("active");
        contentAI.style.display = "flex";
        contentSettings.style.display = "none";
      });
    }

    // 2. Drag & Drop Cover Image
    const coverPreview = document.getElementById("editCoverPreview");
    const coverUrlInput = document.getElementById("editCoverUrl");
    const coverFileInput = document.getElementById("editCoverFile");

    if (coverPreview) {
      coverPreview.addEventListener("dragenter", (e) => {
        e.preventDefault();
        coverPreview.classList.add("dragover");
      });
      coverPreview.addEventListener("dragover", (e) => {
        e.preventDefault();
        coverPreview.classList.add("dragover");
      });
      coverPreview.addEventListener("dragleave", () => {
        coverPreview.classList.remove("dragover");
      });
      coverPreview.addEventListener("drop", (e) => {
        e.preventDefault();
        coverPreview.classList.remove("dragover");
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
          const file = files[0];
          if (file.type.startsWith("image/") || file.type.startsWith("video/")) {
            const reader = new FileReader();
            reader.onload = (event) => {
              const dataUrl = event.target.result;
              coverUrlInput.value = dataUrl;
              coverPreview.style.backgroundImage = `url("${dataUrl}")`;
              coverPreview.innerHTML = "";
              C.toast({ type: "success", title: "Cover uploaded", desc: "Drag & drop cover loaded successfully." });
              updateStats();
            };
            reader.readAsDataURL(file);
          }
        }
      });

      coverPreview.addEventListener("click", (e) => {
        if (e.target.tagName !== "BUTTON" && e.target.tagName !== "INPUT") {
          coverFileInput.click();
        }
      });
    }

    // 3. Stats & SEO Engine
    const editTitle = document.getElementById("editTitle");
    const editBody = document.getElementById("editBodyRich");
    const metaDesc = document.getElementById("editMetaDescription");

    function getCleanText(html) {
      const temp = document.createElement("div");
      temp.innerHTML = html;
      return temp.textContent || temp.innerText || "";
    }

    function updateStats() {
      const titleText = editTitle ? editTitle.value.trim() : "";
      const bodyHTML = editBody ? editBody.innerHTML : "";
      const bodyText = getCleanText(bodyHTML).trim();
      
      const words = bodyText ? bodyText.split(/\s+/).filter(w => w.length > 0).length : 0;
      const chars = bodyText.length;
      const readTime = Math.max(1, Math.ceil(words / 200));

      const wordCountEl = document.getElementById("wordCount");
      const charCountEl = document.getElementById("charCount");
      const readTimeEl = document.getElementById("readTime");
      
      if (wordCountEl) wordCountEl.textContent = words;
      if (charCountEl) charCountEl.textContent = chars;
      if (readTimeEl) readTimeEl.textContent = readTime;

      let score = 0;
      if (titleText.length >= 30 && titleText.length <= 70) score += 25;
      else if (titleText.length > 0) score += 10;

      if (words > 300) score += 25;
      else if (words > 100) score += 15;
      else if (words > 0) score += 5;

      const metaText = metaDesc ? metaDesc.value.trim() : "";
      if (metaText.length >= 100 && metaText.length <= 160) score += 25;
      else if (metaText.length > 0) score += 10;

      if (bodyHTML.includes("<h2") || bodyHTML.includes("<h3")) score += 15;

      const coverUrl = coverUrlInput ? coverUrlInput.value.trim() : "";
      if (coverUrl) score += 10;

      const seoScoreEl = document.getElementById("seoScore");
      const seoBadgeEl = document.getElementById("seoScoreBadge");
      if (seoScoreEl) seoScoreEl.textContent = `${score}/100`;
      
      if (seoBadgeEl) {
        seoBadgeEl.className = "seo-badge";
        if (score >= 80) seoBadgeEl.classList.add("good");
        else if (score >= 50) seoBadgeEl.classList.add("average");
        else seoBadgeEl.classList.add("poor");
      }
    }

    if (editTitle) editTitle.addEventListener("input", updateStats);
    if (editBody) {
      editBody.addEventListener("input", updateStats);
      editBody.addEventListener("keyup", updateStats);
      editBody.addEventListener("click", (e) => {
        const link = e.target.closest("a");
        if (link) {
          e.preventDefault();
          window.open(link.href, "_blank");
        }
      });
    }
    if (metaDesc) metaDesc.addEventListener("input", updateStats);

    window.updatePremiumEditorStats = updateStats;

    // Rich Text Editor Toolbar Listeners
    const editorToolbar = document.getElementById("editorToolbar");
    if (editorToolbar) {
      editorToolbar.querySelectorAll("[data-cmd]").forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          const cmd = btn.dataset.cmd;
          document.execCommand(cmd, false, null);
          editBody.focus();
          updateStats();
        });
      });

      editorToolbar.querySelectorAll("[data-block]").forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          const block = btn.dataset.block;
          document.execCommand("formatBlock", false, block);
          editBody.focus();
          updateStats();
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

      if (editBody) {
        editBody.addEventListener("mouseup", saveSelection);
        editBody.addEventListener("keyup", saveSelection);
      }

      const foreColorInput = document.getElementById("tb-forecolor");
      if (foreColorInput) {
        foreColorInput.addEventListener("input", (e) => {
          restoreSelection();
          const color = e.target.value;
          document.execCommand("foreColor", false, color);
          updateStats();
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
          updateStats();
        });
      }
      
      const tbLink = document.getElementById("tb-link");
      if (tbLink) {
        tbLink.addEventListener("click", (e) => {
          e.preventDefault();
          restoreSelection();
          const sanitizeUrl = (u) => {
            if (!u) return u;
            const t = u.trim();
            if (/^(https?:\/\/|mailto:|tel:|#|\/)/i.test(t)) return t;
            return "https://" + t;
          };
          const selection = window.getSelection();
          if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const selectedText = range.toString().trim();
            
            if (selectedText.length > 0) {
              const url = prompt("Enter the link URL (e.g., https://google.com):");
              if (url) {
                restoreSelection();
                document.execCommand("createLink", false, sanitizeUrl(url));
              }
            } else {
              const linkText = prompt("Enter link text:");
              if (linkText) {
                const url = prompt("Enter the link URL (e.g., https://google.com):");
                if (url) {
                  restoreSelection();
                  const a = document.createElement("a");
                  a.href = sanitizeUrl(url);
                  a.textContent = linkText;
                  a.target = "_blank";
                  range.insertNode(a);
                  range.setStartAfter(a);
                  range.setEndAfter(a);
                  selection.removeAllRanges();
                  selection.addRange(range);
                }
              }
            }
          }
          editBody.focus();
          updateStats();
        });
      }
      
      // --- Premium Image Upload/URL Modal and Floating Remove Button ---
      const modal = document.getElementById("insertInlineImageModal");
      const tabUpload = document.getElementById("btnTabUpload");
      const tabUrl = document.getElementById("btnTabUrl");
      const panelUpload = document.getElementById("panelImageUpload");
      const panelUrl = document.getElementById("panelImageUrl");
      const fileInput = document.getElementById("inlineImageFileInput");
      const urlInput = document.getElementById("inlineImageUrlInput");
      const btnSubmitUrl = document.getElementById("btnSubmitImageUrl");

      if (tabUpload && tabUrl && panelUpload && panelUrl) {
        tabUpload.addEventListener("click", () => {
          tabUpload.className = "btn btn-primary btn-sm";
          tabUrl.className = "btn btn-ghost btn-sm";
          panelUpload.style.display = "flex";
          panelUrl.style.display = "none";
        });
        tabUrl.addEventListener("click", () => {
          tabUrl.className = "btn btn-primary btn-sm";
          tabUpload.className = "btn btn-ghost btn-sm";
          panelUrl.style.display = "flex";
          panelUpload.style.display = "none";
        });
      }

      const tbImg = document.getElementById("tb-image");
      if (tbImg) {
        tbImg.addEventListener("click", (e) => {
          e.preventDefault();
          saveSelection();
          C.openModal("insertInlineImageModal");
        });
      }

      const insertImageAtSelection = (src) => {
        restoreSelection();
        const img = document.createElement("img");
        img.src = src;
        img.style.maxWidth = "100%";
        img.style.height = "auto";
        img.style.display = "block";
        img.style.margin = "16px auto";
        img.style.borderRadius = "var(--r-md)";
        img.style.boxShadow = "0 4px 16px rgba(0,0,0,0.06)";

        const selection = window.getSelection();
        let rangeInserted = false;
        
        if (selection.rangeCount > 0 && savedRange) {
          try {
            const range = savedRange;
            // Ensure the range is inside the editor content
            if (editBody.contains(range.commonAncestorContainer)) {
              range.deleteContents();
              range.insertNode(img);
              
              // Insert an empty paragraph or line break after the image for easy continuation
              const p = document.createElement("p");
              p.innerHTML = "<br>";
              img.after(p);
              
              const newRange = document.createRange();
              newRange.setStart(p, 0);
              newRange.collapse(true);
              selection.removeAllRanges();
              selection.addRange(newRange);
              rangeInserted = true;
            }
          } catch (e) {
            console.error("DOM Range insertion failed:", e);
          }
        }
        
        if (!rangeInserted) {
          editBody.appendChild(img);
          const p = document.createElement("p");
          p.innerHTML = "<br>";
          editBody.appendChild(p);
        }
        
        editBody.focus();
        updateStats();
      };

      if (fileInput) {
        if (panelUpload) {
          panelUpload.addEventListener("click", () => {
            fileInput.click();
          });
        }
        fileInput.addEventListener("change", (e) => {
          const file = e.target.files[0];
          if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
              const base64 = event.target.result;
              insertImageAtSelection(base64);
              C.closeModal("insertInlineImageModal");
              fileInput.value = ""; // reset
            };
            reader.readAsDataURL(file);
          }
        });
      }

      if (btnSubmitUrl) {
        btnSubmitUrl.addEventListener("click", () => {
          const url = urlInput.value.trim();
          if (url) {
            insertImageAtSelection(url);
            C.closeModal("insertInlineImageModal");
            urlInput.value = ""; // reset
          }
        });
      }

      // --- Floating Remove Image Widget ---
      let imageDeleteBtn = document.getElementById("floatingImageDeleteBtn");
      if (!imageDeleteBtn) {
        imageDeleteBtn = document.createElement("button");
        imageDeleteBtn.id = "floatingImageDeleteBtn";
        imageDeleteBtn.type = "button";
        imageDeleteBtn.style.position = "absolute";
        imageDeleteBtn.style.zIndex = "10000";
        imageDeleteBtn.style.display = "none";
        imageDeleteBtn.style.background = "#ef4444";
        imageDeleteBtn.style.color = "#ffffff";
        imageDeleteBtn.style.border = "none";
        imageDeleteBtn.style.padding = "6px 12px";
        imageDeleteBtn.style.borderRadius = "4px";
        imageDeleteBtn.style.fontSize = "12px";
        imageDeleteBtn.style.fontWeight = "bold";
        imageDeleteBtn.style.cursor = "pointer";
        imageDeleteBtn.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
        imageDeleteBtn.innerHTML = "🗑️ Remove Image";
        document.body.appendChild(imageDeleteBtn);
      }

      let activeEditImage = null;

      const hideImageDeleteBtn = () => {
        imageDeleteBtn.style.display = "none";
        if (activeEditImage) {
          activeEditImage.style.outline = "";
          activeEditImage = null;
        }
      };

      if (editBody) {
        editBody.addEventListener("click", (e) => {
          if (e.target.tagName === "IMG") {
            activeEditImage = e.target;
            const rect = activeEditImage.getBoundingClientRect();
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

            imageDeleteBtn.style.top = `${rect.top + scrollTop + 8}px`;
            imageDeleteBtn.style.left = `${rect.right + scrollLeft - 130}px`;
            imageDeleteBtn.style.display = "block";

            e.target.style.outline = "2px solid #ef4444";
            e.target.style.outlineOffset = "2px";
          } else {
            if (e.target !== imageDeleteBtn) {
              hideImageDeleteBtn();
            }
          }
        });

        editBody.addEventListener("keyup", hideImageDeleteBtn);
        editBody.addEventListener("scroll", hideImageDeleteBtn);

        // Drag and drop helper for custom blocks (CTA, infographics, steps)
        let draggedNode = null;

        // Dynamically toggle draggable attribute only when grabbing the handle
        editBody.addEventListener("mousedown", (e) => {
          const handle = e.target.closest(".block-drag-handle");
          if (handle) {
            const wrapper = handle.closest(".custom-block-wrapper");
            if (wrapper) {
              wrapper.setAttribute("draggable", "true");
            }
          }
        });

        editBody.addEventListener("mouseup", (e) => {
          document.querySelectorAll(".custom-block-wrapper[draggable='true']").forEach(el => {
            el.setAttribute("draggable", "false");
          });
        });

        editBody.addEventListener("dragstart", (e) => {
          // Find the wrapper (which was set to draggable="true" on mousedown on handle)
          const target = e.target.closest(".custom-block-wrapper");
          if (target && target.getAttribute("draggable") === "true") {
            draggedNode = target;
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/html", target.outerHTML);
          } else {
            e.preventDefault(); // Prevent standard text selection drag
          }
        });

        editBody.addEventListener("dragover", (e) => {
          if (draggedNode) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";

            // Auto-scroll editBody when dragging near the edges
            const rect = editBody.getBoundingClientRect();
            const topThreshold = rect.top + 60;
            const bottomThreshold = rect.bottom - 60;

            if (e.clientY < topThreshold) {
              editBody.scrollTop -= 12;
            } else if (e.clientY > bottomThreshold) {
              editBody.scrollTop += 12;
            }
          }
        });

        editBody.addEventListener("drop", (e) => {
          if (draggedNode) {
            e.preventDefault();
            let range = null;
            if (document.caretRangeFromPoint) {
              range = document.caretRangeFromPoint(e.clientX, e.clientY);
            } else if (e.rangeParent) {
              range = document.createRange();
              range.setStart(e.rangeParent, e.rangeOffset);
            }

            if (range) {
              let targetNode = range.startContainer;
              
              // Resolve to element node if it's a text node
              if (targetNode.nodeType === Node.TEXT_NODE) {
                targetNode = targetNode.parentNode;
              }
              
              // Find the top-level block inside editBody (e.g. direct child paragraph/header)
              while (targetNode && targetNode.parentNode !== editBody) {
                targetNode = targetNode.parentNode;
              }
              
              draggedNode.remove();
              
              if (targetNode && editBody.contains(targetNode)) {
                // Insert directly after the top-level paragraph to avoid styling breaking
                targetNode.after(draggedNode);
              } else {
                editBody.appendChild(draggedNode);
              }
              
              window.getSelection().removeAllRanges();
            }
            draggedNode = null;
            updateStats();
          }
        });
      }

      imageDeleteBtn.addEventListener("click", (e) => {
        e.preventDefault();
        if (activeEditImage) {
          activeEditImage.remove();
          hideImageDeleteBtn();
          updateStats();
        }
      });
    }

    // 4. Floating Selection Formatting Toolbar
    let selectionToolbar = document.getElementById("floatingSelectionToolbar");
    if (!selectionToolbar) {
      selectionToolbar = document.createElement("div");
      selectionToolbar.id = "floatingSelectionToolbar";
      selectionToolbar.className = "floating-format-bar";
      selectionToolbar.style.display = "none";
      selectionToolbar.innerHTML = `
        <button type="button" class="tb-btn" data-fcmd="bold" title="Bold"><i data-lucide="bold"></i></button>
        <button type="button" class="tb-btn" data-fcmd="italic" title="Italic"><i data-lucide="italic"></i></button>
        <button type="button" class="tb-btn" data-fcmd="underline" title="Underline"><i data-lucide="underline"></i></button>
        <span class="tb-sep"></span>
        <button type="button" class="tb-btn" id="floatingLinkBtn" title="Link"><i data-lucide="link"></i></button>
      `;
      document.body.appendChild(selectionToolbar);
      if (window.lucide) window.lucide.createIcons();
    }

    selectionToolbar.querySelectorAll("[data-fcmd]").forEach(btn => {
      btn.addEventListener("mousedown", (e) => {
        e.preventDefault();
        document.execCommand(btn.dataset.fcmd, false, null);
        updateStats();
      });
    });

    const flLinkBtn = document.getElementById("floatingLinkBtn");
    if (flLinkBtn) {
      flLinkBtn.addEventListener("mousedown", (e) => {
        e.preventDefault();
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
          const url = prompt("Enter URL:");
          if (url) {
            document.execCommand("createLink", false, url);
            updateStats();
          }
        }
      });
    }

    if (editBody) {
      document.addEventListener("selectionchange", () => {
        const selection = window.getSelection();
        if (!selection.isCollapsed && editBody.contains(selection.anchorNode)) {
          const range = selection.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          
          selectionToolbar.style.display = "flex";
          selectionToolbar.style.top = `${window.scrollY + rect.top - 45}px`;
          selectionToolbar.style.left = `${window.scrollX + rect.left + (rect.width/2) - (selectionToolbar.offsetWidth/2)}px`;
        } else {
          setTimeout(() => {
            const activeSelection = window.getSelection();
            if (activeSelection.isCollapsed || !editBody.contains(activeSelection.anchorNode)) {
              selectionToolbar.style.display = "none";
            }
          }, 100);
        }
      });
    }

    // 5. Slash Commands Menu
    let slashMenu = document.getElementById("slashCommandsMenu");
    if (!slashMenu) {
      slashMenu = document.createElement("div");
      slashMenu.id = "slashCommandsMenu";
      slashMenu.className = "slash-commands-menu";
      slashMenu.style.display = "none";
      slashMenu.innerHTML = `
        <div class="slash-category">Text Blocks</div>
        <button type="button" class="slash-item" data-cmd="h2">
          <i data-lucide="heading-1"></i>
          <div>
            <span class="slash-title">Heading 1</span>
            <span class="slash-desc">Large section heading</span>
          </div>
        </button>
        <button type="button" class="slash-item" data-cmd="h3">
          <i data-lucide="heading-2"></i>
          <div>
            <span class="slash-title">Heading 2</span>
            <span class="slash-desc">Medium subsection heading</span>
          </div>
        </button>
        <button type="button" class="slash-item" data-cmd="p">
          <i data-lucide="text"></i>
          <div>
            <span class="slash-title">Paragraph</span>
            <span class="slash-desc">Plain body text</span>
          </div>
        </button>
        <div class="slash-category">Lists &amp; Media</div>
        <button type="button" class="slash-item" data-cmd="ul">
          <i data-lucide="list"></i>
          <div>
            <span class="slash-title">Bulleted List</span>
            <span class="slash-desc">Create a simple bulleted list</span>
          </div>
        </button>
        <button type="button" class="slash-item" data-cmd="ol">
          <i data-lucide="list-ordered"></i>
          <div>
            <span class="slash-title">Numbered List</span>
            <span class="slash-desc">Create a numbered list</span>
          </div>
        </button>
        <button type="button" class="slash-item" data-cmd="quote">
          <i data-lucide="quote"></i>
          <div>
            <span class="slash-title">Blockquote</span>
            <span class="slash-desc">Add styled quote block</span>
          </div>
        </button>
        <button type="button" class="slash-item" data-cmd="img">
          <i data-lucide="image"></i>
          <div>
            <span class="slash-title">Inline Image</span>
            <span class="slash-desc">Insert image by URL</span>
          </div>
        </button>
      `;
      document.body.appendChild(slashMenu);
      if (window.lucide) window.lucide.createIcons();
    }

    let selectedIndex = 0;
    function updateMenuFocus() {
      const items = slashMenu.querySelectorAll(".slash-item");
      items.forEach((item, index) => {
        item.classList.toggle("focused", index === selectedIndex);
      });
    }

    if (editBody) {
      editBody.addEventListener("keyup", (e) => {
        if (e.key === "/") {
          const selection = window.getSelection();
          if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            slashMenu.style.display = "flex";
            slashMenu.style.top = `${window.scrollY + rect.bottom + 8}px`;
            slashMenu.style.left = `${window.scrollX + rect.left}px`;
            selectedIndex = 0;
            updateMenuFocus();
          }
        } else if (slashMenu.style.display !== "none") {
          if (e.key === "Escape") {
            slashMenu.style.display = "none";
          }
        }
      });

      editBody.addEventListener("keydown", (e) => {
        if (slashMenu.style.display !== "none") {
          const items = slashMenu.querySelectorAll(".slash-item");
          if (e.key === "ArrowDown") {
            e.preventDefault();
            selectedIndex = (selectedIndex + 1) % items.length;
            updateMenuFocus();
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            selectedIndex = (selectedIndex - 1 + items.length) % items.length;
            updateMenuFocus();
          } else if (e.key === "Enter") {
            e.preventDefault();
            const focusedItem = items[selectedIndex];
            if (focusedItem) focusedItem.click();
          }
        }
      });
    }

    slashMenu.querySelectorAll(".slash-item").forEach(item => {
      item.addEventListener("mousedown", (e) => {
        e.preventDefault();
        const cmd = item.dataset.cmd;
        
        if (editBody) {
          const text = editBody.innerHTML;
          editBody.innerHTML = text.replace(/\/$/, "");
        }

        if (cmd === "h2" || cmd === "h3" || cmd === "p") {
          document.execCommand("formatBlock", false, cmd);
        } else if (cmd === "ul") {
          document.execCommand("insertUnorderedList", false, null);
        } else if (cmd === "ol") {
          document.execCommand("insertOrderedList", false, null);
        } else if (cmd === "quote") {
          document.execCommand("formatBlock", false, "blockquote");
        } else if (cmd === "img") {
          const url = prompt("Enter Image URL:");
          if (url) document.execCommand("insertImage", false, url);
        }

        slashMenu.style.display = "none";
        if (editBody) editBody.focus();
        updateStats();
      });
    });

    document.addEventListener("mousedown", (e) => {
      if (!slashMenu.contains(e.target) && editBody && !editBody.contains(e.target)) {
        slashMenu.style.display = "none";
      }
    });
  }

  // Run initPremiumEditor on load
  initPremiumEditor();

  function openEdit(d) {
    editing = d;
    document.getElementById("editSub").textContent = `${d.chan} · ${d.title}`;
    document.getElementById("editTitle").value = d.title;
    
    const richBody = document.getElementById("editBodyRich");
    if (richBody) {
      richBody.innerHTML = d.body || "";
    }
    
    const cardTitle = document.getElementById("coverCardTitle");
    const urlLabel = document.getElementById("coverUrlLabel");
    const isVideo = d.chan === "YouTube" || (d.cover_image && (d.cover_image.toLowerCase().endsWith(".mp4") || d.cover_image.toLowerCase().endsWith(".webm") || d.cover_image.startsWith("data:video/")));
    
    if (cardTitle) cardTitle.textContent = isVideo ? "Video File" : "Cover Image";
    if (urlLabel) urlLabel.textContent = isVideo ? "Video URL" : "Image URL";

    const coverPreview = document.getElementById("editCoverPreview");
    const coverUrlInput = document.getElementById("editCoverUrl");
    if (coverPreview && coverUrlInput) {
      coverUrlInput.value = d.cover_image || "";
      if (d.cover_image) {
        if (isVideo || d.cover_image.startsWith("data:video/")) {
          coverPreview.style.backgroundImage = "none";
          coverPreview.style.border = "none";
          coverPreview.innerHTML = `<video src="${d.cover_image}" controls style="width:100%; height:100%; object-fit:cover; border-radius:6px;"></video>`;
        } else {
          coverPreview.style.backgroundImage = `url('${d.cover_image}')`;
          coverPreview.style.border = "none";
          coverPreview.innerHTML = "";
        }
      } else {
        coverPreview.style.backgroundImage = "none";
        coverPreview.style.border = "1.5px dashed var(--border)";
        coverPreview.innerHTML = isVideo
          ? `<i data-lucide="video" class="muted" style="width:32px;height:32px"></i>`
          : `<i data-lucide="image" class="muted" style="width:32px;height:32px"></i>`;
        if (window.lucide) window.lucide.createIcons();
      }
    }
    
    activeEditorTags = Array.isArray(d.tags) ? [...d.tags] : [];
    renderEditorTags();

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
    const editMetaDesc = document.getElementById("editMetaDescription");
    if (editMetaDesc) {
      editMetaDesc.value = d.meta_description || "";
    }
    const editMetaTitle = document.getElementById("editMetaTitle");
    if (editMetaTitle) {
      editMetaTitle.value = d.meta_title || "";
    }
    
    if (window.updatePremiumEditorStats) {
      window.updatePremiumEditorStats();
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
      const meta_description = document.getElementById("editMetaDescription") ? document.getElementById("editMetaDescription").value.trim() : "";
      const meta_title = document.getElementById("editMetaTitle") ? document.getElementById("editMetaTitle").value.trim() : "";
      
      try {
        await CandenceAPI.updateDraft(editing.id, { title, body, cover_image, tags, author_name, custom_date, category, meta_description, meta_title });
        editing.title = title;
        editing.body = body;
        editing.cover_image = cover_image;
        editing.tags = tags;
        editing.author_name = author_name;
        editing.custom_date = custom_date;
        editing.category = category;
        editing.meta_description = meta_description;
        editing.meta_title = meta_title;
        
        await window.MOCK.syncMockData(site.id);
        drafts = window.MOCK.content.filter(x => x.site === site.id);
        renderDrafts();
        if (window.renderPub) window.renderPub();
        
        if (editing.status === "Published" || editing.status === "published") {
          C.toast({ type: "success", title: "Changes saved locally", desc: "Your edits are saved. Click 'Republish' on the post preview to push updates live!" });
        } else {
          C.toast({ type: "success", title: "Changes saved" });
        }
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
      
      const now = new Date();
      if (targetDate < now) {
        C.toast({ type: "warning", title: "Scheduling blocked", desc: "Cannot schedule posts in the past." });
        return;
      }
      
      confirmScheduleBtn.disabled = true;
      try {
        await CandenceAPI.scheduleDraft(draftId, targetDate.toISOString());
        
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

  /* ----- hero / tab buttons that switch tabs ----- */
  document.querySelectorAll("[data-tab]").forEach(b => {
    if (b.classList.contains("tab")) return; // handled by app.js
    b.addEventListener("click", () => {
      const targetTab = b.dataset.tab;
      document.querySelectorAll(".ws-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === targetTab));
      document.querySelectorAll("#wsPanels .tab-panel").forEach(pp => pp.classList.toggle("active", pp.dataset.panel === targetTab));
      if (targetTab === "generate") {
        document.getElementById("ideaTitle")?.focus();
      }
    });
  });

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

  // Set min date for date inputs to prevent past scheduling
  const todayObj = new Date();
  const yyyy = todayObj.getFullYear();
  const mm = String(todayObj.getMonth() + 1).padStart(2, '0');
  const dd = String(todayObj.getDate()).padStart(2, '0');
  const localTodayStr = `${yyyy}-${mm}-${dd}`;
  const schedDateInput = document.getElementById("schedDate");
  const schedTimeInput = document.getElementById("schedTime");
  if (schedDateInput) {
    schedDateInput.min = localTodayStr;
  }

  window.updateWorkspaceMinTime = function() {
    if (schedDateInput && schedTimeInput) {
      const tObj = new Date();
      const y = tObj.getFullYear();
      const m = String(tObj.getMonth() + 1).padStart(2, '0');
      const d = String(tObj.getDate()).padStart(2, '0');
      const todayStr = `${y}-${m}-${d}`;
      
      if (schedDateInput.value === todayStr) {
        const hh = String(tObj.getHours()).padStart(2, '0');
        const min = String(tObj.getMinutes()).padStart(2, '0');
        schedTimeInput.min = `${hh}:${min}`;
      } else {
        schedTimeInput.removeAttribute("min");
      }
    }
  };
  if (schedDateInput) {
    schedDateInput.addEventListener("change", window.updateWorkspaceMinTime);
    schedDateInput.addEventListener("input", window.updateWorkspaceMinTime);
  }

  /* ----- usage stats dashboard logic ----- */
  let usageChartInstance = null;

  async function loadUsageStats() {
    try {
      const stats = await CandenceAPI.getTokenUsageStats(site.id);

      // Render simple stats cards
      document.getElementById("usageTotalTokens").textContent = C.fmt(stats.total_tokens);
      document.getElementById("usagePromptTokens").textContent = C.fmt(stats.prompt_tokens);
      document.getElementById("usageCompletionTokens").textContent = C.fmt(stats.completion_tokens);
      document.getElementById("usageTotalCost").textContent = `$${stats.total_cost.toFixed(2)}`;

      // Update cost description dynamically based on actual models utilized
      const costDesc = document.getElementById("usageCostDesc");
      if (costDesc) {
        const models = Object.keys(stats.model_breakdown || {});
        if (models.length > 0) {
          const names = models.map(m => {
            if (m.toLowerCase().includes("gpt")) return "OpenAI";
            if (m.toLowerCase().includes("gemini")) return "Gemini";
            if (m.toLowerCase().includes("dall")) return "DALL-E";
            return m;
          });
          const uniqueNames = [...new Set(names)];
          costDesc.textContent = `Based on ${uniqueNames.join(" & ")} pricing`;
        } else {
          costDesc.textContent = "Based on model API pricing";
        }
      }

      // Weekly trend label
      const trendVal = document.getElementById("usageWeeklyTrend");
      if (stats.total_tokens > 100000) {
        trendVal.textContent = "High";
        trendVal.style.color = "var(--danger)";
      } else if (stats.total_tokens > 20000) {
        trendVal.textContent = "Moderate";
        trendVal.style.color = "var(--warning)";
      } else {
        trendVal.textContent = "Low";
        trendVal.style.color = "var(--success)";
      }

      // Draw model breakdown list
      const modelContainer = document.getElementById("usageModelBreakdown");
      modelContainer.innerHTML = "";
      const models = Object.keys(stats.model_breakdown);
      if (models.length === 0) {
        modelContainer.innerHTML = `<span class="tsm text-muted">No API usage recorded yet.</span>`;
      } else {
        models.forEach(model => {
          const usage = stats.model_breakdown[model];
          const div = document.createElement("div");
          div.className = "row-between";
          div.style = "font-size:13px; margin-bottom: 4px;";
          div.innerHTML = `
            <span class="fw5" style="color:var(--text)">${model}</span>
            <span class="mono muted">${C.fmt(usage.tokens)} tokens ($${usage.cost.toFixed(4)})</span>
          `;
          modelContainer.appendChild(div);
        });
      }

      // Draw feature breakdown list
      const sectionContainer = document.getElementById("usageSectionBreakdown");
      sectionContainer.innerHTML = "";
      const sections = Object.keys(stats.section_breakdown);
      if (sections.length === 0) {
        sectionContainer.innerHTML = `<span class="tsm text-muted">No API usage recorded yet.</span>`;
      } else {
        sections.forEach(section => {
          const usage = stats.section_breakdown[section];
          const div = document.createElement("div");
          div.className = "row-between";
          div.style = "font-size:13px; margin-bottom: 4px;";
          div.innerHTML = `
            <span class="fw5" style="color:var(--text)">${section}</span>
            <span class="mono muted">${C.fmt(usage.tokens)} tokens ($${usage.cost.toFixed(4)})</span>
          `;
          sectionContainer.appendChild(div);
        });
      }

      // Render line chart
      const chartCanvas = document.getElementById("usageChart");
      if (!chartCanvas) return;

      if (usageChartInstance) {
        usageChartInstance.destroy();
      }

      const labels = stats.weekly_history.map(d => d.day);
      const dataPoints = stats.weekly_history.map(d => d.tokens);

      const computedStyles = getComputedStyle(document.documentElement);
      const primaryColor = computedStyles.getPropertyValue('--primary').trim() || '#3b82f6';
      const gridColor = computedStyles.getPropertyValue('--border').trim() || 'rgba(0, 0, 0, 0.05)';
      const textColor = computedStyles.getPropertyValue('--text').trim() || '#1e293b';

      usageChartInstance = new Chart(chartCanvas, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Tokens Used',
            data: dataPoints,
            borderColor: primaryColor,
            backgroundColor: primaryColor + '15',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 4,
            pointBackgroundColor: primaryColor
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              grid: { color: gridColor },
              ticks: { color: textColor, font: { family: 'Inter' } },
              beginAtZero: true
            },
            x: {
              grid: { display: false },
              ticks: { color: textColor, font: { family: 'Inter' } }
            }
          }
        }
      });

    } catch (err) {
      console.error("Failed to load token usage statistics:", err);
      C.toast({ type: "error", title: "Error Loading Stats", desc: err.message || "Unable to retrieve API token usage details." });
    }
  }

  // Bind to Usage tab click
  const usageTabBtn = document.querySelector('.ws-tabs button[data-tab="usage"]');
  if (usageTabBtn) {
    usageTabBtn.addEventListener("click", loadUsageStats);
  }

  // Initialize global poller on load in case there are running tasks from a previous session/page
  initGlobalTaskPoller();

  renderDrafts();
  C.refreshIcons();
})();
