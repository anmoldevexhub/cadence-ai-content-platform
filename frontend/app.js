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
    const key = name ? name.toLowerCase() : "";
    if (BRAND[key]) return `<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" ${attrs}><path d="${BRAND[key]}"/></svg>`;
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

  // Safely escape HTML to prevent XSS when inserting user-controlled strings into innerHTML
  function escapeHTML(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function buildSidebar(active) {
    const role = store.role;
    const sites = (window.MOCK?.websites || []).filter(s => !s.is_deleted);
    const pendingCount = (window.MOCK?.approvals || []).filter(a => a.status === "Draft").length;

    const navItem = (n) => {
      const badge = n.badge === "approvals" && pendingCount
        ? `<span class="nav-badge">${pendingCount}</span>` : "";
      return `<a class="nav-item ${active === n.id ? "active" : ""}" href="${n.href}">
        ${I(n.icon)}<span>${n.label}</span>${badge}</a>`;
    };

    const sitesHTML = sites.map(s => `
      <a class="nav-item site-item ${active === "site-" + s.id ? "active" : ""}" href="website-workspace.html?site=${s.id}" title="${escapeHTML(s.name)} (${escapeHTML(s.url)})">
        ${faviconHTML(s)}
        <div style="display: flex; flex-direction: column; min-width: 0; flex: 1;">
          <span class="site-name" style="font-size: 13px; font-weight: 600; line-height: 1.2;">${escapeHTML(s.name)}</span>
          <span class="site-url" style="font-size: 10px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; line-height: 1.1;">${escapeHTML(s.url)}</span>
        </div>
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
          <div class="sidebar-sites-scroll" style="max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; padding-right: 4px;">
            ${sites.length ? sitesHTML : `<div class="muted tsm" style="padding:6px 12px">No websites yet</div>`}
          </div>
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
            <span class="avatar" style="background:${user.color}">${localStorage.getItem("candence.settings.avatar." + role) ? `<img src="${localStorage.getItem("candence.settings.avatar." + role)}" alt="${user.name}">` : user.initials}</span>
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
            <span class="avatar avatar-sm" style="background:${user.color}">${localStorage.getItem("candence.settings.avatar." + role) ? `<img src="${localStorage.getItem("candence.settings.avatar." + role)}" alt="User">` : user.initials}</span>
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

  /* ----- Global Task Polling & UI Indicators ----- */
  window.getActiveTasks = function() {
    let ideas = [];
    let draftsList = [];
    try {
      ideas = JSON.parse(localStorage.getItem("candence.active_ideas")) || [];
    } catch(e){}
    try {
      draftsList = JSON.parse(localStorage.getItem("candence.active_drafts")) || [];
    } catch(e){}
    return { ideas, drafts: draftsList };
  };

  window.saveActiveTasks = function(ideas, draftsList) {
    localStorage.setItem("candence.active_ideas", JSON.stringify(ideas));
    localStorage.setItem("candence.active_drafts", JSON.stringify(draftsList));
  };

  let widgetCollapsed = false;
  let widgetCustomX = null;
  let widgetCustomY = null;

  window.updateGlobalTaskWidget = function() {
    const { ideas, drafts: draftsList } = window.getActiveTasks();
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
      
      widget.style.top = widgetCustomY !== null ? `${widgetCustomY}px` : "76px";
      if (widgetCustomX !== null) {
        widget.style.left = `${widgetCustomX}px`;
      } else {
        widget.style.right = "24px";
      }
      
      document.body.appendChild(widget);

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

      // mouseup on `window` (not `widget`) so we detect the mouse release
      // even when the cursor has drifted outside the widget bounds during a drag.
      window.addEventListener("mouseup", (e) => {
        if (!isDragging) return;
        isDragging = false;
        widget.style.cursor = "grab";
        if (!hasMovedSignificant) {
          if (widgetCollapsed) {
            widgetCollapsed = false;
            window.updateGlobalTaskWidget();
          } else {
            // Check if dropdown toggle or button was clicked
            const dropdownToggle = e.target.closest(".task-dropdown-toggle");
            if (dropdownToggle) {
              const dropdown = widget.querySelector(".global-task-dropdown");
              if (dropdown) {
                const isShowing = dropdown.style.display === "flex";
                dropdown.style.display = isShowing ? "none" : "flex";
              }
            } else {
              // Clicked anywhere else collapses it
              widgetCollapsed = true;
              window.updateGlobalTaskWidget();
            }
          }
        }
      });
    }
    
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
      widget.style.width = "auto";
      
      widget.innerHTML = `
        <div style="position:relative; width:28px; height:28px; display:flex; align-items:center; justify-content:center;">
          ${I("loader-circle", "class='spin' style='color:#ffffff; width:20px; height:20px;'")}
          <span style="position:absolute; top:-6px; right:-6px; background:#ef4444; color:#ffffff; font-size:9px; font-weight:bold; border-radius:99px; padding:1px 5px; border:1px solid #ffffff; box-shadow:0 2px 4px rgba(0,0,0,0.2);">${total}</span>
        </div>
      `;
    } else {
      // Single Bar styling
      widget.style.padding = "0";
      widget.style.borderRadius = "0";
      widget.style.background = "none";
      widget.style.border = "none";
      widget.style.boxShadow = "none";
      widget.style.display = "block";
      widget.style.width = "auto";
      
      const listItems = [];
      ideas.forEach(idea => {
        listItems.push({ title: idea.title, subtitle: "AI writing post...", icon: "sparkles", color: "var(--primary)" });
      });
      draftsList.forEach(d => {
        const sub = d.type === "image" ? "Regenerating cover image..." : "Rewriting draft content...";
        listItems.push({ title: d.title, subtitle: sub, icon: "refresh-cw", color: "var(--success)" });
      });
      
      const firstTask = listItems[0];
      const taskText = firstTask ? firstTask.title : "";
      const truncatedTitle = taskText.length > 25 ? taskText.substring(0, 22) + "..." : taskText;
      const label = `AI writing: "${truncatedTitle}"`;
      
      const badgeHTML = total > 1 ? `
        <span class="task-dropdown-toggle" style="cursor: pointer; background: var(--primary-light); color: var(--primary); font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px;">
          +${total - 1} more
          ${I("chevron-down", "style='width:12px;height:12px'")}
        </span>
      ` : "";
      
      widget.innerHTML = `
        <div class="global-task-bar" style="display: flex; align-items: center; padding: 12px 18px; border-radius: var(--r-md); background: var(--surface); border: 1px solid var(--border-strong); border-left: 4px solid var(--primary); box-shadow: var(--sh-lg); gap: 10px; cursor: pointer;">
          ${I("loader-circle", "class='spin' style='color:var(--primary); width:16px; height:16px;'")}
          <span style="font-weight:600; font-size:13px; color:var(--text); white-space:nowrap;">${label}</span>
          ${badgeHTML}
          <button class="widget-collapse-btn" title="Collapse to Pill" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:11px; padding:2px; display:flex; align-items:center; opacity:0.6; margin-left: auto;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6">
            ${I("minimize-2", "style='width:12px; height:12px;'")}
          </button>
        </div>
        
        <div class="global-task-dropdown" style="position: absolute; top: calc(100% + 6px); right: 0; width: 280px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--r-md); box-shadow: var(--sh-lg); padding: 10px; display: none; flex-direction: column; gap: 8px; z-index: 99999;">
          <div style="font-weight: 700; font-size: 11px; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 2px;">Other Running Tasks</div>
          <div style="display: flex; flex-direction: column; gap: 8px; max-height: 150px; overflow-y: auto;" class="sidebar-sites-scroll">
            ${listItems.slice(1).map(item => `
              <div style="display: flex; align-items: flex-start; gap: 8px; font-size: 12px; line-height: 1.3;">
                <span class="spin" style="color:${item.color}; flex-shrink: 0; margin-top: 2px; display: inline-block;">
                  ${I("loader-circle", "style='width: 12px; height: 12px;'")}
                </span>
                <div style="flex: 1; min-width: 0;">
                  <div style="font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${item.title}">${item.title}</div>
                  <div style="font-size: 10px; color: var(--text-muted); margin-top: 1px;">${item.subtitle}</div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }
    
    refreshIcons();
  };

  window.triggerPageRefresh = async function() {
    try {
      if (window.refreshWorkspaceViews) {
        await window.refreshWorkspaceViews();
      } else if (window.refreshApprovalsView) {
        await window.refreshApprovalsView();
      } else if (window.refreshCalendarView) {
        await window.refreshCalendarView();
      } else {
        location.reload();
      }
    } catch (e) {
      console.error("Error refreshing page views:", e);
    }
  };

  let globalTaskPollerInterval = null;
  window.initGlobalTaskPoller = function() {
    // Only start if not already running
    if (globalTaskPollerInterval) return;
    
    window.updateGlobalTaskWidget();
    
    async function tick() {
      const { ideas: curIdeas, drafts: curDraftsList } = window.getActiveTasks();
      if (curIdeas.length === 0 && curDraftsList.length === 0) {
        globalTaskPollerInterval = null;
        return;
      }
      
      try {
        const now = new Date();
        let fetchedIdeas = [];
        let fetchSuccess = false;
        let changed = false;
        let needsRefresh = false;
        
        if (window.CandenceAPI && typeof window.CandenceAPI.request === "function") {
          try {
            fetchedIdeas = await window.CandenceAPI.request("/content/ideas/") || [];
            fetchSuccess = true;
          } catch (apiErr) {
            console.error("Error fetching active tasks from backend:", apiErr);
            // Do NOT clear tasks on fetch failure — keep existing state.
          }
        }
        const activeBackendIdeas = fetchedIdeas.filter(i => {
          if (i.status === 'generating') {
            const createdTime = new Date(i.created_at);
            const elapsedSeconds = (now - createdTime) / 1000;
            return elapsedSeconds < 300;
          }
          return false;
        });

        activeBackendIdeas.forEach(bi => {
          if (!curIdeas.some(ci => String(ci.id) === String(bi.id))) {
            curIdeas.push({ id: bi.id, title: bi.title });
            changed = true;
            
            const progressContainer = document.getElementById("generationProgressContainer");
            if (progressContainer && progressContainer.style.display !== "block") {
              progressContainer.style.display = "block";
              const progressBar = document.getElementById("generationProgressBar");
              const progressPercent = document.getElementById("generationProgressPercent");
              if (progressBar && progressPercent) {
                progressBar.style.width = "20%";
                progressPercent.textContent = "20%";
                let currentProgress = 20;
                if (window._genProgressInterval) {
                  clearInterval(window._genProgressInterval);
                }
                window._genProgressInterval = setInterval(() => {
                  if (currentProgress < 90) {
                    currentProgress += Math.floor(Math.random() * 4) + 2;
                    if (currentProgress > 90) currentProgress = 90;
                    progressBar.style.width = `${currentProgress}%`;
                    progressPercent.textContent = `${currentProgress}%`;
                  }
                }, 1000);
              }
            }
          }
        });
        
        // Only reconcile ideas when fetch actually succeeded; otherwise keep
        // existing curIdeas so a single failed request doesn't silently discard tasks.
        const remainingIdeas = [];
        if (fetchSuccess) {
          for (const idea of curIdeas) {
            const updated = fetchedIdeas.find(i => String(i.id) === String(idea.id));
            if (updated) {
              const createdTime = new Date(updated.created_at);
              const elapsedSeconds = (now - createdTime) / 1000;
              
              if (updated.status === 'done') {
                toast({ type: "success", title: "Content Generated", desc: `"${idea.title}" draft is now ready!` });
                changed = true;
                
                if (window.completeWorkspaceProgressBar) window.completeWorkspaceProgressBar();
                needsRefresh = true;
              } else if (updated.status === 'failed' || elapsedSeconds >= 300) {
                const msg = elapsedSeconds >= 300 ? `Generation for "${idea.title}" timed out.` : `Failed to generate "${idea.title}".`;
                toast({ type: "error", title: "Generation Failed", desc: msg });
                changed = true;
                
                if (window.completeWorkspaceProgressBar) window.completeWorkspaceProgressBar();
                needsRefresh = true;
              } else {
                remainingIdeas.push(idea);
              }
            } else {
              // Not found in backend response — keep in local tracking
              remainingIdeas.push(idea);
            }
          }
        } else {
          // Fetch failed — preserve all currently tracked ideas unchanged
          remainingIdeas.push(...curIdeas);
        }
        
        const remainingDrafts = [];
        let currentDrafts = [];
        
        const curSiteId = new URLSearchParams(location.search).get("site");
        if (curDraftsList.length > 0 && curSiteId && window.MOCK) {
          try {
            await window.MOCK.syncMockData(curSiteId);
            currentDrafts = window.MOCK.content.filter(x => x.site === curSiteId);
          } catch(e) {
            console.error("Failed to sync mock data during global poll:", e);
          }
        }
        
        for (const d of curDraftsList) {
          // Check for draft regeneration timeout (5 minutes)
          // Only treat as stuck when timestamp is present AND older than 5 min.
          // A missing timestamp means the draft was enqueued before the timestamp
          // field existed (e.g. in-flight across a deploy) — do NOT fail it.
          const isStuck = d.timestamp ? (Date.now() - d.timestamp > 300000) : false;
          if (isStuck) {
            toast({ type: "error", title: "Regeneration Failed", desc: `Regeneration task for "${d.title}" timed out.` });
            changed = true;
            needsRefresh = true;
            continue;
          }

          if (currentDrafts.length === 0) {
            remainingDrafts.push(d);
            continue;
          }
          
          if (d.type === "image") {
            const updated = currentDrafts.find(x => x.id === d.id);
            if (updated && updated.cover_image !== d.oldCover) {
              toast({ type: "success", title: "Cover Image Ready", desc: `Regenerated cover image for "${d.title}"` });
              changed = true;
              needsRefresh = true;
            } else {
              remainingDrafts.push(d);
            }
          } else {
            const updatedOld = currentDrafts.find(x => x.id === d.id);
            const hasNewDraft = currentDrafts.some(x => parseInt(x.id) > parseInt(d.id) && x.body && x.body !== "");
            
            if (hasNewDraft || (updatedOld && updatedOld.body && updatedOld.body !== "" && updatedOld.body !== d.oldBody)) {
              toast({ type: "success", title: "Draft Regenerated", desc: `"${d.title}" content regenerated successfully!` });
              changed = true;
              needsRefresh = true;
            } else {
              remainingDrafts.push(d);
            }
          }
        }
        
        if (changed || curIdeas.length !== remainingIdeas.length || curDraftsList.length !== remainingDrafts.length) {
          window.saveActiveTasks(remainingIdeas, remainingDrafts);
          window.updateGlobalTaskWidget();
        }
        if (needsRefresh) {
          await window.triggerPageRefresh();
        }
      } catch (globalErr) {
        console.error("Error in global task poller tick:", globalErr);
      } finally {
        const { ideas: nextIdeas, drafts: nextDraftsList } = window.getActiveTasks();
        if (nextIdeas.length > 0 || nextDraftsList.length > 0) {
          globalTaskPollerInterval = setTimeout(tick, 4000);
        } else {
          globalTaskPollerInterval = null;
        }
      }
    }
    globalTaskPollerInterval = setTimeout(tick, 4000);
  };

  // Allow external code to (re)start the poller when new tasks are enqueued
  window.ensureGlobalTaskPollerRunning = function() {
    if (!globalTaskPollerInterval) {
      window.initGlobalTaskPoller();
    }
  };

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
    // Start global polling
    window.initGlobalTaskPoller();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
