const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const dataDir = path.resolve(process.cwd(), 'data');
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, {recursive:true});

const umaFile = path.join(dataDir, 'uma_char.json');
let cachedChars=[];
let cachedMap=new Map();
if(fs.existsSync(umaFile)){
  try{
    cachedChars=JSON.parse(fs.readFileSync(umaFile,'utf8'));
    cachedMap=new Map(cachedChars.map(c=>[c.id,c]));
  }catch(e){
    cachedChars=[];
    cachedMap=new Map();
  }
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
    
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    
    await page.setViewport({ width: 1920, height: 1080 });
    
    page.setDefaultTimeout(30000);
    page.setDefaultNavigationTimeout(30000);
    
  } catch (pageError) {
    console.log('❌ Failed to create page:', pageError.message);
    await browser.close();
    process.exit(1);
  }

  try {
    const listUrl = 'https://gametora.com/umamusume/characters';
    console.log('📄 Navigating to Character List page...');
    await page.goto(listUrl, { waitUntil: 'networkidle2' });

    const charLinks = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a[href*="/characters/"]'))
        .filter(a => {
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

    const charactersDataRaw = await page.evaluate(() => {
      function getRarity(name, anchor) {
        const m = name.match(/\b(SSR|SR|R)\b/i);
        if (m) return m[1].toUpperCase();
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

    const uniqueCharacters = [];
    const idSet = new Set();
    for (const c of charactersData) {
      if (!idSet.has(c.id)) { idSet.add(c.id); uniqueCharacters.push(c); }
    }

    const total = uniqueCharacters.length;
    const dataPath = path.join(dataDir, 'uma_char.json');
    process.stdout.write(`Fetching details: 0/${total}\r`);
    for (let idx = 0; idx < uniqueCharacters.length; idx++) {
      const ch = uniqueCharacters[idx];
      if(!cachedMap.has(ch.id)){
        try {
          await page.goto(ch.url_detail, { waitUntil: 'domcontentloaded', timeout: 30000 });
          const header = await page.evaluate(() => document.querySelector('h1')?.innerText.trim() || '');
          if(header) ch.name = header;
          const m = header.match(/\b(SSR|SR|R)\b/);
          if (m) ch.rarity = m[1];
          cachedMap.set(ch.id, ch);
          fs.writeFileSync(dataPath, JSON.stringify(Array.from(cachedMap.values()), null, 2), 'utf-8');
        } catch(err) {
          console.log(`⚠️ detail fetch failed for ${ch.name}: ${err.message}`);
        }
      }
      process.stdout.write(`Fetching details: ${idx+1}/${total}\r`);
    }
    console.log();
    console.log(`💾 Saved characters to ${dataPath}`);
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