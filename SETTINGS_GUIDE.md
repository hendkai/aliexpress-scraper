# Settings & Administration Guide

## Overview
The Settings page provides administrative tools for managing your AliExpress Scraper database and configuration.

## Access
Navigate to **Settings** in the main menu or visit: `http://localhost:5000/settings`

## Features

### 📊 Database Statistics
Real-time overview of your database:
- **Total Products**: All products in database
- **Tracked Products**: Products being monitored for price changes
- **Price Records**: Historical price data points
- **Database Size**: Current size of the SQLite database file
- **Active Keywords**: Keywords configured for auto-scraping
- **Scraping Logs**: Historical scraping activity records

### 🔧 Maintenance Actions

#### Clean Up Old Data
Removes old, unnecessary data to optimize performance:
- **Price history** older than 90 days
- **Inactive products** not tracked and older than 30 days  
- **Scraping logs** older than 60 days

**Recommended**: Run monthly for optimal performance.

#### Export Data
Creates a backup of all tracked products and their price history:
- Exports to JSON format
- Includes last 365 days of price history
- Saved to `results/` directory
- Filename format: `aliexpress_export_YYYYMMDD_HHMMSS.json`

**Recommended**: Export before major changes or regularly for backup.

### ⚠️ Danger Zone

#### Reset Database
**DESTRUCTIVE ACTION** - Permanently deletes ALL data:
- All products and variants
- All price history
- All tracking settings  
- All keywords and scraping logs

**Safety Features**:
- Requires typing exact confirmation phrase: `RESET ALL DATA`
- Double confirmation dialog
- Cannot be undone

**Use Cases**:
- Fresh start with new product categories
- Resolving database corruption issues
- Testing and development

## Safety & Security

### Confirmation Requirements
- **Cleanup**: Single confirmation dialog
- **Export**: No confirmation (read-only)
- **Reset**: Double confirmation + exact phrase typing

### Data Protection
- Export creates backup before destructive operations
- Database file can be manually backed up from filesystem
- All operations provide detailed success/error messages

## Best Practices

1. **Regular Maintenance**:
   - Run cleanup monthly
   - Monitor database size
   - Export data before major changes

2. **Before Reset**:
   - Export current data
   - Verify backup file
   - Understand complete data loss

3. **Performance**:
   - Large databases (>100MB) may benefit from cleanup
   - Consider exporting and resetting if performance degrades

## Troubleshooting

### Common Issues
- **Slow performance**: Run cleanup to remove old data
- **Large database**: Export important data, then reset
- **Export fails**: Check disk space in `results/` directory
- **Reset fails**: Restart application and try again

### Error Messages
- **Invalid confirmation**: Type exact phrase `RESET ALL DATA`
- **Database error**: Check file permissions and disk space
- **Export error**: Verify `results/` directory is writable

## Technical Details

### File Locations
- Database: `aliexpress_scraper.db`
- Exports: `results/aliexpress_export_*.json`
- Session cache: `session_cache.json`

### API Endpoints
- `GET /settings` - Settings page
- `POST /api/settings/cleanup_old_data` - Cleanup
- `POST /api/settings/export_data` - Export
- `POST /api/settings/reset_database` - Reset

### Database Schema
Settings operations affect all tables:
- `products` - Product information and variants
- `price_history` - Historical price data
- `search_keywords` - Auto-scraping configuration
- `scraping_logs` - Activity logs