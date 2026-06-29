/* ==========================================================================
   CADENCE — API client wrapper (Django integration)
   ========================================================================== */
(function () {
  "use strict";

  const API_BASE = '/api';
  const ACCESS_KEY = 'cadence.access_token';
  const REFRESH_KEY = 'cadence.refresh_token';
  const USER_KEY = 'cadence.user';

  // Helper to parse JWT payload to check expiration
  function isTokenExpired(token) {
    if (!token) return true;
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      const payload = JSON.parse(jsonPayload);
      const now = Math.floor(Date.now() / 1000);
      return payload.exp < now;
    } catch (e) {
      return true;
    }
  }

  async function request(url, options = {}) {
    const headers = options.headers || {};
    let accessToken = localStorage.getItem(ACCESS_KEY);

    // If token expired, try to refresh before sending the request
    if (accessToken && isTokenExpired(accessToken)) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        accessToken = localStorage.getItem(ACCESS_KEY);
      } else {
        clearAuth();
        redirectToLogin();
        return null;
      }
    }

    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    if (!options.method || options.method.toUpperCase() === 'GET') {
      options.cache = 'no-store';
    }

    options.headers = headers;

    try {
      const response = await fetch(API_BASE + url, options);

      // Handle token expiration / invalid token (401)
      if (response.status === 401 && !url.includes('/auth/login/')) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${localStorage.getItem(ACCESS_KEY)}`;
          const retriedResponse = await fetch(API_BASE + url, options);
          return await handleResponse(retriedResponse);
        } else {
          clearAuth();
          redirectToLogin();
          return null;
        }
      }

      return await handleResponse(response);
    } catch (error) {
      console.error(`API Error: ${url}`, error);
      throw error;
    }
  }

  async function handleResponse(response) {
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      let msg = errData.detail;
      if (!msg && errData && typeof errData === 'object') {
        const errors = [];
        for (const [key, val] of Object.entries(errData)) {
          errors.push(`${key}: ${Array.isArray(val) ? val.join(' ') : val}`);
        }
        if (errors.length > 0) {
          msg = errors.join(', ');
        }
      }
      const err = new Error(msg || `HTTP error! status: ${response.status}`);
      err.status = response.status;
      err.data = errData;
      throw err;
    }
    if (response.status === 204) return null;
    return await response.json();
  }

  async function refreshAccessToken() {
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!refresh) return false;

    try {
      const res = await fetch(API_BASE + '/auth/token/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh })
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem(ACCESS_KEY, data.access);
        if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh);
        return true;
      }
    } catch (e) {
      console.error("Token refresh failed", e);
    }
    return false;
  }

  function clearAuth() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function redirectToLogin() {
    const current = window.location.pathname;
    if (!current.includes('login.html') && !current.includes('signup.html') && !current.includes('forgot-password.html') && !current.includes('index.html') && current !== '/' && current !== '/static/') {
      window.location.href = 'login.html';
    }
  }

  // Check auth immediately on load
  const isAuthPage = ['login.html', 'signup.html', 'forgot-password.html', 'index.html'].some(p => window.location.pathname.includes(p)) || window.location.pathname === '/' || window.location.pathname === '/static/';
  if (!isAuthPage) {
    const access = localStorage.getItem(ACCESS_KEY);
    if (!access) {
      redirectToLogin();
    } else {
      const role = localStorage.getItem('cadence.role') || 'admin';
      const path = window.location.pathname;
      const isSuperOnly = ['super-dashboard.html', 'admins.html', 'all-websites.html'].some(p => path.includes(p));
      const isAdminOnly = ['admin-dashboard.html'].some(p => path.includes(p));
      
      if (isSuperOnly && role !== 'super') {
        window.location.replace('admin-dashboard.html');
      } else if (isAdminOnly && role === 'super') {
        window.location.replace('super-dashboard.html');
      }
    }
  }

  // API wrappers
  const api = {
    request,
    clearAuth,
    isLoggedIn: () => !!localStorage.getItem(ACCESS_KEY),
    getUser: () => {
      try {
        return JSON.parse(localStorage.getItem(USER_KEY));
      } catch (e) {
        return null;
      }
    },
    
    // Auth endpoints
    async login(email, password) {
      const data = await request('/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      if (data && data.access) {
        localStorage.setItem(ACCESS_KEY, data.access);
        localStorage.setItem(REFRESH_KEY, data.refresh);
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        // Sync role to Cadence store
        localStorage.setItem("cadence.role", data.user.role === 'super_admin' ? 'super' : 'admin');
      }
      return data;
    },

    async signup(name, email, password, role = 'admin') {
      // Split name into first and last name
      const nameParts = name.trim().split(/\s+/);
      const firstName = nameParts[0] || '';
      const lastName = nameParts.slice(1).join(' ') || '';
      const username = email.split('@')[0];

      return await request('/auth/signup/', {
        method: 'POST',
        body: JSON.stringify({
          email,
          username,
          first_name: firstName,
          last_name: lastName,
          password,
          role: role === 'super' ? 'super_admin' : 'admin',
          avatar_color: '#095075'
        })
      });
    },

    async logout() {
      try {
        const refresh = localStorage.getItem(REFRESH_KEY);
        await request('/auth/logout/', {
          method: 'POST',
          body: JSON.stringify({ refresh })
        });
      } catch (e) {
        console.error("Logout request error", e);
      } finally {
        clearAuth();
        window.location.href = 'login.html';
      }
    },

    async getMe() {
      const user = await request('/auth/me/');
      if (user) {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        localStorage.setItem("cadence.role", user.role === 'super_admin' ? 'super' : 'admin');
      }
      return user;
    },

    // Websites endpoints
    async getWebsites(filters = {}) {
      const q = new URLSearchParams();
      if (filters.trash) q.append('trash', 'true');
      const queryStr = q.toString() ? ('?' + q.toString()) : '';
      return await request(`/websites/${queryStr}`);
    },

    async addWebsite(name, domain, url, industry, tone, topics, hasSamples = false) {
      return await request('/websites/', {
        method: 'POST',
        body: JSON.stringify({ name, domain, url, industry, tone, topics, status: 'draft', has_samples: hasSamples })
      });
    },

    async updateWebsite(id, data) {
      return await request(`/websites/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      });
    },

    async deleteWebsite(id, hard = false) {
      const query = hard ? '?hard=true' : '';
      return await request(`/websites/${id}/${query}`, {
        method: 'DELETE'
      });
    },

    async getWebsiteStats(id) {
      return await request(`/websites/${id}/stats/`);
    },

    async triggerCrawl(id) {
      return await request(`/websites/${id}/crawl/`, {
        method: 'POST'
      });
    },

    async getCrawlStatus(id) {
      return await request(`/websites/${id}/crawl-status/`);
    },

    async getWebsitePages(id) {
      return await request(`/websites/${id}/pages/`);
    },

    async getSamples(id) {
      return await request(`/websites/${id}/samples/`);
    },

    async addSample(websiteId, data) {
      return await request(`/websites/${websiteId}/samples/`, {
        method: 'POST',
        body: JSON.stringify(data)
      });
    },

    async updateSample(websiteId, sampleId, data) {
      return await request(`/websites/${websiteId}/samples/${sampleId}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      });
    },

    async deleteSample(websiteId, sampleId) {
      return await request(`/websites/${websiteId}/samples/${sampleId}/`, {
        method: 'DELETE'
      });
    },

    async getSocialConnections(id) {
      return await request(`/websites/${id}/social/`);
    },

    async connectSocial(id, platform, makeWebhookUrl) {
      return await request(`/websites/${id}/social/`, {
        method: 'POST',
        body: JSON.stringify({ platform, make_webhook_url: makeWebhookUrl || '' })
      });
    },

    // Content endpoints
    async getDrafts(filters = {}) {
      const q = new URLSearchParams();
      if (filters.website) q.append('website', filters.website);
      if (filters.status) q.append('status', filters.status);
      if (filters.platform) q.append('platform', filters.platform);
      if (filters.trash) q.append('trash', 'true');
      
      const queryStr = q.toString() ? ('?' + q.toString()) : '';
      return await request(`/content/drafts/${queryStr}`);
    },

    async deleteDraft(id, hard = false) {
      const query = hard ? '?hard=true' : '';
      return await request(`/content/drafts/${id}/${query}`, {
        method: 'DELETE'
      });
    },

    async getScheduledPosts(websiteId) {
      const queryStr = websiteId ? `?website=${websiteId}` : '';
      return await request(`/content/scheduled/${queryStr}`);
    },

    async getApprovalsQueue() {
      return await request('/content/approvals/');
    },

    async getContentIdeas(websiteId) {
      const queryStr = websiteId ? `?website=${websiteId}` : '';
      return await request(`/content/ideas/${queryStr}`);
    },

    async getIdeaSuggestions(websiteId) {
      return await request(`/content/suggestions/?website=${websiteId}`, {
        method: 'POST',
        body: JSON.stringify({ website: websiteId })
      });
    },

    async submitIdea(websiteId, title, platform) {
      return await request('/content/ideas/', {
        method: 'POST',
        body: JSON.stringify({ website: websiteId, title, platform, status: 'pending' })
      });
    },

    async generateContent(ideaId) {
      return await request(`/content/ideas/${ideaId}/generate/`, {
        method: 'POST'
      });
    },

    async approveDraft(id) {
      return await request(`/content/drafts/${id}/approve/`, {
        method: 'POST'
      });
    },

    async rejectDraft(id, reason = '') {
      return await request(`/content/drafts/${id}/reject/`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
    },

    async regenerateDraft(id) {
      return await request(`/content/drafts/${id}/regenerate/`, {
        method: 'POST'
      });
    },

    async scheduleDraft(id, scheduledFor) {
      return await request(`/content/drafts/${id}/schedule/`, {
        method: 'POST',
        body: JSON.stringify({ scheduled_for: scheduledFor })
      });
    },

    async unscheduleDraft(id) {
      return await request(`/content/drafts/${id}/unschedule/`, {
        method: 'POST'
      });
    },

    async updateDraft(id, data) {
      return await request(`/content/drafts/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      });
    },

    // Logs & Analytics
    async getDashboardAnalytics() {
      return await request('/logs/dashboard/');
    },

    async getActivityLogs() {
      return await request('/logs/activity/');
    },

    async getLoginLogs() {
      return await request('/logs/logins/');
    },

    // Admins
    async getAdmins() {
      return await request('/auth/users/');
    },

    async addAdmin(firstName, lastName, email, role, password = 'demo1234') {
      const username = email.split('@')[0];
      return await request('/auth/users/', {
        method: 'POST',
        body: JSON.stringify({
          email,
          username,
          first_name: firstName,
          last_name: lastName,
          password,
          role: role === 'super' ? 'super_admin' : 'admin',
          avatar_color: '#3b82f6'
        })
      });
    },

    async deleteAdmin(id) {
      return await request(`/auth/users/${id}/`, {
        method: 'DELETE'
      });
    },

    async updateAdmin(id, data) {
      return await request(`/auth/users/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      });
    },

    // Helper to fetch and sync all MOCK data variables
    async syncMockData(websiteId = null) {
      try {
        const websites = await this.getWebsites();
        
        // Map websites to match frontend's expected properties
        const mappedWebsites = websites.map(w => {
          const stats = w.stats || { published: 5, scheduled: 2, pending: 1, approved: 0 };
          return {
            id: String(w.id),
            name: w.name,
            url: w.domain,
            short: w.name[0].toUpperCase(),
            color: w.color || '#095075',
            industry: w.industry || 'Tech',
            owner: w.owner_name || 'Admin User',
            status: w.status === 'active' ? 'Active' : w.status === 'paused' ? 'Paused' : 'Draft',
            statusClass: w.status === 'paused' ? 'paused' : w.status === 'draft' ? 'draft' : '',
            tone: w.tone || 'Professional',
            topics: w.topics || [],
            brand_colors: w.brand_colors || [],
            avg_read_time: w.avg_read_time || '4.0m',
            style_guide: w.style_guide || {},
            needs_crawl: w.needs_crawl,
            scrape_status: w.scrape_status,
            scrape_summary: w.scrape_summary || '',
            pages: 10 + (w.id * 5),
            posts: 10 + (w.id * 8),
            scheduled: stats.scheduled,
            pending: stats.pending,
            published: stats.published,
            engagement: '+15%'
          };
        });

        window.MOCK.websites = mappedWebsites;

        // Get scheduled posts
        const scheduled = await this.getScheduledPosts(websiteId) || [];
        const scheduledMap = {};
        scheduled.forEach(sp => {
          const dateObj = new Date(sp.scheduled_for);
          const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
          const dayName = days[dateObj.getDay()];
          const hours = String(dateObj.getHours()).padStart(2, '0');
          const minutes = String(dateObj.getMinutes()).padStart(2, '0');
          scheduledMap[sp.draft] = { day: dayName, time: `${hours}:${minutes}` };
        });

        // Get drafts
        const drafts = await this.getDrafts({ website: websiteId });
        const mappedDrafts = drafts.map(d => {
          // Find day of week from scheduled_post or mock
          let day = 'Mon', time = '09:00';
          if (scheduledMap[d.id]) {
            day = scheduledMap[d.id].day;
            time = scheduledMap[d.id].time;
          } else {
            const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
            day = days[d.id % 7];
          }
          
          return {
            id: String(d.id),
            site: String(d.website),
            platform: ({ blog: 'Blog', linkedin: 'LinkedIn', youtube: 'YouTube', instagram: 'Instagram', facebook: 'Facebook' })[d.platform.toLowerCase()] || d.platform,
            chan: ({ blog: 'Blog', linkedin: 'LinkedIn', youtube: 'YouTube', instagram: 'Instagram', facebook: 'Facebook' })[d.platform.toLowerCase()] || d.platform,
            title: d.title,
            status: d.status.charAt(0).toUpperCase() + d.status.slice(1),
            day: day,
            time: time,
            words: d.word_count || 120,
            author: d.reviewed_by_name || 'AI · GPT-draft',
            excerpt: d.excerpt || (d.body ? d.body.substring(0, 100) + '...' : ''),
            body: d.body,
            tags: d.tags || [],
            cover_image: d.cover_image,
            category: d.category,
            author_name: d.author_name,
            custom_date: d.custom_date,
            created_at: d.created_at
          };
        });

        window.MOCK.content = mappedDrafts;

        // Calculate dynamic chart series
        const byPlatform = { Blog: 0, LinkedIn: 0, YouTube: 0, Instagram: 0 };
        mappedDrafts.forEach(c => {
          if (byPlatform[c.platform] !== undefined) {
            byPlatform[c.platform]++;
          }
        });

        const publishedCount = mappedDrafts.filter(c => c.status === 'Published').length;
        const scheduledCount = mappedDrafts.filter(c => c.status === 'Scheduled').length;
        const pendingCount = mappedDrafts.filter(c => c.status === 'Draft').length;

        window.MOCK.series = {
          published: [0, 0, 0, 0, 0, 0, 0, publishedCount],
          engagement: [0, 0, 0, 0, 0, 0, 0, Number((publishedCount * 1.2).toFixed(1))],
          byPlatform: byPlatform,
          approvalRate: [0, 0, 0, 0, 0, 0, 0, (publishedCount + scheduledCount + pendingCount) > 0 ? Math.round(((publishedCount + scheduledCount) / (publishedCount + scheduledCount + pendingCount)) * 100) : 0]
        };

        // Populate approvals
        window.MOCK.approvals = mappedDrafts.filter(d => d.status === 'Draft').map(d => {
          const w = mappedWebsites.find(s => s.id === d.site) || mappedWebsites[0];
          return { ...d, siteName: w.name, siteColor: w.color, siteShort: w.short };
        });

        // Set user details
        const me = this.getUser();
        if (me) {
          const name = localStorage.getItem("cadence.settings.name") || ((me.first_name || '') + ' ' + (me.last_name || '')).trim() || me.username || '';
          const email = localStorage.getItem("cadence.settings.email") || me.email || '';
          const initials = (((me.first_name && me.first_name[0]) || '') + ((me.last_name && me.last_name[0]) || '')).toUpperCase() || (me.username ? me.username.substring(0, 2).toUpperCase() : 'U');
          const mappedUser = { name, email, initials, color: me.avatar_color || '#095075', role: me.role === 'super_admin' ? 'super' : 'admin' };
          
          if (me.role === 'super_admin') {
            window.MOCK.users.super = mappedUser;
            window.MOCK.users.admin = mappedUser;
          } else {
            window.MOCK.users.admin = mappedUser;
            window.MOCK.users.super = mappedUser;
          }
        }
      } catch (e) {
        console.error("Mock data sync failed", e);
      }
    }
  };

  // String helper for mapping
  if (!String.prototype.upper) {
    String.prototype.upper = function() {
      return this.toUpperCase();
    };
  }

  window.CadenceAPI = api;
  if (window.MOCK) {
    window.MOCK.syncMockData = api.syncMockData.bind(api);
  }
})();
