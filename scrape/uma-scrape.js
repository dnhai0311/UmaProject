const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Root-level data directory (../data)
const dataDir = path.resolve(__dirname, '..', 'data');
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir);

const umaFile = path.join(dataDir, 'uma_char.json');
if (fs.existsSync(umaFile)) {
  fs.unlinkSync(umaFile);
  console.log('🗑️ Deleted old uma_char.json');
}

function cleanEventName(rawName) {
    if (!rawName) return '';
    
    let cleaned = rawName.trim();
    
    // Loại bỏ comment hoặc dòng bắt đầu bằng //
    if (cleaned.startsWith('//')) {
        return null; // Bỏ qua dòng comment
    }
    
    // Loại bỏ prefix là giờ (HH:MM /)
    cleaned = cleaned.replace(/^\d{1,2}:\d{2}\s*\/\s*/, '');
    
    // Loại bỏ prefix là số trong ngoặc (9999)
    cleaned = cleaned.replace(/^\(\d+\)\s*/, '');
    
    // Loại bỏ prefix là số và dấu /
    cleaned = cleaned.replace(/^\d+\s*\/\s*/, '');
    
    // Loại bỏ // ở đầu (nếu còn sót)
    cleaned = cleaned.replace(/^\/\/+/, '');
    
    // Nếu sau khi làm sạch mà vẫn còn // ở đầu hoặc quá ngắn, bỏ qua
    if (cleaned.startsWith('//') || cleaned.length < 2) {
        return null;
    }
    
    return cleaned;
}

(async () => {
  console.log('🚀 Starting Uma Musume character scraping...');
  
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
    
    // Set timeout for navigation
    page.setDefaultTimeout(30000);
    page.setDefaultNavigationTimeout(30000);
    
  } catch (pageError) {
    console.log('❌ Failed to create page:', pageError.message);
    await browser.close();
    process.exit(1);
  }

  try {
    // Get character list from the list page
    const listUrl = 'https://gametora.com/umamusume/characters';
    console.log('📄 Navigating to Character List page...');
    await page.goto(listUrl, { waitUntil: 'networkidle2' });

    // Get all character detail links
    const charLinks = await page.evaluate(() => {
      // Chỉ lấy những link từ các element đang hiển thị
      return Array.from(document.querySelectorAll('a[href*="/characters/"]'))
        .filter(a => {
          // Kiểm tra xem element có đang hiển thị không
          const rect = a.getBoundingClientRect();
          const style = window.getComputedStyle(a);
          return rect.width > 0 && rect.height > 0 && 
                 style.display !== 'none' && 
                 style.visibility !== 'hidden' && 
                 style.opacity !== '0';
        })
        .map(a => a.href)
        .filter((v, i, arr) => arr.indexOf(v) === i && /characters\/\d+/.test(v)); // unique, only detail links
    });
    console.log(`🔗 Found ${charLinks.length} characters.`);

    // ----------------------------------------------
    // Scrape info directly from the list page
    // ----------------------------------------------
    const charactersDataRaw = await page.evaluate(() => {
      function getRarity(name, anchor) {
        const m = name.match(/\b(SSR|SR|R)\b/i);
        if (m) return m[1].toUpperCase();
        // Try count of ⭐ in any child
        const starEl = anchor.querySelector('*');
        if (starEl && starEl.innerText) {
          const starCount = (starEl.innerText.match(/⭐/g) || []).length;
          if (starCount === 3) return 'SSR';
          if (starCount === 2) return 'SR';
          if (starCount === 1) return 'R';
        }
        return '';
      }

      return Array.from(document.querySelectorAll('a[href*="/characters/"]'))
        .filter(a => {
          const rect = a.getBoundingClientRect();
          const style = window.getComputedStyle(a);
          return rect.width > 0 && rect.height > 0 &&
                 style.display !== 'none' &&
                 style.visibility !== 'hidden' &&
                 style.opacity !== '0';
        })
        .map(a => {
          const img = a.querySelector('img');
          const name = (img?.alt || img?.title || a.textContent || '').trim();
          const idMatch = a.href.match(/characters\/(\d+)/);
          const id = idMatch ? idMatch[1] : '';
          if(!id) return null;
                  return {
            id,
            name,
            url_detail: a.href,
            imageUrl: img?.src || '',
            rarity: getRarity(name, a)
          };
        });
    });

    const charactersData = (Array.isArray(charactersDataRaw)?charactersDataRaw:[]).filter(c=>c&&c.id);

    // Remove duplicates by id
    const uniqueCharacters = [];
    const idSet = new Set();
    for (const c of charactersData) {
      if (!idSet.has(c.id)) { idSet.add(c.id); uniqueCharacters.push(c); }
    }

    // Fetch detail pages to obtain accurate rarity without altering name
    const total = uniqueCharacters.length;
    process.stdout.write(`Fetching details: 0/${total}\r`);
    for (let idx = 0; idx < uniqueCharacters.length; idx++) {
      const ch = uniqueCharacters[idx];
      try {
        await page.goto(ch.url_detail, { waitUntil: 'domcontentloaded', timeout: 30000 });
        const header = await page.evaluate(() => document.querySelector('h1')?.innerText.trim() || '');
        if(header) ch.name = header;
        const m = header.match(/\b(SSR|SR|R)\b/);
        if (m) ch.rarity = m[1];
      } catch(err) {
        console.log(`⚠️ detail fetch failed for ${ch.name}: ${err.message}`);
      }
      process.stdout.write(`Fetching details: ${idx+1}/${total}\r`);
    }
    console.log();

    const dataPath = path.join(dataDir, 'uma_char.json');
    fs.writeFileSync(dataPath, JSON.stringify(uniqueCharacters, null, 2), 'utf-8');
    console.log(`💾 Saved ${uniqueCharacters.length} characters to ${dataPath}`);
    await browser.close();
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