const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Utility function for timeout
function waitTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
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
  const outputFile = './data/all_training_events.json';
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
    
    // Save options to file
    fs.writeFileSync(
      path.join(__dirname, 'data', 'training_options.json'),
      JSON.stringify(options, null, 2)
    );
    console.log('💾 Saved options to data/training_options.json');

    // Lấy toàn bộ dữ liệu: tất cả support cards, nhân vật, scenarios
    const combinations = [];
    const availableCharacters = options.characters; // Lấy tất cả characters
    const availableCards = options.supportCards; // Lấy tất cả support cards
    const availableScenarios = options.scenarios.length > 0 ? options.scenarios : ['URA Finals']; // Lấy tất cả scenarios
    
    console.log(`📊 Creating optimized combinations:`);
    console.log(`   👤 Characters: ${availableCharacters.length}`);
    console.log(`   🎴 Support Cards: ${availableCards.length}`);
    console.log(`   📖 Scenarios: ${availableScenarios.length}`);
    
    // Tối ưu hóa combinations theo yêu cầu
    // Tính toán số lượng combinations cần thiết để cover toàn bộ dữ liệu
    
    const totalCards = availableCards.length;
    const totalCharacters = availableCharacters.length;
    const totalScenarios = availableScenarios.length;
    
    // Tính số lần cần chọn 6 cards để cover tất cả cards
    const fullCardCombinations = Math.ceil(totalCards / 6);
    
    // Tính số cards còn lại sau khi chọn đủ 6 cards
    const remainingCards = totalCards % 6;
    
    // Tính tổng số combinations cần thiết
    // Phải đảm bảo mỗi nhân vật được test ít nhất 1 lần
    const minCombinationsForCharacters = totalCharacters;
    const combinationsForCards = fullCardCombinations + (remainingCards > 0 ? 1 : 0);
    
    // Lấy số lớn hơn để đảm bảo cover cả cards và characters
    const totalCombinations = Math.max(minCombinationsForCharacters, combinationsForCards);
    
    console.log(`   🔢 Calculation:`);
    console.log(`      Full card combinations (6 cards each): ${fullCardCombinations}`);
    console.log(`      Remaining cards: ${remainingCards}`);
    console.log(`      Combinations needed for cards: ${combinationsForCards}`);
    console.log(`      Combinations needed for characters: ${minCombinationsForCharacters}`);
    console.log(`      Total combinations needed: ${totalCombinations} (max of both)`);
    
    const usedCharacters = [];
    const usedScenarios = [];
    const usedCards = [];
    
    for (let i = 0; i < totalCombinations; i++) {
      // Select character (prioritize unused, then random)
      let characterIndex;
      if (usedCharacters.length < totalCharacters) {
        characterIndex = getRandomUnusedIndex(usedCharacters, totalCharacters);
      } else {
        characterIndex = Math.floor(Math.random() * totalCharacters);
      }
      const character = availableCharacters[characterIndex];
      usedCharacters.push(characterIndex);
      
      // Select scenario (prioritize unused, then random)
      let scenarioIndex;
      if (usedScenarios.length < totalScenarios) {
        scenarioIndex = getRandomUnusedIndex(usedScenarios, totalScenarios);
      } else {
        scenarioIndex = Math.floor(Math.random() * totalScenarios);
      }
      const scenario = availableScenarios[scenarioIndex];
      usedScenarios.push(scenarioIndex);
      
      // Select cards based on combination number
      let cardCount;
      if (i < combinationsForCards) {
        // Các lần trong phạm vi cards cần thiết
        if (i < fullCardCombinations - 1) {
          // Các lần đầu: chọn 6 cards
          cardCount = 6;
        } else if (i === fullCardCombinations - 1) {
          // Lần cuối cùng của full combinations: chọn 6 cards hoặc ít hơn nếu cần
          cardCount = Math.min(6, totalCards - (fullCardCombinations - 1) * 6);
        } else if (remainingCards > 0) {
          // Lần cuối cùng: chọn cards còn lại (chỉ nếu có cards còn lại)
          cardCount = remainingCards;
        } else {
          // Không có cards còn lại
          cardCount = 0;
        }
      } else {
        // Các lần còn lại (để cover characters): chọn 6 cards hoặc ít hơn
        const remainingUnusedCards = totalCards - usedCards.length;
        cardCount = Math.min(6, Math.max(0, remainingUnusedCards));
      }
      
      let combinationCards = [];
      if (cardCount > 0) {
        const cardIndices = getRandomUniqueIndices(cardCount, totalCards, usedCards);
        combinationCards = cardIndices.map(index => availableCards[index]);
        usedCards.push(...cardIndices);
      }
      
      combinations.push({
        character,
        scenario,
        cards: combinationCards
      });
      
      console.log(`   Combination ${i + 1}: Character ${characterIndex + 1}/${totalCharacters} (${usedCharacters.length} used), Scenario ${scenarioIndex + 1}/${totalScenarios} (${usedScenarios.length} used), Cards: ${combinationCards.length}/${cardCount} (${usedCards.length} used)`);
      console.log(`   📋 Combination details:`);
      console.log(`      👤 Character: ${character.alt || character.title || 'Unknown'}`);
      console.log(`      📖 Scenario: ${scenario}`);
      console.log(`      🎴 Cards: ${combinationCards.length} cards`);
    }

    const allEvents = [];
    let combinationCount = 0;

    for (const combination of combinations) {
      combinationCount++;
      console.log(`\n🔄 Testing combination ${combinationCount}/${combinations.length}`);
      console.log(`   🎴 Testing: ${combination.cards.length} cards + ${combination.scenario} + ${combination.character.alt || combination.character.title || 'Unknown'}`);

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
        
        // Select character
        try {
          await selectCharacter(page, combination.character);
          await waitTimeout(600);
        } catch (characterError) {
          console.log(`   ⚠️ Error selecting character: ${characterError.message}`);
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
      const finalResults = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'all_training_events.json'), 'utf8'));
      
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
      console.log(`      Character: ${result.combination.character.alt || result.combination.character.title || 'Unknown'}`);
      console.log(`      Scenario: ${result.combination.scenario}`);
      console.log(`      Cards: ${result.combination.cards.length} cards`);
      console.log(`      Events found: ${result.events.length}`);
      if (result.error) {
        console.log(`      Error: ${result.error}`);
      }
    });
    
    console.log('\n💾 Results saved to data/all_training_events.json');
    console.log('📁 File location: ' + path.join(__dirname, 'data', 'all_training_events.json'));
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

async function scrapeEvents(page) {
  return await scrapeEventsFromEventViewer(page);
}

async function scrapeEventsFromEventViewer(page) {
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
    
    // Click through all images sequentially by index
    for (let i = 0; i < imageHandles.length; i++) {
      console.log(`  🎯 Clicking image ${i + 1}/${imageHandles.length}`);
      
      try {
        // Scroll into view and click
        await imageHandles[i].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
        await waitTimeout(300);
        await imageHandles[i].click();
        await waitTimeout(800);
        
        // Get event items after clicking
        const eventHandles = await page.$$('.compatibility_viewer_item__SWULM');
        console.log(`    📋 Found ${eventHandles.length} events for image ${i + 1}`);
        
        for (let j = 0; j < eventHandles.length; j++) {
          try {
            await eventHandles[j].evaluate(el => el.scrollIntoView({behavior: 'auto', block: 'center'}));
            await waitTimeout(200);
            await eventHandles[j].click();
            await waitTimeout(500);
            
            // Get popup detail (tooltip)
            const detail = await page.evaluate(() => {
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

              const rows = Array.from(tippy.querySelectorAll('.tooltips_ttable__dvIzv tr'));
              const choices = rows.map(row => {
                const tds = row.querySelectorAll('td');
                const choiceText = tds[0]?.textContent?.trim() || '';
                const effectText = tds[1]?.textContent?.trim() || '';
                
                // Tách các effect thành mảng riêng biệt
                // Trước tiên split theo \n, sau đó split theo các pattern khác
                let effects = effectText.split('\n').filter(effect => effect.trim());
                
                // Nếu chỉ có 1 effect, thử tách theo các pattern khác
                if (effects.length === 1) {
                  const singleEffect = effects[0];
                  
                  // Tách theo các pattern phổ biến - sử dụng regex để tìm và tách
                  const patterns = [
                    {
                      regex: /([A-Za-z]+ \+[0-9]+)([A-Za-z\s]+ \+[0-9]+)/g,
                      example: "Energy +10Skill points +5"
                    },
                    {
                      regex: /([A-Za-z]+ \+[0-9]+),([A-Za-z\s]+ \+[0-9]+)/g,
                      example: "Power +8, Technique +2"
                    },
                    {
                      regex: /([A-Za-z]+ \+[0-9]+)\s+([A-Za-z\s]+ \+[0-9]+)/g,
                      example: "Wisdom +10 Skill points +15"
                    }
                  ];
                  
                  let foundPattern = false;
                  for (const pattern of patterns) {
                    const matches = [...singleEffect.matchAll(pattern.regex)];
                    if (matches.length > 0) {
                      // Tách theo pattern này
                      const parts = [];
                      let lastIndex = 0;
                      
                      for (const match of matches) {
                        if (match.index > lastIndex) {
                          parts.push(singleEffect.substring(lastIndex, match.index).trim());
                        }
                        parts.push(match[1].trim());
                        parts.push(match[2].trim());
                        lastIndex = match.index + match[0].length;
                      }
                      
                      if (lastIndex < singleEffect.length) {
                        parts.push(singleEffect.substring(lastIndex).trim());
                      }
                      
                      effects = parts.filter(part => part.trim());
                      foundPattern = true;
                      break;
                    }
                  }
                  
                                  // Nếu vẫn không tách được, thử tách theo các từ khóa
                if (!foundPattern && effects.length === 1) {
                  const keywords = ['Energy', 'Speed', 'Stamina', 'Power', 'Technique', 'Wisdom', 'Skill points', 'Motivation', 'Friendship'];
                  const parts = [];
                  let currentPart = '';
                  let lastIndex = 0;
                  
                  for (const keyword of keywords) {
                    const keywordIndex = singleEffect.indexOf(keyword, lastIndex);
                    if (keywordIndex !== -1) {
                      if (currentPart) {
                        parts.push(currentPart.trim());
                      }
                      currentPart = keyword;
                      lastIndex = keywordIndex + keyword.length;
                    }
                  }
                  
                  if (currentPart) {
                    parts.push(currentPart.trim());
                  }
                  
                  if (parts.length > 1) {
                    effects = parts;
                  }
                }
                
                // Nếu vẫn chưa tách được, thử tách theo các pattern phức tạp hơn
                if (effects.length === 1) {
                  const singleEffect = effects[0];
                  
                  // Pattern cho các trường hợp phức tạp - cải tiến logic
                  const complexPatterns = [
                    // Tách theo các từ khóa phức tạp với logic thông minh hơn
                    {
                      test: (text) => text.includes('Randomly') && text.includes('either'),
                      logic: (text) => {
                        // Xử lý trường hợp "Randomly either...or..."
                        const parts = [];
                        
                        // Tách theo "Randomly either"
                        if (text.includes('Randomly either')) {
                          parts.push('Randomly either');
                          const afterRandomly = text.substring(text.indexOf('Randomly either') + 'Randomly either'.length);
                          
                          // Tách theo "or"
                          if (afterRandomly.includes('or')) {
                            const orIndex = afterRandomly.indexOf('or');
                            const beforeOr = afterRandomly.substring(0, orIndex).trim();
                            const afterOr = afterRandomly.substring(orIndex + 2).trim();
                            
                            if (beforeOr) parts.push(beforeOr);
                            parts.push('or');
                            if (afterOr) parts.push(afterOr);
                          } else {
                            parts.push(afterRandomly.trim());
                          }
                        }
                        
                        return parts.filter(part => part.trim());
                      }
                    },
                    // Tách theo dấu ngoặc đơn với logic cải tiến
                    {
                      test: (text) => text.includes('(') && text.includes(')'),
                      logic: (text) => {
                        const parts = [];
                        let currentText = text;
                        
                        // Tìm và tách theo dấu ngoặc
                        while (currentText.includes('(') && currentText.includes(')')) {
                          const openIndex = currentText.indexOf('(');
                          const closeIndex = currentText.indexOf(')', openIndex);
                          
                          if (openIndex > 0) {
                            parts.push(currentText.substring(0, openIndex).trim());
                          }
                          parts.push(currentText.substring(openIndex, closeIndex + 1).trim());
                          currentText = currentText.substring(closeIndex + 1);
                        }
                        
                        if (currentText.trim()) {
                          parts.push(currentText.trim());
                        }
                        
                        return parts.filter(part => part.trim());
                      }
                    },
                                // Tách theo các từ khóa đơn giản hơn
            {
              test: (text) => text.includes('Get') || text.includes('Practice') || text.includes('status'),
              logic: (text) => {
                const keywords = ['Get', 'Practice', 'status', 'Mood', 'Last trained stat'];
                const parts = [];
                let currentText = text;
                
                for (const keyword of keywords) {
                  const index = currentText.indexOf(keyword);
                  if (index !== -1) {
                    if (index > 0) {
                      parts.push(currentText.substring(0, index).trim());
                    }
                    parts.push(keyword);
                    currentText = currentText.substring(index + keyword.length);
                  }
                }
                
                if (currentText.trim()) {
                  parts.push(currentText.trim());
                }
                
                return parts.filter(part => part.trim());
              }
            },
                      // Tách theo các từ khóa phức tạp hơn cho trường hợp đặc biệt
          {
            test: (text) => text.includes('statusor') || text.includes('○') || text.includes('-1Last') || text.includes('+5Get') || text.includes('+10Get') || text.includes('+15Get') || text.includes('+20Get'),
            logic: (text) => {
              const parts = [];
              let currentText = text;
              
              // Tách theo "statusor" -> "status" + "or"
              if (currentText.includes('statusor')) {
                const statusorIndex = currentText.indexOf('statusor');
                if (statusorIndex > 0) {
                  parts.push(currentText.substring(0, statusorIndex).trim());
                }
                parts.push('status');
                parts.push('or');
                currentText = currentText.substring(statusorIndex + 'statusor'.length);
              }
              
              // Tách theo "-1Last" -> "-1" + "Last"
              if (currentText.includes('-1Last')) {
                const minusIndex = currentText.indexOf('-1Last');
                if (minusIndex > 0) {
                  parts.push(currentText.substring(0, minusIndex).trim());
                }
                parts.push('-1');
                parts.push('Last');
                currentText = currentText.substring(minusIndex + '-1Last'.length);
              }
              
              // Tách theo "+5Get", "+10Get", "+15Get", "+20Get" -> "+5" + "Get", etc.
              const getPatterns = ['+5Get', '+10Get', '+15Get', '+20Get'];
              for (const pattern of getPatterns) {
                if (currentText.includes(pattern)) {
                  const patternIndex = currentText.indexOf(pattern);
                  if (patternIndex > 0) {
                    const beforePattern = currentText.substring(0, patternIndex).trim();
                    // Thử tách thêm phần trước pattern nếu có dạng "Speed -5Power"
                    if (beforePattern.includes('Power') && beforePattern.includes('-')) {
                      const powerIndex = beforePattern.indexOf('Power');
                      if (powerIndex > 0) {
                        parts.push(beforePattern.substring(0, powerIndex).trim());
                        parts.push('Power');
                      } else {
                        parts.push(beforePattern);
                      }
                    } else {
                      parts.push(beforePattern);
                    }
                  }
                  parts.push(pattern.substring(0, pattern.length - 3)); // Lấy phần số
                  parts.push('Get');
                  currentText = currentText.substring(patternIndex + pattern.length);
                  break;
                }
              }
              
              // Tách theo "○"
              if (currentText.includes('○')) {
                const circleIndex = currentText.indexOf('○');
                if (circleIndex > 0) {
                  parts.push(currentText.substring(0, circleIndex).trim());
                }
                parts.push('○');
                currentText = currentText.substring(circleIndex + 1);
              }
              
              if (currentText.trim()) {
                parts.push(currentText.trim());
              }
              
              return parts.filter(part => part.trim());
            }
          },
          // Tách theo các pattern phức tạp nhất - xử lý toàn bộ chuỗi
          {
            test: (text) => text.includes('Randomly either') && (text.includes('statusor') || text.includes('-1Last')),
            logic: (text) => {
              const parts = [];
              let currentText = text;
              
              // Tách theo "Randomly either"
              if (currentText.includes('Randomly either')) {
                parts.push('Randomly either');
                currentText = currentText.substring(currentText.indexOf('Randomly either') + 'Randomly either'.length);
              }
              
              // Tách theo "-1Last" -> "-1" + "Last"
              if (currentText.includes('-1Last')) {
                const minusIndex = currentText.indexOf('-1Last');
                if (minusIndex > 0) {
                  parts.push(currentText.substring(0, minusIndex).trim());
                }
                parts.push('-1');
                parts.push('Last');
                currentText = currentText.substring(minusIndex + '-1Last'.length);
              }
              
              // Tách theo dấu ngoặc
              if (currentText.includes('(') && currentText.includes(')')) {
                const openIndex = currentText.indexOf('(');
                const closeIndex = currentText.indexOf(')', openIndex);
                
                if (openIndex > 0) {
                  parts.push(currentText.substring(0, openIndex).trim());
                }
                parts.push(currentText.substring(openIndex, closeIndex + 1).trim());
                currentText = currentText.substring(closeIndex + 1);
              }
              
              // Tách theo "statusor" -> "status" + "or"
              if (currentText.includes('statusor')) {
                const statusorIndex = currentText.indexOf('statusor');
                if (statusorIndex > 0) {
                  parts.push(currentText.substring(0, statusorIndex).trim());
                }
                parts.push('status');
                parts.push('or');
                currentText = currentText.substring(statusorIndex + 'statusor'.length);
              }
              
              // Tách theo "○"
              if (currentText.includes('○')) {
                const circleIndex = currentText.indexOf('○');
                if (circleIndex > 0) {
                  parts.push(currentText.substring(0, circleIndex).trim());
                }
                parts.push('○');
                currentText = currentText.substring(circleIndex + 1);
              }
              
              if (currentText.trim()) {
                parts.push(currentText.trim());
              }
              
              return parts.filter(part => part.trim());
            }
          }
                  ];
                  
                  for (const pattern of complexPatterns) {
                    if (pattern.test && pattern.test(singleEffect)) {
                      const parts = pattern.logic(singleEffect);
                      if (parts.length > 1) {
                        effects = parts;
                        break;
                      }
                    }
                  }
                }
                }
                
                // Join tất cả effects bằng \n
                const combinedEffects = effects.join('\n');
                
                return {
                  choice: choiceText,
                  effects: combinedEffects
                };
              });
              return { event: eventName, type, choices };
            });
            
            if (detail && detail.event) {
              allEvents.push(detail);
              console.log(`      ✅ Added event: ${detail.event} (Type: ${detail.type})`);
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
    
    // Filter duplicate events (by event name)
    const uniqueEvents = Array.from(new Map(allEvents.map(e => [e.event, e])).values());
    console.log(`  ✅ Found ${uniqueEvents.length} unique events with detail`);
    
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
    
    // Create simplified results structure
    const simplifiedResults = {
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

    // Process character events
    const characterEvents = {};
    allEvents.forEach(result => {
      if (result.events && result.events.length > 0) {
        const charName = result.combination.character.alt || result.combination.character.title || 'Unknown';
        if (!characterEvents[charName]) {
          characterEvents[charName] = [];
        }
        characterEvents[charName].push(...result.events);
      }
    });

    // Convert to array format and remove duplicates
    function groupByType(events) {
      const groups = {};
      events.forEach(e => {
        const type = e.type || 'Unknown';
        if (!groups[type]) groups[type] = [];
        groups[type].push(e);
      });
      return Object.entries(groups).map(([type, events]) => ({ type, events }));
    }

    Object.keys(characterEvents).forEach(charName => {
      const uniqueEvents = Array.from(new Map(characterEvents[charName].map(e => [e.event, e])).values());
      simplifiedResults.characters.push({
        id: charName,
        eventGroups: groupByType(uniqueEvents)
      });
    });

    // Process support card events
    const cardEvents = {};
    allEvents.forEach(result => {
      if (result.events && result.events.length > 0) {
        result.combination.cards.forEach(card => {
          const cardName = card.alt || card.title || 'Unknown';
          if (!cardEvents[cardName]) {
            cardEvents[cardName] = [];
          }
          cardEvents[cardName].push(...result.events);
        });
      }
    });

    // Convert to array format and remove duplicates
    Object.keys(cardEvents).forEach(cardName => {
      const uniqueEvents = Array.from(new Map(cardEvents[cardName].map(e => [e.event, e])).values());
      simplifiedResults.supportCards.push({
        id: cardName,
        eventGroups: groupByType(uniqueEvents)
      });
    });

    // Process scenario events
    const scenarioEvents = {};
    allEvents.forEach(result => {
      if (result.events && result.events.length > 0) {
        const scenarioName = result.combination.scenario;
        if (!scenarioEvents[scenarioName]) {
          scenarioEvents[scenarioName] = [];
        }
        scenarioEvents[scenarioName].push(...result.events);
      }
    });

    // Convert to array format and remove duplicates
    Object.keys(scenarioEvents).forEach(scenarioName => {
      const uniqueEvents = Array.from(new Map(scenarioEvents[scenarioName].map(e => [e.event, e])).values());
      simplifiedResults.scenarios.push({
        id: scenarioName,
        eventGroups: groupByType(uniqueEvents)
      });
    });

    // Save to file
    fs.writeFileSync(
      path.join(__dirname, 'data', 'all_training_events.json'),
      JSON.stringify(simplifiedResults, null, 2)
    );
    
    console.log(`  ✅ Progress saved: ${combinationCount}/${totalCombinations} (${simplifiedResults.progress.percentage}%)`);
    console.log(`     👤 Characters: ${simplifiedResults.characters.length}`);
    console.log(`     🎴 Support Cards: ${simplifiedResults.supportCards.length}`);
    console.log(`     📖 Scenarios: ${simplifiedResults.scenarios.length}`);
    
  } catch (error) {
    console.log(`  ⚠️ Error saving progress: ${error.message}`);
  }
}

// Run the scraper
// Để chạy headless: scrapeTrainingEvents(true)
// Để chạy visible: scrapeTrainingEvents(false)
scrapeTrainingEvents(true).catch(console.error); 