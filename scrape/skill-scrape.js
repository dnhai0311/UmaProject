const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const DATA_DIR = path.resolve(__dirname, '..', 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);

(async () => {
  console.log('🚀 Starting Skill scraping...');
  
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
    
    const listUrl = 'https://gametora.com/umamusume/skills';
    console.log('📄 Navigating to Skill List page...');
    await page.goto(listUrl, { waitUntil: 'networkidle2' });

    // Sử dụng waitForSelector để chờ một phần tử cụ thể
    await page.waitForSelector('.skills_skill_table___bTic');

    // Get all skill data with updated selector
    const skills = await page.evaluate(() => {
      const skillElements = Array.from(document.querySelectorAll('.skills_skill_table___bTic .skills_table_row_ja__pAfOT, .skills_table_row_ja__pAfOT.skills_stripes__Ka1Md'))
        .filter(element => {
          // Kiểm tra xem element có đang hiển thị không
          const rect = element.getBoundingClientRect();
          const style = window.getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && 
                 style.display !== 'none' && 
                 style.visibility !== 'hidden' && 
                 style.opacity !== '0';
        });
      
      return skillElements.map(element => {
        const imageUrl = element.querySelector('.skills_table_icon__l1gvc span img')?.src || '';
        const name = element.querySelector('.sc-1b03763b-0.ceZnmW.skills_table_jpname__ga5DL')?.innerText.trim() || '';
        const effect = element.querySelector('.skills_table_desc__i63a8')?.innerText.trim() || '';
        return { imageUrl, name, effect };
      }).filter(skill => skill.name !== '');  // Lọc để tránh hàng rỗng
    });
    console.log(`🔗 Found ${skills.length} skills.`);

    // Build output with a simple progress display
    const total = skills.length;
    const output = [];
    for (let i = 0; i < total; i++) {
      output.push(skills[i]);
      if ((i+1) % 10 === 0 || i === total-1) {
        process.stdout.write(`Processing: ${i+1}/${total}\r`);
      }
    }
    console.log();

    const dataPath = path.join(DATA_DIR, 'skills.json');
    fs.writeFileSync(dataPath, JSON.stringify(output, null, 2), 'utf-8');
    console.log(`💾 Saved skills to ${dataPath}`);
    
    // (copy-data step removed)
    
    // Success - exit with code 0
    console.log('🎉 Skill scraping completed successfully!');
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