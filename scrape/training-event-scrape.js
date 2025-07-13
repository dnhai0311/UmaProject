const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Utility function for timeout
function waitTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper function to scroll to element and ensure it's visible before clicking
async function scrollToAndClick(page, selector, description = 'element') {
  console.log(`  🎯 Scrolling to and clicking ${description} (${selector})`);
  
  // Find element
  const element = await page.$(selector);
  if (!element) {
    throw new Error(`${description} not found: ${selector}`);
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
  
  // Wait for scroll to complete
  await waitTimeout(1000);
  
  // Click the element
  await element.click();
  console.log(`  ✅ Successfully clicked ${description}`);
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

    await waitTimeout(3000);

    // Get available options
    const options = await getAvailableOptions(page);
    console.log(`✅ Found ${options.supportCards.length} support cards, ${options.scenarios.length} scenarios, ${options.characters.length} characters`);
    
    // Save options to file
    fs.writeFileSync(
      path.join(__dirname, 'data', 'training_options.json'),
      JSON.stringify(options, null, 2)
    );
    console.log('💾 Saved options to data/training_options.json');

    // Create combinations ensuring each character, scenario, and support card is used at least once
    const combinations = [];
    const availableCharacters = options.characters.slice(0, 28); // Use all characters
    const availableCards = options.supportCards.slice(0, 51); // Use all support cards
    const availableScenarios = options.scenarios.length > 0 ? options.scenarios : ['URA Finals'];
    
    console.log(`📊 Creating combinations with even distribution:`);
    console.log(`   👤 Characters: ${availableCharacters.length}`);
    console.log(`   🎴 Support Cards: ${availableCards.length}`);
    console.log(`   📖 Scenarios: ${availableScenarios.length}`);
    
    // Calculate how many combinations we need to cover everything
    const maxCombinations = Math.max(
      Math.ceil(availableCharacters.length / 1), // 1 character per combination
      Math.ceil(availableCards.length / 6), // 6 cards per combination
      Math.ceil(availableScenarios.length / 1) // 1 scenario per combination
    );
    
    console.log(`   🔄 Will create ${maxCombinations} combinations to cover all items`);
    
    // Helper function to get random index from unused items
    function getRandomUnusedIndex(usedIndices, max) {
      const unusedIndices = [];
      for (let i = 0; i < max; i++) {
        if (!usedIndices.includes(i)) {
          unusedIndices.push(i);
        }
      }
      if (unusedIndices.length === 0) return Math.floor(Math.random() * max); // Fallback to random if all used
      return unusedIndices[Math.floor(Math.random() * unusedIndices.length)];
    }
    
    // Helper function to get random unique indices, prioritizing unused
    function getRandomUniqueIndices(count, max, usedIndices = []) {
      const indices = [];
      const localUsed = [...usedIndices];
      
      while (indices.length < count) {
        let randomIndex;
        if (localUsed.length < max) {
          // Try to use unused items first
          randomIndex = getRandomUnusedIndex(localUsed, max);
        } else {
          // If all items used, pick random
          randomIndex = Math.floor(Math.random() * max);
        }
        
        if (!indices.includes(randomIndex)) {
          indices.push(randomIndex);
          localUsed.push(randomIndex);
        }
      }
      return indices;
    }
    
    // Track used items
    const usedCharacters = [];
    const usedScenarios = [];
    const usedCards = [];
    
    for (let i = 0; i < maxCombinations; i++) {
      // Select character (prioritize unused, then random)
      let characterIndex;
      if (usedCharacters.length < availableCharacters.length) {
        characterIndex = getRandomUnusedIndex(usedCharacters, availableCharacters.length);
      } else {
        characterIndex = Math.floor(Math.random() * availableCharacters.length);
      }
      const character = availableCharacters[characterIndex];
      usedCharacters.push(characterIndex);
      
      // Select scenario (prioritize unused, then random)
      let scenarioIndex;
      if (usedScenarios.length < availableScenarios.length) {
        scenarioIndex = getRandomUnusedIndex(usedScenarios, availableScenarios.length);
      } else {
        scenarioIndex = Math.floor(Math.random() * availableScenarios.length);
      }
      const scenario = availableScenarios[scenarioIndex];
      usedScenarios.push(scenarioIndex);
      
      // Select 6 support cards (prioritize unused, then random)
      const cardIndices = getRandomUniqueIndices(6, availableCards.length, usedCards);
      const combinationCards = cardIndices.map(index => availableCards[index]);
      usedCards.push(...cardIndices);
      
      combinations.push({
        supportCards: combinationCards,
        character: character,
        scenario: scenario
      });
      
      console.log(`   Combination ${i + 1}: Character ${characterIndex + 1}/${availableCharacters.length} (${usedCharacters.length} used), Scenario ${scenarioIndex + 1}/${availableScenarios.length} (${usedScenarios.length} used), Cards [${cardIndices.map(idx => idx + 1).join(',')}]/${availableCards.length} (${usedCards.length} used)`);
    }

    const allEvents = [];
    let combinationCount = 0;

    for (const combination of combinations) {
      combinationCount++;
      console.log(`\n🔄 Testing combination ${combinationCount}/${combinations.length}`);
      console.log(`   🎴 Testing: ${combination.supportCards.length} cards + ${combination.scenario} + ${combination.character.alt || 'Character'}`);

      try {
        // Select all 6 support cards (select first available for each slot)
        for (let i = 0; i < 6; i++) {
          await selectCard(page, i, combination.supportCards[i]);
        }
        
        // Select scenario if available
        if (combination.scenario) {
          await selectScenario(page, combination.scenario);
        }
        
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
    // Get support cards from modal (need to click a support slot first)
    console.log('  📋 Getting support cards from modal...');
    
    // Scroll to and click support slot to open modal
    await scrollToAndClick(page, '#boxSupport1', 'support slot 1');
    await waitTimeout(3000); // Wait longer for modal to fully load
    
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
          
          return visibleCards.map(img => ({
            src: img.src,
            alt: img.alt || '',
            title: img.title || ''
          }));
        }
      }
      return [];
    });
    
    options.supportCards = supportCards;
    console.log(`  ✅ Final total: ${supportCards.length} support cards found`);
    
    // Close support modal properly
    await page.keyboard.press('Escape');
    await waitTimeout(2000);
    
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
    let lastLength = 0;
    
    try {
      await scrollToAndClick(page, '#boxChar', 'character box');
      await waitTimeout(2000);
    } catch (error) {
      console.log('  ⚠️ Error clicking character box:', error.message);
      characterImgs = [];
      // Continue to scenarios with empty characters
    }
    if (characterImgs !== undefined) {
      try {
        // Get all visible characters directly without scrolling
        characterImgs = await page.evaluate(() => {
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
        
        console.log(`Found ${characterImgs.length} character images.`);
        
        await page.keyboard.press('Escape');
        await waitTimeout(1000);
        
      } catch (error) {
        console.log('  ⚠️ Error during character processing:', error.message);
        characterImgs = [];
      }
    }
    
    options.characters = characterImgs;
    console.log(`  ✅ Final total: ${characterImgs.length} characters found`);
    
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
        await waitTimeout(1000);
        
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
    await waitTimeout(1500);
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
    await waitTimeout(1000);
  } catch (error) {
    throw new Error(`Failed to select card: ${error.message}`);
  }
}

async function selectScenario(page, scenarioName) {
  console.log(`   📖 Selecting scenario: ${scenarioName}`);
  
  try {
    await scrollToAndClick(page, '#boxScenario', 'scenario box');
    await waitTimeout(1500);
    
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
    
    await waitTimeout(1000);
    
  } catch (error) {
    throw new Error(`Failed to select scenario: ${error.message}`);
  }
}

async function selectCharacter(page, characterObj) {
  console.log(`   👤 Selecting character`);
  try {
    await scrollToAndClick(page, '#boxChar', 'character box');
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
    // Wait for the specific Event Viewer (5th compatibility_result_box)
    await page.waitForSelector('div.compatibility_result_box__OpJCO:nth-of-type(5)', { timeout: 10000 });
    
    // Get all images in the specific Event Viewer
    const imageHandles = await page.$$('div.compatibility_result_box__OpJCO:nth-of-type(5) img');
    console.log(`  🖱️ Found ${imageHandles.length} images in Event Viewer (5th box)`);
    
    if (imageHandles.length === 0) {
      console.log('  ⚠️ No images found in Event Viewer, trying alternative selector...');
      // Fallback to general selector
      const fallbackHandles = await page.$$('.compatibility_result_box__OpJCO img');
      console.log(`  🔄 Found ${fallbackHandles.length} images with fallback selector`);
      return [];
    }
    
    let allEvents = [];
    
    // Click through all images sequentially by index
    for (let i = 0; i < imageHandles.length; i++) {
      console.log(`  🎯 Clicking image ${i + 1}/${imageHandles.length}`);
      
      try {
        // Scroll into view and click
        await imageHandles[i].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
        await waitTimeout(500);
        await imageHandles[i].click();
        await waitTimeout(1200);
        
        // Get event items after clicking
        const eventHandles = await page.$$('.compatibility_viewer_item__SWULM');
        console.log(`    📋 Found ${eventHandles.length} events for image ${i + 1}`);
        
        for (let j = 0; j < eventHandles.length; j++) {
          try {
            await eventHandles[j].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
            await waitTimeout(300);
            await eventHandles[j].click();
            await waitTimeout(800);
            
            // Get popup detail (tooltip)
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
              console.log(`      ✅ Added event: ${detail.event}`);
            }
            
            // Close tooltip
            await page.keyboard.press('Escape');
            await waitTimeout(200);
          } catch (eventError) {
            console.log(`    ⚠️ Error processing event ${j + 1}: ${eventError.message}`);
          }
        }
      } catch (imageError) {
        console.log(`  ⚠️ Error clicking image ${i + 1}: ${imageError.message}`);
      }
    }
    
    // Filter duplicate events (by event name)
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