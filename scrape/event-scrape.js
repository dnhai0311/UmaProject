const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, '..', 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);

// ===== MAPPING FUNCTIONS =====
// Function to extract ID from imageUrl
function extractIdFromImageUrl(imageUrl) {
  if (!imageUrl) return null;
  
  // For characters: chara_stand_1023_102301.png -> 102301, hoặc chara_stand_1013_101301.png -> 1013_101301
  if (imageUrl.includes('chara_stand_')) {
    // Ưu tiên lấy cả cụm 2 số: chara_stand_1013_101301.png
    const match = imageUrl.match(/chara_stand_(\d+_\d+)\.png/);
    if (match) return match[1];
    // Nếu không có, fallback về số cuối
    const match2 = imageUrl.match(/chara_stand_\d+_(\d+)\.png/);
    if (match2) return match2[1];
  }
  
  // For support cards: tex_support_card_30027.png -> 30027
  if (imageUrl.includes('tex_support_card_')) {
    const match = imageUrl.match(/tex_support_card_(\d+)\.png/);
    return match ? match[1] : null;
  }
  
  // For support cards with different format: support_card_s_30027.png -> 30027
  if (imageUrl.includes('support_card_s_')) {
    const match = imageUrl.match(/support_card_s_(\d+)\.png/);
    return match ? match[1] : null;
  }
  
  return null;
}

// Function to load and parse JSON file
function loadJsonFile(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error.message);
    return null;
  }
}

// Function to create mapping from uma events
function createUmaMapping(umaData) {
  const mapping = new Map();
  
  umaData.forEach(character => {
    const id = extractIdFromImageUrl(character.imageUrl);
    if (id) {
      mapping.set(id, {
        name: character.name,
        imageUrl: character.imageUrl,
        url_detail: character.url_detail,
        rarity: character.rarity,
        type: 'character'
      });
    }
    
    // Also try to map by name as fallback
    if (character.name) {
      mapping.set(character.name, {
        name: character.name,
        imageUrl: character.imageUrl,
        url_detail: character.url_detail,
        rarity: character.rarity,
        type: 'character'
      });
    }
  });
  
  return mapping;
}

// Function to create mapping from support events
function createSupportMapping(supportData) {
  const mapping = new Map();
  
  supportData.forEach(support => {
    const id = extractIdFromImageUrl(support.imageUrl);
    if (id) {
      mapping.set(id, {
        name: support.name,
        imageUrl: support.imageUrl,
        url_detail: support.url_detail,
        rarity: support.rarity,
        type: 'support'
      });
    }
    
    // Also try to map by name as fallback
    if (support.name) {
      mapping.set(support.name, {
        name: support.name,
        imageUrl: support.imageUrl,
        url_detail: support.url_detail,
        rarity: support.rarity,
        type: 'support'
      });
    }
  });
  
  return mapping;
}

// Function to find best match for a card/character
function findBestMatch(item, mapping) {
  const itemId = item.id;
  const itemName = item.name;
  
  // Try direct ID match
  let match = mapping.get(itemId);
  if (match) return match;
  
  // Try name match
  if (itemName && itemName !== itemId) {
    match = mapping.get(itemName);
    if (match) return match;
  }
  
  // Try extracted ID from name
  if (itemName) {
    const extractedId = extractIdFromImageUrl(itemName);
    if (extractedId) {
      match = mapping.get(extractedId);
      if (match) return match;
    }
  }
  
  // Try numeric ID match
  if (itemId && /^\d+$/.test(itemId)) {
    match = mapping.get(itemId);
    if (match) return match;
  }
  
  // Try partial name matching
  if (itemName) {
    for (const [key, value] of mapping.entries()) {
      if (key.includes(itemName) || itemName.includes(key)) {
        return value;
      }
    }
  }
  
  // Try fuzzy matching for support cards
  if (itemName && itemName.length > 3) {
    for (const [key, value] of mapping.entries()) {
      const keyLower = key.toLowerCase();
      const nameLower = itemName.toLowerCase();
      
      // Check if key contains the name or vice versa
      if (keyLower.includes(nameLower) || nameLower.includes(keyLower)) {
        return value;
      }
      
      // Check for common patterns
      if (keyLower.includes('support card') && nameLower.includes('support card')) {
        return value;
      }
    }
  }
  
  return null;
}

// Function to enhance training events data with character/support info
function enhanceTrainingEventsData(trainingData, umaMapping, supportMapping) {
  const enhancedData = {
    ...trainingData,
    characters: [],
    supportCards: [],
    scenarios: trainingData.scenarios || [],
    events: trainingData.events || [],
    progress: trainingData.progress || {},
    timestamp: trainingData.timestamp || new Date().toISOString()
  };

  // Enhance characters with detailed info
  trainingData.characters.forEach(char => {
    const umaInfo = findBestMatch(char, umaMapping);
    
    if (umaInfo) {
      enhancedData.characters.push({
        ...char,
        name: umaInfo.name,
        imageUrl: umaInfo.imageUrl,
        url_detail: umaInfo.url_detail,
        rarity: umaInfo.rarity
      });
    } else {
      // Fallback if not found in uma mapping
      enhancedData.characters.push({
        ...char,
        name: char.id,
        imageUrl: null,
        url_detail: null,
        rarity: null
      });
    }
  });

  // Enhance support cards with detailed info
  trainingData.supportCards.forEach(card => {
    const supportInfo = findBestMatch(card, supportMapping);
    
    if (supportInfo) {
      enhancedData.supportCards.push({
        ...card,
        name: supportInfo.name,
        imageUrl: supportInfo.imageUrl,
        url_detail: supportInfo.url_detail,
        rarity: supportInfo.rarity
      });
    } else {
      // Fallback if not found in support mapping
      enhancedData.supportCards.push({
        ...card,
        name: card.id,
        imageUrl: null,
        url_detail: null,
        rarity: null
      });
    }
  });

  return enhancedData;
}

// ===== END MAPPING FUNCTIONS =====

// Function to clean event names by removing unwanted prefixes
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

const SPEED_FACTOR = 1;
function waitTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms * SPEED_FACTOR));
}

// ==============================================
// NEW HELPER – ensure all event items are loaded
// ==============================================
async function collectAllEventHandles(page) {
  // Scroll the Event Viewer list until no new items appear so that
  // all lazily-rendered events are present in the DOM, then return
  // every ".compatibility_viewer_item__SWULM" element handle.
  let prevCount = -1;
  let stableCycles = 0;
  const MAX_CYCLES = 10;

  while (stableCycles < 2 && stableCycles < MAX_CYCLES) {
    await page.evaluate(() => {
      const viewer = document.querySelector('.compatibility_result_box__OpJCO');
      if (viewer) viewer.scrollBy(0, viewer.scrollHeight);
    });
    await waitTimeout(250);

    const curCount = await page.evaluate(() =>
      document.querySelectorAll('.compatibility_viewer_item__SWULM').length
    );

    if (curCount === prevCount) {
      stableCycles += 1; // list size unchanged – maybe done
    } else {
      prevCount = curCount;
      stableCycles = 0;  // reset when new items appear
    }
  }

  return await page.$$('.compatibility_viewer_item__SWULM');
}

// Helper function to get random index from unused items
function getRandomUnusedIndex(usedIndices, max) {
  const unusedIndices = [];
  for (let i = 0; i < max; i++) {
    if (!usedIndices.includes(i)) {
      unusedIndices.push(i);
    }
  }
  if (unusedIndices.length === 0) return Math.floor(Math.random() * max);
  return unusedIndices[Math.floor(Math.random() * unusedIndices.length)];
}

// Helper function to get random unique indices, prioritizing unused
function getRandomUniqueIndices(count, max, usedIndices = []) {
  const indices = [];
  const localUsed = [...usedIndices];
  
  while (indices.length < count) {
    let randomIndex;
    if (localUsed.length < max) {
      randomIndex = getRandomUnusedIndex(localUsed, max);
    } else {
      randomIndex = Math.floor(Math.random() * max);
    }
    
    if (!indices.includes(randomIndex)) {
      indices.push(randomIndex);
      localUsed.push(randomIndex);
    }
  }
  return indices;
}

// Helper function to scroll to element and ensure it's visible before clicking
async function scrollToAndClick(page, selector, description = 'element') {
  console.log(`  🎯 Scrolling to and clicking ${description} (${selector})`);
  
  // Wait for element to be available with shorter timeout
  await page.waitForSelector(selector, { timeout: 8000 });
  
  // Find element
  const element = await page.$(selector);
  if (!element) {
    throw new Error(`${description} not found: ${selector}`);
  }
  
  // Check if element is visible and clickable (giảm thời gian check)
  const isVisible = await element.evaluate(el => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return (
      rect.width > 0 && rect.height > 0 &&
      style.display !== 'none' && 
      style.visibility !== 'hidden' &&
      style.pointerEvents !== 'none'
    );
  });
  
  if (!isVisible) {
    throw new Error(`${description} is not visible or clickable: ${selector}`);
  }
  
  // Scroll element into view with more precise positioning
  await page.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    const scrollTop = window.pageYOffset + rect.top - (window.innerHeight / 2);
    window.scrollTo({
      top: scrollTop,
      behavior: 'auto'
    });
  }, element);
  
  // Giảm wait time cho scroll
  await waitTimeout(400);
  
  // Click the element with retry logic (giảm xuống 1 attempt)
  try {
    await element.click({ timeout: 5000 });
    console.log(`  ✅ Successfully clicked ${description}`);
  } catch (clickError) {
    console.log(`  ⚠️ Click failed: ${clickError.message}`);
    throw new Error(`Failed to click ${description}: ${clickError.message}`);
  }
}

async function scrapeTrainingEvents(headlessMode = true) {
  console.log('🚀 Starting Training Event Helper scraper...');
  console.log(`📱 Running in ${headlessMode ? 'headless' : 'visible'} mode`);
  
  // Xóa file kết quả cũ nếu có
  const fs = require('fs');
  const outputFile = path.join(DATA_DIR, 'events.json');
  if (fs.existsSync(outputFile)) {
    fs.unlinkSync(outputFile);
    console.log('🗑️ Deleted old results file');
  }
  
  const browser = await puppeteer.launch({
    headless: headlessMode, // Sử dụng tham số headlessMode
    defaultViewport: headlessMode ? { width: 1920, height: 1080 } : null,
    args: [
      ...(headlessMode ? [] : ['--start-maximized']), // Chỉ maximize khi không headless
      '--disable-extensions',
      '--disable-plugins',
      '--disable-images',
      '--disable-javascript', // Tắt JS không cần thiết
      '--disable-gpu',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--disable-features=VizDisplayCompositor'
    ],
    protocolTimeout: 30000,
    timeout: 30000
  });

  try {
    const page = await browser.newPage();
    
    // Set page-level timeouts (giảm xuống)
    page.setDefaultTimeout(20000);
    page.setDefaultNavigationTimeout(30000);
    
    // Navigate to the Training Event Helper page
    console.log('📱 Navigating to Training Event Helper page...');
    await page.goto('https://gametora.com/umamusume/training-event-helper', {
      waitUntil: 'domcontentloaded', // Thay đổi từ networkidle2 sang domcontentloaded để nhanh hơn
      timeout: 30000
    });

    await waitTimeout(2000); // Giảm wait time

    // Get available options
    const options = await getAvailableOptions(page);
    console.log(`✅ Found ${options.supportCards.length} support cards, ${options.scenarios.length} scenarios, ${options.characters.length} characters`);
    
    // Skip writing training_options.json per preference

    // === 1. REPLACE old combination creation logic ===
    // find section after options retrieved where combinations created; we'll insert new block and comment old (not deleting for now)
    // Locate marker: "// Lấy toàn bộ dữ liệu: tất cả support cards, nhân vật, scenarios" - replace logic below until before const combinations = [] existing.
    // We'll insert easier by redefining combinations before it's used
    // Add after we fetch options (right after console logs)
    // ------------------------------
    // Build combinations (new logic)
    // ------------------------------
    const combinations = [];

    // Phase 1: each character with scenario (cycling) ; first N (scenario count) allowScenarioEvent true
    options.characters.forEach((char, idx) => {
      const scenario = options.scenarios[idx % options.scenarios.length] || 'URA Finals';
      combinations.push({
        character: char,
        scenario,
        cards: [],
        allowScenarioEvent: idx < options.scenarios.length
      });
    });

    // Phase 2: each support card alone with scenario cycling
    options.supportCards.forEach((card, idx) => {
      const scenario = options.scenarios[idx % options.scenarios.length] || 'URA Finals';
      combinations.push({
        character: null,
        scenario,
        cards: [card],
        allowScenarioEvent: false
      });
    });

    console.log(`📊 Total combinations generated: ${combinations.length}`);

    // === old combination generation block skipped ===
    /*
    ...
    */

    const allEvents = [];
    let combinationCount = 0;

    for (const combination of combinations) {
      combinationCount++;
      console.log(`\n🔄 Testing combination ${combinationCount}/${combinations.length}`);
      console.log(`   🎴 Testing: ${combination.cards.length} cards + ${combination.scenario} + ${combination.character?.alt || combination.character?.title || 'Unknown'}`);

      try {
        // Xóa state hiện tại trước khi chọn mới
        await clearCurrentState(page);
        
        // Select cards (nếu có)
        if (combination.cards.length > 0) {
          for (let i = 0; i < combination.cards.length; i++) {
            try {
              await selectCard(page, i, combination.cards[i]);
              // Giảm wait time giữa các card selections
              if (i < combination.cards.length - 1) await waitTimeout(300);
            } catch (cardError) {
              console.log(`   ⚠️ Error selecting card ${i + 1}: ${cardError.message}`);
            }
          }
        }
        
        // Select scenario
        try {
          await selectScenario(page, combination.scenario);
          await waitTimeout(400);
        } catch (scenarioError) {
          console.log(`   ⚠️ Error selecting scenario: ${scenarioError.message}`);
        }
        
        // Select character if present
        if (combination.character) {
          try {
            await selectCharacter(page, combination.character);
            await waitTimeout(600);
          } catch (characterError) {
            console.log(`   ⚠️ Error selecting character: ${characterError.message}`);
          }
        }
        
        // Wait a bit for Event Viewer to load
        await waitTimeout(3000);
        
        // Debug: Check what's on the page
        const pageContent = await page.evaluate(() => {
          const allElements = document.querySelectorAll('*');
          const classNames = new Set();
          allElements.forEach(el => {
            if (el.className && typeof el.className === 'string') {
              el.className.split(' ').forEach(cls => {
                if (cls.includes('compatibility') || cls.includes('event') || cls.includes('result')) {
                  classNames.add(cls);
                }
              });
            }
          });
          return Array.from(classNames);
        });
        console.log(`  🔍 Found classes: ${pageContent.join(', ')}`);
        
        // Scrape events (now owner-aware, needs combination context)
        const events = await scrapeEvents(page, combination);
        
        if (events.length > 0) {
          console.log(`✅ Found ${events.length} events for this combination`);
        } else {
          console.log(`⚠️  No events found for this combination`);
        }
        
        allEvents.push({
          combination,
          events
        });
        
        // Save progress to JSON after each successful combination
        saveResultsToJSON(allEvents, combinationCount, combinations.length);
        
      } catch (error) {
        console.error(`❌ Error testing combination: ${error.message}`);
        allEvents.push({
          combination,
          events: [],
          error: error.message
        });
        
        // Save progress to JSON even if there's an error
        saveResultsToJSON(allEvents, combinationCount, combinations.length);
        
        // Try to reset the page state by refreshing if there's a serious error
        if (error.message.includes('timeout') || error.message.includes('detached')) {
          console.log('🔄 Attempting to refresh page to reset state...');
          try {
            await page.reload({ waitUntil: 'networkidle2', timeout: 30000 });
            await waitTimeout(5000);
          } catch (refreshError) {
            console.error(`❌ Failed to refresh page: ${refreshError.message}`);
          }
        }
      }
    }

    // Final save to ensure all data is saved
    saveResultsToJSON(allEvents, combinationCount, combinations.length);

    console.log('\n🎉 Scraping completed!');
    console.log(`📊 Total combinations tested: ${combinationCount}`);
    console.log(`📊 Total event combinations found: ${allEvents.filter(e => e.events.length > 0).length}`);
    
    // Load final results from JSON to display summary
    try {
      const finalResults = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'events.json'), 'utf8'));
      
      // Hiển thị thông tin chi tiết về kết quả
      console.log('\n📋 Final Results summary:');
      console.log(`   👤 Characters with events: ${finalResults.characters.length}`);
      console.log(`   🎴 Support cards with events: ${finalResults.supportCards.length}`);
      console.log(`   📖 Scenarios with events: ${finalResults.scenarios.length}`);
      console.log(`   📊 Progress: ${finalResults.progress.completed}/${finalResults.progress.total} (${finalResults.progress.percentage}%)`);
      
    } catch (error) {
      console.log('\n📋 Results summary:');
      console.log(`   👤 Characters with events: ${allEvents.filter(e => e.events.length > 0).length}`);
      console.log(`   🎴 Support cards with events: ${allEvents.filter(e => e.events.length > 0).length}`);
      console.log(`   📖 Scenarios with events: ${allEvents.filter(e => e.events.length > 0).length}`);
    }
    
    // Hiển thị chi tiết từng combination
    console.log('\n📋 Combination details:');
    allEvents.forEach((result, index) => {
      console.log(`   Combination ${index + 1}:`);
      console.log(`      Character: ${result.combination.character?.alt || result.combination.character?.title || 'Unknown'}`);
      console.log(`      Scenario: ${result.combination.scenario}`);
      console.log(`      Cards: ${result.combination.cards.length} cards`);
      console.log(`      Events found: ${result.events.length}`);
      if (result.error) {
        console.log(`      Error: ${result.error}`);
      }
    });
    
    console.log('\n💾 Results saved to data/events.json');
    console.log('📁 File location: ' + path.join(DATA_DIR, 'events.json'));
    console.log('📄 Format: Simplified JSON with progress tracking');

  } catch (error) {
    console.error('❌ Error during scraping:', error);
  } finally {
    await browser.close();
  }
}

async function getAvailableOptions(page) {
  console.log('🔍 Getting available options...');
  const options = { supportCards: [], scenarios: [], characters: [] };
  try {
    // Get support cards from modal (need to click a support slot first)
    console.log('  📋 Getting support cards from modal...');
    
    // Scroll to and click support slot to open modal
    await scrollToAndClick(page, '#boxSupport1', 'support slot 1');
    await waitTimeout(2000); // Giảm wait time cho modal load
    
    // Wait for modal to appear
    await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
    
    // Check if support modal is available
    const modalCount = await page.evaluate(() => {
      return document.querySelectorAll('[role="dialog"]').length;
    });
    
    console.log(`  🔍 Found ${modalCount} modal(s) after clicking support slot`);
    
    // Get all visible support cards directly without scrolling
    const supportCards = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      for (const modal of modals) {
        const supportImgs = modal.querySelectorAll('img[src*="support_card_s_"]');
        if (supportImgs.length > 0) {
          console.log('Getting visible cards from modal with', supportImgs.length, 'total images');
          
          // Get all visible cards
          const visibleCards = Array.from(modal.querySelectorAll('img')).filter(img => {
            if (!img.src.includes('support_card_s_')) return false;
            
            const rect = img.getBoundingClientRect();
            const style = window.getComputedStyle(img);
            
            return (
              rect.width > 0 && rect.height > 0 &&
              style.display !== 'none' && 
              style.visibility !== 'hidden'
            );
          });
          
          console.log('Found', visibleCards.length, 'visible cards');
          
          return visibleCards.map(img => {
            // Tìm tên card từ parent elements
            let cardName = img.alt || img.title || '';
            
            // Tìm tên trong parent container
            const parent = img.closest('[class*="card"], [class*="support"], [class*="item"]');
            if (parent) {
              const nameElement = parent.querySelector('[class*="name"], [class*="title"], [class*="text"]');
              if (nameElement && nameElement.textContent.trim()) {
                cardName = nameElement.textContent.trim();
              }
            }
            
            // Nếu vẫn không có tên, lấy từ URL
            if (!cardName) {
              const urlParts = img.src.split('/');
              const fileName = urlParts[urlParts.length - 1];
              cardName = fileName.replace('.png', '').replace('.jpg', '').replace('support_card_s_', '');
            }
            
            return {
              src: img.src,
              alt: cardName,
              title: cardName
            };
          });
        }
      }
      return [];
    });
    
    options.supportCards = supportCards;
    console.log(`  ✅ Final total: ${supportCards.length} support cards found`);
    
    // Debug: Hiển thị một số tên cards đầu tiên
    if (supportCards.length > 0) {
      console.log('  �� Sample card names:');
      supportCards.slice(0, 5).forEach((card, index) => {
        console.log(`     ${index + 1}. ${card.alt || card.title || 'No name'}`);
      });
    }
    
    // Close support modal properly
    await page.keyboard.press('Escape');
    await waitTimeout(1000); // Giảm wait time
    
    // Check if page is still accessible
    try {
      await page.evaluate(() => {
        return document.readyState;
      });
    } catch (error) {
      console.log('  ⚠️ Page seems to be detached, refreshing...');
      await page.reload({ waitUntil: 'networkidle2' });
      await waitTimeout(3000);
    }
    
    // Get character images
    console.log('  👤 Getting characters from modal...');
    let characterImgs = [];
    
    try {
      await scrollToAndClick(page, '#boxChar', 'character box');
      await waitTimeout(1500); // Giảm wait time
      
      // Wait for modal to appear
      await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
      
      // Get all visible characters directly without scrolling
      characterImgs = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        console.log('Found', modals.length, 'modals');
        
        if (modals.length === 0) return [];
        
        // Find the modal that contains character images
        let charModal = null;
        for (let i = 0; i < modals.length; i++) {
          const modal = modals[i];
          const charImgs = modal.querySelectorAll('img[src*="/characters/thumb/chara_stand_"]');
          console.log(`Modal ${i}: Found ${charImgs.length} character images`);
          if (charImgs.length > 0) {
            charModal = modal;
            break;
          }
        }
        
        if (!charModal) {
          console.log('No character modal found, trying alternative selectors...');
          // Try alternative selectors
          for (let i = 0; i < modals.length; i++) {
            const modal = modals[i];
            const allImgs = modal.querySelectorAll('img');
            console.log(`Modal ${i}: Total images: ${allImgs.length}`);
            
            // Check if any image contains character-like URLs
            const charImgs = Array.from(allImgs).filter(img => 
              img.src.includes('character') || 
              img.src.includes('chara') ||
              img.src.includes('thumb')
            );
            console.log(`Modal ${i}: Character-like images: ${charImgs.length}`);
            
            if (charImgs.length > 0) {
              charModal = modal;
              break;
            }
          }
        }
        
        if (!charModal) {
          console.log('Still no character modal found');
          return [];
        }
        
        const imgs = Array.from(charModal.querySelectorAll('img')).filter(img => {
          // Accept any image that might be a character
          const isCharacter = img.src.includes('/characters/thumb/chara_stand_') ||
                             img.src.includes('character') ||
                             img.src.includes('chara') ||
                             img.src.includes('thumb');
          
          if (!isCharacter) return false;
          
          const style = window.getComputedStyle(img);
          const rect = img.getBoundingClientRect();
          return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            rect.width > 0 && rect.height > 0
          );
        });
        
        console.log('Final character images found:', imgs.length);
        
        return imgs.map(img => {
          // Tìm tên character từ parent elements
          let charName = img.alt || img.title || '';
          
          // Tìm tên trong parent container - cải thiện logic tìm kiếm
          const parent = img.closest('[class*="character"], [class*="chara"], [class*="item"], [class*="card"]');
          if (parent) {
            // Tìm tên trong các phần tử con
            const nameSelectors = [
              '[class*="name"]',
              '[class*="title"]', 
              '[class*="text"]',
              'span',
              'div',
              'p'
            ];
            
            for (const selector of nameSelectors) {
              const nameElement = parent.querySelector(selector);
              if (nameElement && nameElement.textContent.trim() && nameElement.textContent.trim().length > 0) {
                const text = nameElement.textContent.trim();
                // Kiểm tra xem text có vẻ là tên nhân vật không (không quá dài, không chứa ký tự đặc biệt)
                if (text.length > 0 && text.length < 50 && !text.includes('http') && !text.includes('www')) {
                  charName = text;
                  break;
                }
              }
            }
            
            // Nếu vẫn không tìm được, tìm trong các phần tử anh em
            if (!charName || charName === '') {
              const siblings = Array.from(parent.parentElement?.children || []);
              for (const sibling of siblings) {
                if (sibling !== parent && sibling.textContent.trim() && sibling.textContent.trim().length > 0) {
                  const text = sibling.textContent.trim();
                  if (text.length > 0 && text.length < 50 && !text.includes('http') && !text.includes('www')) {
                    charName = text;
                    break;
                  }
                }
              }
            }
          }
          
          // Nếu vẫn không có tên, lấy từ URL
          if (!charName || charName === '') {
            const urlParts = img.src.split('/');
            const fileName = urlParts[urlParts.length - 1];
            charName = fileName.replace('.png', '').replace('.jpg', '').replace('chara_stand_', '');
          }
          
          return {
            src: img.src,
            alt: charName,
            title: charName
          };
        });
      });
      
      console.log(`Found ${characterImgs.length} character images.`);
      
      await page.keyboard.press('Escape');
      await waitTimeout(500); // Giảm wait time
      
    } catch (error) {
      console.log('  ⚠️ Error during character processing:', error.message);
      characterImgs = [];
    }
    
    // Fallback: nếu không tìm thấy nhân vật nào, sử dụng nhân vật mặc định
    if (characterImgs.length === 0) {
      console.log('  ⚠️ No characters found, using default characters');
      characterImgs = [
        { src: 'default_character_1', alt: 'Default Character 1', title: 'Default Character 1' },
        { src: 'default_character_2', alt: 'Default Character 2', title: 'Default Character 2' },
        { src: 'default_character_3', alt: 'Default Character 3', title: 'Default Character 3' }
      ];
    }
    
    options.characters = characterImgs;
    console.log(`  ✅ Final total: ${characterImgs.length} characters found`);
    
    // Debug: Hiển thị một số tên characters đầu tiên
    if (characterImgs.length > 0) {
      console.log('  👤 Sample character names:');
      characterImgs.slice(0, 5).forEach((char, index) => {
        console.log(`     ${index + 1}. ${char.alt || char.title || 'No name'}`);
      });
    }
    
    // Get scenarios from modal
    console.log('  📖 Getting scenarios from modal...');
    let scenarios = [];
    
    // Try different selectors for scenario box
    const scenarioSelectors = ['#boxScenario', '[id*="scenario"]', '[id*="Scenario"]'];
    let scenarioBox = null;
    
    for (const selector of scenarioSelectors) {
      scenarioBox = await page.$(selector);
      if (scenarioBox) {
        console.log(`  🎯 Found scenario box with selector: ${selector}`);
        break;
      }
    }
    
    if (scenarioBox) {
      try {
        await scrollToAndClick(page, '#boxScenario', 'scenario box');
        await waitTimeout(2000);
        
        scenarios = await page.evaluate(() => {
          try {
            // Use the correct selector for scenario names
            const scenarioSelector = '.tooltips_tooltip_striped__0p4n9 > div > div > .fVBhhN.sc-9ae1b094-0 > .fpCljy.sc-9ae1b094-1 > span';
            const scenarioElements = document.querySelectorAll(scenarioSelector);
            
            return Array.from(scenarioElements).map(element => {
              return element.textContent.trim();
            }).filter(text => text.length > 0);
            
          } catch (error) {
            console.log('Error with user selector, falling back to old method');
            
            // Fallback to old method if user selector fails
            const modals = document.querySelectorAll('[role="dialog"]');
            let scenarioModal = null;
            
            for (const modal of modals) {
              const content = modal.innerText.toLowerCase();
              if (content.includes('select a scenario') || 
                  content.includes('scenario') ||
                  content.includes('finals') ||
                  content.includes('hai') ||
                  content.includes('live')) {
                scenarioModal = modal;
                break;
              }
            }
            
            if (!scenarioModal) return [];
            
            const scenarioElements = Array.from(scenarioModal.querySelectorAll('.sc-98a8819c-1.litiDm'));
            
            return scenarioElements.map(element => {
              const textElement = element.querySelector('.sc-98a8819c-2.IVPoU');
              const text = textElement ? textElement.textContent.trim() : '';
              return text;
            }).filter(text => 
              text.length > 0 && 
              text !== 'Remove' &&
              !text.includes('(Original)') &&
              !text.includes('(Christmas)') &&
              !text.includes('(Summer)') &&
              !text.includes('(Wedding)')
            );
          }
        });
        
        await page.keyboard.press('Escape');
        await waitTimeout(500); // Giảm wait time
        
      } catch (error) {
        console.log('  ⚠️ Error during scenario processing:', error.message);
        scenarios = ['URA Finals', 'Aoharu Hai', 'Make a New Track', 'Grand Live', 'Grand Masters'];
      }
    } else {
      console.log('  ⚠️ No scenario box found, using default scenarios');
      scenarios = ['URA Finals', 'Aoharu Hai', 'Make a New Track', 'Grand Live', 'Grand Masters'];
    }
    
    options.scenarios = scenarios;
    console.log(`  ✅ Final total: ${scenarios.length} scenarios found`);
  } catch (error) {
    console.error('❌ Error getting options:', error);
  }
  return options;
}

async function selectCard(page, cardIndex, cardObj) {
  console.log(`   🎴 Selecting card ${cardIndex + 1}`);
  try {
    const cardSelector = `#boxSupport${cardIndex + 1}`;
    await scrollToAndClick(page, cardSelector, `support slot ${cardIndex + 1}`);
    await waitTimeout(800); // Giảm wait time
    
    // Wait for modal to appear with shorter timeout
    await page.waitForSelector('[role="dialog"]', { timeout: 8000 });
    
    const selected = await page.evaluate((targetSrc) => {
      const modals = document.querySelectorAll('[role="dialog"]');
      if (modals.length === 0) return false;
      
      // Find the modal that contains support cards
      let supportModal = null;
      for (const modal of modals) {
        const supportImgs = modal.querySelectorAll('img[src*="support_card_s_"]');
        if (supportImgs.length > 0) {
          supportModal = modal;
          break;
        }
      }
      
      if (!supportModal) return false;
      
      const imgs = Array.from(supportModal.querySelectorAll('img'));
      const cardImg = imgs.find(img => img.src === targetSrc);
      if (cardImg) {
        cardImg.click();
        return true;
      }
      return false;
    }, cardObj.src);
    
    if (!selected) {
      throw new Error(`Card with src ${cardObj.src} not found`);
    }
    
    await waitTimeout(400); // Giảm wait time
    
    // Close modal if still open
    try {
      await page.keyboard.press('Escape');
      await waitTimeout(300);
    } catch (closeError) {
      console.log(`   ⚠️ Warning: Could not close modal: ${closeError.message}`);
    }
    
  } catch (error) {
    // Try to close any open modals before throwing error
    try {
      await page.keyboard.press('Escape');
      await waitTimeout(300);
    } catch (closeError) {
      // Ignore close errors
    }
    throw new Error(`Failed to select card: ${error.message}`);
  }
}

async function selectScenario(page, scenarioName) {
  console.log(`   📖 Selecting scenario: ${scenarioName}`);
  
  try {
    await scrollToAndClick(page, '#boxScenario', 'scenario box');
    await waitTimeout(1000); // Giảm wait time
    
    const selected = await page.evaluate((targetName) => {
      try {
        // Use the correct selector for scenario options
        const scenarioSelector = '.tooltips_tooltip_striped__0p4n9 > div > div > .fVBhhN.sc-9ae1b094-0 > .fpCljy.sc-9ae1b094-1 > span';
        const scenarioElements = document.querySelectorAll(scenarioSelector);
        
        const targetElement = Array.from(scenarioElements).find(element => {
          return element.textContent.trim() === targetName;
        });
        
        if (targetElement) {
          // Click on the scenario element
          targetElement.click();
          return true;
        }
        
        return false;
      } catch (error) {
        console.log('Error with scenario selector:', error.message);
        
        // Fallback to old method
        const modals = document.querySelectorAll('[role="dialog"]');
        if (modals.length === 0) return false;
        
        const scenarioModal = modals[0];
        const options = Array.from(scenarioModal.querySelectorAll('.sc-98a8819c-1.litiDm'));
        const targetOption = options.find(option => {
          const textElement = option.querySelector('.sc-98a8819c-2.IVPoU');
          return textElement && textElement.textContent.trim() === targetName;
        });
        
        if (targetOption) {
          targetOption.click();
          return true;
        }
        return false;
      }
    }, scenarioName);
    
    if (!selected) {
      throw new Error(`Scenario "${scenarioName}" not found`);
    }
    
    await waitTimeout(600); // Giảm wait time
    
  } catch (error) {
    throw new Error(`Failed to select scenario: ${error.message}`);
  }
}

async function selectCharacter(page, characterObj) {
  console.log(`   👤 Selecting character`);
  try {
    await scrollToAndClick(page, '#boxChar', 'character box');
    await waitTimeout(1000); // Giảm wait time
    const selected = await page.evaluate((targetSrc) => {
      const modals = document.querySelectorAll('[role="dialog"]');
      if (modals.length === 0) return false;
      const charModal = modals[0];
      const imgs = Array.from(charModal.querySelectorAll('img'));
      const charImg = imgs.find(img => img.src === targetSrc);
      if (charImg) {
        charImg.click();
        return true;
      }
      return false;
    }, characterObj.src);
    if (!selected) {
      throw new Error(`Character with src ${characterObj.src} not found`);
    }
    await waitTimeout(600); // Giảm wait time
  } catch (error) {
    throw new Error(`Failed to select character: ${error.message}`);
  }
}

async function scrapeEvents(page, combination) {
  return await scrapeEventsFromEventViewer(page, combination);
}

async function scrapeEventsFromEventViewer(page, combination) {
  console.log('  📋 Scraping events from Event Viewer...');
  try {
    // Wait for any Event Viewer to appear
    await page.waitForSelector('.compatibility_result_box__OpJCO', { timeout: 15000 });
    
    // Get all Event Viewer boxes
    const eventViewers = await page.$$('.compatibility_result_box__OpJCO');
    console.log(`  📦 Found ${eventViewers.length} Event Viewer boxes`);
    
    // If no Event Viewers found, try to find any event-related content
    if (eventViewers.length === 0) {
      console.log('  🔍 No Event Viewer boxes found, looking for alternative selectors...');
      
      // Try alternative selectors
      const alternativeSelectors = [
        '[class*="compatibility"]',
        '[class*="event"]',
        '[class*="result"]',
        '.compatibility_result_box',
        '.event-viewer',
        '.result-box'
      ];
      
      for (const selector of alternativeSelectors) {
        const elements = await page.$$(selector);
        console.log(`  🔍 Selector "${selector}": ${elements.length} elements`);
        if (elements.length > 0) {
          eventViewers.push(...elements);
        }
      }
      
      if (eventViewers.length === 0) {
        console.log('  ⚠️ No event-related content found');
        return [];
      }
    }
    
    // Find the Event Viewer that contains images (usually the last one)
    let targetViewer = null;
    let maxImages = 0;
    
    for (let i = 0; i < eventViewers.length; i++) {
      const images = await eventViewers[i].$$('img');
      console.log(`  📋 Event Viewer ${i + 1}: ${images.length} images`);
      if (images.length > maxImages) {
        maxImages = images.length;
        targetViewer = eventViewers[i];
      }
    }
    
    if (!targetViewer) {
      console.log('  ⚠️ No Event Viewer with images found');
      return [];
    }
    
    // Get all images in the target Event Viewer
    const imageHandles = await targetViewer.$$('img');
    console.log(`  🖱️ Found ${imageHandles.length} images in target Event Viewer`);
    
    let allEvents = [];
    
    const allowScenario = combination.allowScenarioEvent;
    const finalIndex = allowScenario ? imageHandles.length : imageHandles.length - 1;

    // Click through relevant images sequentially
    for (let i = 0; i < finalIndex; i++) {
      // Scope owner variables inside loop to avoid bleed-over
      let ownerType;
      let ownerName;
      // Determine who this icon represents
      const isScenarioIcon = allowScenario && i === imageHandles.length - 1;

      if (isScenarioIcon) {
        ownerType = 'scenario';
        ownerName = combination.scenario;
      } else if (combination.character && i === 0) {
        ownerType = 'character';
        ownerName = combination.character?.alt || combination.character?.title || 'Unknown';
      } else {
        // support icon
        const offset = combination.character ? i - 1 : i;
        const cardObj = combination.cards[offset];
        ownerType = 'support';
        ownerName = cardObj ? (cardObj.alt || cardObj.title || 'Unknown') : 'Unknown';
      }
      console.log(`  🎯 Clicking image ${i + 1}/${imageHandles.length}`);
      
      try {
        // Scroll into view and click
        await imageHandles[i].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
        await waitTimeout(300);
        await imageHandles[i].click();
        await waitTimeout(800);
        
        // Get event items after clicking (use helper to load all lazily rendered items)
        const eventHandles = await collectAllEventHandles(page);
        console.log(`    📋 Found ${eventHandles.length} events for image ${i + 1}`);
        
        for (let j = 0; j < eventHandles.length; j++) {
          try {
            await eventHandles[j].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
            await waitTimeout(200);
            await eventHandles[j].click();
            await waitTimeout(500);
            
            // Get popup detail (tooltip)
            const detail = await page.evaluate(() => {
              // Function to clean event names by removing unwanted prefixes
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

              const tippy = document.querySelector('.tippy-box');
              if (!tippy) return null;
              const eventName = tippy.querySelector('.tooltips_ttable_heading__jlJcE')?.textContent?.trim() || '';

              // Tìm event type từ các event groups
              let type = 'Unknown';
              let eventItem = document.querySelector('.compatibility_viewer_item__SWULM.clicked') || 
                             document.querySelector('.compatibility_viewer_item__SWULM:hover') ||
                             document.querySelector('.compatibility_viewer_item__SWULM');
              
              if (eventItem) {
                // Tìm kiếm type trong các phần tử cha
                let el = eventItem.parentElement;
                let level = 1;
                
                while (el && el !== document.body && level <= 10) {
                  // Kiểm tra xem có phải là header/type không
                  if (el.tagName === 'H1' || el.tagName === 'H2' || el.tagName === 'H3' || el.tagName === 'H4') {
                    type = el.textContent.trim();
                    break;
                  }
                  
                  // Kiểm tra class có chứa từ khóa type
                  if (el.className && (
                    el.className.includes('type') || 
                    el.className.includes('group') || 
                    el.className.includes('category') ||
                    el.className.includes('header') ||
                    el.className.includes('title')
                  )) {
                    type = el.textContent.trim();
                    break;
                  }
                  
                  // Kiểm tra text có chứa từ khóa event type - TÌM KIẾM CÁC EVENT GROUPS
                  const text = el.textContent.trim();
                  if (text) {
                    // Tìm các event groups cụ thể
                    const eventGroups = [
                      'Costume Events',
                      'Events With Choices', 
                      'Date Events',
                      'Special Events',
                      'After a Race',
                      'Events Without Choices',
                      'Chain Events',
                      'Random Events',
                      'Secret Events'
                    ];
                    
                    for (const group of eventGroups) {
                      if (text.includes(group)) {
                        type = group;
                        break;
                      }
                    }
                    
                    if (type !== 'Unknown') break;
                  }
                  
                  el = el.parentElement;
                  level++;
                }
                
                // Nếu vẫn chưa tìm được type, tìm kiếm trong các phần tử anh em
                if (type === 'Unknown') {
                  let sibling = eventItem.previousElementSibling;
                  while (sibling && type === 'Unknown') {
                    if (sibling.tagName === 'H1' || sibling.tagName === 'H2' || sibling.tagName === 'H3' || sibling.tagName === 'H4') {
                      type = sibling.textContent.trim();
                      break;
                    }
                    
                    // Kiểm tra text của sibling có chứa event groups không
                    const siblingText = sibling.textContent.trim();
                    if (siblingText) {
                      const eventGroups = [
                        'Costume Events',
                        'Events With Choices', 
                        'Date Events',
                        'Special Events',
                        'After a Race',
                        'Events Without Choices',
                        'Chain Events',
                        'Random Events',
                        'Secret Events'
                      ];
                      
                      for (const group of eventGroups) {
                        if (siblingText.includes(group)) {
                          type = group;
                          break;
                        }
                      }
                      
                      if (type !== 'Unknown') break;
                    }
                    
                    sibling = sibling.previousElementSibling;
                  }
                }
                
                // Nếu vẫn chưa tìm được, tìm kiếm trong toàn bộ Event Viewer
                if (type === 'Unknown') {
                  const eventViewer = document.querySelector('.compatibility_result_box__OpJCO');
                  if (eventViewer) {
                    const allText = eventViewer.textContent;
                    const eventGroups = [
                      'Costume Events',
                      'Events With Choices', 
                      'Date Events',
                      'Special Events',
                      'After a Race',
                      'Events Without Choices',
                      'Chain Events',
                      'Random Events',
                      'Secret Events'
                    ];
                    
                    for (const group of eventGroups) {
                      if (allText.includes(group)) {
                        // Kiểm tra xem event hiện tại có thuộc group này không
                        const eventIndex = Array.from(eventViewer.querySelectorAll('.compatibility_viewer_item__SWULM')).indexOf(eventItem);
                        const groupElements = Array.from(eventViewer.querySelectorAll('*')).filter(el => 
                          el.textContent && el.textContent.includes(group)
                        );
                        
                        // Nếu tìm thấy group và event gần nhau, coi như thuộc group đó
                        if (groupElements.length > 0) {
                          type = group;
                          break;
                        }
                      }
                    }
                  }
                }
              }

              /* ---------------- NEW CHOICE / EFFECT PARSER ---------------- */
              const parseEffectLine = (txt) => {
                const statMatch = txt.match(/^([A-Za-z ]+?)\s*([+-]?-?\d+)/);
                if (statMatch) {
                  const stat = statMatch[1].trim();
                  return { kind: 'stat', raw: txt, stat, amount: parseInt(statMatch[2]) };
                }

                const lower = txt.toLowerCase();
                if (lower.startsWith('obtain') && lower.includes('skill')) {
                  return { kind: 'skill', raw: txt };
                }
                if (lower.includes('status')) {
                  return { kind: 'status', raw: txt };
                }

                return { kind: 'text', raw: txt };
              };

              const pushSegmentsFromText = (arr, text) => {
                const parts = text.split(/\s+or\s+/i);
                  if (parts.length > 1) {
                  arr.push(parseEffectLine(parts[0]));
                  arr.push({ kind: 'divider_or', raw: 'or' });
                  parts.slice(1).forEach(p => arr.push(parseEffectLine(p)));
                } else {
                  arr.push(parseEffectLine(text));
                }
              };

              let choices = [];
              const tableEl = tippy.querySelector('table.tooltips_ttable__dvIzv');

              if (tableEl) {
                tableEl.querySelectorAll('tr').forEach(tr => {
                  const tds = tr.querySelectorAll('td');
                  if (tds.length < 2) return;
                  const optionName = tds[0].textContent.trim();
                  const effectCell = tds[1];
                  const segs = [];

                  effectCell.childNodes.forEach(node => {
                    const txt = node.textContent.trim();
                    if (!txt) return;
                    if (node.className && node.className.includes('eventhelper_random_text')) {
                      segs.push({ kind: 'random_header', raw: txt });
                    } else if (node.className && node.className.includes('eventhelper_divider_or')) {
                      segs.push({ kind: 'divider_or', raw: txt || 'or' });
                          } else {
                      pushSegmentsFromText(segs, txt);
                        }
                  });

                  if (segs.length) choices.push({ choice: optionName, effects: segs });
                });
                      } else {
                const singleCell = tippy.querySelector('.tooltips_ttable_cell___3NMF');
                if (singleCell) {
                  const segs = [];
                  Array.from(singleCell.querySelectorAll('div')).forEach(d => {
                    const t = d.textContent.trim();
                    if (t) pushSegmentsFromText(segs, t);
                  });
                  if (segs.length) choices.push({ choice: '', effects: segs });
                      }
                    }
              /* ---------------- END NEW PARSER ---------------- */
              const cleanedEventName = cleanEventName(eventName);
              if (cleanedEventName) {
                return { event: cleanedEventName, type, choices };
              } else {
                return null; // Bỏ qua event có tên null sau khi clean
              }
            });
            
            if (detail && detail.event) {
              // Get owner image src
              const ownerImageSrc = await imageHandles[i].evaluate(el => el.src);
              // Build owner detail URL based on image ID
              let ownerUrl = null;
              const extractedId = extractIdFromImageUrl(ownerImageSrc);
              if (extractedId) {
                if (ownerType === 'character') {
                  ownerUrl = `https://gametora.com/umamusume/characters/${extractedId.replace(/_.*/, '')}`;
                } else if (ownerType === 'support') {
                  ownerUrl = `https://gametora.com/umamusume/supports/${extractedId}`;
                }
              }

              allEvents.push({
                ownerType,
                ownerName,
                ownerImage: ownerImageSrc,
                ownerUrl,
                event: detail
              });
              console.log(`      ✅ Added event: ${detail.event} (Type: ${detail.type}) -> ${ownerType}: ${ownerName}`);
            } else if (detail && !detail.event) {
              console.log(`      ⏭️ Skipping event with invalid name`);
            }
            
            // Close tooltip
            await page.keyboard.press('Escape');
            await waitTimeout(100);
          } catch (eventError) {
            console.log(`    ⚠️ Error processing event ${j + 1}: ${eventError.message}`);
          }
        }
      } catch (imageError) {
        console.log(`  ⚠️ Error clicking image ${i + 1}: ${imageError.message}`);
      }
    }
    
    // Remove duplicates per owner + event content
    const eventMap = new Map();
    let duplicateCount = 0;

    allEvents.forEach(evObj => {
      if (evObj && evObj.event && evObj.event.event) {
        const keyContent = JSON.stringify({
          ownerType: evObj.ownerType,
          ownerName: evObj.ownerName,
          event: evObj.event.event,
          type: evObj.event.type,
          choices: evObj.event.choices ? evObj.event.choices.map(c => ({ choice: c.choice, effects: c.effects })) : []
        });
        if (!eventMap.has(keyContent)) {
          eventMap.set(keyContent, evObj);
        } else {
          duplicateCount++;
        }
      }
    });

    const uniqueEvents = Array.from(eventMap.values());
    console.log(`  ✅ Found ${uniqueEvents.length} unique owner-tagged events (removed ${duplicateCount} duplicates)`);

    return uniqueEvents;
  } catch (error) {
    console.log('  ❌ Error scraping events:', error.message);
    return [];
  }
}

// Helper to clear current state (click delete button and confirm)
async function clearCurrentState(page) {
  try {
    console.log('  🗑️ Clearing current state...');
    
    // Close any open modals first
    await page.keyboard.press('Escape');
    await waitTimeout(300);
    
    // Try to close any remaining modals
    await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      modals.forEach(modal => {
        const closeBtn = Array.from(modal.querySelectorAll('button, [role="button"]')).find(
          btn => btn.textContent && (btn.textContent.toLowerCase().includes('close') || btn.textContent.toLowerCase().includes('cancel'))
        );
        if (closeBtn) closeBtn.click();
      });
    });
    await waitTimeout(500);
    
    // Look for delete button and click it
    const deleteButton = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
      const deleteBtn = buttons.find(btn => 
        btn.textContent && (
          btn.textContent.toLowerCase().includes('delete') || 
          btn.textContent.toLowerCase().includes('clear') ||
          btn.textContent.toLowerCase().includes('reset')
        )
      );
      return deleteBtn ? true : false;
    });
    
    if (deleteButton) {
      console.log('  🎯 Found delete button, clicking...');
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
        const deleteBtn = buttons.find(btn => 
          btn.textContent && (
            btn.textContent.toLowerCase().includes('delete') || 
            btn.textContent.toLowerCase().includes('clear') ||
            btn.textContent.toLowerCase().includes('reset')
          )
        );
        if (deleteBtn) deleteBtn.click();
      });
      await waitTimeout(1000);
      
      // Look for confirmation dialog and click Yes/OK
      const confirmButton = await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
        const confirmBtn = buttons.find(btn => 
          btn.textContent && (
            btn.textContent.toLowerCase().includes('yes') || 
            btn.textContent.toLowerCase().includes('ok') ||
            btn.textContent.toLowerCase().includes('confirm')
          )
        );
        return confirmBtn ? true : false;
      });
      
      if (confirmButton) {
        console.log('  ✅ Found confirmation button, clicking Yes...');
        await page.evaluate(() => {
          const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
          const confirmBtn = buttons.find(btn => 
            btn.textContent && (
              btn.textContent.toLowerCase().includes('yes') || 
              btn.textContent.toLowerCase().includes('ok') ||
              btn.textContent.toLowerCase().includes('confirm')
            )
          );
          if (confirmBtn) confirmBtn.click();
        });
        await waitTimeout(2000);
      }
    } else {
      console.log('  ⚠️ No delete button found, refreshing page...');
      // Fallback: refresh page if no delete button found
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
      await waitTimeout(3000);
    }
    
    console.log('  ✅ State cleared successfully');
  } catch (error) {
    console.log(`  ⚠️ Could not clear current state: ${error.message}, refreshing page...`);
    try {
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
      await waitTimeout(3000);
    } catch (refreshError) {
      console.log(`  ❌ Failed to refresh page: ${refreshError.message}`);
    }
  }
}

// Helper to save results to JSON file after each combination
function saveResultsToJSON(allEvents, combinationCount, totalCombinations) {
  try {
    console.log(`  💾 Saving progress to JSON (${combinationCount}/${totalCombinations})...`);
    
    // Load mapping data
    // (Old inline dynamic mapping block removed – we now use mapping files later)

    // Tạo cấu trúc tối ưu
    const optimizedData = {
      events: [], // unique events pool
      characters: [],
      supportCards: [],
      scenarios: [],
      progress: {
        completed: combinationCount,
        total: totalCombinations,
        percentage: Math.round((combinationCount / totalCombinations) * 100)
      },
      timestamp: new Date().toISOString()
    };

    // 1. Thu thập tất cả event (không lọc trùng)
    let eventCounter = 0;
    allEvents.forEach(result => {
      if (result.events && result.events.length > 0) {
        result.events.forEach(evObj => {
          const ev = evObj.event;
          const eventId = `event_${++eventCounter}`;
          optimizedData.events.push({ id: eventId, ...ev });
        });
      }
    });
    console.log(`  ✅ Collected ${optimizedData.events.length} events (no dedup)`);

    // 2. Lưu character -> group -> eventIds (đã sửa để tránh duplicate)
    const charMap = new Map();
    const cardMap = new Map();
    const scenarioMap = new Map();

    allEvents.forEach(result => {
      if (result.events && result.events.length > 0) {
        result.events.forEach(evObj => {
          const ev = evObj.event;
          const ownerType = evObj.ownerType;
          const ownerName = evObj.ownerName;

          const eventType = ev.type || 'Unknown';
          const eventKey = JSON.stringify({
            ownerType: ownerType,
            ownerName: ownerName,
            event: ev.event,
            type: ev.type,
            choices: ev.choices || []
          });
          const eventId = `event_${++eventCounter}`;
          optimizedData.events.push({ id: eventId, ...ev });

          const targetMap = ownerType === 'character' ? charMap : ownerType === 'support' ? cardMap : ownerType === 'scenario' ? scenarioMap : null;
          if (!targetMap) return;

          if (!targetMap.has(ownerName)) targetMap.set(ownerName, {});
          if (!targetMap.get(ownerName)[eventType]) targetMap.get(ownerName)[eventType] = new Set();
          targetMap.get(ownerName)[eventType].add(eventId);
        });
      }
    });

    // Convert maps to arrays for optimizedData
    charMap.forEach((groups, charName) => {
      optimizedData.characters.push({
        id: charName,
        eventGroups: Object.entries(groups).map(([type, ids]) => ({ type, eventIds: Array.from(ids) }))
      });
    });

    cardMap.forEach((groups, cardName) => {
      optimizedData.supportCards.push({
        id: cardName,
        eventGroups: Object.entries(groups).map(([type, ids]) => ({ type, eventIds: Array.from(ids) }))
      });
    });

    scenarioMap.forEach((groups, scenarioName) => {
      optimizedData.scenarios.push({
        id: scenarioName,
        eventGroups: Object.entries(groups).map(([type, ids]) => ({ type, eventIds: Array.from(ids) }))
      });
    });

    // --------------------
    // Enhance with mapping from existing data files
    // --------------------
    const umaDataMap = loadJsonFile(path.join(DATA_DIR, 'uma_char.json')) || [];
    const supportDataMap = loadJsonFile(path.join(DATA_DIR, 'support_card.json')) || [];
    const umaMapping = createUmaMapping(umaDataMap);
    const supportMapping = createSupportMapping(supportDataMap);

    const enhancedData = enhanceTrainingEventsData(optimizedData, umaMapping, supportMapping);

    // Now continue detail mapping for skills/status on enhancedData.events

    // Load skills and status data for detail mapping
    console.log('  🔧 Loading skills & status database for detail mapping...');
    const skillsDB = loadJsonFile(path.join(DATA_DIR, 'skills.json')) || [];
    const statusDB = loadJsonFile(path.join(DATA_DIR, 'conditions.json')) || { positive_conditions: [], negative_conditions: [] };

    const statusList = [...statusDB.positive_conditions, ...statusDB.negative_conditions];

    const findSkill = (raw) => {
      const lower = raw.toLowerCase();
      return skillsDB.find(s => lower.includes(s.name.toLowerCase()));
    };

    const findStatus = (raw) => {
      const lower = raw.toLowerCase();
      return statusList.find(st => lower.includes(st.condition.toLowerCase()));
    };

    // Add detail to segments inside enhancedData events
    enhancedData.events.forEach(ev => {
      if (ev.choices) {
        ev.choices.forEach(ch => {
          if (ch && Array.isArray(ch.effects)) {
            ch.effects.forEach(seg => {
              if (seg && !seg.detail) {
                if (seg.kind === 'skill') {
                  const skill = findSkill(seg.raw);
                  if (skill) {
                    seg.detail = { effect: skill.effect, name: skill.name, imageUrl: skill.imageUrl };
                  }
                } else if (seg.kind === 'status') {
                  const st = findStatus(seg.raw);
                  if (st) {
                    seg.detail = { effect: st.effect, condition: st.condition };
                  }
                } else if (seg.kind === 'text') {
                  const lower = seg.raw.toLowerCase();
                  const skillMatch = skillsDB.find(s => lower.includes(s.name.toLowerCase()));
                  if (skillMatch) {
                    seg.kind = 'skill';
                    seg.detail = { effect: skillMatch.effect, name: skillMatch.name, imageUrl: skillMatch.imageUrl };
                    // Detect hint amount if present
                    const hm = seg.raw.match(/hint\s*\+?(-?\d+)/i);
                    if (hm) {
                      seg.hint = parseInt(hm[1]);
                    }
                  } else {
                    const statusMatch = statusList.find(st => lower.includes(st.condition.toLowerCase()));
                    if (statusMatch) {
                      seg.kind = 'status';
                      seg.detail = { effect: statusMatch.effect, condition: statusMatch.condition };
                    }
                  }
                }
              }
            });
          }
        });
      }
    });

    // Apply mapping to enhance data with names and imageUrls
    // Mapping already applied above; using enhancedData
    
    // Calculate mapping statistics
    const mappedCharacters = enhancedData.characters.filter(c => c.name !== c.id).length;
    const mappedCards = enhancedData.supportCards.filter(c => c.name !== c.id).length;
    
    // Save enhanced data to file
    fs.writeFileSync(
      path.join(DATA_DIR, 'events.json'),
      JSON.stringify(enhancedData, null, 2)
    );
    
    // ---------------- DEBUG TXT ----------------
    const eventLookup = new Map();
    enhancedData.events.forEach(ev => eventLookup.set(ev.id, ev));

    let debugLines = [];

    const pushOwner = (ownerArr, typeLabel) => {
      ownerArr.forEach(owner => {
        debugLines.push(`${typeLabel}: ${owner.name || owner.id}`);
        owner.eventGroups.forEach(group => {
          const evNames = group.eventIds.map(id => eventLookup.get(id)?.event || id);
          debugLines.push(`  ${group.type} (${evNames.length})`);
          evNames.forEach(nm => debugLines.push(`    - ${nm}`));
        });
        debugLines.push('');
      });
    };

    pushOwner(enhancedData.characters, 'Character');
    pushOwner(enhancedData.supportCards, 'Support');
    pushOwner(enhancedData.scenarios, 'Scenario');

    fs.writeFileSync(path.join(DATA_DIR, 'event.txt'), debugLines.join("\n"), 'utf-8');
    // -------------------------------------------

    console.log(`  ✅ Progress saved: ${combinationCount}/${totalCombinations} (${enhancedData.progress.percentage}%)`);
    console.log(`     👤 Characters: ${enhancedData.characters.length} (mapped: ${mappedCharacters}/${enhancedData.characters.length})`);
    console.log(`     🎴 Support Cards: ${enhancedData.supportCards.length} (mapped: ${mappedCards}/${enhancedData.supportCards.length})`);
    console.log(`     📖 Scenarios: ${enhancedData.scenarios.length}`);
    console.log(`     📦 Unique events: ${enhancedData.events.length}`);
  } catch (error) {
    console.log(`  ⚠️ Error saving progress: ${error.message}`);
  }
}

// Run the scraper
// Để chạy headless: scrapeTrainingEvents(true)
// Để chạy visible: scrapeTrainingEvents(false)
scrapeTrainingEvents(true).catch(console.error); 