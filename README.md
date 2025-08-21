# 🚁 Pilot Job Tracker - Automated Aviation Job Monitoring System

A comprehensive Python system that automatically tracks commercial pilot job openings across multiple airlines and aviation companies worldwide, with real-time Telegram notifications for new and closed positions.

## ✨ Key Features

- **🎯 Pilot-Specific Filtering**: Advanced filtering for pilot, copilot, first officer, captain, and pilot cadet positions
- **🌐 Multi-Source Data Collection**: Supports Greenhouse API, Lever API, Workday sites, and generic web scraping
- **📱 Real-Time Notifications**: Instant Telegram alerts for job openings and closures
- **🔍 Intelligent Change Detection**: Accurately tracks job status changes over time
- **⚡ Automated Scheduling**: Runs every 15 minutes via GitHub Actions (free tier compatible)
- **🛡️ Secure Configuration**: Uses GitHub Secrets for sensitive credentials
- **📊 Comprehensive Coverage**: 20+ major airlines and aviation companies
- **🗄️ Local Database**: SQLite storage with job history and metadata

## 🚀 Quick Start

### 1. Repository Setup
```bash
git clone <your-repo-url>
cd pilot-job-tracker
pip install -r requirements.txt
playwright install chromium
```

### 2. Telegram Bot Setup
1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
3. Add secrets to your GitHub repository:
    - `TELEGRAM_BOT_TOKEN`: Your bot token
    - `TELEGRAM_CHAT_ID`: Your chat ID

### 3. Local Testing
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python main.py
```

### 4. Automated Deployment
Push to GitHub - the workflow runs automatically every 15 minutes!

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Extractors     │───▶│  Job Filtering  │
│                 │    │                  │    │                 │
│ • Greenhouse    │    │ • API Clients    │    │ • Pilot Keywords│
│ • Lever         │    │ • Web Scrapers   │    │ • Relevance     │
│ • Workday       │    │ • Playwright     │    │   Scoring       │
│ • Generic HTML  │    │ • BeautifulSoup  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                  │
                                  ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Notifications │◀───│  Change Detection │◀───│   Database      │
│                 │    │                  │    │                 │
│ • Telegram Bot  │    │ • New Jobs       │    │ • SQLite        │
│ • Job Alerts    │    │ • Closed Jobs    │    │ • Job History   │
│                 │    │ • Deduplication  │    │ • Metadata      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🎯 Supported Job Types

The system automatically identifies and filters these pilot positions:

### Primary Keywords (High Priority)
- **Pilot** - Commercial, airline, cargo pilots
- **Captain** - Senior pilot positions
- **First Officer** - Co-pilot roles
- **Copilot/Co-Pilot** - Assistant pilot positions

### Training & Development
- **Pilot Cadet** - Training programs
- **Second Officer** - Junior pilot roles
- **Flight Officer** - Military/government roles

### Technical Terms
- **ATP/ATPL** - Airline Transport Pilot License holders
- **Commercial Pilot** - Licensed commercial aviators

## 🏢 Supported Airlines & Companies

### Major US Airlines
- American Airlines, Delta Air Lines, United Airlines
- Southwest Airlines, JetBlue Airways, Alaska Airlines
- Spirit Airlines, Frontier Airlines

### Cargo Airlines
- FedEx Express, UPS Airlines

### Regional Airlines
- SkyWest Airlines, Republic Airways

### Business Aviation
- NetJets, FlexJet

### International
- Emirates (and more configurable via YAML)

### Government/Military
- USAJOBS Aviation positions

## 📁 Project Structure

```
pilot-job-tracker/
├── main.py                    # Main application orchestrator
├── config_enhanced.yml        # Full airline configuration
├── config_working.yml         # Tested/working sources only
├── job_filter.py             # Pilot job filtering logic
├── storage.py                # SQLite database operations
├── notifier.py               # Telegram notification system
├── test_system.py            # Comprehensive test suite
├── extractors/               # Data extraction modules
│   ├── __init__.py          #   Extractor factory
│   ├── greenhouse.py        #   Greenhouse API client
│   ├── lever.py             #   Lever API client
│   ├── workday.py           #   Workday scraper
│   ├── json_api.py          #   Generic JSON API client
│   ├── html_generic.py      #   BeautifulSoup scraper
│   └── playwright_generic.py #   Playwright scraper
├── .github/workflows/
│   └── pilot-job-tracker.yml # GitHub Actions workflow
├── requirements.txt          # Python dependencies
├── SETUP.md                 # Detailed setup guide
└── README.md               # This file
```

## 🔧 Configuration

### Adding New Airlines

Edit `config_enhanced.yml` to add new sources:

```yaml
targets:
  - company: "New Airline"
    source: "html"                    # or "greenhouse", "lever", "playwright"
    url: "https://careers.newairline.com/search/?q=pilot"
    selectors:
      item: ".job-listing"            # CSS selector for job items
      title: ".job-title"             # Job title selector
      location: ".job-location"       # Location selector  
      url: "a::attr(href)"           # Link selector
      description: ".job-description" # Optional: job description
```

### Filtering Configuration

```yaml
filtering:
  pilot_jobs_only: true              # Enable pilot-specific filtering
  minimum_pilot_score: 1            # Minimum relevance score (0-10)
```

## 📱 Notification Examples

**New Job Alert:**
```
🟢 NEW — First Officer - Boeing 737-800
Company: Southwest Airlines
Location: Dallas, TX (DFW)
Link: https://careers.southwest.com/job/123456
```

**Job Closure Alert:**
```
🔴 CLOSED — Captain - International Routes
Company: Delta Air Lines
Location: Atlanta, GA (ATL)
Link (historical): https://careers.delta.com/job/456789
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_system.py
```

Test individual components:
```bash
# Test job filtering
python -c "from job_filter import *; print(is_pilot_job({'title': 'Commercial Pilot'}))"

# Test Telegram bot
python test_bot.py

# Test specific extractor
python -c "from extractors.greenhouse import fetch; print(len(fetch('airbnb')))"
```

## 🔒 Security Features

- **No Hardcoded Secrets**: All sensitive data via environment variables
- **GitHub Secrets Integration**: Secure credential storage
- **Rate Limiting**: Respectful scraping with delays
- **Error Handling**: Graceful failures without exposing internals
- **Audit Trail**: Complete database logging of all changes

## ⚡ Performance & Reliability

- **Efficient Deduplication**: Prevents duplicate job notifications
- **Smart Change Detection**: Only notifies on actual changes
- **Fault Tolerance**: Continues processing even if some sources fail
- **Optimized Scraping**: Minimizes resource usage and blocking
- **Database Persistence**: No data loss between runs

## 📈 Monitoring & Maintenance

### GitHub Actions Dashboard
- View execution logs in the "Actions" tab
- Download database snapshots from artifacts
- Monitor success/failure rates

### Local Monitoring
```bash
# Check recent job activity
sqlite3 jobs.db "SELECT company, title, first_seen FROM jobs ORDER BY first_seen DESC LIMIT 10;"

# View success rates
python -c "import sqlite3; c=sqlite3.connect('jobs.db'); print(c.execute('SELECT COUNT(*) FROM jobs').fetchone())"
```

## 🐛 Troubleshooting

### Common Issues

**No jobs found:**
- Check if airline websites changed structure
- Verify CSS selectors in configuration
- Review GitHub Actions logs for errors

**No notifications:**
- Verify bot token and chat ID in GitHub Secrets
- Test locally with `python test_bot.py`
- Check if Telegram blocked the bot

**Scraping blocked:**
- Some airlines block automated requests
- GitHub Actions IP may be blocked
- Consider adding delays or rotating user agents

### Debug Mode

Enable verbose logging:
```bash
export DEBUG=1
python main.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-airline`
3. Add airline configuration to `config_enhanced.yml`
4. Test with `python test_system.py`
5. Submit a pull request

### Adding New Extractors

1. Create extractor in `extractors/new_source.py`
2. Add import to `extractors/__init__.py`
3. Update `fetch_one()` function
4. Add test cases to `test_system.py`

## 📜 License

Open source under MIT License. Use responsibly and respect website terms of service.

## 🙏 Acknowledgments

- **Greenhouse & Lever**: For providing public APIs
- **Playwright Team**: For reliable web automation
- **BeautifulSoup**: For HTML parsing capabilities
- **GitHub Actions**: For free automation hosting
- **Telegram**: For notification infrastructure

---

**⚠️ Important Notes:**
- Always respect robots.txt and website terms of service
- Monitor your GitHub Actions usage to stay within free tier limits
- Some airlines may block automated requests - this is normal
- Keep your Telegram bot token secure and rotate periodically

**🚁 Ready for takeoff? Set up your bot and start tracking pilot opportunities worldwide!**