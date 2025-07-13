const puppeteer = require('puppeteer');

function waitTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testWorkingParts() {
  console.log('🧪 Testing working parts...');
  
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    args: ['--start-maximized']
  });

  try {
    const page = await browser.newPage();
    await page.goto('https://gametora.com/umamusume/training-event-helper', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    await waitTimeout(3000);

    // Test 1: Support Cards
    console.log('\n=== TEST 1: SUPPORT CARDS ===');
    await page.click('#boxSupport1');
    await waitTimeout(3000);
    
    // Debug modal info first
    const modalInfo = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      return Array.from(modals).map((modal, index) => ({
        index,
        supportImages: modal.querySelectorAll('img[src*="support_card_s_"]').length,
        allImages: modal.querySelectorAll('img').length
      }));
    });
    console.log('Modal info:', modalInfo);
    
    const supportCards = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      for (const modal of modals) {
        const supportImgs = modal.querySelectorAll('img[src*="support_card_s_"]');
        if (supportImgs.length > 0) {
          console.log('Found modal with', supportImgs.length, 'support images');
          
          // Reset scroll and trigger loading
          modal.scrollTop = 0;
          
          // Force a small scroll to trigger lazy loading
          setTimeout(() => {
            modal.scrollTop = 10;
            setTimeout(() => {
              modal.scrollTop = 0;
            }, 100);
          }, 100);
          
          return { modalFound: true, totalImages: supportImgs.length };
        }
      }
      return { modalFound: false };
    });
    
    // Wait for images to load after triggering
    await waitTimeout(3000);
    
    const supportCards2 = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      for (const modal of modals) {
        const supportImgs = modal.querySelectorAll('img[src*="support_card_s_"]');
        if (supportImgs.length > 0) {
          // Get visible cards after triggering
          const visibleCards = Array.from(modal.querySelectorAll('img')).filter(img => {
            if (!img.src.includes('support_card_s_')) return false;
            const rect = img.getBoundingClientRect();
            const style = window.getComputedStyle(img);
            return rect.width > 0 && rect.height > 0 && 
                   style.display !== 'none' && 
                   style.visibility !== 'hidden';
          });
          
          console.log('After trigger loading, found', visibleCards.length, 'visible cards');
          
          return visibleCards.map(img => ({
            src: img.src,
            alt: img.alt || '',
            title: img.title || ''
          }));
        }
      }
      return [];
    });
    
    console.log(`✅ Support cards (first try):`, supportCards);
    
    console.log(`✅ Support cards found (second try): ${supportCards2.length}`);
    console.log('Sample:', supportCards2.slice(0, 3));
    
    await page.keyboard.press('Escape');
    await waitTimeout(2000);

    // Test 2: Scenarios
    console.log('\n=== TEST 2: SCENARIOS ===');
    await page.click('#boxScenario');
    await waitTimeout(3000);
    
    const scenarios = await page.evaluate(() => {
      try {
        const scenarioSelector = '.tooltips_tooltip_striped__0p4n9 > div > div > .fVBhhN.sc-9ae1b094-0 > .fpCljy.sc-9ae1b094-1 > span';
        const scenarioElements = document.querySelectorAll(scenarioSelector);
        
        return Array.from(scenarioElements).map(element => {
          return element.textContent.trim();
        }).filter(text => text.length > 0);
      } catch (error) {
        return { error: error.message };
      }
    });
    
    console.log(`✅ Scenarios found: ${scenarios.length}`);
    console.log('Scenarios:', scenarios);
    
    await page.keyboard.press('Escape');
    await waitTimeout(2000);

    // Test 3: Characters
    console.log('\n=== TEST 3: CHARACTERS ===');
    await page.click('#boxChar');
    await waitTimeout(3000);
    
    const characters = await page.evaluate(() => {
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
    
    console.log(`✅ Characters found: ${characters.length}`);
    console.log('Sample:', characters.slice(0, 3));
    
    await page.keyboard.press('Escape');
    await waitTimeout(2000);

    // Test 4: Try scenario selection
    console.log('\n=== TEST 4: SCENARIO SELECTION ===');
    if (scenarios.length > 0) {
      const testScenario = scenarios[0];
      console.log(`Testing selection of: ${testScenario}`);
      
      await page.click('#boxScenario');
      await waitTimeout(2000);
      
      const selectionResult = await page.evaluate((targetName) => {
        try {
          const scenarioSelector = '.tooltips_tooltip_striped__0p4n9 > div > div > .fVBhhN.sc-9ae1b094-0 > .fpCljy.sc-9ae1b094-1 > span';
          const scenarioElements = document.querySelectorAll(scenarioSelector);
          
          const targetElement = Array.from(scenarioElements).find(element => {
            return element.textContent.trim() === targetName;
          });
          
          if (targetElement) {
            targetElement.click();
            return { success: true };
          }
          
          return { success: false, error: 'Element not found' };
        } catch (error) {
          return { success: false, error: error.message };
        }
      }, testScenario);
      
      console.log('Selection result:', selectionResult);
      
      await waitTimeout(2000);
    }

    console.log('\n🎉 All tests completed!');

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await browser.close();
  }
}

testWorkingParts().catch(console.error); 