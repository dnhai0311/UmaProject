const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, '..', 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);

function loadJsonFile(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error.message);
    return null;
  }
}



const SPEED_FACTOR = 0.3;
function waitTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms * SPEED_FACTOR));
}

function stableStringify(obj) {
  const keys = [];
  JSON.stringify(obj, (k, v) => {
    keys.push(k);
    return v;
  });
  keys.sort();
  return JSON.stringify(obj, keys);
}

async function collectAllEventHandles(page) {
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
async function scrollToAndClick(page, selector, description = 'element') {
  console.log(`  🎯 Scrolling to and clicking ${description} (${selector})`);
  
  await page.waitForSelector(selector, { timeout: 8000 });
  
  const element = await page.$(selector);
  if (!element) {
    throw new Error(`${description} not found: ${selector}`);
  }
  
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
  
  await page.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    const scrollTop = window.pageYOffset + rect.top - (window.innerHeight / 2);
    window.scrollTo({
      top: scrollTop,
      behavior: 'auto'
    });
  }, element);
  
  await waitTimeout(400);
  
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
  
  const fs = require('fs');
  const outputFile = path.join(DATA_DIR, 'events.json');
  let previousData = null;
  if (fs.existsSync(outputFile)) {
    previousData = loadJsonFile(outputFile);
    if(previousData){
      console.log(`🔄 Loaded previous events database with ${previousData.events?.length||0} events`);
    }
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
    
    page.setDefaultTimeout(20000);
    page.setDefaultNavigationTimeout(30000);
    
    console.log('📱 Navigating to Training Event Helper page...');
    await page.goto('https://gametora.com/umamusume/training-event-helper', {
      waitUntil: 'domcontentloaded', // Thay đổi từ networkidle2 sang domcontentloaded để nhanh hơn
      timeout: 30000
    });

    await waitTimeout(2000); // Giảm wait time

    const options = await getAvailableOptions(page);
    console.log(`✅ Found ${options.supportCards.length} support cards, ${options.scenarios.length} scenarios, ${options.characters.length} characters`);
    

    const combinations = [];

    options.characters.forEach((char, idx) => {
      const scenario = options.scenarios[idx % options.scenarios.length] || 'URA Finals';
      combinations.push({
        character: char,
        scenario,
        cards: [],
        allowScenarioEvent: idx < options.scenarios.length
      });
    });

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

    const extractId = (obj)=>{
      if(!obj) return null;
      if(obj.id) return String(obj.id);
      const str=(obj.src||obj.alt||obj.title||'');
      const nums=str.match(/\d+/g);
      if(!nums||nums.length===0) return null;
      nums.sort((a,b)=>b.length-a.length);
      return nums[0];
    };
    let doneCharIds = new Set();
    let doneCardIds = new Set();

    if(previousData){
      doneCharIds = new Set((previousData.characters||[]).map(c=>String(c.id)));
      doneCardIds = new Set((previousData.supportCards||[]).map(s=>String(s.id)));
      
      const before = combinations.length;
      const filtered = combinations.filter(comb=>{
        const cid = comb.character ? extractId(comb.character) : null;
        if(cid && doneCharIds.has(cid)) return false;
        const sid = (comb.cards && comb.cards.length>0) ? extractId(comb.cards[0]) : null;
        if(sid && doneCardIds.has(sid)) return false;
        return true;
      });
      combinations.length=0; combinations.push(...filtered);
      console.log(`🪄 Filtered combinations: removed ${before - combinations.length}, remaining ${combinations.length}`);
    }

    const allEvents = [];
    let combinationCount = 0;
    const totalCombinations = combinations.length;

    for (const combination of combinations) {
      const cid = combination.character ? extractId(combination.character) : null;
      const sid = (combination.cards && combination.cards.length>0) ? extractId(combination.cards[0]) : null;
      console.log(`   🔍 Compare IDs - cid=${cid} ; sid=${sid}`);
      combinationCount++;
      console.log(`\n🔄 Testing combination ${combinationCount}/${totalCombinations}`);
      console.log(`   🎴 Testing: ${combination.cards.length} cards + ${combination.scenario} + ${combination.character?.alt || combination.character?.title || 'Unknown'}`);

      try {
        await clearCurrentState(page);
        
        if (combination.cards.length > 0) {
          for (let i = 0; i < combination.cards.length; i++) {
            try {
              await selectCard(page, i, combination.cards[i]);
              if (i < combination.cards.length - 1) await waitTimeout(300);
            } catch (cardError) {
              console.log(`   ⚠️ Error selecting card ${i + 1}: ${cardError.message}`);
            }
          }
        }
        
        try {
          await selectScenario(page, combination.scenario);
          await waitTimeout(400);
        } catch (scenarioError) {
          console.log(`   ⚠️ Error selecting scenario: ${scenarioError.message}`);
        }
        
        if (combination.character) {
          try {
            await selectCharacter(page, combination.character);
            await waitTimeout(600);
          } catch (characterError) {
            console.log(`   ⚠️ Error selecting character: ${characterError.message}`);
          }
        }
        
        await waitTimeout(3000);
        
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
        
        saveResultsToJSON(allEvents, combinationCount, totalCombinations, previousData);
        
      } catch (error) {
        console.error(`❌ Error testing combination: ${error.message}`);
        allEvents.push({
          combination,
          events: [],
          error: error.message
        });
        
        saveResultsToJSON(allEvents, combinationCount, totalCombinations, previousData);
        
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

    saveResultsToJSON(allEvents, combinationCount, totalCombinations, previousData);

    console.log('\n🎉 Scraping completed!');
    console.log(`📊 Total combinations tested: ${combinationCount}`);
    console.log(`📊 Total event combinations found: ${allEvents.filter(e => e.events.length > 0).length}`);
    
    try {
      const finalResults = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'events.json'), 'utf8'));
      
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
    console.log('  📋 Getting support cards from modal...');
    
    await scrollToAndClick(page, '#boxSupport1', 'support slot 1');
    await waitTimeout(2000); // Giảm wait time cho modal load
    
    await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
    
    const modalCount = await page.evaluate(() => {
      return document.querySelectorAll('[role="dialog"]').length;
    });
    
    console.log(`  🔍 Found ${modalCount} modal(s) after clicking support slot`);
    
    const supportCards = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      for (const modal of modals) {
        const supportImgs = modal.querySelectorAll('img[src*="support_card_s_"]');
        if (supportImgs.length > 0) {
          console.log('Getting visible cards from modal with', supportImgs.length, 'total images');
          
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
            let cardName = img.alt || img.title || '';
            
            const parent = img.closest('[class*="card"], [class*="support"], [class*="item"]');
            if (parent) {
              const nameElement = parent.querySelector('[class*="name"], [class*="title"], [class*="text"]');
              if (nameElement && nameElement.textContent.trim()) {
                cardName = nameElement.textContent.trim();
              }
            }
            
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
    
    
    await page.keyboard.press('Escape');
    await waitTimeout(1000); // Giảm wait time
    
    try {
      await page.evaluate(() => {
        return document.readyState;
      });
    } catch (error) {
      console.log('  ⚠️ Page seems to be detached, refreshing...');
      await page.reload({ waitUntil: 'networkidle2' });
      await waitTimeout(3000);
    }
    
    console.log('  👤 Getting characters from modal...');
    let characterImgs = [];
    
    try {
      await scrollToAndClick(page, '#boxChar', 'character box');
      await waitTimeout(1500); // Giảm wait time
      
      await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
      
      characterImgs = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        console.log('Found', modals.length, 'modals');
        
        if (modals.length === 0) return [];
        
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
          for (let i = 0; i < modals.length; i++) {
            const modal = modals[i];
            const allImgs = modal.querySelectorAll('img');
            console.log(`Modal ${i}: Total images: ${allImgs.length}`);
            
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
          let charName = img.alt || img.title || '';
          
          const parent = img.closest('[class*="character"], [class*="chara"], [class*="item"], [class*="card"]');
          if (parent) {
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
                if (text.length > 0 && text.length < 50 && !text.includes('http') && !text.includes('www')) {
                  charName = text;
                  break;
                }
              }
            }
            
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
    
    
    console.log('  📖 Getting scenarios from modal...');
    let scenarios = [];
    
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
            const scenarioSelector = '.tooltips_tooltip_striped__0p4n9 > div > div > .fVBhhN.sc-9ae1b094-0 > .fpCljy.sc-9ae1b094-1 > span';
            const scenarioElements = document.querySelectorAll(scenarioSelector);
            
            return Array.from(scenarioElements).map(element => {
              return element.textContent.trim();
            }).filter(text => text.length > 0);
            
          } catch (error) {
            console.log('Error with user selector, falling back to old method');
            
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
    
    await page.waitForSelector('[role="dialog"]', { timeout: 8000 });
    
    const selected = await page.evaluate((targetSrc) => {
      const modals = document.querySelectorAll('[role="dialog"]');
      if (modals.length === 0) return false;
      
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
    
    try {
      await page.keyboard.press('Escape');
      await waitTimeout(300);
    } catch (closeError) {
      console.log(`   ⚠️ Warning: Could not close modal: ${closeError.message}`);
    }
    
  } catch (error) {
    try {
      await page.keyboard.press('Escape');
      await waitTimeout(300);
    } catch (closeError) {
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
        const scenarioSelector = '.tooltips_tooltip_striped__0p4n9 > div > div > .fVBhhN.sc-9ae1b094-0 > .fpCljy.sc-9ae1b094-1 > span';
        const scenarioElements = document.querySelectorAll(scenarioSelector);
        
        const targetElement = Array.from(scenarioElements).find(element => {
          return element.textContent.trim() === targetName;
        });
        
        if (targetElement) {
          targetElement.click();
          return true;
        }
        
        return false;
      } catch (error) {
        console.log('Error with scenario selector:', error.message);
        
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
  console.log('  📋 Collecting events by cycling owner icons (rev2)');
  try {
    await page.waitForSelector('.compatibility_result_box__OpJCO', { timeout: 15000 });
    
    let iconHandles = await page.$$('div.filters_viewer_image__TifjQ, div.filters_viewer_image_active__DA901');
    if (iconHandles.length === 0) {
      console.log('  ⚠️  No owner icons found');
        return [];
    }

    const uniqueIcons = [];
    const seenIds = new Set();
    for (const h of iconHandles) {
      const id = await (await h.getProperty('id')).jsonValue();
      if (!seenIds.has(id)) {
        uniqueIcons.push(h);
        seenIds.add(id);
      }
    }

    console.log(`  📸 Found ${uniqueIcons.length} owner icons to iterate`);

    const allEvents = [];

    for (let idx = 0; idx < uniqueIcons.length; idx++) {
      const icon = uniqueIcons[idx];
      try {
        await icon.evaluate(el => el.scrollIntoView({ behavior: 'auto', block: 'center' }));
            await waitTimeout(200);
        await icon.click();
        await waitTimeout(800); // allow viewer switch
      } catch (clickErr) {
        console.log(`  ⚠️  Cannot click icon ${idx + 1}: ${clickErr.message}`);
        continue;
      }

      const ownerHtmlId = await (await icon.getProperty('id')).jsonValue();

      const ownerInfo = await page.evaluate(() => {
        const top = document.querySelector('.eventhelper_viewer_top_label__0DVa0');
        const name = top ? (top.querySelector('b')?.textContent?.trim() || 'Unknown') : 'Unknown';
        const a = top ? top.querySelector('a[href]') : null;
        let type = 'scenario';
        let url = a ? a.href : null;
        if (url) {
          if (url.includes('/characters/')) type = 'character';
          else if (url.includes('/supports/')) type = 'support';
        }
        const activeIcon = document.querySelector('.filters_viewer_image_active__DA901 img');
        const imageSrc = activeIcon ? activeIcon.src : null;
        return { name, type, url, imageSrc };
      });

        let ownerId = null;
      if (ownerInfo.url) {
        const m = ownerInfo.url.match(/(\d+)/);
        if (m) ownerId = m[1];
      }
      if (!ownerId && ownerHtmlId) {
        const m = ownerHtmlId.match(/(\d+)/);
        if (m) ownerId = m[1];
      }
      if (!ownerId) ownerId = ownerHtmlId || ownerInfo.name;

      console.log(`    ▶ Owner ${idx + 1}/${uniqueIcons.length}: ${ownerInfo.type} – ${ownerInfo.name} (id=${ownerId})`);

      const viewerBox = await page.$('.compatibility_result_box__OpJCO');
      if (!viewerBox) {
        console.log('      ⚠️  No viewer after activation');
        continue;
      }
      let prevCount = -1;
      let stable = 0;
      while (stable < 2) {
        await viewerBox.evaluate(el => el.scrollBy(0, el.scrollHeight));
        await waitTimeout(250);
        const cur = await viewerBox.evaluate(el => el.querySelectorAll('.compatibility_viewer_item__SWULM').length);
        if (cur === prevCount) stable++; else { prevCount = cur; stable = 0; }
      }

      const eventItems = await viewerBox.$$('.compatibility_viewer_item__SWULM');
      console.log(`      • Events found: ${eventItems.length}`);

      for (let eIdx = 0; eIdx < eventItems.length; eIdx++) {
        try {
          const ev = eventItems[eIdx];
          await ev.evaluate(el => el.scrollIntoView({ behavior: 'auto', block: 'center' }));
          await waitTimeout(100);
          await ev.click();
          await waitTimeout(400);

          const detail = await page.evaluate(() => {
            function clean(name) {
              if (!name) return ''; let t = name.trim(); if (t.startsWith('//')) return null; t = t.replace(/^(\d{1,2}:\d{2}|\(\d+\)|\d+)\s*\/\s*/, ''); t = t.replace(/^\/\/+/, ''); if (t.length < 2) return null; return t;
            }
            const tippy = document.querySelector('.tippy-box'); if (!tippy) return null;
            const eventName = tippy.querySelector('.tooltips_ttable_heading__jlJcE')?.textContent?.trim() || '';
            const groups = ['Costume Events','Events With Choices','Date Events','Special Events','After a Race','Events Without Choices','Chain Events','Random Events','Secret Events'];
            let type = 'Unknown';
            const clicked = document.querySelector('.compatibility_viewer_item__SWULM.clicked') || document.querySelector('.compatibility_viewer_item__SWULM:hover');
            if (clicked) {
              let p = clicked.parentElement;
              while (p && p !== document.body) {
                const txt = p.textContent; if (groups.some(g=>txt.includes(g))) { type = groups.find(g=>txt.includes(g)); break; } p = p.parentElement; }
            }
            const parseLine = txt => { const m = txt.match(/^([A-Za-z ]+?)\s*([+-]?-?\d+)/); if (m) return { kind:'stat',raw:txt,stat:m[1].trim(),amount:parseInt(m[2])}; const l = txt.toLowerCase(); if (l.startsWith('obtain')&&l.includes('skill')) return {kind:'skill',raw:txt}; if (l.includes('status')) return {kind:'status',raw:txt}; return {kind:'text',raw:txt}; };
            const pushSeg = (arr, t) => { const parts = t.split(/\s+or\s+/i); if (parts.length>1){arr.push(parseLine(parts[0]));arr.push({kind:'divider_or',raw:'or'});parts.slice(1).forEach(p=>arr.push(parseLine(p)));} else arr.push(parseLine(t));};
            let choices=[]; const tbl=tippy.querySelector('table.tooltips_ttable__dvIzv'); if(tbl){tbl.querySelectorAll('tr').forEach(tr=>{const tds=tr.querySelectorAll('td');if(tds.length<2)return;const opt=tds[0].textContent.trim();const segs=[];tds[1].childNodes.forEach(n=>{const txt=n.textContent.trim();if(!txt)return;if(n.className&&n.className.includes('eventhelper_random_text'))segs.push({kind:'random_header',raw:txt});else if(n.className&&n.className.includes('eventhelper_divider_or'))segs.push({kind:'divider_or',raw:txt||'or'});else pushSeg(segs,txt);});if(segs.length)choices.push({choice:opt,effects:segs});});} else {const cell=tippy.querySelector('.tooltips_ttable_cell___3NMF');if(cell){const segs=[];cell.querySelectorAll('div').forEach(d=>{const t=d.textContent.trim();if(t)pushSeg(segs,t);});if(segs.length)choices.push({choice:'',effects:segs});}}
            const cleanName=clean(eventName); if(!cleanName) return null; return {event:cleanName,type,choices};
            });
            
            if (detail && detail.event) {
            allEvents.push({ ownerId, ownerType: ownerInfo.type, ownerName: ownerInfo.name, ownerImage: ownerInfo.imageSrc, ownerUrl: ownerInfo.url, event: detail });
            console.log(`        ✅ ${detail.event}`);
          }

            await page.keyboard.press('Escape');
          await page.mouse.click(10, 10);
          await waitTimeout(60);
        } catch (evErr) {
          console.log(`        ⚠️  Event ${eIdx + 1}: ${evErr.message}`);
        }
      }
    }
    
    return allEvents;
  } catch (err) {
    console.log('  ❌ Error in event collection rev2:', err.message);
    return [];
  }
}

async function clearCurrentState(page) {
  try {
    console.log('  🗑️ Clearing current state...');
    
    await page.keyboard.press('Escape');
    await waitTimeout(300);
    
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

function saveResultsToJSON(allEvents, combinationCount, totalCombinations, previousData) {
  try {
    console.log(`  💾 Saving progress to JSON (${combinationCount}/${totalCombinations})...`);
    

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

    let eventCounter = 0;
    const charMap = new Map();
    const cardMap = new Map();
    const scenarioMap = new Map();
    const eventDedupMap = new Map(); // Track unique events

    if(previousData){
      if(Array.isArray(previousData.events)){
        previousData.events.forEach(ev=>{
          optimizedData.events.push(ev);
          const num=parseInt((ev.id||'').split('_')[1]);
          if(!isNaN(num) && num>eventCounter) eventCounter=num;
          const dkey=stableStringify({event:ev.event,type:ev.type,choices:ev.choices});
          eventDedupMap.set(dkey, ev.id);
        });
      }

      const mergeOwner = (sourceArr, targetMap)=>{
        if(Array.isArray(sourceArr)){
          sourceArr.forEach(rec=>{
            if(!targetMap.has(rec.id)){
              const gMap = new Map(rec.eventGroups.map(g=>[g.type,new Set(g.eventIds)]));
              targetMap.set(rec.id,{id:rec.id,name:rec.name,groups:gMap});
            } else {
              const existing=targetMap.get(rec.id);
              rec.eventGroups.forEach(g=>{
                if(!existing.groups.has(g.type)) existing.groups.set(g.type,new Set());
                g.eventIds.forEach(eid=> existing.groups.get(g.type).add(eid));
              });
            }
          });
        }
      };
      mergeOwner(previousData.characters,charMap);
      mergeOwner(previousData.supportCards,cardMap);
      mergeOwner(previousData.scenarios,scenarioMap);
    }

    allEvents.forEach(result => {
      if (result.events && result.events.length > 0) {
        result.events.forEach(evObj => {
          const ev = evObj.event;
          const ownerType = evObj.ownerType;
          const ownerName = evObj.ownerName;
          const ownerId = evObj.ownerId;

          const dedupKey = stableStringify({
            event: ev.event,
            type: ev.type,
            choices: ev.choices
          });

          const addOwnerLink = (targetMap, eventType, eid) => {
            if (!targetMap.has(ownerId)) {
              targetMap.set(ownerId, { id: ownerId, name: ownerName, groups: new Map() });
            }
            const rec = targetMap.get(ownerId);
            if (!rec.groups.has(eventType)) rec.groups.set(eventType, new Set());
            rec.groups.get(eventType).add(eid);
          };

          if (eventDedupMap.has(dedupKey)) {
            const existingEventId = eventDedupMap.get(dedupKey);
            const eventType = ev.type || 'Unknown';
            const targetMap = ownerType === 'character' ? charMap : ownerType === 'support' ? cardMap : ownerType === 'scenario' ? scenarioMap : null;
            if (targetMap) addOwnerLink(targetMap, eventType, existingEventId);
          } else {
            const eventId = `event_${++eventCounter}`;
            eventDedupMap.set(dedupKey, eventId);
            optimizedData.events.push({ id: eventId, ...ev });

            const eventType = ev.type || 'Unknown';
            const targetMap = ownerType === 'character' ? charMap : ownerType === 'support' ? cardMap : ownerType === 'scenario' ? scenarioMap : null;
            if (targetMap) addOwnerLink(targetMap, eventType, eventId);
          }
        });
      }
    });
    console.log(`  ✅ Collected ${optimizedData.events.length} unique events and linked to owners (duplicates filtered)`);

    charMap.forEach(record => {
      optimizedData.characters.push({
        id: record.id,
        name: record.name,
        eventGroups: Array.from(record.groups.entries()).map(([type, ids]) => ({ type, eventIds: Array.from(ids) }))
      });
    });

    cardMap.forEach(record => {
      optimizedData.supportCards.push({
        id: record.id,
        name: record.name,
        eventGroups: Array.from(record.groups.entries()).map(([type, ids]) => ({ type, eventIds: Array.from(ids) }))
      });
    });

    scenarioMap.forEach(record => {
      optimizedData.scenarios.push({
        id: record.id,
        name: record.name,
        eventGroups: Array.from(record.groups.entries()).map(([type, ids]) => ({ type, eventIds: Array.from(ids) }))
      });
    });

    const enhancedData = optimizedData;


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

    enhancedData.events.forEach(ev => {
      if (ev.choices) {
        ev.choices.forEach(ch => {
          if (ch && Array.isArray(ch.effects)) {
            ch.effects.forEach(seg => {
              if (seg && /hint/i.test(seg.raw || '')) {
                // Treat any effect containing "hint" as a skill regardless of initial kind
                seg.kind = 'skill';
                const hm = seg.raw.match(/hint\s*\+?(-?\d+)/i);
                if (hm) seg.hint = parseInt(hm[1]);
              }
              if (seg && !seg.detail) {
                if (seg.kind === 'skill') {
                  const skill = findSkill(seg.raw);
                  if (skill) {
                    seg.detail = { effect: skill.effect, name: skill.name };
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
                    seg.detail = { effect: skillMatch.effect, name: skillMatch.name };
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

    
    fs.writeFileSync(
      path.join(DATA_DIR, 'events.json'),
      JSON.stringify(enhancedData, null, 2)
    );

    const linkedIds = new Set();
    [...enhancedData.characters, ...enhancedData.supportCards, ...enhancedData.scenarios]
      .forEach(owner => owner.eventGroups.forEach(g => g.eventIds.forEach(id => linkedIds.add(id))));
    const unlinked = enhancedData.events.filter(ev => !linkedIds.has(ev.id));
    console.log(`  🔎 Validation: ${unlinked.length} / ${enhancedData.events.length} events chưa gắn owner`);


    console.log(`  ✅ Progress saved: ${combinationCount}/${totalCombinations} (${enhancedData.progress.percentage}%)`);
    console.log(`     👤 Characters: ${enhancedData.characters.length}`);
    console.log(`     🎴 Support Cards: ${enhancedData.supportCards.length}`);
    console.log(`     📖 Scenarios: ${enhancedData.scenarios.length}`);
    console.log(`     📦 Unique events: ${enhancedData.events.length}`);
  } catch (error) {
    console.log(`  ⚠️ Error saving progress: ${error.message}`);
  }
}

scrapeTrainingEvents(true).catch(console.error); 