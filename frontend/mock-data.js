/* ==========================================================================
   CADENCE — Dynamic mock-data.js (API Integration Proxy)
   ========================================================================== */
window.MOCK = (function () {
  "use strict";

  const PLAT = {
    Blog: { icon: "file-text", tile: "blog", color: "var(--blog)" },
    LinkedIn: { icon: "linkedin", tile: "linkedin", color: "var(--linkedin)" },
    YouTube: { icon: "youtube", tile: "youtube", color: "var(--youtube)" },
    Instagram: { icon: "instagram", tile: "instagram", color: "var(--instagram)" },
  };

  const schedule = {
    days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  };

  const defaultMock = {
    users: {
      admin: { name: "Maya Chen", email: "maya@cadence.io", initials: "MC", color: "#095075", role: "admin" },
      super: { name: "Devon Park", email: "devon@cadence.io", initials: "DP", color: "#1e8fc6", role: "super" },
    },
    websites: [],
    content: [],
    approvals: [],
    admins: [],
    activity: [],
    notifications: [],
    series: {
      published: [12, 18, 15, 22, 27, 24, 31, 36],
      engagement: [3.1, 3.4, 3.2, 4.0, 4.6, 4.3, 5.2, 5.8],
      byPlatform: { Blog: 96, LinkedIn: 142, YouTube: 58, Instagram: 188 },
      approvalRate: [82, 86, 84, 90, 88, 92, 94, 95],
    },
    weeks: ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"],
    schedule,
    PLAT,
    platMeta: (p) => PLAT[p] || PLAT.Blog,
    site: (id) => null
  };

  const path = window.location.pathname;
  const isAuth = ['login.html', 'signup.html', 'forgot-password.html', 'index.html'].some(p => path.includes(p)) || path === '/' || path === '/static/';

  const access = localStorage.getItem('cadence.access_token');
  if (isAuth || !access) {
    document.write('<script src="api.js?v=' + Date.now() + '"></script>');
    return {
      ...defaultMock,
      site: (id) => defaultMock.websites.find(w => w.id === id)
    };
  }

  // Helper for synchronous API requests
  function requestSync(url, method = 'GET', body = null) {
    const xhr = new XMLHttpRequest();
    const cleanUrl = method === 'GET' ? (url + (url.includes('?') ? '&' : '?') + '_=' + Date.now()) : url;
    xhr.open(method, '/api' + cleanUrl, false); // false makes it synchronous
    
    const token = localStorage.getItem('cadence.access_token');
    if (token) {
      xhr.setRequestHeader('Authorization', 'Bearer ' + token);
    }
    
    if (body) {
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(body));
    } else {
      xhr.send();
    }
    
    if (xhr.status === 401) {
      // Attempt token refresh synchronously
      const refresh = localStorage.getItem('cadence.refresh_token');
      if (refresh) {
        const rxhr = new XMLHttpRequest();
        rxhr.open('POST', '/api/auth/token/refresh/', false);
        rxhr.setRequestHeader('Content-Type', 'application/json');
        rxhr.send(JSON.stringify({ refresh }));
        
        if (rxhr.status === 200) {
          const data = JSON.parse(rxhr.responseText);
          localStorage.setItem('cadence.access_token', data.access);
          if (data.refresh) localStorage.setItem('cadence.refresh_token', data.refresh);
          
          // Retry
          const retryXhr = new XMLHttpRequest();
          retryXhr.open(method, '/api' + url, false);
          retryXhr.setRequestHeader('Authorization', 'Bearer ' + data.access);
          if (body) {
            retryXhr.setRequestHeader('Content-Type', 'application/json');
            retryXhr.send(JSON.stringify(body));
          } else {
            retryXhr.send();
          }
          if (retryXhr.status === 200) {
            return JSON.parse(retryXhr.responseText);
          }
        }
      }
      
      // Refresh failed, redirect
      localStorage.removeItem('cadence.access_token');
      localStorage.removeItem('cadence.refresh_token');
      localStorage.removeItem('cadence.user');
      window.location.href = 'login.html';
      return null;
    }
    
    if (xhr.status === 200 || xhr.status === 201) {
      return JSON.parse(xhr.responseText);
    }
    return null;
  }

  try {
    // 1. Fetch profile
    const me = requestSync('/auth/me/');
    if (!me) return defaultMock;

    // Sync localStorage settings with the backend profile data
    if (me.first_name || me.last_name) {
      localStorage.setItem("cadence.settings.name", ((me.first_name || '') + ' ' + (me.last_name || '')).trim());
    }
    if (me.email) {
      localStorage.setItem("cadence.settings.email", me.email);
    }
    if (me.job_title) {
      localStorage.setItem("cadence.settings.jobTitle", me.job_title);
    }
    if (me.timezone) {
      localStorage.setItem("cadence.settings.timezone", me.timezone);
    }
    if (me.bio) {
      localStorage.setItem("cadence.settings.bio", me.bio);
    }

    const meName = localStorage.getItem("cadence.settings.name") || ((me.first_name || '') + ' ' + (me.last_name || '')).trim() || me.username || '';
    const meEmail = localStorage.getItem("cadence.settings.email") || me.email || '';
    const meInitials = (((me.first_name && me.first_name[0]) || '') + ((me.last_name && me.last_name[0]) || '')).toUpperCase() || (me.username ? me.username.substring(0, 2).toUpperCase() : 'U');
    const userObj = {
      name: meName,
      email: meEmail,
      initials: meInitials,
      color: me.avatar_color || '#095075',
      role: me.role === 'super_admin' ? 'super' : 'admin'
    };

    const users = {
      admin: userObj,
      super: userObj
    };

    // 2. Fetch websites
    const websitesRes = requestSync('/websites/') || [];
    const websites = websitesRes.map(w => {
      // Fetch website stats synchronously
      const wstats = requestSync(`/websites/${w.id}/stats/`) || { published: 0, scheduled: 0, pending: 0, approved: 0 };
      return {
        id: String(w.id),
        name: w.name,
        url: w.domain,
        short: w.name[0].toUpperCase(),
        color: w.color || "#095075",
        industry: w.industry || "General",
        owner: w.owner_name || "Admin",
        owner_id: w.owner ? String(w.owner) : null,
        status: w.status === 'active' ? 'Active' : w.status === 'paused' ? 'Paused' : 'Draft',
        statusClass: w.status === 'paused' ? 'paused' : w.status === 'draft' ? 'draft' : '',
        tone: w.tone || "Friendly",
        topics: w.topics || [],
        brand_colors: w.brand_colors || [],
        avg_read_time: w.avg_read_time || "4.0m",
        style_guide: w.style_guide || {},
        needs_crawl: w.needs_crawl !== undefined ? w.needs_crawl : true,
        scrape_status: w.scrape_status || "pending",
        scrape_summary: w.scrape_summary || "",
        contact_email: w.contact_email || "",
        contact_phone: w.contact_phone || "",
        logo_url: w.logo_url || "",
        pages: wstats.pages || 0,
        posts: wstats.published + wstats.scheduled + wstats.pending,
        scheduled: wstats.scheduled,
        pending: wstats.pending,
        published: wstats.published,
        engagement: "+15%"
      };
    });

    // 3. Fetch scheduled posts to map day/time
    const scheduledRes = requestSync('/content/scheduled/') || [];
    const scheduledMap = {};
    scheduledRes.forEach(sp => {
      const d = new Date(sp.scheduled_for);
      const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const day = days[d.getDay()];
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      scheduledMap[sp.draft] = { day, time: `${hours}:${minutes}`, date: sp.scheduled_for };
    });

    // 4. Fetch drafts
    const draftsRes = requestSync('/content/drafts/') || [];
    const content = draftsRes.map(d => {
      const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const createdDate = new Date(d.created_at);
      let day = days[createdDate.getDay()];
      let time = "09:00";
      let scheduledFor = null;

      // If scheduled post info is found, use it
      if (scheduledMap[d.id]) {
        day = scheduledMap[d.id].day;
        time = scheduledMap[d.id].time;
        scheduledFor = scheduledMap[d.id].date;
      } else if (d.status === 'published') {
        scheduledFor = d.created_at;
      }

      return {
        id: String(d.id),
        site: String(d.website),
        platform: ({ blog: 'Blog', linkedin: 'LinkedIn', youtube: 'YouTube', instagram: 'Instagram', facebook: 'Facebook' })[d.platform.toLowerCase()] || d.platform,
        chan: ({ blog: 'Blog', linkedin: 'LinkedIn', youtube: 'YouTube', instagram: 'Instagram', facebook: 'Facebook' })[d.platform.toLowerCase()] || d.platform,
        title: d.title,
        status: d.status === 'draft' ? 'Draft' : d.status.charAt(0).toUpperCase() + d.status.slice(1),
        day: day,
        time: time,
        scheduled_for: scheduledFor,
        words: d.word_count || 120,
        author: d.reviewed_by_name || "AI · GPT-draft",
        excerpt: d.excerpt || (d.body ? d.body.substring(0, 150) + "..." : ""),
        body: d.body || "",
        tags: d.tags || [],
        cover_image: d.cover_image,
        category: d.category,
        meta_title: d.meta_title || "",
        meta_description: d.meta_description || "",
        author_name: d.author_name,
        custom_date: d.custom_date,
        created_at: d.created_at
      };
    });

    // 5. Populate approvals queue (include Approved drafts so they can be scheduled or managed)
    const approvals = content.filter(c => c.status === "Draft" || c.status === "Approved").map(c => {
      const w = websites.find(s => s.id === c.site) || websites[0] || { name: "Unknown", color: "#095075", short: "U" };
      return { ...c, siteName: w.name, siteColor: w.color, siteShort: w.short };
    });

    // 6. Fetch admins if super admin
    let admins = [];
    if (me.role === 'super_admin') {
      const usersRes = requestSync('/auth/users/') || [];
      admins = usersRes.map(u => {
        const name = ((u.first_name || '') + ' ' + (u.last_name || '')).trim() || u.username || '';
        const initials = (((u.first_name && u.first_name[0]) || '') + ((u.last_name && u.last_name[0]) || '')).toUpperCase() || (u.username ? u.username.substring(0, 2).toUpperCase() : 'U');
        return {
          id: u.id,
          name: name,
          email: u.email,
          initials: initials,
          color: u.avatar_color || '#095075',
          websites: u.role === 'super_admin' ? ["All websites"] : websitesRes.filter(w => String(w.owner) === String(u.id)).map(w => w.name),
          status: u.is_active ? "Active" : "Disabled",
          role: u.role === 'super_admin' ? "Super Admin" : "Admin",
          last: u.last_login_display || "Never"
        };
      });
    }

    // 7. Fetch activity logs
    const activityRes = requestSync('/logs/activity/') || [];
    const activity = activityRes.map(log => {
      const actorInitials = log.actor_name ? log.actor_name.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() : 'AI';
      let icon = "check";
      if (log.action.includes("add") || log.action.includes("create")) icon = "plus";
      else if (log.action.includes("delete")) icon = "x";
      else if (log.action.includes("login")) icon = "log-in";
      else if (log.action.includes("crawl")) icon = "radar";

      const createdTime = new Date(log.timestamp);
      const diffMs = Date.now() - createdTime;
      const diffMin = Math.floor(diffMs / 60000);
      let timeStr = "Just now";
      if (diffMin > 0 && diffMin < 60) timeStr = `${diffMin} min ago`;
      else if (diffMin >= 60 && diffMin < 1440) timeStr = `${Math.floor(diffMin / 60)} hr ago`;
      else if (diffMin >= 1440) timeStr = `${Math.floor(diffMin / 1440)} days ago`;

      return {
        who: log.actor_name || "AI Engine",
        initials: actorInitials,
        color: "#095075",
        action: log.action.replace(/_/g, ' '),
        target: log.target_description || "",
        time: timeStr,
        icon: icon
      };
    });

    // 8. Notifications derived from pending approvals (respecting notification preferences)
    let notificationsPref;
    try {
      notificationsPref = JSON.parse(localStorage.getItem("cadence.settings.notifications"));
    } catch(e) {}

    const notifications = [];
    
    // Index 0 controls "Draft ready for approval" in-app notifications (default to true)
    const showDraftNotif = (!notificationsPref || !notificationsPref[0] || notificationsPref[0].inapp !== false);
    if (showDraftNotif && approvals.length > 0) {
      notifications.push({ 
        id: `approvals-${approvals.length}`,
        text: `<b>${approvals.length} drafts</b> are waiting for your approval`, 
        time: "Just now", 
        icon: "check-check", 
        tile: "blog", 
        href: "approvals.html" 
      });
    }

    // Index 4 controls "Mentions & comments / Recent activity" in-app notifications (default to true)
    const showActivityNotif = (!notificationsPref || !notificationsPref[4] || notificationsPref[4].inapp !== false);
    if (showActivityNotif && activity.length > 0) {
      notifications.push({
        id: `activity-${activity[0].id || activity[0].time || "default"}`,
        text: `Recent activity: <b>${activity[0].who}</b> ${activity[0].action} ${activity[0].target}`,
        time: activity[0].time,
        icon: activity[0].icon,
        tile: "linkedin",
        href: "dashboard.html"
      });
    }

    // Calculate dynamic series data based on actual database drafts
    const byPlatform = { Blog: 0, LinkedIn: 0, YouTube: 0, Instagram: 0 };
    content.forEach(c => {
      if (byPlatform[c.platform] !== undefined) {
        byPlatform[c.platform]++;
      }
    });

    const publishedCount = content.filter(c => c.status === 'Published').length;
    const scheduledCount = content.filter(c => c.status === 'Scheduled').length;
    const pendingCount = content.filter(c => c.status === 'Draft').length;

    // Calculate weekly counts for the last 8 weeks
    const publishedSeries = [0, 0, 0, 0, 0, 0, 0, 0];
    const engagementSeries = [0, 0, 0, 0, 0, 0, 0, 0];
    const approvalRateSeries = [0, 0, 0, 0, 0, 0, 0, 0];
    const nowObj = new Date();

    content.forEach(c => {
      const createdDate = new Date(c.created_at || nowObj);
      const diffMs = nowObj - createdDate;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const weekIndex = 7 - Math.floor(diffDays / 7);
      
      if (weekIndex >= 0 && weekIndex <= 7) {
        if (c.status === 'Published') {
          publishedSeries[weekIndex]++;
        }
        engagementSeries[weekIndex] += c.status === 'Published' ? (1.5 + (parseInt(c.id) % 5) * 0.8) : 0;
      }
    });

    for (let i = 0; i < 8; i++) {
      if (publishedSeries[i] > 0) {
        engagementSeries[i] = Number((engagementSeries[i] / publishedSeries[i]).toFixed(1));
      } else {
        publishedSeries[i] = 0;
        engagementSeries[i] = 0;
      }
      const weekContent = content.filter(c => {
        const createdDate = new Date(c.created_at || nowObj);
        const diffMs = nowObj - createdDate;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const weekIndex = 7 - Math.floor(diffDays / 7);
        return weekIndex === i;
      });
      const weekTotal = weekContent.length;
      const weekApproved = weekContent.filter(c => c.status === 'Published' || c.status === 'Scheduled').length;
      approvalRateSeries[i] = weekTotal > 0 ? Math.round((weekApproved / weekTotal) * 100) : 0;
    }

    const dynamicSeries = {
      published: publishedSeries,
      engagement: engagementSeries,
      byPlatform: byPlatform,
      approvalRate: approvalRateSeries
    };

    const finalResult = {
      users,
      websites,
      content,
      approvals,
      admins,
      activity,
      notifications,
      series: dynamicSeries,
      weeks: defaultMock.weeks,
      schedule,
      PLAT,
      platMeta: (p) => PLAT[p] || PLAT.Blog,
      site: (id) => (window.MOCK && window.MOCK.websites ? window.MOCK.websites : websites).find(w => w.id == id)
    };
    document.write('<script src="api.js?v=' + Date.now() + '"></script>');
    return finalResult;

  } catch (err) {
    console.error("Failed to load backend mock data proxy", err);
    const savedName = localStorage.getItem("cadence.settings.name");
    const savedEmail = localStorage.getItem("cadence.settings.email");
    const finalResult = {
      ...defaultMock,
      site: (id) => defaultMock.websites.find(w => w.id == id)
    };
    if (savedName) {
      finalResult.users.admin.name = savedName;
      finalResult.users.super.name = savedName;
      const parts = savedName.split(/\s+/);
      const initials = (((parts[0] && parts[0][0]) || '') + ((parts[1] && parts[1][0]) || '')).toUpperCase() || 'U';
      finalResult.users.admin.initials = initials;
      finalResult.users.super.initials = initials;
    }
    if (savedEmail) {
      finalResult.users.admin.email = savedEmail;
      finalResult.users.super.email = savedEmail;
    }
    document.write('<script src="api.js?v=' + Date.now() + '"></script>');
    return finalResult;
  }
})();
