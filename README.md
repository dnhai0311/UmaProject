# Uma Project

Uma Musume Character and Card Selector Application

## Cấu trúc thư mục

```
UmaProject/
├── scrape/                    # Thư mục chứa các script scraping
│   ├── data/                  # Dữ liệu JSON được tạo bởi các script scraping
│   │   ├── all_skills.json
│   │   ├── all_support_events.json
│   │   ├── all_uma_events.json
│   │   └── all_scenario_events.json
│   ├── skill-scrape.js        # Script scrape skills
│   ├── support-scrape.js      # Script scrape support cards
│   ├── uma-scrape.js          # Script scrape uma characters
│   ├── scenario-scrape.js     # Script scrape scenarios
│   ├── copy-data.js           # Script copy data từ scrape/data sang public/data
│   └── package.json           # Dependencies cho scraping
├── public/
│   ├── data/                  # Dữ liệu JSON cho frontend (copy từ scrape/data)
│   │   ├── all_skills.json
│   │   ├── all_support_events.json
│   │   ├── all_uma_events.json
│   │   └── all_scenario_events.json
│   └── index.html
├── src/                       # React frontend code
└── package.json               # Dependencies cho frontend
```

## Cách sử dụng

### 1. Cài đặt dependencies

```bash
# Cài đặt dependencies cho frontend
npm install

# Cài đặt dependencies cho scraping
cd scrape
npm install
cd ..
```

### 2. Chạy scraping

```bash
# Scrape tất cả dữ liệu
npm run scrape-all

# Hoặc scrape từng loại riêng biệt
cd scrape
npm run scrape-skills      # Scrape skills
npm run scrape-scenarios   # Scrape scenarios  
npm run scrape-support     # Scrape support cards
npm run scrape-uma         # Scrape uma characters
```

### 3. Chạy ứng dụng

```bash
# Chạy cả frontend và backend
npm run dev

# Hoặc chạy riêng biệt
npm start      # Frontend
npm run server # Backend
```

## Quy trình làm việc

1. **Scraping dữ liệu**: Các script trong thư mục `scrape/` sẽ tạo file JSON trong `scrape/data/`
2. **Copy dữ liệu**: Tự động copy từ `scrape/data/` sang `public/data/` sau khi scraping
3. **Frontend access**: Frontend đọc dữ liệu từ `public/data/` thông qua HTTP

## Lưu ý

- Dữ liệu được lưu trong `scrape/data/` để dễ quản lý và backup
- Frontend truy cập dữ liệu từ `public/data/` thông qua HTTP requests
- Script `copy-data.js` tự động được chạy sau mỗi lần scraping để đồng bộ dữ liệu 