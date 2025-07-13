const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Utility function for timeout
function waitTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function scrapeTrainingEvents() {
  console.log('🚀 Starting Training Event Helper scraper...');
  
  // Xóa file kết quả cũ nếu có
  const fs = require('fs');
  const outputFile = './data/all_training_events.json';
  if (fs.existsSync(outputFile)) {
    fs.unlinkSync(outputFile);
    console.log('🗑️ Deleted old results file');
  }
  
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    args: ['--start-maximized']
  });

  try {
    const page = await browser.newPage();
    
    // Navigate to the Training Event Helper page
    console.log('📱 Navigating to Training Event Helper page...');
    await page.goto('https://gametora.com/umamusume/training-event-helper', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    await waitTimeout(5000);

    // Get available options
    const options = await getAvailableOptions(page);
    console.log(`✅ Found ${options.supportCards.length} support cards, ${options.scenarios.length} scenarios, ${options.characters.length} characters`);
    
    // Save options to file
    fs.writeFileSync(
      path.join(__dirname, 'data', 'training_options.json'),
      JSON.stringify(options, null, 2)
    );
    console.log('💾 Saved options to data/training_options.json');

    // Tạo combinations chỉ từ các card thực tế (theo index)
    const combinations = [];
    const availableCharacters = options.characters.slice(0, 5);
    const availableCards = options.supportCards.slice(0, 30);
    for (let i = 0; i < 5; i++) {
      const startCardIndex = i * 6;
      const endCardIndex = startCardIndex + 6;
      const combinationCards = availableCards.slice(startCardIndex, endCardIndex);
      combinations.push({
        supportCards: combinationCards,
        character: availableCharacters[i],
        scenario: options.scenarios[0]
      });
    }

    const allEvents = [];
    let combinationCount = 0;

    for (const combination of combinations) {
      combinationCount++;
      console.log(`\n🔄 Testing combination ${combinationCount}/${combinations.length}`);
      console.log(`   🎴 Testing: ${combination.supportCards.length} cards + ${combination.scenario} + ${combination.character}`);

      try {
        // Select all 6 support cards (select first available for each slot)
        for (let i = 0; i < 6; i++) {
          await selectCard(page, i, combination.supportCards[i]);
        }
        
        // Don't select scenario - use current one
        
        // Select character
        await selectCharacter(page, combination.character);
        
        // Scrape events
        const events = await scrapeEvents(page);
        
        if (events.length > 0) {
          console.log(`✅ Found ${events.length} events for this combination`);
        } else {
          console.log(`⚠️  No events found for this combination`);
        }
        
        allEvents.push({
          combination,
          events
        });
        
      } catch (error) {
        console.error(`❌ Error testing combination: ${error.message}`);
        allEvents.push({
          combination,
          events: [],
          error: error.message
        });
      }
    }

    // Save results
    const results = {
      allEvents,
      totalCombinations: combinationCount,
      timestamp: new Date().toISOString()
    };

    fs.writeFileSync(
      path.join(__dirname, 'data', 'all_training_events.json'),
      JSON.stringify(results, null, 2)
    );

    console.log('\n🎉 Scraping completed!');
    console.log(`📊 Total combinations tested: ${combinationCount}`);
    console.log(`📊 Total event combinations found: ${allEvents.filter(e => e.events.length > 0).length}`);
    console.log('💾 Results saved to data/all_training_events.json');

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
    // Get support cards from modal (dựa vào <img> giống character)
    console.log('  📋 Getting support cards from modal...');
    await page.click('#boxSupport1');
    await waitTimeout(2000);
    let supportCards = [];
    let lastLength = 0;
    do {
      lastLength = supportCards.length;
      await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        if (modals.length < 2) return;
        const supportModal = modals[1];
        supportModal.scrollTop = supportModal.scrollHeight;
      });
      await waitTimeout(1500);
      // Lấy tất cả img là support card thực tế
      const newCards = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        if (modals.length < 2) return [];
        const supportModal = modals[1];
        const imgs = Array.from(supportModal.querySelectorAll('img')).filter(img => {
          const style = window.getComputedStyle(img);
          const rect = img.getBoundingClientRect();
          return (
            img.src.includes('support_card_s_') &&
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            rect.width > 0 && rect.height > 0
          );
        });
        return imgs.map(img => ({
          src: img.src,
          alt: img.alt || '',
          title: img.title || ''
        }));
      });
      supportCards = Array.from(new Map([...supportCards, ...newCards].map(card => [card.src, card])).values());
      // Log số lượng lấy được
      console.log(`Scroll: found ${supportCards.length} support card images.`);
    } while (supportCards.length > lastLength);
    options.supportCards = supportCards;
    await page.keyboard.press('Escape');
    await waitTimeout(1000);
    // Lấy characterImgs
    lastLength = 0;
    await page.click('#boxChar');
    await waitTimeout(2000);
    do {
      lastLength = characterImgs.length;
      await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        if (modals.length === 0) return;
        const charModal = modals[0];
        charModal.scrollTop = charModal.scrollHeight;
      });
      await waitTimeout(1500);
      // Lấy tất cả img là nhân vật thực tế trong .sc-98a8819c-1.limvpr
      const newImgs = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        if (modals.length === 0) return [];
        const charModal = modals[0];
        const imgs = Array.from(charModal.querySelectorAll('.sc-98a8819c-1.limvpr img')).filter(img => {
          const style = window.getComputedStyle(img);
          const rect = img.getBoundingClientRect();
          return (
            img.src.includes('/characters/thumb/chara_stand_') &&
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            rect.width > 0 && rect.height > 0
          );
        });
        return imgs.map(img => ({
          src: img.src,
          alt: img.alt || '',
          title: img.title || ''
        }));
      });
      characterImgs = Array.from(new Map([...characterImgs, ...newImgs].map(img => [img.src, img])).values());
      // Log số lượng lấy được
      console.log(`Scroll: found ${characterImgs.length} character images.`);
    } while (characterImgs.length > lastLength);
    options.characters = characterImgs;
    await page.keyboard.press('Escape');
    await waitTimeout(1000);
  } catch (error) {
    console.error('❌ Error getting options:', error);
  }
  return options;
}

async function selectCard(page, cardIndex, cardObj) {
  console.log(`   🎴 Selecting card ${cardIndex + 1}`);
  try {
    const cardSelector = `#boxSupport${cardIndex + 1}`;
    await page.click(cardSelector);
    await waitTimeout(1500);
    const selected = await page.evaluate((targetSrc) => {
      const modals = document.querySelectorAll('[role="dialog"]');
      if (modals.length < 2) return false;
      const supportModal = modals[1];
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
    await waitTimeout(1000);
  } catch (error) {
    throw new Error(`Failed to select card: ${error.message}`);
  }
}

async function selectScenario(page, scenarioName) {
  console.log(`   📖 Selecting scenario: ${scenarioName}`);
  
  try {
    await page.click('#boxScenario');
    await waitTimeout(1500);
    
    const selected = await page.evaluate((targetName) => {
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
    }, scenarioName);
    
    if (!selected) {
      throw new Error(`Scenario "${scenarioName}" not found`);
    }
    
    await waitTimeout(1000);
    
  } catch (error) {
    throw new Error(`Failed to select scenario: ${error.message}`);
  }
}

async function selectCharacter(page, characterObj) {
  console.log(`   👤 Selecting character`);
  try {
    await page.click('#boxChar');
    await waitTimeout(1500);
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
    await waitTimeout(1000);
  } catch (error) {
    throw new Error(`Failed to select character: ${error.message}`);
  }
}

async function scrapeEvents(page) {
  return await scrapeEventsFromEventViewer(page);
}

async function scrapeEventsFromEventViewer(page) {
  console.log('  📋 Scraping events from Event Viewer...');
  try {
    await page.waitForSelector('.compatibility_result_box__OpJCO', { timeout: 10000 });
    // Lấy tất cả hình (character + 6 support card) trong Event Viewer
    const imageHandles = await page.$$('.compatibility_result_box__OpJCO img');
    console.log(`  🖱️ Found ${imageHandles.length} images in Event Viewer`);
    let allEvents = [];
    for (let i = 0; i < imageHandles.length; i++) {
      // Scroll vào hình để chắc chắn nó hiện trên màn hình
      await imageHandles[i].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
      // Click hình
      await imageHandles[i].click();
      await waitTimeout(1200);
      // Lấy event items sau khi click
      const eventHandles = await page.$$('.compatibility_viewer_item__SWULM');
      for (let j = 0; j < eventHandles.length; j++) {
        await eventHandles[j].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
        await eventHandles[j].click();
        await waitTimeout(800);
        // Lấy popup chi tiết (tooltip)
        const detail = await page.evaluate(() => {
          const tippy = document.querySelector('.tippy-box');
          if (!tippy) return null;
          const eventName = tippy.querySelector('.tooltips_ttable_heading__jlJcE')?.textContent?.trim() || '';
          const rows = Array.from(tippy.querySelectorAll('.tooltips_ttable__dvIzv tr'));
          const choices = rows.map(row => {
            const tds = row.querySelectorAll('td');
            return {
              choice: tds[0]?.textContent?.trim() || '',
              effect: tds[1]?.textContent?.trim() || ''
            };
          });
          return { event: eventName, choices };
        });
        if (detail && detail.event) {
          allEvents.push(detail);
        }
        // Đóng tooltip nếu cần
        await page.keyboard.press('Escape');
        await waitTimeout(200);
      }
    }
    // Lọc trùng event (theo tên event)
    const uniqueEvents = Array.from(new Map(allEvents.map(e => [e.event, e])).values());
    console.log(`  ✅ Found ${uniqueEvents.length} unique events with detail`);
    return uniqueEvents;
  } catch (error) {
    console.log('  ❌ Error scraping events:', error.message);
    return [];
  }
}

// Helper to enable settings in Event Viewer
async function enableEventViewerSettings(page) {
  // Mở Settings
  await page.evaluate(() => {
    // Tìm nút Settings trong Event Viewer
    const eventViewer = document.querySelector('.compatibility_result_box__OpJCO');
    if (!eventViewer) return;
    const settingsBtn = Array.from(eventViewer.querySelectorAll('button, [role="button"]')).find(
      btn => btn.textContent && btn.textContent.toLowerCase().includes('settings')
    );
    if (settingsBtn) settingsBtn.click();
  });
  await waitTimeout(1000);

  // Bật Show all cards at once
  await page.evaluate(() => {
    const modal = document.querySelector('[role="dialog"]');
    if (!modal) return;
    const showAll = Array.from(modal.querySelectorAll('label')).find(
      el => el.textContent && el.textContent.toLowerCase().includes('show all cards')
    );
    if (showAll) {
      const input = showAll.querySelector('input[type="checkbox"]');
      if (input && !input.checked) input.click();
    }
  });
  await waitTimeout(500);

  // Bật Expand events
  await page.evaluate(() => {
    const modal = document.querySelector('[role="dialog"]');
    if (!modal) return;
    const expand = Array.from(modal.querySelectorAll('label')).find(
      el => el.textContent && el.textContent.toLowerCase().includes('expand events')
    );
    if (expand) {
      const input = expand.querySelector('input[type="checkbox"]');
      if (input && !input.checked) input.click();
    }
  });
  await waitTimeout(500);

  // Đóng modal Settings (bấm lại nút Settings)
  await page.evaluate(() => {
    const modal = document.querySelector('[role="dialog"]');
    if (modal) {
      // Tìm nút Close hoặc Settings để đóng
      const closeBtn = Array.from(modal.querySelectorAll('button, [role="button"]')).find(
        btn => btn.textContent && (btn.textContent.toLowerCase().includes('settings') || btn.textContent.toLowerCase().includes('close'))
      );
      if (closeBtn) closeBtn.click();
    }
  });
  await waitTimeout(1000);
}

// Run the scraper
scrapeTrainingEvents().catch(console.error); 