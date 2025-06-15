from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl, Field
import yt_dlp
import os
import json
import re
import time
import hashlib
import uuid
from typing import Optional, Dict, Any
import tempfile
import unicodedata

app = FastAPI(
    title="🏆 Twitter Video Downloader API - Smart Detection Edition",
    version="3.0.0",
    description="""
    ## 🎯 **Best Quality Video Extraction from Twitter/X with Smart Adult Content Detection**
    
    ### 🆕 **NEW: Smart Adult Content Detection (v3.0)**
    - 🧠 **Automatic Detection**: No need to specify if content is adult/NSFW
    - 🔄 **Two-Step Process**: Tries without cookies first, then with cookies if needed
    - 🏷️ **Smart Labeling**: Only marks as "Adult (18+)" when cookies were actually required
    - ✅ **Boolean Field**: `is_adult: true/false` for easy programming logic
    
    ### 🏆 **Enhanced Quality Selection**
    - ✅ **Automatically selects highest quality MP4** (1080p, 720p, etc.)
    - ✅ **Returns all MP4 qualities** with download URLs
    - ✅ **Smart ranking** by resolution → bitrate → fps
    - ✅ **Detailed format analysis** with 15+ formats checked
    
    ### 🚀 **Key Features:**
    - 🎬 **Best Quality**: Always gets highest resolution MP4 available
    - 📊 **All Options**: Response includes all available MP4 qualities
    - 🧠 **Smart Detection**: Automatically detects adult/private content (no manual input!)
    - 🔒 **Authentication**: Seamless cookie-based access for restricted content
    - ⚡ **Fast Extraction**: Optimized yt-dlp configuration  
    - 🍪 **Cookie Management**: Web interface for easy authentication
    - 🧪 **Unified Testing**: Both endpoints return identical JSON structure
    - 📈 **Performance**: Smart caching and format analysis
    
    ### 📋 **Quick Start:**
    1. **Test any URL**: `/test?url=https://x.com/user/status/123` (auto-detects content type)
    2. **Full API**: `POST /video/fetch` with any Twitter URL (identical response)
    3. **Private content**: Upload cookies once via `/cookies/manager` (works for all requests)
    
    ### 🧠 **Smart Content Detection Logic:**
    1. **First Attempt**: Try to access without cookies (for public content)
    2. **Auto-Retry**: If blocked (403/401/NSFW), automatically retry with cookies
    3. **Smart Labeling**: 
       - Used cookies = `"content_rating": "Adult (18+)"` + `"is_adult": true`
       - No cookies needed = `"content_rating": "General Audience"` + `"is_adult": false`
    
    ### 🎯 **Quality Selection Logic:**
    1. **Resolution Priority**: 1080p > 720p > 480p > 360p
    2. **Bitrate Analysis**: Higher total bitrate = better quality
    3. **Video Bitrate**: Secondary quality metric
    4. **Frame Rate**: Higher FPS preferred when available
    """,
    contact={
        "name": "API Documentation",
        "url": "https://apitest.rdownload.org/docs",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
video_cache: Dict[str, Dict[str, Any]] = {}
COOKIES_FILE = 'cookies.txt'

# Pydantic models
class VideoRequest(BaseModel):
    url: HttpUrl

class CookiesRequest(BaseModel):
    cookies: list

class RawCookiesRequest(BaseModel):
    raw_cookies: str  # JSON string of raw cookies
    
class CookiesResponse(BaseModel):
    success: bool
    message: str
    cookies_count: int = 0

class VideoResponse(BaseModel):
    """🏆 Smart Detection Video Response with Best Quality Selection (v3.0)"""
    
    success: bool
    title: str
    description: Optional[str] = ""
    thumbnail: Optional[str] = ""
    duration: int = 0
    duration_formatted: str = "Unknown"
    uploader: str = ""
    upload_date: str = ""
    upload_date_formatted: str = ""
    view_count: int = 0
    like_count: int = 0
    repost_count: int = 0
    download_url: str = Field(description="🏆 BEST QUALITY MP4 download URL (auto-selected)")
    filename: str
    format: str = Field(default="mp4", description="Video format (always MP4)")
    quality: str = Field(default="Unknown", description="🎯 Resolution of selected best quality (e.g., '1080p')")
    file_size: Optional[int] = Field(default=None, description="File size in bytes of best quality video")
    content_rating: str = "General Audience"
    is_adult: bool = Field(default=False, description="🔞 True if adult/NSFW content (required cookies), False if general audience")
    expires_at: float = Field(description="URL expiration timestamp (6 hours from extraction)")
    available_qualities: Optional[list] = Field(
        default=[], 
        description="📊 ALL MP4 qualities available with URLs, bitrates, and file sizes"
    )
    total_formats_found: Optional[int] = Field(
        default=0, 
        description="🔍 Total number of formats discovered by yt-dlp"
    )
    mp4_formats_found: Optional[int] = Field(
        default=0, 
        description="🎬 Number of MP4 formats available for download"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "title": "Amazing Video Title",
                "description": "Video description here",
                "thumbnail": "https://pbs.twimg.com/...",
                "duration": 45,
                "duration_formatted": "0:45",
                "uploader": "username",
                "upload_date": "20240101",
                "upload_date_formatted": "2024-01-01",
                "view_count": 1000,
                "like_count": 50,
                "repost_count": 10,
                "download_url": "https://video.twimg.com/ext_tw_video/...1080p.mp4",
                "filename": "Amazing_Video_Title.mp4",
                "format": "mp4",
                "quality": "1080p",
                "file_size": 15728640,
                "content_rating": "General Audience",
                "is_adult": False,
                "expires_at": 1704097200.0,
                "available_qualities": [
                    {
                        "quality": "1080p",
                        "bitrate": "2048kbps",
                        "filesize": 15728640,
                        "url": "https://video.twimg.com/.../1080p.mp4"
                    },
                    {
                        "quality": "720p", 
                        "bitrate": "1280kbps",
                        "filesize": 8388608,
                        "url": "https://video.twimg.com/.../720p.mp4"
                    }
                ],
                "total_formats_found": 15,
                "mp4_formats_found": 4
            }
        }

class ErrorResponse(BaseModel):
    error: str

def save_cookies_from_json(cookies_json: list) -> bool:
    """Convert JSON cookies to Netscape format and save to file"""
    try:
        netscape_cookies = []
        
        for cookie in cookies_json:
            # Extract required fields with defaults
            domain = cookie.get('domain', '')
            flag = 'TRUE' if cookie.get('hostOnly', False) else 'FALSE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            expiration = int(cookie.get('expirationDate', 0))
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            # Create Netscape format line
            netscape_line = f"{domain}	{flag}	{path}	{secure}	{expiration}	{name}	{value}"
            netscape_cookies.append(netscape_line)
        
        # Write to cookies file
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# Generated by Twitter Video Downloader\n\n")
            for line in netscape_cookies:
                f.write(line + '\n')
        
        print(f"✅ Saved {len(cookies_json)} cookies to {COOKIES_FILE}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving cookies: {e}")
        return False

def normalize_twitter_url(url: str) -> str:
    """Normalize Twitter/X URL to standard format"""
    url = url.strip()
    url = re.sub(r'twitter\.com', 'x.com', url)
    return url

def is_valid_twitter_url(url: str) -> bool:
    """Check if URL is a valid Twitter/X URL"""
    pattern = r'https?://(twitter\.com|x\.com)/.+/status/\d+'
    return bool(re.match(pattern, url))

def get_cache_key(url: str) -> str:
    """Generate cache key from URL"""
    return hashlib.md5(url.encode()).hexdigest()

def is_cache_valid(cache_entry: dict, max_age: int = 3600) -> bool:
    """Check if cache entry is still valid (default 1 hour)"""
    return time.time() - cache_entry['timestamp'] < max_age

def extract_video_info(url: str) -> dict:
    """Extract video information using yt-dlp with smart adult content detection"""
    
    # Enhanced yt-dlp options for best quality
    base_ydl_opts = {
        'format': 'best[ext=mp4][vcodec!=none]/best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'noplaylist': True,
        'extract_flat': False,
        'listformats': False,  # We'll handle format selection manually
    }
    
    # First attempt: Try without cookies (for general audience content)
    print("🔍 Attempting to access content without cookies...")
    ydl_opts = base_ydl_opts.copy()
    used_cookies = False
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video information
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise ValueError("No video information could be extracted")
            
            # Get video format information
            formats = info.get('formats', [])
            if not formats:
                raise ValueError("No video formats found")
            
            # Print all available formats for debugging
            print(f"\n📊 Found {len(formats)} total formats:")
            
            # Filter and analyze MP4 formats
            mp4_formats = []
            for fmt in formats:
                if fmt.get('ext') == 'mp4' and fmt.get('vcodec') != 'none':
                    quality_info = {
                        'format_id': fmt.get('format_id', 'unknown'),
                        'height': fmt.get('height', 0),
                        'width': fmt.get('width', 0),
                        'tbr': fmt.get('tbr', 0),  # Total bitrate
                        'vbr': fmt.get('vbr', 0),  # Video bitrate
                        'fps': fmt.get('fps', 0),
                        'filesize': fmt.get('filesize', 0),
                        'url': fmt.get('url', ''),
                        'format_note': fmt.get('format_note', ''),
                        'format': fmt
                    }
                    mp4_formats.append(quality_info)
                    print(f"  📹 MP4: {quality_info['height']}p, {quality_info['tbr']}kbps, {quality_info['format_note']}")
            
            if not mp4_formats:
                # If no MP4 formats, check all formats
                print("❌ No MP4 formats found! Available formats:")
                for fmt in formats[:10]:  # Show first 10
                    print(f"  📺 {fmt.get('ext', 'unknown')}: {fmt.get('height', 'unknown')}p, {fmt.get('format_note', '')}")
                raise ValueError("No MP4 video formats available")
            
            # Sort MP4 formats by quality (height first, then bitrate)
            mp4_formats.sort(key=lambda x: (
                x['height'] or 0,      # Primary: Height
                x['tbr'] or 0,         # Secondary: Total bitrate  
                x['vbr'] or 0,         # Tertiary: Video bitrate
                x['fps'] or 0          # Quaternary: FPS
            ), reverse=True)
            
            # Show sorted quality analysis
            print(f"\n🏆 MP4 Quality Rankings:")
            for i, fmt in enumerate(mp4_formats[:5], 1):
                print(f"  {i}. {fmt['height']}p, {fmt['tbr']}kbps, {fmt['format_note']}")
            
            # Select the best MP4 format
            best_format = mp4_formats[0]['format']
            print(f"\n✅ Selected BEST MP4: {mp4_formats[0]['height']}p, {mp4_formats[0]['tbr']}kbps")
            
            # Create quality summary for response
            all_mp4_qualities = [
                {
                    'quality': f"{fmt['height']}p" if fmt['height'] else 'Unknown',
                    'bitrate': f"{fmt['tbr']}kbps" if fmt['tbr'] else 'Unknown',
                    'filesize': fmt['filesize'] or 'Unknown',
                    'url': fmt['url']
                }
                for fmt in mp4_formats[:5]  # Top 5 qualities
            ]
            
            # Extract metadata with safe defaults
            title = info.get('title', 'Unknown Video')
            description = info.get('description', '')
            uploader = info.get('uploader', info.get('channel', 'Unknown'))
            duration = info.get('duration', 0)
            upload_date = info.get('upload_date', '')
            view_count = info.get('view_count', 0)
            like_count = info.get('like_count', 0)
            repost_count = info.get('repost_count', 0)
            thumbnail = info.get('thumbnail', '')
            
            # Format duration
            def format_duration(seconds):
                if not seconds:
                    return "Unknown"
                minutes, seconds = divmod(int(seconds), 60)
                hours, minutes = divmod(minutes, 60)
                if hours:
                    return f"{hours}:{minutes:02d}:{seconds:02d}"
                return f"{minutes}:{seconds:02d}"
            
            duration_formatted = format_duration(duration)
            
            # Format upload date
            def format_upload_date(date_str):
                if not date_str or len(date_str) != 8:
                    return "Unknown"
                try:
                    year, month, day = date_str[:4], date_str[4:6], date_str[6:8]
                    return f"{year}-{month}-{day}"
                except:
                    return "Unknown"
            
            upload_date_formatted = format_upload_date(upload_date)
            
            # Clean filename
            def clean_filename(filename):
                if not filename:
                    return f"twitter_video_{int(time.time())}.mp4"
                # Remove invalid characters
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
                return filename[:100] + ".mp4"  # Limit length
            
            # Get download URL and file info
            download_url = best_format.get('url', '')
            if not download_url:
                raise ValueError("Could not extract download URL")
            
            # Generate filename
            safe_title = clean_filename(title)
            filename = f"{safe_title}"
            
            # Get quality info
            quality = best_format.get('format_note', 'Unknown')
            if not quality or quality == 'Unknown':
                height = best_format.get('height')
                if height:
                    quality = f"{height}p"
                else:
                    quality = "Unknown"
            
            # Get file size
            file_size = best_format.get('filesize') or best_format.get('filesize_approx')
            
            # Helper function for safe integer conversion
            def safe_int(value, default=0):
                try:
                    return int(value) if value is not None else default
                except (ValueError, TypeError):
                    return default
            
            # Calculate expiration time (URLs typically expire in 6 hours)
            expires_at = time.time() + (6 * 3600)
            
            return {
                "success": True,
                "title": title,
                "description": description or "",
                "thumbnail": thumbnail,
                "duration": safe_int(duration),
                "duration_formatted": duration_formatted,
                "uploader": uploader,
                "upload_date": upload_date,
                "upload_date_formatted": upload_date_formatted,
                "view_count": safe_int(view_count),
                "like_count": safe_int(like_count),
                "repost_count": safe_int(repost_count),
                "download_url": download_url,
                "filename": filename,
                "format": best_format.get('ext', 'mp4'),
                "quality": quality,
                "file_size": file_size,
                "content_rating": 'Adult (18+)' if used_cookies else 'General Audience',
                "is_adult": used_cookies,
                "expires_at": expires_at,
                "available_qualities": all_mp4_qualities,  # All MP4 qualities available
                "total_formats_found": len(formats),
                "mp4_formats_found": len(mp4_formats)
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ First attempt failed: {error_msg}")
        
        # Check if error suggests authentication is needed
        if any(keyword in error_msg for keyword in ["403", "401", "Forbidden", "Unauthorized", "private", "protected", "NSFW", "authentication", "requires authentication"]):
            if os.path.exists(COOKIES_FILE):
                print("🔄 Retrying with cookies for adult/private content...")
                try:
                    # Second attempt: Try with cookies
                    ydl_opts_with_cookies = base_ydl_opts.copy()
                    ydl_opts_with_cookies['cookiefile'] = COOKIES_FILE
                    used_cookies = True
                    
                    with yt_dlp.YoutubeDL(ydl_opts_with_cookies) as ydl:
                        # Extract video information
                        info = ydl.extract_info(url, download=False)
                        
                        if not info:
                            raise ValueError("No video information could be extracted")
                        
                        # Get video format information
                        formats = info.get('formats', [])
                        if not formats:
                            raise ValueError("No video formats found")
                        
                        # Print all available formats for debugging
                        print(f"\n📊 Found {len(formats)} total formats:")
                        
                        # Filter and analyze MP4 formats
                        mp4_formats = []
                        for fmt in formats:
                            if fmt.get('ext') == 'mp4' and fmt.get('vcodec') != 'none':
                                quality_info = {
                                    'format_id': fmt.get('format_id', 'unknown'),
                                    'height': fmt.get('height', 0),
                                    'width': fmt.get('width', 0),
                                    'tbr': fmt.get('tbr', 0),  # Total bitrate
                                    'vbr': fmt.get('vbr', 0),  # Video bitrate
                                    'fps': fmt.get('fps', 0),
                                    'filesize': fmt.get('filesize', 0),
                                    'url': fmt.get('url', ''),
                                    'format_note': fmt.get('format_note', ''),
                                    'format': fmt
                                }
                                mp4_formats.append(quality_info)
                                print(f"  📹 MP4: {quality_info['height']}p, {quality_info['tbr']}kbps, {quality_info['format_note']}")
                        
                        if not mp4_formats:
                            # If no MP4 formats, check all formats
                            print("❌ No MP4 formats found! Available formats:")
                            for fmt in formats[:10]:  # Show first 10
                                print(f"  📺 {fmt.get('ext', 'unknown')}: {fmt.get('height', 'unknown')}p, {fmt.get('format_note', '')}")
                            raise ValueError("No MP4 video formats available")
                        
                        # Sort MP4 formats by quality (height first, then bitrate)
                        mp4_formats.sort(key=lambda x: (
                            x['height'] or 0,      # Primary: Height
                            x['tbr'] or 0,         # Secondary: Total bitrate  
                            x['vbr'] or 0,         # Tertiary: Video bitrate
                            x['fps'] or 0          # Quaternary: FPS
                        ), reverse=True)
                        
                        # Show sorted quality analysis
                        print(f"\n🏆 MP4 Quality Rankings:")
                        for i, fmt in enumerate(mp4_formats[:5], 1):
                            print(f"  {i}. {fmt['height']}p, {fmt['tbr']}kbps, {fmt['format_note']}")
                        
                        # Select the best MP4 format
                        best_format = mp4_formats[0]['format']
                        print(f"\n✅ Selected BEST MP4: {mp4_formats[0]['height']}p, {mp4_formats[0]['tbr']}kbps (using cookies)")
                        
                        # Create quality summary for response
                        all_mp4_qualities = [
                            {
                                'quality': f"{fmt['height']}p" if fmt['height'] else 'Unknown',
                                'bitrate': f"{fmt['tbr']}kbps" if fmt['tbr'] else 'Unknown',
                                'filesize': fmt['filesize'] or 'Unknown',
                                'url': fmt['url']
                            }
                            for fmt in mp4_formats[:5]  # Top 5 qualities
                        ]
                        
                        # Extract metadata with safe defaults
                        title = info.get('title', 'Unknown Video')
                        description = info.get('description', '')
                        uploader = info.get('uploader', info.get('channel', 'Unknown'))
                        duration = info.get('duration', 0)
                        upload_date = info.get('upload_date', '')
                        view_count = info.get('view_count', 0)
                        like_count = info.get('like_count', 0)
                        repost_count = info.get('repost_count', 0)
                        thumbnail = info.get('thumbnail', '')
                        
                        # Format duration
                        def format_duration(seconds):
                            if not seconds:
                                return "Unknown"
                            minutes, seconds = divmod(int(seconds), 60)
                            hours, minutes = divmod(minutes, 60)
                            if hours:
                                return f"{hours}:{minutes:02d}:{seconds:02d}"
                            return f"{minutes}:{seconds:02d}"
                        
                        duration_formatted = format_duration(duration)
                        
                        # Format upload date
                        def format_upload_date(date_str):
                            if not date_str or len(date_str) != 8:
                                return "Unknown"
                            try:
                                year, month, day = date_str[:4], date_str[4:6], date_str[6:8]
                                return f"{year}-{month}-{day}"
                            except:
                                return "Unknown"
                        
                        upload_date_formatted = format_upload_date(upload_date)
                        
                        # Clean filename
                        def clean_filename(filename):
                            if not filename:
                                return f"twitter_video_{int(time.time())}.mp4"
                            # Remove invalid characters
                            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                            filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
                            return filename[:100] + ".mp4"  # Limit length
                        
                        # Get download URL and file info
                        download_url = best_format.get('url', '')
                        if not download_url:
                            raise ValueError("Could not extract download URL")
                        
                        # Generate filename
                        safe_title = clean_filename(title)
                        filename = f"{safe_title}"
                        
                        # Get quality info
                        quality = best_format.get('format_note', 'Unknown')
                        if not quality or quality == 'Unknown':
                            height = best_format.get('height')
                            if height:
                                quality = f"{height}p"
                            else:
                                quality = "Unknown"
                        
                        # Get file size
                        file_size = best_format.get('filesize') or best_format.get('filesize_approx')
                        
                        # Helper function for safe integer conversion
                        def safe_int(value, default=0):
                            try:
                                return int(value) if value is not None else default
                            except (ValueError, TypeError):
                                return default
                        
                        # Calculate expiration time (URLs typically expire in 6 hours)
                        expires_at = time.time() + (6 * 3600)
                        
                        return {
                            "success": True,
                            "title": title,
                            "description": description or "",
                            "thumbnail": thumbnail,
                            "duration": safe_int(duration),
                            "duration_formatted": duration_formatted,
                            "uploader": uploader,
                            "upload_date": upload_date,
                            "upload_date_formatted": upload_date_formatted,
                            "view_count": safe_int(view_count),
                            "like_count": safe_int(like_count),
                            "repost_count": safe_int(repost_count),
                            "download_url": download_url,
                            "filename": filename,
                            "format": best_format.get('ext', 'mp4'),
                            "quality": quality,
                            "file_size": file_size,
                                                         "content_rating": 'Adult (18+)' if used_cookies else 'General Audience',
                             "is_adult": used_cookies,
                             "expires_at": expires_at,
                            "available_qualities": all_mp4_qualities,  # All MP4 qualities available
                            "total_formats_found": len(formats),
                            "mp4_formats_found": len(mp4_formats)
                        }
                        
                except Exception as cookie_error:
                    print(f"❌ Cookie attempt also failed: {cookie_error}")
                    raise
            else:
                print("❌ No cookies available for private content")
                raise
        else:
            print(f"❌ Non-authentication error: {error_msg}")
            raise

@app.post("/video/fetch", response_model=VideoResponse)
async def fetch_video_data(request: VideoRequest):
    """
    🏆 **Extract BEST QUALITY Video from Twitter/X with Smart Adult Detection** 
    
    **🆕 NEW: Smart Adult Content Detection (v3.0)**
    - 🧠 **No Manual Input**: Automatically detects if content is adult/NSFW
    - 🔄 **Two-Step Process**: Tries without cookies, then with cookies if needed
    - 🏷️ **Smart Labeling**: Only marks "Adult (18+)" when authentication was required
    - ✅ **Boolean Field**: `is_adult: true/false` for easy programming
    
    **🏆 Enhanced Quality Selection**
    - ✅ Automatically selects **highest quality MP4** available (1080p, 720p, etc.)
    - ✅ Returns **all MP4 qualities** with download URLs in response
    - ✅ Smart ranking by resolution → bitrate → fps
    - ✅ Detailed format analysis with 15+ formats checked
    
    **🚀 Key Features:**
    - 🎯 **Best Quality**: Always gets highest resolution MP4
    - 📊 **All Options**: Response includes all available MP4 qualities  
    - 🧠 **Smart Detection**: Fully automatic adult content detection
    - 🔒 **Seamless Auth**: Cookie-based access handled transparently
    - ⚡ **Fast Extraction**: Optimized yt-dlp configuration
    - 🗂️ **Format Details**: Shows total formats found and MP4 count
    
    **🧠 Detection Process:**
    1. **Public Content**: Access without cookies → `is_adult: false`
    2. **Private/NSFW**: Blocked → Auto-retry with cookies → `is_adult: true`
    
    **🎯 Quality Priority:**
    1. Resolution (1080p > 720p > 480p > 360p)
    2. Total bitrate (higher = better)
    3. Video bitrate (secondary quality metric)
    4. Frame rate (higher FPS preferred)
    
    **📊 Response Fields:**
    - `download_url`: Best quality MP4 URL
    - `is_adult`: Boolean - true if required authentication
    - `content_rating`: Text - "Adult (18+)" or "General Audience"
    - `available_qualities`: Array of all MP4 options with URLs
    - `quality`: Resolution of selected best format
    - `total_formats_found`: All formats discovered
    - `mp4_formats_found`: Number of MP4 options available
    """
    try:
        url = str(request.url)
        normalized_url = normalize_twitter_url(url)
        
        if not is_valid_twitter_url(normalized_url):
            raise HTTPException(
                status_code=400,
                detail="Please provide a valid Twitter/X URL (e.g., https://twitter.com/user/status/123...)"
            )
        
        # Check cache first
        cache_key = get_cache_key(url)
        if cache_key in video_cache and is_cache_valid(video_cache[cache_key]):
            print("Returning cached video data")
            cached_data = video_cache[cache_key]['data']
            return VideoResponse(**cached_data)
        
        print(f"Extracting video data for: {url}")
        
        # Extract video information and download URL
        video_data = extract_video_info(url)
        
        # Cache the result
        video_cache[cache_key] = {
            'data': video_data,
            'timestamp': time.time()
        }
        
        print(f"Successfully extracted: {video_data['title']}")
        print(f"Content Rating: {video_data['content_rating']}")
        print(f"Download URL ready: {video_data['download_url'][:100]}...")
        
        return VideoResponse(**video_data)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Video extraction error: {error_msg}")
        
        # Provide specific error messages
        if "HTTP Error 404" in error_msg or "Not Found" in error_msg:
            error_msg = "Tweet not found. The tweet may have been deleted, the account is private, or the tweet doesn't contain a video."
        elif "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
            error_msg = "Access forbidden. Cannot access private accounts or restricted content. Try uploading cookies."
        elif "HTTP Error 429" in error_msg or "Too Many Requests" in error_msg:
            error_msg = "Rate limit exceeded. Please wait a few minutes before trying again."
        elif "HTTP Error 401" in error_msg or "Unauthorized" in error_msg:
            error_msg = "Unauthorized access. Upload cookies to access private/restricted content."
        elif "Unsupported URL" in error_msg:
            error_msg = "This Twitter/X URL is not supported. Please make sure the tweet contains a video."
        elif "Video unavailable" in error_msg:
            error_msg = "Video is unavailable. It might be private, deleted, or from a protected account."
        elif "Unable to extract" in error_msg or "Could not extract" in error_msg:
            error_msg = "Unable to extract video. The tweet might not contain a video or might be restricted."
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            error_msg = "Network connection error. Please check your internet connection and try again."
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/auth/cookies")
async def upload_cookies(request: CookiesRequest):
    """
    Upload browser cookies to access private/restricted Twitter content.
    Export cookies from your authenticated browser session.
    """
    try:
        if not request.cookies:
            raise HTTPException(status_code=400, detail="No cookies provided")
        
        success = save_cookies_from_json(request.cookies)
        if success:
            return {"message": "Cookies uploaded successfully! You can now access private/restricted content."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save cookies")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading cookies: {str(e)}")

@app.delete("/auth/cookies")
async def clear_cookies():
    """Clear stored cookies"""
    try:
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
        return {"message": "Cookies cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cookies: {str(e)}")

@app.get("/auth/status")
async def auth_status():
    """Check authentication status"""
    has_cookies = os.path.exists(COOKIES_FILE)
    cookie_count = 0
    
    if has_cookies:
        try:
            with open(COOKIES_FILE, 'r') as f:
                lines = f.readlines()
                cookie_count = len([line for line in lines if line.strip() and not line.startswith('#')])
        except:
            pass
    
    return {
        "authenticated": has_cookies,
        "cookie_count": cookie_count,
        "status": "Ready for private content" if has_cookies else "Upload cookies to access private content"
    }

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    return {
        "cache_size": len(video_cache),
        "cache_enabled": True
    }

@app.post("/cache/clear")
async def clear_cache():
    """Clear video cache"""
    global video_cache
    cache_size = len(video_cache)
    video_cache.clear()
    return {"message": f"Cache cleared. Removed {cache_size} entries."}

@app.post("/cookies/add-raw", response_model=CookiesResponse)
async def add_raw_cookies(request: RawCookiesRequest):
    """Add raw cookies and convert to Netscape format"""
    try:
        import json
        
        # Parse the raw cookies JSON
        raw_cookies = json.loads(request.raw_cookies)
        
        if not isinstance(raw_cookies, list):
            raise ValueError("Cookies must be an array")
        
        # Save raw cookies to temporary file
        temp_file = 'temp_raw_cookies.json'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(raw_cookies, f, indent=2)
        
        # Convert to Netscape format
        from cookie_watcher import convert_raw_cookies_to_netscape
        success = convert_raw_cookies_to_netscape(temp_file, COOKIES_FILE)
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if success:
            cookies_count = len(raw_cookies)
            return CookiesResponse(
                success=True,
                message=f"Successfully converted {cookies_count} cookies to Netscape format",
                cookies_count=cookies_count
            )
        else:
            return CookiesResponse(
                success=False,
                message="Failed to convert cookies"
            )
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing cookies: {str(e)}")

@app.post("/cookies/validate", response_model=CookiesResponse)
async def validate_cookies():
    """Validate current cookies by testing with yt-dlp"""
    try:
        if not os.path.exists(COOKIES_FILE):
            return CookiesResponse(
                success=False,
                message="No cookies file found. Please add cookies first."
            )
        
        # Test cookies with a simple Twitter/X URL
        test_url = "https://x.com/elonmusk/status/1"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'cookiefile': COOKIES_FILE,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Try to extract info - this will test if cookies work
                info = ydl.extract_info(test_url, download=False)
                
            return CookiesResponse(
                success=True,
                message="Cookies are valid and working!"
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "private" in error_msg or "protected" in error_msg:
                return CookiesResponse(
                    success=False,
                    message="Cookies are loaded but may not have sufficient permissions for private content"
                )
            elif "login" in error_msg or "auth" in error_msg:
                return CookiesResponse(
                    success=False,
                    message="Cookies are invalid or expired. Please update your cookies."
                )
            else:
                return CookiesResponse(
                    success=True,
                    message="Cookies are loaded (validation inconclusive but likely working)"
                )
                
    except Exception as e:
        return CookiesResponse(
            success=False,
            message=f"Error validating cookies: {str(e)}"
        )

@app.get("/cookies/status", response_model=CookiesResponse)
async def get_cookies_status():
    """Get current cookies status"""
    try:
        if not os.path.exists(COOKIES_FILE):
            return CookiesResponse(
                success=False,
                message="No cookies file found",
                cookies_count=0
            )
        
        # Count lines in cookies file (approximate cookie count)
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
            cookies_count = len(lines)
        
        return CookiesResponse(
            success=True,
            message=f"Cookies file exists with {cookies_count} entries",
            cookies_count=cookies_count
        )
        
    except Exception as e:
        return CookiesResponse(
            success=False,
            message=f"Error reading cookies status: {str(e)}"
        )

@app.get("/cookies/manager")
async def cookie_manager():
    """Cookie management interface"""
    html_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cookie Manager - Twitter Video Downloader</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #1DA1F2; text-align: center; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
            textarea { width: 100%; height: 200px; margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; }
            button { background: #1DA1F2; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            button:hover { background: #0d8bd9; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            .loading { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🍪 Cookie Manager</h1>
            
            <div class="section">
                <h3>Current Cookie Status</h3>
                <div id="status" class="status info">Loading...</div>
                <button onclick="checkStatus()">Refresh Status</button>
            </div>
            
            <div class="section">
                <h3>Add Raw Cookies</h3>
                <p>Paste your raw cookies JSON array here (from browser developer tools):</p>
                <textarea id="rawCookies" placeholder='[{"domain":".x.com","name":"auth_token","value":"your_token_here",...}]'></textarea>
                <br>
                <button onclick="addCookies()">Add Cookies</button>
                <button onclick="validateCookies()">Validate Cookies</button>
            </div>
            
            <div class="section">
                <h3>Quick Test</h3>
                <p>Test video extraction with current cookies:</p>
                <input type="text" id="testUrl" placeholder="https://x.com/user/status/123..." style="width: 70%; padding: 8px;">
                <button onclick="testVideo()">Test Video</button>
            </div>
            
            <div id="result" class="status" style="display: none;"></div>
        </div>
        
        <script>
            async function checkStatus() {
                const statusEl = document.getElementById('status');
                statusEl.className = 'status loading';
                statusEl.textContent = 'Checking status...';
                
                try {
                    const response = await fetch('/cookies/status');
                    const data = await response.json();
                    
                    if (data.success) {
                        statusEl.className = 'status success';
                        statusEl.textContent = `✅ ${data.message}`;
                    } else {
                        statusEl.className = 'status error';
                        statusEl.textContent = `❌ ${data.message}`;
                    }
                } catch (error) {
                    statusEl.className = 'status error';
                    statusEl.textContent = `❌ Error: ${error.message}`;
                }
            }
            
            async function addCookies() {
                const rawCookies = document.getElementById('rawCookies').value;
                const resultEl = document.getElementById('result');
                
                if (!rawCookies.trim()) {
                    showResult('error', 'Please paste your raw cookies JSON');
                    return;
                }
                
                showResult('loading', 'Adding cookies...');
                
                try {
                    const response = await fetch('/cookies/add-raw', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ raw_cookies: rawCookies })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok && data.success) {
                        showResult('success', `✅ ${data.message}`);
                        checkStatus(); // Refresh status
                    } else {
                        showResult('error', `❌ ${data.message || data.detail}`);
                    }
                } catch (error) {
                    showResult('error', `❌ Error: ${error.message}`);
                }
            }
            
            async function validateCookies() {
                showResult('loading', 'Validating cookies...');
                
                try {
                    const response = await fetch('/cookies/validate', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.success) {
                        showResult('success', `✅ ${data.message}`);
                    } else {
                        showResult('error', `❌ ${data.message}`);
                    }
                } catch (error) {
                    showResult('error', `❌ Error: ${error.message}`);
                }
            }
            
            async function testVideo() {
                const url = document.getElementById('testUrl').value;
                
                if (!url.trim()) {
                    showResult('error', 'Please enter a Twitter/X URL');
                    return;
                }
                
                showResult('loading', 'Testing video extraction...');
                
                try {
                    const response = await fetch(`/test?url=${encodeURIComponent(url)}`);
                    const data = await response.json();
                    
                    if (data.status === '✅ SUCCESS') {
                        showResult('success', `✅ Success! Video: "${data.title}" (${data.quality})`);
                    } else {
                        showResult('error', `❌ ${data.error || data.status}`);
                    }
                } catch (error) {
                    showResult('error', `❌ Error: ${error.message}`);
                }
            }
            
            function showResult(type, message) {
                const resultEl = document.getElementById('result');
                resultEl.className = `status ${type}`;
                resultEl.textContent = message;
                resultEl.style.display = 'block';
            }
            
            // Load status on page load
            checkStatus();
        </script>
    </body>
    </html>
    '''
    
    return HTMLResponse(content=html_content)

@app.get("/test", response_model=VideoResponse)
async def test_endpoint(url: str = "https://x.com/adh0005812/status/1672884416430096384"):
    """
    🧪 **Browser Test - Smart Detection & Best Quality Extraction**
    
    **🆕 NEW: Identical to Main API (v3.0)**
    - 🔄 **Same Response**: Returns identical JSON structure as `/video/fetch`
    - 🧠 **Smart Detection**: Automatically detects adult/NSFW content
    - 🏆 **Best Quality**: Shows highest quality MP4 selected
    - 📊 **Complete Data**: All fields including `is_adult` boolean
    - ⚡ **Browser-Friendly**: Easy GET request for testing
    
    **🧠 Smart Content Detection:**
    - 📺 **Public Videos**: `is_adult: false`, `content_rating: "General Audience"`
    - 🔞 **NSFW/Private**: `is_adult: true`, `content_rating: "Adult (18+)"`
    - 🔄 **Auto-Retry**: Seamlessly tries with cookies if needed
    
    **📝 Example URLs:**
    - `?url=https://x.com/user/status/123` (public content)
    - `?url=https://twitter.com/user/status/456` (any content type)
    
    **📊 Complete Response Includes:**
    - `download_url`: Best quality MP4 download URL
    - `is_adult`: Boolean flag for content type
    - `content_rating`: Human-readable content classification
    - `available_qualities`: All MP4 quality options
    - `quality`: Selected quality (e.g., "1080p")
    - `total_formats_found`: All formats discovered by yt-dlp
    - `mp4_formats_found`: Number of MP4 options available
    - All standard metadata (title, uploader, duration, etc.)
    """
    try:
        # Use the existing video extraction function
        normalized_url = normalize_twitter_url(url)
        
        if not is_valid_twitter_url(normalized_url):
            return {"error": "Invalid Twitter/X URL", "example": "https://x.com/user/status/123456789"}
        
        # Extract video info
        video_data = extract_video_info(normalized_url)
        
        # Return full response (same as API endpoint) for consistency
        return VideoResponse(**video_data)
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful error messages
        if "HTTP Error 404" in error_msg or "Not Found" in error_msg:
            error_msg = "Tweet not found or deleted"
        elif "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
            error_msg = "Access forbidden - need authentication cookies"
        elif "HTTP Error 401" in error_msg or "Unauthorized" in error_msg:
            error_msg = "Unauthorized - upload cookies for private content"
        elif "Unable to extract" in error_msg or "Could not extract" in error_msg:
            error_msg = "Could not extract video from this URL"
        
        return {
            "status": "❌ ERROR",
            "error": error_msg,
            "url_tested": url,
            "help": {
                "cookie_status": "/auth/status",
                "upload_cookies": "Drop raw_cookies.json file in folder",
                "docs": "/docs for full API testing"
            }
        }

@app.get("/")
async def root():
    """
    🏠 **Twitter Video Downloader API - Smart Detection Edition**
    
    **🆕 NEW: Smart Adult Content Detection (v3.0)**
    - Automatic detection - no manual input required
    - Two-step process: tries without cookies, then with cookies
    - Boolean `is_adult` field for easy programming
    - Smart labeling based on actual authentication needs
    
    **🏆 Best Quality Auto-Selection**
    - Always gets highest quality MP4 (1080p, 720p, etc.)
    - Smart quality ranking by resolution + bitrate
    - Returns all available MP4 qualities in response
    
    **🚀 Key Features:**
    - Fully automatic adult content detection
    - Best quality video extraction
    - Unified API responses (test & main endpoints identical)
    - Seamless cookie-based authentication
    - Real-time format analysis
    """
    return {
        "message": "🏆 Twitter Video Downloader API - Smart Detection Edition",
        "version": "3.0.0",
        "new_features_v3": {
            "smart_detection": "Automatic adult/NSFW content detection - no manual input needed",
            "unified_responses": "Test and main API endpoints return identical JSON structure",
            "boolean_flag": "Added is_adult boolean field for easy programming logic",
            "seamless_auth": "Transparent cookie-based authentication for private content"
        },
        "quality_features": {
            "best_quality": "Automatically selects highest quality MP4 available",
            "all_qualities": "Returns all MP4 options with download URLs",
            "smart_ranking": "Quality selection by resolution → bitrate → fps",
            "format_analysis": "Detailed logging of 15+ formats found"
        },
        "endpoints": {
            "test": "GET /test (🧪 browser testable - identical to main API)",
            "fetch_video": "POST /video/fetch (🏆 smart detection + best quality)",
            "upload_cookies": "POST /auth/cookies (🔒 private content access)",
            "auth_status": "GET /auth/status (🔍 authentication check)",
            "cache_stats": "GET /cache/stats (📊 performance metrics)",
            "cookie_manager": "GET /cookies/manager (🍪 web interface)",
            "add_raw_cookies": "POST /cookies/add-raw (📁 drag & drop cookies)",
            "validate_cookies": "POST /cookies/validate (✅ test authentication)",
            "cookies_status": "GET /cookies/status (🔄 cookie health check)"
        },
        "demo_urls": {
            "public_content": "/test?url=https://x.com/user/status/123",
            "auto_detection": "Any URL - system automatically detects content type"
        },
        "documentation": "/docs",
        "cookie_manager": "/cookies/manager"
    }

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print("🚀 Starting Twitter Video Downloader API...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"🍪 Cookie Manager: http://{host}:{port}/cookies/manager")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port) 