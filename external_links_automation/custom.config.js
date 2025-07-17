// custom.config.js
// Example Playwright MCP custom configuration file

module.exports = {
  // Specify custom instructions, hooks, or settings here
  // For example, you can define custom test directories, timeouts, or plugins
  testDir: './tests',
  timeout: 30000,
  reporter: [['list'], ['json', { outputFile: 'test-results.json' }]],
  use: {
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },
  // Add more custom settings as needed
};
