# 🔐 Password Saving Guide for AskSQL Console

## ✅ What I've Implemented

Your AskSQL app now has **automatic credential saving** with a simple checkbox!

### 💾 **"Remember Me" Feature** (NEW!)
- **How it works**: Check the "💾 Remember credentials on this computer" box when connecting
- **What it does**: 
  - Saves your credentials to `~/.asksql_credentials.json` on your computer
  - Password is base64 encoded (basic obfuscation, not encryption)
  - Auto-loads credentials when you open the app next time
- **When it helps**: 
  - Credentials persist even after closing the browser
  - No need to re-enter credentials ever again!
  - Works across browser sessions and restarts

### ⚡ **Session Persistence**
- Once connected, credentials stay in memory while the browser tab is open
- Form fields auto-populate with your last connection
- Connection status shows at the bottom of the sidebar

### 🗑️ **Clear Button**
- Removes credentials from both memory AND disk
- Useful when switching databases or removing saved credentials

## 🎯 How to Use

### First Time Setup:
1. Open your AskSQL app
2. Enter your database credentials in the sidebar
3. ✅ **Check the box**: "💾 Remember credentials on this computer"
4. Click "🔌 Connect"
5. You'll see: "✅ Connected & credentials saved!"

### Next Time:
1. Open the app
2. **Credentials auto-load automatically!** ✨
3. Just click "🔌 Connect" (or they may already be connected!)

### To Stop Saving Credentials:
1. Uncheck "💾 Remember credentials on this computer"
2. Click "🔌 Connect"
3. Or click "🗑️ Clear" to remove saved credentials entirely

## 🔒 Security Notes

- **File Location**: Credentials saved to `~/.asksql_credentials.json` in your home directory
- **Encoding**: Password is base64 encoded (basic obfuscation, NOT encryption)
- **Local Only**: File stays on your computer, never transmitted anywhere
- **Session Storage**: Also kept in browser memory during active session
- **Easy Removal**: Click "🗑️ Clear" to delete saved credentials anytime

⚠️ **Important**: This is basic obfuscation, not encryption. Don't use this on shared computers or for highly sensitive databases. For production use, consider using environment variables or a proper secrets manager.

## 🎨 Visual Indicators

When you're connected, you'll see:
- ✅ Green success message: "Connected to **MySQL** at `localhost:3306`"
- 💾 If credentials are saved: "Credentials saved to disk" caption

## 🚀 New Features

1. **💾 Remember Me checkbox**: One-click credential saving
2. **Auto-load on startup**: Credentials load automatically when you open the app
3. **Connection status**: Always know if you're connected
4. **Disk persistence**: Credentials survive browser restarts
5. **Easy clearing**: One-click removal of saved credentials

## 🐛 Troubleshooting

**Q: Checkbox is there but credentials don't save?**
- Check file permissions in your home directory
- Look for error messages in the app
- Try clicking "🗑️ Clear" then reconnecting

**Q: Want to see the saved file?**
```bash
cat ~/.asksql_credentials.json
```
(Password will be base64 encoded)

**Q: Want to manually delete saved credentials?**
```bash
rm ~/.asksql_credentials.json
```

**Q: Credentials not auto-loading?**
- Make sure you checked "💾 Remember credentials" when connecting
- Check if `~/.asksql_credentials.json` exists
- Try refreshing the page

**Q: Using a shared computer?**
- **Don't check** "💾 Remember credentials"
- Click "🗑️ Clear" when done
- Or manually delete `~/.asksql_credentials.json`

## 📝 Technical Details

The implementation includes:
- JSON file storage in user's home directory (`~/.asksql_credentials.json`)
- Base64 encoding for password obfuscation
- Automatic loading on app startup
- Session state management
- Checkbox state persistence
- Graceful error handling
