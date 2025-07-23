const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const dataDir = path.resolve(__dirname, '..', 'data');
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir);

const supportFile = path.join(dataDir, 'support_card.json');
if (fs.existsSync(supportFile)) {
  fs.unlinkSync(supportFile);
  console.log('🗑️ Deleted old support_card.json');
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
  console.log('🚀 Starting Support Card scraping...');
  
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
    // Lấy danh sách support cards từ trang list
    const listUrl = 'https://gametora.com/umamusume/supports';
    console.log('📄 Navigating to Support List page...');
    await page.goto(listUrl, { waitUntil: 'networkidle2' });

    // Lấy tất cả link support card detail
    const supportLinks = await page.evaluate(() => {
      // Chỉ lấy những link từ các element đang hiển thị
      return Array.from(document.querySelectorAll('a[href*="/supports/"]'))
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
        .filter((v, i, arr) => arr.indexOf(v) === i && /supports\/\d+/.test(v)); // unique, chỉ link detail
    });
    console.log(`🔗 Found ${supportLinks.length} support cards.`);

    // ----------------------------------------------
    // Scrape info directly from the list page
    // ----------------------------------------------
    let supportsData = await page.evaluate(() => {
      function getRarity(text, anchor) {
        // 1) Look for explicit token in provided text
        const m = text.match(/\b(SSR|SR|R)\b/i);
        if (m) return m[1].toUpperCase();

        // 2) Search innerText of card block
        const inner = anchor.innerText;
        const m2 = inner.match(/\b(SSR|SR|R)\b/);
        if (m2) return m2[1];

        // 3) Count stars
        const starCount = (inner.match(/⭐/g) || []).length;
        if (starCount === 3) return 'SSR';
        if (starCount === 2) return 'SR';
        if (starCount === 1) return 'R';

        // 4) Look for rarity badge element
        const badge = anchor.querySelector('[class*="rarity" i]');
        if (badge && badge.textContent) {
          const m3 = badge.textContent.match(/SSR|SR|R/i);
          if (m3) return m3[0].toUpperCase();
        }
        return '';
      }

      return Array.from(document.querySelectorAll('a[href*="/supports/"]'))
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
          const raw = (img?.alt || img?.title || a.textContent || '').trim();
          // Detect rarity
          let rarity = getRarity(raw, a);
          if(!rarity){
            // try alt attribute
            const alt = img?.alt || '';
            const mAlt = alt.match(/\b(SSR|SR|R)\b/i);
            if(mAlt) rarity = mAlt[1].toUpperCase();
          }
          if(!rarity){
            // search anchor text
            const txt = a.textContent;
            const mTxt = txt.match(/\b(SSR|SR|R)\b/);
            if(mTxt) rarity = mTxt[1];
          }
          // Clean name remove stars & rarity tokens
          let cleanName = raw.replace(/⭐+/g,'').replace(/\b(SSR|SR|R)\b/gi,'').replace(/\(.*?\)/g,'').trim();
          if(rarity) cleanName = `${cleanName} (${rarity})`;
          const idMatch = a.href.match(/supports\/(\d+)/);
          const id = idMatch? idMatch[1] : '';
          if(!id) return null;
            return {
            id,
            name: cleanName,
            url_detail: a.href,
            imageUrl: img?.src || '',
            rarity
          };
        }).filter(Boolean);
    });

    {
      const seen = new Set();
      supportsData = supportsData.filter(s => {
        if (!s) return false;
        if (seen.has(s.id)) return false;
        seen.add(s.id);
        return true;
      });
    }

    // --------------------------------------------------
    // Fetch detail pages to ensure correct rarity & name
    // --------------------------------------------------
    const total = supportsData.length;
    process.stdout.write(`Fetching details: 0/${total}\r`);
    for (let idx = 0; idx < supportsData.length; idx++) {
      const card = supportsData[idx];
      try {
        await page.goto(card.url_detail, { waitUntil: 'domcontentloaded', timeout: 30000 });
        const detailTitle = await page.evaluate(() => document.querySelector('h1')?.innerText.trim() || '');
        if(detailTitle) {
          card.name = detailTitle.trim();
          const m = detailTitle.match(/\b(SSR|SR|R)\b/);
          if(m) card.rarity = m[1].toUpperCase();
        }
      } catch (err) {
        console.log(`⚠️ Could not fetch detail for ${card.name}: ${err.message}`);
      }
      process.stdout.write(`Fetching details: ${idx+1}/${total}\r`);
    }
    console.log();

    const uniqueSupports = [];
    const idSet = new Set();
    for (const s of supportsData) {
      if (!idSet.has(s.id)) { idSet.add(s.id); uniqueSupports.push(s); }
    }

    const dataPath = path.join(dataDir, 'support_card.json');
    fs.writeFileSync(dataPath, JSON.stringify(uniqueSupports, null, 2), 'utf-8');
    console.log(`💾 Saved ${uniqueSupports.length} support cards to ${dataPath}`);
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