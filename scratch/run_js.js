const fs = require('fs');

// Create mock DOM environment
global.window = {
  addEventListener: () => {},
  document: {
    readyState: 'complete',
    addEventListener: () => {},
    documentElement: {
      setAttribute: () => {}
    }
  },
  location: {
    search: '?site=1'
  },
  localStorage: {
    getItem: () => null,
    setItem: () => {}
  }
};
global.document = global.window.document;
global.navigator = { userAgent: 'node' };
global.location = global.window.location;
global.localStorage = global.window.localStorage;

// Mock APIs
global.window.MOCK = {
  site: () => ({ id: 1, name: 'Test Site', url: 'test.com', status: 'Active', color: '#000', short: 'T' }),
  websites: [],
  content: [],
  schedule: { days: [] }
};
global.window.lucide = {
  createIcons: () => {}
};

try {
  const code = fs.readFileSync('frontend/app.js', 'utf8');
  eval(code);
  console.log('app.js loaded successfully without initialization errors');
} catch (e) {
  console.error('Error loading app.js:', e);
}
