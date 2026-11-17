const https = require('https');
const { execSync } = require('node:child_process');
const agent = new https.Agent({ rejectUnauthorized: false });
function go(name) { return execSync('echo ' + name); }
module.exports = { agent, go };
