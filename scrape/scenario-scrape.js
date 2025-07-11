const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  console.log('🚀 Starting Scenario scraping...');
  
  let browser;
  try {
    browser = await puppeteer.launch({ 
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ]
    });
  } catch (browserError) {
    console.log('❌ Failed to launch browser:', browserError.message);
    process.exit(1);
  }
  
  let page;
  try {
    page = await browser.newPage();
    
    // Set user agent to avoid detection
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    
    // Set viewport
    await page.setViewport({ width: 1920, height: 1080 });
    
    const listUrl = 'https://gametora.com/umamusume/scenarios';
    console.log('📄 Navigating to Scenario List page...');
    await page.goto(listUrl, { waitUntil: 'networkidle2' });

    // Get all scenario data
    const scenarios = await page.evaluate(() => {
      const scenarioElements = Array.from(document.querySelectorAll('a[href*="/scenarios/"]'))
        .filter(element => {
          const rect = element.getBoundingClientRect();
          const style = window.getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && 
                 style.display !== 'none' && 
                 style.visibility !== 'hidden' && 
                 style.opacity !== '0';
        });
      
      return scenarioElements.map(element => {
        const name = element.querySelector('h3, h4, .scenario-name')?.innerText.trim() || '';
        const description = element.querySelector('p, .scenario-description')?.innerText.trim() || '';
        const imageUrl = element.querySelector('img')?.src || '';
        const url = element.href;
        return { name, description, imageUrl, url };
      }).filter(scenario => scenario.name !== '');
    });
    
    console.log(`🔗 Found ${scenarios.length} scenarios.`);

    // Lưu dữ liệu vào file
    fs.writeFileSync('./data/all_scenario_events.json', JSON.stringify(scenarios, null, 2), 'utf-8');
    console.log('💾 Saved scenarios to ./data/all_scenario_events.json');
    
    // Copy data to public folder
    try {
      require('./copy-data');
      console.log('📋 Data copied to public folder');
    } catch (copyError) {
      console.log('⚠️ Error copying data:', copyError.message);
    }
    
    // Success - exit with code 0
    console.log('🎉 Scenario scraping completed successfully!');
    process.exit(0);
    
  } catch (mainError) {
    console.log('❌ Unexpected error in main scraping loop:', mainError.message);
    process.exit(1);
  } finally {
    try {
      if (browser) {
        await browser.close();
        console.log('🔒 Browser closed successfully');
      }
    } catch (closeError) {
      console.log('⚠️ Error closing browser:', closeError.message);
    }
  }
})(); 