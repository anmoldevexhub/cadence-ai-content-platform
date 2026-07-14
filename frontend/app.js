/* ==========================================================================
   CADENCE — shared app.js
   Injects sidebar + topbar shell, wires theme/role toggle, tabs, modals,
   dropdowns, toasts. Loaded after mock-data.js on every dashboard page.
   ========================================================================== */
(function () {
  "use strict";

  /* ---------- persisted prefs ---------- */
  const store = {
    get theme() { return localStorage.getItem("candence.theme") || "light"; },
    set theme(v) { localStorage.setItem("candence.theme", v); },
    get role() { return localStorage.getItem("candence.role") || "admin"; },
    set role(v) { localStorage.setItem("candence.role", v); },
  };

  // apply theme ASAP (also done inline in <head> to avoid flash)
  document.documentElement.setAttribute("data-theme", store.theme);

  /* ---------- icons helper ---------- */
  // Lucide dropped brand glyphs — supply our own inline SVGs for platforms.
  const BRAND = {
    linkedin: 'M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z',
    youtube: 'M23.5 6.2a3.02 3.02 0 0 0-2.12-2.14C19.5 3.55 12 3.55 12 3.55s-7.5 0-9.38.51A3.02 3.02 0 0 0 .5 6.2C0 8.07 0 12 0 12s0 3.93.5 5.8a3.02 3.02 0 0 0 2.12 2.14c1.88.51 9.38.51 9.38.51s7.5 0 9.38-.51a3.02 3.02 0 0 0 2.12-2.14C24 15.93 24 12 24 12s0-3.93-.5-5.8zM9.55 15.57V8.43L15.82 12l-6.27 3.57z',
    instagram: 'M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.43.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.43.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.43-.36-1.06-.41-2.23-.06-1.27-.07-1.65-.07-4.85s.01-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.43-.16 1.06-.36 2.23-.41 1.27-.06 1.65-.07 4.85-.07M12 0C8.74 0 8.33.01 7.05.07c-1.28.06-2.15.26-2.91.56-.79.3-1.46.72-2.13 1.38A5.86 5.86 0 0 0 .63 4.14c-.3.76-.5 1.63-.56 2.91C.01 8.33 0 8.74 0 12s.01 3.67.07 4.95c.06 1.28.26 2.15.56 2.91.3.79.72 1.46 1.38 2.13.67.66 1.34 1.08 2.13 1.38.76.3 1.63.5 2.91.56C8.33 23.99 8.74 24 12 24s3.67-.01 4.95-.07c1.28-.06 2.15-.26 2.91-.56a5.86 5.86 0 0 0 2.13-1.38 5.86 5.86 0 0 0 1.38-2.13c.3-.76.5-1.63.56-2.91.06-1.28.07-1.69.07-4.95s-.01-3.67-.07-4.95c-.06-1.28-.26-2.15-.56-2.91a5.86 5.86 0 0 0-1.38-2.13A5.86 5.86 0 0 0 19.86.63c-.76-.3-1.63-.5-2.91-.56C15.67.01 15.26 0 12 0zm0 5.84A6.16 6.16 0 1 0 12 18.16 6.16 6.16 0 0 0 12 5.84zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm7.85-10.41a1.44 1.44 0 1 1-2.88 0 1.44 1.44 0 0 1 2.88 0z',
  };
  const I = (name, attrs = "") => {
    if (BRAND[name]) return `<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" ${attrs}><path d="${BRAND[name]}"/></svg>`;
    return `<i data-lucide="${name}" ${attrs}></i>`;
  };
  function refreshIcons() { if (window.lucide) window.lucide.createIcons(); }

  /* ---------- nav config ---------- */
  const NAV_MAIN = [
    { id: "dashboard", label: "Dashboard", icon: "layout-dashboard", href: "dashboard.html" },
    { id: "calendar", label: "Content Calendar", icon: "calendar-days", href: "calendar.html" },
    { id: "approvals", label: "Approvals", icon: "check-check", href: "approvals.html", badge: "approvals" },
    { id: "analytics", label: "Analytics", icon: "bar-chart-3", href: "analytics.html" },
    { id: "trash", label: "Trash", icon: "trash-2", href: "trash.html" },
  ];
  const NAV_ADMIN = [
    { id: "admins", label: "Admins & Roles", icon: "users", href: "admins.html" },
    { id: "all-websites", label: "All Websites", icon: "globe", href: "all-websites.html" },
  ];

  function faviconHTML(site) {
    return `<span class="favicon" style="background:${site.color}">${site.short}</span>`;
  }

  function buildSidebar(active) {
    const role = store.role;
    const sites = (window.MOCK?.websites || []).filter(s => !s.is_deleted).slice(0, 6);
    const pendingCount = (window.MOCK?.approvals || []).filter(a => a.status === "Draft").length;

    const navItem = (n) => {
      const badge = n.badge === "approvals" && pendingCount
        ? `<span class="nav-badge">${pendingCount}</span>` : "";
      return `<a class="nav-item ${active === n.id ? "active" : ""}" href="${n.href}">
        ${I(n.icon)}<span>${n.label}</span>${badge}</a>`;
    };

    const sitesHTML = sites.map(s => `
      <a class="nav-item site-item ${active === "site-" + s.id ? "active" : ""}" href="website-workspace.html?site=${s.id}">
        ${faviconHTML(s)}<span class="site-name">${s.name}</span>
        <span class="site-dot ${s.statusClass}"></span>
      </a>`).join("");

    const adminGroup = role === "super" ? `
      <div class="nav-group">
        <div class="nav-label">Administration</div>
        ${NAV_ADMIN.map(navItem).join("")}
      </div>` : "";

    const usersObj = window.MOCK?.users || {};
    const user = (role === "super" ? usersObj.super : usersObj.admin) || usersObj.admin || { name: "User", initials: "U", color: "#095075" };

    return `
      <div class="sidebar__brand">
        <span class="brand-mark">${I("audio-waveform")}</span>
        <span class="brand-name">Candence</span>
      </div>
      <div class="sidebar__scroll">
        <div class="nav-group">
          <div class="nav-label">Workspace</div>
          ${NAV_MAIN.map(navItem).join("")}
        </div>
        ${adminGroup}
        <div class="nav-group">
          <div class="nav-label">Websites <a href="add-website.html" title="Add website" style="color:var(--text-muted)">${I("plus", "style='width:14px;height:14px'")}</a></div>
          ${sites.length ? sitesHTML : `<div class="muted tsm" style="padding:6px 12px">No websites yet</div>`}
          <a class="nav-item" href="add-website.html" style="color:var(--text-muted)">${I("plus-circle")}<span>Add website</span></a>
        </div>
        <div class="nav-group">
          <div class="nav-label">Account</div>
          <a class="nav-item ${active === "settings" ? "active" : ""}" href="settings.html">${I("settings")}<span>Settings</span></a>
        </div>
      </div>
      <div class="sidebar__footer">
        <div class="dropdown">
          <div class="user-card" data-menu="usermenu">
            <span class="avatar" style="background:${user.color}">${localStorage.getItem("candence.settings.avatar") ? `<img src="${localStorage.getItem("candence.settings.avatar")}" alt="${user.name}">` : user.initials}</span>
            <span class="meta"><span class="nm">${user.name}</span><span class="rl">${role === "super" ? "Super Admin" : "Admin"}</span></span>
            ${I("chevrons-up-down")}
          </div>
          <div class="menu left" id="usermenu" style="bottom:calc(100% + 6px); top:auto; transform-origin:bottom left">
            <div class="menu-head"><div class="nm">${user.name}</div><div class="em">${user.email}</div></div>
            <div class="menu-sep"></div>
            <a class="menu-item" href="settings.html">${I("user")}Profile</a>
            <div class="menu-sep"></div>
            <a class="menu-item danger" href="login.html">${I("log-out")}Sign out</a>
          </div>
        </div>
      </div>`;
  }
  function markNotificationsAsRead() {
    const notifs = window.MOCK?.notifications || [];
    if (!notifs.length) return;
    
    let readIds = [];
    try {
      readIds = JSON.parse(localStorage.getItem("candence.read_notifications")) || [];
    } catch(e) {}
    
    notifs.forEach(n => {
      if (n.id && !readIds.includes(n.id)) {
        readIds.push(n.id);
      }
    });
    
    localStorage.setItem("candence.read_notifications", JSON.stringify(readIds));
    
    // Hide the badge-count element
    const badge = document.querySelector("[data-menu='notifs'] .badge-count");
    if (badge) {
      badge.remove();
    }
  }

  function buildTopbar() {
    const role = store.role;
    const usersObj = window.MOCK?.users || {};
    const user = (role === "super" ? usersObj.super : usersObj.admin) || usersObj.admin || { name: "User", initials: "U", color: "#095075" };
    
    let readIds = [];
    try {
      readIds = JSON.parse(localStorage.getItem("candence.read_notifications")) || [];
    } catch(e) {}
    
    const notifs = window.MOCK?.notifications || [];
    const unreadCount = notifs.filter(n => n.id && !readIds.includes(n.id)).length;
    
    return `
      <button class="icon-btn sidebar-toggle" data-action="toggle-sidebar" aria-label="Menu">${I("menu")}</button>
      <label class="topbar__search">
        ${I("search")}
        <input type="text" placeholder="Search websites, content, ideas…" aria-label="Search" />
        <kbd>⌘K</kbd>
      </label>
      <div class="topbar__actions">
        <div class="dropdown">
          <button class="icon-btn" data-menu="notifs" aria-label="Notifications">${I("bell")}${unreadCount > 0 ? `<span class="badge-count">${unreadCount}</span>` : ''}</button>
          <div class="menu" id="notifs" style="min-width:320px">
            <div class="row-between" style="padding:8px 10px 10px"><strong>Notifications</strong><a class="tsm" id="markAllReadBtn" style="color:var(--primary); cursor:pointer;">Mark all read</a></div>
            <div class="menu-sep"></div>
            ${notifs.map(n => `
              <a class="menu-item" href="${n.href}" style="align-items:flex-start">
                <span class="icon-tile tile-${n.tile}" style="width:30px;height:30px;border-radius:8px">${I(n.icon, "style='width:15px;height:15px'")}</span>
                <span style="flex:1"><span style="display:block;color:var(--text);font-weight:500">${n.text}</span><span class="txs muted">${n.time}</span></span>
              </a>`).join("")}
          </div>
        </div>
        <button class="icon-btn" data-action="toggle-theme" aria-label="Toggle theme">${I("sun-moon")}</button>
        <div class="dropdown">
          <button class="icon-btn" data-menu="topuser" aria-label="Account" style="width:auto;padding:3px;border-radius:99px">
            <span class="avatar avatar-sm" style="background:${user.color}">${localStorage.getItem("candence.settings.avatar") ? `<img src="${localStorage.getItem("candence.settings.avatar")}" alt="User">` : user.initials}</span>
          </button>
          <div class="menu" id="topuser">
            <a class="menu-item" href="settings.html">${I("user")}Profile</a>
            <a class="menu-item" href="settings.html">${I("settings")}Settings</a>
            <div class="menu-sep"></div>
            <a class="menu-item danger" href="login.html">${I("log-out")}Sign out</a>
          </div>
        </div>
      </div>`;
  }

  /* ---------- mount shell ---------- */
  function mountShell() {
    const sb = document.getElementById("sidebar");
    const tb = document.getElementById("topbar");
    if (sb) sb.innerHTML = buildSidebar(sb.dataset.active || "");
    if (tb) tb.innerHTML = buildTopbar();
    
    // Inject global search modal if it doesn't exist
    if (!document.getElementById("globalSearchModal")) {
      const searchModalDiv = document.createElement("div");
      searchModalDiv.className = "modal-overlay";
      searchModalDiv.id = "globalSearchModal";
      searchModalDiv.style.alignItems = "flex-start";
      searchModalDiv.style.paddingTop = "10vh";
      searchModalDiv.style.zIndex = "2000";
      searchModalDiv.innerHTML = `
        <div class="modal" style="max-width: 600px; width: 90vw; border-radius: var(--r-lg); box-shadow: var(--sh-xl);">
          <div class="modal__body" style="padding: var(--s4);">
            <div class="topbar__search" style="border: 1px solid var(--border-strong); border-radius: var(--r-md); padding: 12px; font-size: 16px; margin-bottom: var(--s4); width: 100%; display: flex; gap: 8px;">
              ${I("search", "style='width:20px; height:20px; color:var(--text-muted)'")}
              <input type="text" id="gSearchInput" placeholder="Search websites, content, ideas..." style="border:none; outline:none; background:none; color:var(--text); flex:1; font-size:16px;" autofocus />
            </div>
            <div id="gSearchResults" style="max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
              <div class="muted tsm" style="padding: 10px; text-align: center;">Type to search...</div>
            </div>
          </div>
        </div>`;
      document.body.appendChild(searchModalDiv);
      wireGlobalSearch();
    }
    
    refreshIcons();
    wireShell();
  }

  function wireGlobalSearch() {
    const searchInput = document.getElementById("gSearchInput");
    const searchResults = document.getElementById("gSearchResults");
    if (!searchInput || !searchResults) return;
    
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      if (!query) {
        searchResults.innerHTML = `<div class="muted tsm" style="padding: 10px; text-align: center;">Type to search...</div>`;
        return;
      }
      
      const sites = (window.MOCK?.websites || []).filter(s => !s.is_deleted && (s.name.toLowerCase().includes(query) || s.url.toLowerCase().includes(query)));
      const drafts = (window.MOCK?.content || []).filter(d => !d.is_deleted && d.title.toLowerCase().includes(query));
      
      let html = "";
      
      if (sites.length) {
        html += `<div style="font-weight: 700; font-size: 11px; text-transform: uppercase; color: var(--text-muted); margin: 8px 0 4px; padding-left: 6px;">Websites</div>`;
        sites.forEach(s => {
          html += `
            <a class="menu-item" href="website-workspace.html?site=${s.id}" style="padding: 10px; border-radius: var(--r-md); display: flex; align-items: center; gap: var(--s3); background: var(--bg-subtle);">
              <span class="favicon" style="background:${s.color}; width:20px; height:20px; border-radius:4px; font-size:10px; display: grid; place-items: center; color: white;">${s.short}</span>
              <span style="font-weight: 550; color: var(--text);">${s.name}</span>
              <span class="muted txs" style="margin-left: auto;">${s.url}</span>
            </a>`;
        });
      }
      
      if (drafts.length) {
        html += `<div style="font-weight: 700; font-size: 11px; text-transform: uppercase; color: var(--text-muted); margin: 12px 0 4px; padding-left: 6px;">Content & Drafts</div>`;
        drafts.forEach(d => {
          const s = window.MOCK?.site(d.site) || { name: "Unknown", color: "#095075", short: "U" };
          const p = window.MOCK?.platMeta ? window.MOCK.platMeta(d.platform) : { icon: "file-text", color: "var(--primary)" };
          
          html += `
            <a class="menu-item" href="website-workspace.html?site=${d.site}&tab=generate" style="padding: 10px; border-radius: var(--r-md); display: flex; align-items: center; gap: var(--s3); background: var(--bg-subtle);">
              <span class="icon-tile tile-${d.platform.toLowerCase()}" style="width:20px; height:20px; border-radius:4px; display: grid; place-items: center; background: ${p.color}20; color: ${p.color};">${I(p.icon || 'file-text', "style='width:12px; height:12px'")}</span>
              <div style="display: flex; flex-direction: column; overflow: hidden; flex: 1;">
                <span style="font-weight: 550; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${d.title}</span>
                <span class="muted txs" style="display: flex; align-items: center; gap: 4px;">
                  <span class="badge badge-${d.status.toLowerCase()}" style="padding: 1px 4px; font-size: 9px;">${d.status}</span> on ${s.name}
                </span>
              </div>
            </a>`;
        });
      }
      
      if (!html) {
        html = `<div class="muted tsm" style="padding: 20px; text-align: center;">No matches found for "${query}"</div>`;
      }
      
      searchResults.innerHTML = html;
      refreshIcons();
    });
    
    // Bind click listener on topbar search input
    document.addEventListener("click", (e) => {
      const trigger = e.target.closest(".topbar__search");
      if (trigger && !trigger.closest("#globalSearchModal")) {
        e.preventDefault();
        window.Candence.openModal("globalSearchModal");
        searchInput.value = "";
        searchInput.focus();
        searchResults.innerHTML = `<div class="muted tsm" style="padding: 10px; text-align: center;">Type to search...</div>`;
      }
    });

    // Keyboard shortcut (⌘K or Ctrl+K)
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        window.Candence.openModal("globalSearchModal");
        searchInput.value = "";
        searchInput.focus();
        searchResults.innerHTML = `<div class="muted tsm" style="padding: 10px; text-align: center;">Type to search...</div>`;
      }
    });
  }

  /* ---------- interactivity ---------- */
  function closeAllMenus(except) {
    document.querySelectorAll(".menu.open").forEach(m => { if (m !== except) m.classList.remove("open"); });
  }

  function wireShell() {
    if (window._shellWired) return;
    window._shellWired = true;
    // dropdown menus
    document.addEventListener("click", (e) => {
      const trigger = e.target.closest("[data-menu]");
      if (trigger) {
        e.stopPropagation();
        const menu = document.getElementById(trigger.dataset.menu);
        if (menu) {
          const willOpen = !menu.classList.contains("open");
          closeAllMenus(menu);
          menu.classList.toggle("open", willOpen);
          
          if (trigger.dataset.menu === "notifs" && willOpen) {
            markNotificationsAsRead();
          }
        }
      } else {
        closeAllMenus();
      }
    });

    // mark all read button click
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("#markAllReadBtn");
      if (btn) {
        e.preventDefault();
        e.stopPropagation();
        markNotificationsAsRead();
      }
    });

    // theme toggle
    document.addEventListener("click", (e) => {
      const b = e.target.closest('[data-action="toggle-theme"]');
      if (b) {
        e.stopPropagation();
        toggleTheme();
      }
    });

    // role toggle
    document.addEventListener("click", (e) => {
      const b = e.target.closest("[data-role]");
      if (b) {
        e.stopPropagation();
        setRole(b.dataset.role);
      }
    });

    // sign out logic
    document.addEventListener("click", (e) => {
      const a = e.target.closest('a[href="login.html"]');
      if (a) {
        e.preventDefault();
        if (window.CandenceAPI) {
          window.CandenceAPI.logout();
        } else {
          localStorage.removeItem('candence.access_token');
          localStorage.removeItem('candence.refresh_token');
          localStorage.removeItem('candence.user');
          location.href = 'login.html';
        }
      }
    });

    // sidebar (mobile)
    document.addEventListener("click", (e) => {
      const b = e.target.closest('[data-action="toggle-sidebar"]');
      if (b) {
        e.stopPropagation();
        toggleSidebar();
      }
    });

    const bd = document.getElementById("backdrop");
    if (bd) bd.addEventListener("click", toggleSidebar);
  }

  function toggleTheme() {
    const next = store.theme === "dark" ? "light" : "dark";
    store.theme = next;
    document.documentElement.setAttribute("data-theme", next);
    window.dispatchEvent(new CustomEvent("themechange", { detail: next }));
    toast({ type: "info", title: next === "dark" ? "Dark mode on" : "Light mode on" });
  }

  function setRole(role) {
    if (store.role === role) return;
    store.role = role;
    mountShell();
    window.dispatchEvent(new CustomEvent("rolechange", { detail: role }));
    toast({ type: "info", title: role === "super" ? "Viewing as Super Admin" : "Viewing as Admin",
      desc: role === "super" ? "Extra management screens unlocked" : "Standard workspace view" });
  }

  function toggleSidebar() {
    document.getElementById("sidebar")?.classList.toggle("open");
    document.getElementById("backdrop")?.classList.toggle("show");
  }

  /* ---------- toasts ---------- */
  function ensureToastWrap() {
    let w = document.querySelector(".toast-wrap");
    if (!w) { w = document.createElement("div"); w.className = "toast-wrap"; document.body.appendChild(w); }
    return w;
  }
  const TOAST_IC = { success: "check", error: "x", info: "info" };
  function toast({ type = "success", title = "", desc = "", timeout = 3200 } = {}) {
    const w = ensureToastWrap();
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="t-ic">${I(TOAST_IC[type] || "check")}</span>
      <div class="t-body"><div class="t-title">${title}</div>${desc ? `<div class="t-desc">${desc}</div>` : ""}</div>
      <button class="t-close" aria-label="Dismiss">${I("x")}</button>`;
    w.appendChild(el);
    refreshIcons();
    const kill = () => { el.classList.add("hide"); setTimeout(() => el.remove(), 240); };
    el.querySelector(".t-close").addEventListener("click", kill);
    if (timeout) setTimeout(kill, timeout);
  }

  /* ---------- modals ---------- */
  function openModal(id) {
    const m = document.getElementById(id);
    if (m) { m.classList.add("open"); refreshIcons(); }
  }
  function closeModal(idOrEl) {
    const m = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
    if (m) m.classList.remove("open");
  }
  // delegate close on overlay click + [data-close]
  document.addEventListener("click", (e) => {
    if (e.target.classList?.contains("modal-overlay")) closeModal(e.target);
    const c = e.target.closest?.("[data-close-modal]");
    if (c) closeModal(c.closest(".modal-overlay"));
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { closeAllMenus(); document.querySelectorAll(".modal-overlay.open").forEach(closeModal); }
  });

  /* ---------- tabs (generic) ---------- */
  function wireTabs(root = document) {
    root.querySelectorAll("[data-tabs]").forEach(group => {
      group.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
          const target = tab.dataset.tab;
          group.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
          const scope = group.dataset.tabsScope ? document.getElementById(group.dataset.tabsScope) : document;
          scope.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.dataset.panel === target));
        });
      });
    });
  }

  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(e);
      reader.readAsText(file);
    });
  }

  /* ---------- helpers exposed ---------- */
  window.Candence = {
    store, toast, openModal, closeModal, wireTabs, refreshIcons, mountShell,
    icon: I,
    fmt: (n) => n.toLocaleString("en-US"),
    readFileAsText
  };

  /* ---------- boot ---------- */
  function boot() {
    mountShell();
    wireTabs();
    // mark active site in sidebar from query param
    const params = new URLSearchParams(location.search);
    if (params.get("site")) {
      document.querySelectorAll(`.site-item[href*="site=${params.get("site")}"]`).forEach(a => a.classList.add("active"));
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
