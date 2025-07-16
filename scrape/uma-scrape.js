const puppeteer = require('puppeteer');
const fs = require('fs');

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

    // Load existing data if file exists
    let allResults = [];
    if (fs.existsSync('./data/all_uma_events.json')) {
      try {
        allResults = JSON.parse(fs.readFileSync('./data/all_uma_events.json', 'utf-8'));
        console.log(`📖 Loaded ${allResults.length} existing umamusume from ./data/all_uma_events.json`);
      } catch (e) {
        console.log('⚠️ Error reading existing file, starting fresh');
      }
    }

    // Loop through each character, scrape info and events
    for (let i = 0; i < charLinks.length; i++) {
      const url = charLinks[i];
      console.log(`\n📄 [${i+1}/${charLinks.length}] Scraping: ${url}`);

      const existingIndex = allResults.findIndex(char => {
        // So sánh URL chính xác
        if (char.url_detail === url) return true;
        
        // So sánh ID từ URL
        const urlId = url.match(/characters\/(\d+)/)?.[1];
        const existingId = char.url_detail?.match(/characters\/(\d+)/)?.[1];
        if (urlId && existingId && urlId === existingId) return true;
        
        return false;
      });
      
      if (existingIndex !== -1) {
        console.log(`⏭️ Character already scraped at index ${existingIndex}, skipping...`);
        continue;
      }

      let retryCount = 0;
      const maxRetries = 3;
      
      while (retryCount < maxRetries) {
        try {
          await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

          const character = await page.evaluate(() => {
            const name = document.querySelector('h1')?.innerText || '';
            const url_detail = window.location.href;
            const imageUrl = document.querySelector('img[src*="chara_stand_"]')?.src || '';
            
            // Lấy rarity từ tên trước (R, SR, SSR)
            let rarity = '';
            if (name) {
              const rarityMatch = name.match(/\b(R|SR|SSR)\b/);
              if (rarityMatch) {
                rarity = rarityMatch[1];
              }
            }
            
            // Nếu không tìm thấy trong tên, tìm từ stars
            if (!rarity) {
              const starElements = Array.from(document.querySelectorAll('*')).filter(el =>
                el.innerText && el.innerText.includes('⭐')
              );
              if (starElements.length > 0) {
                const sortedElements = starElements.sort((a, b) =>
                  (a.innerText.length - b.innerText.length)
                );
                rarity = sortedElements[0].innerText.trim();
              }
            }
            
            return { name, url_detail, imageUrl, rarity };
          });
          console.log(`✅ Character: ${character.name}`);

          // Get list of event names first
          const eventNames = (await page.evaluate(() => {
            return Array.from(document.querySelectorAll('[class*="compatibility_viewer_item"]'))
              .map(div => div.innerText.trim())
              .filter(name => name.length > 0);
          }))
          console.log(`   Found ${eventNames.length} events to scrape.`);

          const events = [];

          // Loop through each event name, click, get data, then reload
          for (const eventName of eventNames) {
            console.log(`   📋 Scraping event: ${eventName}`);
            try {
              // Find and click the event element using a more robust approach
              const clickSuccess = await page.evaluate((name) => {
                const elements = Array.from(document.querySelectorAll('[class*="compatibility_viewer_item"]'));
                const foundElement = elements.find(el => el.innerText.trim() === name);
                
                if (foundElement) {
                  // Try to click the element directly
                  try {
                    foundElement.click();
                    return true;
                  } catch (clickError) {
                    console.log('Direct click failed, trying alternative method');
                    return false;
                  }
                }
                return false;
              }, eventName);

              if (!clickSuccess) {
                console.log(`      ⚠️ Could not click event: ${eventName}. Skipping this event.`);
                continue; // Skip this event instead of exiting
              }

              // Short pause to ensure tippy-content appears
              await new Promise(resolve => setTimeout(resolve, 500));

              const eventDetail = await page.evaluate((name) => {
                function cleanEffect(effect) {
                  if (!effect) return effect;
                  return effect
                    .split('\n')
                    .filter(line => !/Website last updated|Affiliate Merch|Discord|Patreon|Crowdin|Affiliate/i.test(line))
                    .join('\n')
                    .trim();
                }

                function parseEffect(effectString) {
                  const lines = effectString.split('\n');
                  const effectParts = [];
                  let skill = null;
                  let bond = null;

                  lines.forEach(line => {
                    const trimmedLine = line.trim();
                    if (trimmedLine.includes('hint +')) {
                      const skillName = trimmedLine.replace(/hint \+\d+/, '').trim();
                      skill = {
                        name: skillName,
                        effect: `hint +${trimmedLine.match(/hint \+(\d+)/)[1] || '1'}`
                      };
                    } else if (trimmedLine.includes('Bond +')) {
                        const bondValue = trimmedLine.match(/Bond \+(\d+)/) ? trimmedLine.match(/Bond \+(\d+)/)[1] : '0';
                        bond = { name: 'Bond', effect: `+${bondValue}` };
                    }
                    else {
                      effectParts.push(trimmedLine);
                    }
                  });

                  return {
                    effect: effectParts.join('\n').trim(),
                    skill: skill,
                    bond: bond
                  };
                }

                let choices = [];
                const eventContainer = document.querySelector('.tippy-content');

                if (eventContainer) {
                  const tables = Array.from(eventContainer.querySelectorAll('table'));
                  if (tables.length > 0) {
                    for (const table of tables) {
                      const rows = Array.from(table.querySelectorAll('tr'));
                      for (const row of rows) {
                        const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim());
                        if (cells.length >= 2) {
                          const rawEffect = cleanEffect(cells[1]);
                          const parsedData = parseEffect(rawEffect);

                          choices.push({
                            choice: cells[0],
                            effect: parsedData.effect,
                            skill: parsedData.skill,
                            bond: parsedData.bond
                          });
                        }
                      }
                    }
                  }
                }

                // Handle events with no choices
                if (choices.length === 0) {
                  let effectText = eventContainer ? eventContainer.innerText : '';
                  if (effectText) {
                    const lines = effectText.split('\n').map(l => l.trim()).filter(Boolean);
                    const nameIndex = lines.indexOf(name);
                    let effectContent = '';
                    if (nameIndex !== -1 && nameIndex + 1 < lines.length) {
                      for (let j = nameIndex + 1; j < lines.length; j++) {
                          const currentLine = lines[j];
                          // Heuristic: stop if the line looks like another event title or is too short
                          if (currentLine.length < 3 || currentLine.includes('?') || currentLine.includes('!')) {
                              break;
                          }
                          effectContent += currentLine + '\n';
                      }
                    }
                    const cleanedEffect = cleanEffect(effectContent);

                    const parsedData = parseEffect(cleanedEffect);

                    choices.push({
                      choice: 'No Choice',
                      effect: parsedData.effect || 'Effect not found',
                      skill: parsedData.skill,
                      bond: parsedData.bond
                    });
                  } else {
                    choices.push({
                      choice: 'No Choice',
                      effect: 'Effect not found',
                      skill: null,
                      bond: null
                    });
                  }
                }
                return {
                  event: name,
                  choices
                };

              }, eventName);

              eventDetail.event = cleanEventName(eventDetail.event);
              
              // Bỏ qua event nếu tên bị clean thành null
              if (!eventDetail.event) {
                console.log(`      ⏭️ Skipping event with invalid name: ${eventName}`);
                continue;
              }
              
              events.push(eventDetail);

            } catch (e) {
                console.log(`      ❌ Error processing event ${eventName}: ${e.message}`);
                // Don't exit the program, just continue with next event
                continue;
            } finally {
                console.log('      🔄 Reloading page...');
                try {
                  await page.reload({ waitUntil: 'networkidle2' });
                  await new Promise(resolve => setTimeout(resolve, 2000)); // Reduced delay
                } catch (reloadError) {
                  console.log(`      ⚠️ Error reloading page: ${reloadError.message}`);
                  // Try to navigate back to the character page
                  try {
                    await page.goto(url, { waitUntil: 'networkidle2' });
                    await new Promise(resolve => setTimeout(resolve, 2000));
                  } catch (navError) {
                    console.log(`      ❌ Error navigating back to character page: ${navError.message}`);
                  }
                }
            }
          }
          console.log(`   📝 Events scraped: ${events.length}`);

          const skills = await page.evaluate(() => {
            function parseSkillsSection(sectionTitle) {
              const fullText = document.body.innerText;
              const lines = fullText.split('\n').map(l => l.trim()).filter(Boolean);
              const titleIndex = lines.findIndex(line => line === sectionTitle);
              if (titleIndex === -1) return [];

              const skills = [];
              let i = titleIndex + 1;

              while (i < lines.length) {
                const line = lines[i];
                if (['Unique skills', 'Innate skills', 'Awakening skills', 'Skills from events', 'Training Events', 'Costume Events', 'Events With Choices', 'Objectives'].includes(line)) {
                  break;
                }
                if (line === 'Details') {
                  const skill = { name: '', description: '' };
                  i++;
                  if (i < lines.length) {
                    skill.name = lines[i];
                    i++;
                    const descriptionLines = [];
                    while (i < lines.length && lines[i] !== 'Details') {
                      const descLine = lines[i];
                       if (['Unique skills', 'Innate skills', 'Awakening skills', 'Skills from events', 'Training Events', 'Costume Events', 'Events With Choices', 'Objectives'].includes(descLine)) {
                        break;
                      }
                      descriptionLines.push(descLine);
                      i++;
                    }
                    skill.description = descriptionLines.join(' ');
                    if (skill.name) skills.push(skill);
                  }
                } else {
                  i++;
                }
              }
              return skills;
            }

            return {
              unique: parseSkillsSection('Unique skills'),
              innate: parseSkillsSection('Innate skills'),
              event: parseSkillsSection('Skills from events')
            };
          });
          console.log(`   🎯 Skills scraped: ${skills.unique.length} unique, ${skills.innate.length} innate, ${skills.event.length} event`);

          allResults.push({ ...character, events, skills });

          fs.writeFileSync('./data/all_uma_events.json', JSON.stringify(allResults, null, 2), 'utf-8');
          console.log(`💾 Saved ${allResults.length} umamusume to ./data/all_uma_events.json`);

          // Success, break out of retry loop
          break;

        } catch (e) {
          retryCount++;
          console.log(`❌ Error scraping ${url} (attempt ${retryCount}/${maxRetries}):`, e.message);
          
          if (retryCount >= maxRetries) {
            console.log(`❌ Failed to scrape ${url} after ${maxRetries} attempts. Moving to next character.`);
          } else {
            console.log(`🔄 Retrying in 5 seconds...`);
            await new Promise(resolve => setTimeout(resolve, 5000));
          }
        }
      }
    }
    console.log('💾 Final save completed');
    
    // Copy data to public folder
    try {
      require('./copy-data');
      console.log('📋 Data copied to public folder');
    } catch (copyError) {
      console.log('⚠️ Error copying data:', copyError.message);
    }
    
    // Success - exit with code 0
    console.log('🎉 All characters scraped successfully!');
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