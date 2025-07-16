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

    // Đọc dữ liệu hiện có nếu file tồn tại
    let allResults = [];
    if (fs.existsSync('./data/all_support_events.json')) {
      try {
        allResults = JSON.parse(fs.readFileSync('./data/all_support_events.json', 'utf-8'));
        console.log(`📖 Loaded ${allResults.length} existing support cards from ./data/all_support_events.json`);
      } catch (e) {
        console.log('⚠️ Error reading existing file, starting fresh');
      }
    }

    // Lặp từng support card, scrape info và training events
    for (let i = 0; i < supportLinks.length; i++) {
      const url = supportLinks[i];
      console.log(`\n📄 [${i+1}/${supportLinks.length}] Scraping: ${url}`);

      // Kiểm tra xem support card này đã được scrape chưa
      const existingIndex = allResults.findIndex(support => {
        // So sánh URL chính xác
        if (support.url_detail === url) return true;
        
        // So sánh ID từ URL
        const urlId = url.match(/supports\/(\d+)/)?.[1];
        const existingId = support.url_detail?.match(/supports\/(\d+)/)?.[1];
        if (urlId && existingId && urlId === existingId) return true;
        
        return false;
      });
      
      if (existingIndex !== -1) {
        console.log(`⏭️ Support card already scraped at index ${existingIndex}, skipping...`);
        continue;
      }

      let retryCount = 0;
      const maxRetries = 3;
      
      while (retryCount < maxRetries) {
        try {
          await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

          // Có thể giữ lại delay này nếu cần, hoặc loại bỏ nếu không gây vấn đề
          await new Promise(resolve => setTimeout(resolve, 2000));

          // Lấy name, url, image, rarity
          const support = await page.evaluate(() => {
            const name = document.querySelector('h1')?.innerText || '';
            const url_detail = window.location.href;
            const imageUrl = document.querySelector('img[src*="support_"]')?.src || '';
            
            // Lấy rarity từ tên (R, SR, SSR)
            let rarity = '';
            if (name) {
              const rarityMatch = name.match(/\b(R|SR|SSR)\b/);
              if (rarityMatch) {
                rarity = rarityMatch[1];
              }
            }
            
            return { name, url_detail, imageUrl, rarity };
          });
          console.log(`✅ Support Card: ${support.name}`);

          // Lấy danh sách tên event trước
          const eventNames = (await page.evaluate(() => {
            const eventBoxes = Array.from(document.querySelectorAll('[class*="eventhelper_elist"]'));
            let names = [];
            for (const box of eventBoxes) {
              const eventDivs = Array.from(box.querySelectorAll('[class*="compatibility_viewer_item"]'));
              for (const div of eventDivs) {
                const eventName = div.innerText.trim();
                if (eventName.length > 0) {
                  names.push(eventName);
                }
              }
            }
            return names;
          }))
          console.log(`   Found ${eventNames.length} training events to scrape.`);

          const trainingEvents = [];

          // Lặp qua từng tên event, click, lấy data rồi reload
          for (const eventName of eventNames) {
            console.log(`   📋 Scraping event: ${eventName}`);
            try {
              // Sử dụng logic click đơn giản và ổn định hơn
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

              // Đợi một khoảng thời gian cố định để tooltip hiện ra
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

                    // 1. Kiểm tra nếu là dòng skill hint
                    if (trimmedLine.includes('hint +')) {
                      const skillName = trimmedLine.replace(/hint \+\d+/, '').trim();
                      const hintLevel = trimmedLine.match(/hint \+(\d+)/) ? trimmedLine.match(/hint \+(\d+)/)[1] : '1';
                      skill = {
                        name: skillName,
                        effect: `hint +${hintLevel}`
                      };
                    }
                    // 2. Kiểm tra nếu là dòng bond point
                    else if (trimmedLine.includes('Bond +')) {
                      const bondName = trimmedLine.replace(/ Bond \+\d+/, '').trim();
                      const bondValue = trimmedLine.match(/Bond \+(\d+)/) ? trimmedLine.match(/Bond \+(\d+)/)[1] : '0';
                      bond = {
                        name: bondName,
                        effect: `+${bondValue}`
                      };
                    }
                    // 3. Nếu không phải, nó là effect thông thường
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

                // Xử lý cho các event không có lựa chọn
                if (choices.length === 0) {
                  let effectText = eventContainer ? eventContainer.innerText : '';
                  if (effectText) {
                    const lines = effectText.split('\n').map(l => l.trim()).filter(Boolean);
                    const nameIndex = lines.findIndex(l => l === name);
                    let effectContent = '';
                    if (nameIndex !== -1 && nameIndex + 1 < lines.length) {
                      // Lấy các dòng effect sau tên event, dừng khi gặp dòng trống hoặc dòng có vẻ là tiêu đề khác
                      for (let j = nameIndex + 1; j < lines.length; j++) {
                          const currentLine = lines[j];
                          // Heuristic: dừng nếu dòng quá ngắn (có thể là dòng trống) hoặc chứa các ký tự đặc biệt của câu hỏi/lựa chọn
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
              
              trainingEvents.push(eventDetail);

            } catch (e) {
                console.log(`      ❌ Error processing event ${eventName}: ${e.message}`);
                // Don't exit the program, just continue with next event
                continue;
            } finally {
                // **RESET TRẠNG THÁI TRANG BẰNG CÁCH RELOAD**
                // Đây là bước quan trọng để đảm bảo sự ổn định cho lần lặp tiếp theo
                console.log('      🔄 Resetting page state...');
                try {
                  await page.reload({ waitUntil: 'networkidle2' });
                  await new Promise(resolve => setTimeout(resolve, 2000)); // Reduced delay
                } catch (reloadError) {
                  console.log(`      ⚠️ Error reloading page: ${reloadError.message}`);
                  // Try to navigate back to the support card page
                  try {
                    await page.goto(url, { waitUntil: 'networkidle2' });
                    await new Promise(resolve => setTimeout(resolve, 2000));
                  } catch (navError) {
                    console.log(`      ❌ Error navigating back to support card page: ${navError.message}`);
                  }
                }
            }
          }

          console.log(`   📝 Training Events scraped: ${trainingEvents.length}`);

          // Lấy Support hints và Skills from events (giữ nguyên logic cũ)
          const hintsAndSkills = await page.evaluate(() => {
            function parseSection(sectionTitle) {
              const fullText = document.body.innerText;
              const lines = fullText.split('\n').map(l => l.trim()).filter(Boolean);

              const titleIndex = lines.findIndex(line => line === sectionTitle);
              if (titleIndex === -1) return [];

              const items = [];
              let i = titleIndex + 1;

              while (i < lines.length) {
                const line = lines[i];

                if (['Support hints', 'Skills from events', 'Training Events', 'Costume Events', 'Events With Choices', 'Objectives', 'Unique skills', 'Innate skills', 'Awakening skills'].includes(line)) {
                  break;
                }

                if (line === 'Details') {
                  const item = { name: '', description: '' };
                  i++;

                  if (i < lines.length) {
                    item.name = lines[i];
                    i++;

                    const descriptionLines = [];
                    while (i < lines.length && lines[i] !== 'Details') {
                      const descLine = lines[i];
                      if (['Support hints', 'Skills from events', 'Training Events', 'Costume Events', 'Events With Choices', 'Objectives', 'Unique skills', 'Innate skills', 'Awakening skills'].includes(descLine)) {
                        break;
                      }
                      descriptionLines.push(descLine);
                      i++;
                    }
                    item.description = descriptionLines.join(' ');

                    if (item.name) {
                      items.push(item);
                    }
                  }
                } else {
                  i++;
                }
              }
              return items;
            }

            return {
              supportHints: parseSection('Support hints'),
              skillsFromEvents: parseSection('Skills from events')
            };
          });

          console.log(`   💡 Support Hints scraped: ${hintsAndSkills.supportHints.length}`);
          console.log(`   🎯 Skills from Events scraped: ${hintsAndSkills.skillsFromEvents.length}`);

          allResults.push({
            ...support,
            trainingEvents,
            supportHints: hintsAndSkills.supportHints,
            skillsFromEvents: hintsAndSkills.skillsFromEvents
          });

          fs.writeFileSync('./data/all_support_events.json', JSON.stringify(allResults, null, 2), 'utf-8');
          console.log(`💾 Saved ${allResults.length} support cards to ./data/all_support_events.json`);

          // Success, break out of retry loop
          break;

        } catch (e) {
          retryCount++;
          console.log(`❌ Error scraping ${url} (attempt ${retryCount}/${maxRetries}):`, e.message);
          
          if (retryCount >= maxRetries) {
            console.log(`❌ Failed to scrape ${url} after ${maxRetries} attempts. Moving to next support card.`);
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
    console.log('🎉 All support cards scraped successfully!');
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