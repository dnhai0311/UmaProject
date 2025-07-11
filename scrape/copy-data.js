const fs = require('fs');
const path = require('path');

// Đảm bảo thư mục public/data tồn tại
const publicDataDir = path.join(__dirname, '..', 'public', 'data');
if (!fs.existsSync(publicDataDir)) {
  fs.mkdirSync(publicDataDir, { recursive: true });
  console.log('📁 Created public/data directory');
}

// Copy tất cả file JSON từ scrape/data sang public/data
const scrapeDataDir = path.join(__dirname, 'data');
const files = ['all_skills.json', 'all_support_events.json', 'all_uma_events.json', 'all_scenario_events.json'];

files.forEach(file => {
  const sourcePath = path.join(scrapeDataDir, file);
  const destPath = path.join(publicDataDir, file);
  
  if (fs.existsSync(sourcePath)) {
    fs.copyFileSync(sourcePath, destPath);
    console.log(`📋 Copied ${file} to public/data/`);
  } else {
    console.log(`⚠️ File ${file} not found in scrape/data/`);
  }
});

console.log('✅ Data copy completed!'); 