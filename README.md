# 🎬 Twitter Video Downloader

A powerful and user-friendly Twitter/X video downloader with FastAPI backend, automatic cookie management, and support for private/restricted content.

## ✨ Features

- **🚀 Fast Video Extraction**: Download videos from Twitter/X with metadata
- **🔒 Private Content Support**: Access private accounts and adult content with cookies
- **🎯 Smart Caching**: 1-hour cache to reduce API calls and improve performance
- **📁 Auto Cookie Management**: Drop raw_cookies.json files for automatic conversion
- **🌐 REST API**: Full-featured API with interactive documentation
- **🔄 Real-time Monitoring**: Live file watching and processing
- **📱 Browser Testing**: Simple GET endpoints for easy testing

## 🛠️ Installation

### 1. Clone and Setup
```bash
git clone <your-repo>
cd twitter-video-downloader
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
# Option 1: Run full service manager (recommended)
python service_manager.py

# Option 2: Run API server only
python main.py

# Option 3: Run cookie watcher only
python cookie_watcher.py
```

## 🚀 Quick Start

### Method 1: Service Manager (Recommended)
```bash
python service_manager.py
```
This starts both the API server and cookie file watcher.

### Method 2: API Only
```bash
python main.py
```
Then visit `http://localhost:8000` for the API.

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information and endpoints |
| `GET` | `/test` | Browser-testable endpoint |
| `POST` | `/video/fetch` | Extract video data and download URL |
| `POST` | `/auth/cookies` | Upload authentication cookies |
| `GET` | `/auth/status` | Check authentication status |
| `DELETE` | `/auth/cookies` | Clear stored cookies |

### Testing in Browser
```
http://localhost:8000/test?url=https://x.com/user/status/123&adult=true
```

### API Documentation
- **Interactive Docs**: `http://localhost:8000/docs`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## 🔑 Authentication Setup

### For Private/Adult Content

1. **Export Cookies from Browser**:
   - Install a browser extension like "Cookie Editor" or "EditThisCookie"
   - Log into Twitter/X in your browser
   - Export all cookies for twitter.com or x.com domain
   - Save as JSON format

2. **Upload Cookies**:
   ```bash
   # Method 1: Drop file (auto-detected)
   # Save exported cookies as "raw_cookies.json" in the project folder
   # The file watcher will automatically convert it
   
   # Method 2: API Upload
   curl -X POST "http://localhost:8000/auth/cookies" \
        -H "Content-Type: application/json" \
        -d '{"cookies": [your_cookie_array]}'
   ```

3. **Verify Authentication**:
   ```bash
   curl http://localhost:8000/auth/status
   ```

## 📋 Usage Examples

### Basic Video Download
```bash
curl -X POST "http://localhost:8000/video/fetch" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://twitter.com/user/status/1234567890",
       "is_adult_content": false
     }'
```

### Adult Content Download
```bash
curl -X POST "http://localhost:8000/video/fetch" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://x.com/user/status/1234567890", 
       "is_adult_content": true
     }'
```

### Browser Testing
```
http://localhost:8000/test?url=https://x.com/user/status/1234567890&adult=true
```

## 📊 Response Format

```json
{
  "success": true,
  "title": "Video Title",
  "description": "Video description",
  "thumbnail": "https://...",
  "duration": 30,
  "duration_formatted": "0:30",
  "uploader": "username",
  "upload_date": "20231201",
  "upload_date_formatted": "2023-12-01",
  "view_count": 1000,
  "like_count": 50,
  "repost_count": 10,
  "download_url": "https://video.twimg.com/...",
  "filename": "Video_Title-abc12345.mp4",
  "format": "mp4",
  "quality": "720p",
  "file_size": 5242880,
  "content_rating": "General Audience",
  "expires_at": 1701454800.0
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Set custom port
export PORT=8000

# Optional: Set cookies file location
export COOKIES_FILE=cookies.txt
```

### File Structure
```
twitter-video-downloader/
├── main.py              # FastAPI application
├── service_manager.py   # Service orchestrator
├── cookie_watcher.py    # Cookie file monitor
├── requirements.txt     # Dependencies
├── README.md           # Documentation
├── cookies.txt         # Generated cookie file (auto-created)
└── raw_cookies.json    # Drop cookies here (auto-processed)
```

## 🚨 Error Handling

The API provides detailed error messages:

| Error Code | Description | Solution |
|------------|-------------|----------|
| `400` | Invalid URL format | Use valid Twitter/X URL |
| `401` | Unauthorized access | Upload authentication cookies |
| `403` | Access forbidden | Check if account is private |
| `404` | Tweet not found | Verify the tweet exists |
| `429` | Rate limit exceeded | Wait before retrying |
| `500` | Extraction failed | Check URL and try again |

## 🔒 Privacy & Security

- **Local Processing**: All processing happens on your machine
- **No Data Storage**: Videos are not stored, only URLs provided
- **Cookie Security**: Cookies are stored locally in standard format
- **Rate Limiting**: Respects Twitter's API limitations

## 🐛 Troubleshooting

### Common Issues

1. **"No cookies file found"**
   ```bash
   # Upload cookies using the /auth/cookies endpoint
   # Or drop raw_cookies.json in the folder
   ```

2. **"Tweet not found"**
   ```bash
   # Check if the tweet exists and is public
   # For private accounts, ensure you have valid cookies
   ```

3. **"Rate limit exceeded"**
   ```bash
   # Wait a few minutes before making more requests
   # Consider using authenticated requests with cookies
   ```

4. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```

### Debug Mode
```bash
# Run with verbose logging
python main.py --log-level debug
```

## 📈 Performance

- **Caching**: 1-hour TTL for video metadata
- **Concurrent Requests**: Supports multiple simultaneous downloads
- **Memory Usage**: Optimized for minimal memory footprint
- **Rate Limiting**: Built-in respect for API limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and personal use only. Please respect:
- Twitter's Terms of Service
- Content creators' rights
- Copyright laws
- Privacy and data protection regulations

Use responsibly and ensure you have the right to download the content.

## 🔗 Links

- **API Documentation**: `http://localhost:8000/docs`
- **Test Endpoint**: `http://localhost:8000/test`
- **Status Check**: `http://localhost:8000/auth/status` 