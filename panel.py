import telebot
import requests
import time
import threading
import json

# 🔑 Bot Token from BotFather
BOT_TOKEN = "8500852701:AAF5cKxS_ttpiErOhsGeOUknAZ4njSFMxAg"
# 👑 Admin ID (Only your numeric ID)
ADMIN_IDS = [6710024903]

# API URLs
ADD_URL = "https://addfriendmain-by-wotaxx.vercel.app/add?uid={uid}&password={password}&region={region}&adduid={player_id}"
REMOVE_URL = "https://addfriendmain-by-wotaxx.vercel.app/remove?uid={uid}&password={password}&region={region}&adduid={player_id}"

# Temporary database to track added players
added_players = {}

bot = telebot.TeleBot(BOT_TOKEN)

def read_friend_credentials():
    """Read UID and password from friend.txt file"""
    try:
        with open("friend.txt", "r") as file:
            lines = file.readlines()
            if len(lines) >= 2:
                uid = lines[0].strip()
                password = lines[1].strip()
                return uid, password
            else:
                return None, None
    except FileNotFoundError:
        return None, None

def test_api_connection(uid, password, region="IND", test_player_id="123456789"):
    """Test if the API is working with current credentials"""
    try:
        test_url = ADD_URL.format(
            uid=uid,
            password=password,
            region=region,
            player_id=test_player_id
        )
        
        response = requests.get(test_url, timeout=10)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

# 🟢 /start and /help
@bot.message_handler(commands=["start", "help"])
def send_help(msg):
    # Test credentials on start
    uid, password = read_friend_credentials()
    status_info = ""
    
    if uid and password:
        status_code, response_text = test_api_connection(uid, password)
        if status_code == 200:
            status_info = "✅ Credentials are working properly!"
        else:
            status_info = f"❓ API Test: Status {status_code}, Response: {response_text[:100]}"
    else:
        status_info = "❌ No credentials found in friend.txt"
    
    bot.reply_to(msg,
        f"👑 Welcome to Friend Management Bot by xr\n\n"
        f"{status_info}\n\n"
        "🔸 Add and remove friends using uid and password\n\n"
        "📝 Commands:\n"
        "➕ /add <region> <player_id> - Add a friend\n"
        "➖ /rem <region> <player_id> - Remove a friend\n"
        "📋 /list - View added friends (Admin only)\n"
        "🔧 /test - Test API connection\n\n"
        "🌍 Regions: ME, EU, IND, etc.",
        parse_mode="Markdown"
    )

# 🔧 /test - Test API connection
@bot.message_handler(commands=["test"])
def test_connection(msg):
    uid, password = read_friend_credentials()
    
    if not uid or not password:
        bot.reply_to(msg, "❌ Credentials not found in friend.txt")
        return
    
    bot.reply_to(msg, "🔄 Testing API connection...")
    
    status_code, response_text = test_api_connection(uid, password)
    
    if status_code == 200:
        bot.reply_to(msg, f"✅ API is working!\nStatus: {status_code}\nResponse: {response_text}")
    else:
        bot.reply_to(msg, f"❌ API test failed!\nStatus: {status_code}\nResponse: {response_text}")

# ➕ /add region player_id
@bot.message_handler(commands=["add"])
def handle_add(msg):
    try:
        # Parse command: /add ME 123456789
        parts = msg.text.split()
        if len(parts) != 3:
            bot.reply_to(msg, "❗ Please use the correct format:\n/add <region> <player_id>")
            return
        
        region = parts[1].upper()
        player_id = parts[2]
        
 
        
        # Validate player_id (should be numeric)
        if not player_id.isdigit():
            bot.reply_to(msg, "❌ Player ID must be numeric")
            return
        
        # Read credentials from file
        uid, password = read_friend_credentials()
        
        if not uid or not password:
            bot.reply_to(msg, "❌ Credentials not found. Please check friend.txt file.")
            return
        
        # Build the API URL
        url = ADD_URL.format(
            uid=uid,
            password=password,
            region=region,
            player_id=player_id
        )
        
        bot.reply_to(msg, f"🔄 Adding friend...\nRegion: {region}\nPlayer ID: {player_id}")
        
        # Send request to API with timeout
        try:
            r = requests.get(url, timeout=30)
            response_text = r.text
            
            # Debug information
            print(f"DEBUG - Add Request: {url}")
            print(f"DEBUG - Status Code: {r.status_code}")
            print(f"DEBUG - Response: {response_text}")
            
            if r.status_code == 200:
                if "error" in response_text.lower():
                    bot.reply_to(msg, f"❌ API returned error:\n{response_text}")
                else:
                    bot.reply_to(msg, f"✅ Friend added successfully!\n\nRegion: {region}\nPlayer ID: {player_id}\nResponse: {response_text}")
                    
                    # Store in temporary database
                    added_players[player_id] = {
                        "by": msg.from_user.id,
                        "time": time.time(),
                        "region": region
                    }
                    
                    # Schedule automatic removal after 24 hours
                    threading.Thread(target=remove_after_24h, args=(player_id, region, msg.chat.id), daemon=True).start()
            else:
                bot.reply_to(msg, f"❌ Failed to add friend.\nStatus: {r.status_code}\nResponse: {response_text}")
                
        except requests.exceptions.Timeout:
            bot.reply_to(msg, "❌ Request timeout. The server took too long to respond.")
        except requests.exceptions.ConnectionError:
            bot.reply_to(msg, "❌ Connection error. Cannot reach the API server.")
        except requests.exceptions.RequestException as e:
            bot.reply_to(msg, f"❌ Request failed: {str(e)}")
            
    except Exception as e:
        bot.reply_to(msg, f"❌ Unexpected error: {str(e)}")

# ➖ /rem region player_id
@bot.message_handler(commands=["rem"])
def handle_remove(msg):
    try:
        # Parse command: /rem ME 123456789
        parts = msg.text.split()
        if len(parts) != 3:
            bot.reply_to(msg, "❗ Please use the correct format:\n/rem <region> <player_id>")
            return
        
        region = parts[1].upper()
        player_id = parts[2]
        
        # Read credentials from file
        uid, password = read_friend_credentials()
        
        if not uid or not password:
            bot.reply_to(msg, "❌ Credentials not found. Please check friend.txt file.")
            return
        
        # Build the API URL
        url = REMOVE_URL.format(
            uid=uid,
            password=password,
            region=region,
            player_id=player_id
        )
        
        # Send request to API
        try:
            r = requests.get(url, timeout=30)
            response_text = r.text
            
            print(f"DEBUG - Remove Request: {url}")
            print(f"DEBUG - Status Code: {r.status_code}")
            print(f"DEBUG - Response: {response_text}")
            
            if r.status_code == 200:
                bot.reply_to(msg, f"✅ Friend removed successfully!\n\nRegion: {region}\nPlayer ID: {player_id}\nResponse: {response_text}")
                
                # Remove from temporary database
                added_players.pop(player_id, None)
            else:
                bot.reply_to(msg, f"❌ Failed to remove friend.\nStatus: {r.status_code}\nResponse: {response_text}")
                
        except requests.exceptions.Timeout:
            bot.reply_to(msg, "❌ Request timeout. The server took too long to respond.")
        except requests.exceptions.ConnectionError:
            bot.reply_to(msg, "❌ Connection error. Cannot reach the API server.")
            
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {str(e)}")

# 📋 /list (Admin only)
@bot.message_handler(commands=["list"])
def handle_list(msg):
    if msg.from_user.id in ADMIN_IDS:
        if not added_players:
            bot.reply_to(msg, "📭 No friends have been added.")
        else:
            text = "📄 Added Friends List:\n\n"
            for player_id, data in added_players.items():
                # Calculate time remaining for auto-removal
                time_elapsed = time.time() - data['time']
                time_remaining = 86400 - time_elapsed
                hours_remaining = max(0, int(time_remaining / 3600))
                
                text += f"• {player_id} (Region: {data['region']}, Added by: {data['by']}, Auto-remove in: {hours_remaining}h)\n"
            bot.reply_to(msg, text)
    else:
        bot.reply_to(msg, "🚫 This command is for administrators only.")

# ⏱ Automatic removal after 24 hours
def remove_after_24h(player_id, region, chat_id):
    time.sleep(86400)  # 24 hours
    
    # Read credentials from file
    uid, password = read_friend_credentials()
    
    if uid and password:
        # Build the removal URL
        url = REMOVE_URL.format(
            uid=uid,
            password=password,
            region=region,
            player_id=player_id
        )
        
        # Send removal request
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                bot.send_message(chat_id, f"🗑️ Friend automatically removed: {player_id} (Region: {region})")
            else:
                bot.send_message(chat_id, f"⚠️ Attempted to remove friend: {player_id} but failed. Status: {r.status_code}")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Error auto-removing friend {player_id}: {str(e)}")
    
    # Remove from database
    added_players.pop(player_id, None)

# 🚀 Start the bot
print("✅ Bot is now running...")
print("📁 Reading credentials from friend.txt...")

# Check if credentials file exists
uid, password = read_friend_credentials()
if uid and password:
    print(f"✅ Credentials loaded - UID: {uid}")
    print("🔧 Testing API connection...")
    status_code, response = test_api_connection(uid, password)
    print(f"🔧 API Test - Status: {status_code}, Response: {response}")
else:
    print("❌ Could not load credentials from friend.txt")

print("🤖 Bot is ready to receive commands!")
bot.infinity_polling()