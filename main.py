from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    Message,
    CallbackQuery,
)
from os import environ, remove
from threading import Thread
from json import load
from re import search

from texts import HELP_TEXT
import bypasser
import freewall
from time import time
from db import DB
import requests
from datetime import datetime, timedelta
import os
import urllib.parse
import logging

# Add this at the top of the file
VERIFICATION_REQUIRED = os.getenv('VERIFICATION_REQUIRED', 'true').lower() == 'true'

admin_ids = [6025969005, 6018060368]

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI')  # Get MongoDB URI from environment variables
client = MongoClient(MONGO_URI)
db = client['terabox_bot']
users_collection = db['users']

# bot
with open("config.json", "r") as f:
    DATA: dict = load(f)


def getenv(var):
    return environ.get(var) or DATA.get(var, None)


bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
with app:
    app.set_bot_commands(
        [
            BotCommand("start", "Welcome Message"),
            BotCommand("help", "List of All Supported Sites"),
            BotCommand("get_token", "Check Your Token Status"),
        ]
    )

# DB
db_api = getenv("DB_API")
db_owner = getenv("DB_OWNER")
db_name = getenv("DB_NAME")
try: database = DB(api_key=db_api, db_owner=db_owner, db_name=db_name)
except: 
    print("Database is Not Set")
    database = None


# handle index
def handleIndex(ele: str, message: Message, msg: Message):
    result = bypasser.scrapeIndex(ele)
    try:
        app.delete_messages(message.chat.id, msg.id)
    except:
        pass
    if database and result: database.insert(ele, result)
    for page in result:
        app.send_message(
            message.chat.id,
            page,
            reply_to_message_id=message.id,
            disable_web_page_preview=True,
        )


# loop thread
def loopthread(message: Message, otherss=False):

    urls = []
    if otherss:
        texts = message.caption
    else:
        texts = message.text

    if texts in [None, ""]:
        return
    for ele in texts.split():
        if "http://" in ele or "https://" in ele:
            urls.append(ele)
    if len(urls) == 0:
        return

    if bypasser.ispresent(bypasser.ddl.ddllist, urls[0]):
        msg: Message = app.send_message(
            message.chat.id, "⚡ __generating...__", reply_to_message_id=message.id
        )
    elif freewall.pass_paywall(urls[0], check=True):
        msg: Message = app.send_message(
            message.chat.id, "🕴️ __jumping the wall...__", reply_to_message_id=message.id
        )
    else:
        if "https://olamovies" in urls[0] or "https://psa.wf/" in urls[0]:
            msg: Message = app.send_message(
                message.chat.id,
                "⏳ __this might take some time...__",
                reply_to_message_id=message.id,
            )
        else:
            msg: Message = app.send_message(
                message.chat.id, "🔎 __bypassing...__", reply_to_message_id=message.id
            )

    strt = time()
    links = ""
    temp = None

    for ele in urls:
        if database: df_find = database.find(ele)
        else: df_find = None
        if df_find:
            print("Found in DB")
            temp = df_find
        elif search(r"https?:\/\/(?:[\w.-]+)?\.\w+\/\d+:", ele):
            handleIndex(ele, message, msg)
            return
        elif bypasser.ispresent(bypasser.ddl.ddllist, ele):
            try:
                temp = bypasser.ddl.direct_link_generator(ele)
            except Exception as e:
                temp = "**Error**: " + str(e)
        elif freewall.pass_paywall(ele, check=True):
            freefile = freewall.pass_paywall(ele)
            if freefile:
                try:
                    app.send_document(
                        message.chat.id, freefile, reply_to_message_id=message.id
                    )
                    remove(freefile)
                    app.delete_messages(message.chat.id, [msg.id])
                    return
                except:
                    pass
            else:
                app.send_message(
                    message.chat.id, "__Failed to Jump", reply_to_message_id=message.id
                )
        else:
            try:
                temp = bypasser.shortners(ele)
            except Exception as e:
                temp = "**Error**: " + str(e)

        print("bypassed:", temp)
        if temp != None:
            if (not df_find) and ("http://" in temp or "https://" in temp) and database:
                print("Adding to DB")
                database.insert(ele, temp)
            links = links + temp + "\n"

    end = time()
    print("Took " + "{:.2f}".format(end - strt) + "sec")

    if otherss:
        try:
            app.send_photo(
                message.chat.id,
                message.photo.file_id,
                f"__{links}__",
                reply_to_message_id=message.id,
            )
            app.delete_messages(message.chat.id, [msg.id])
            return
        except:
            pass

    try:
        final = []
        tmp = ""
        for ele in links.split("\n"):
            tmp += ele + "\n"
            if len(tmp) > 4000:
                final.append(tmp)
                tmp = ""
        final.append(tmp)
        app.delete_messages(message.chat.id, msg.id)
        tmsgid = message.id
        for ele in final:
            tmsg = app.send_message(
                message.chat.id,
                f"__{ele}__",
                reply_to_message_id=tmsgid,
                disable_web_page_preview=True,
            )
            tmsgid = tmsg.id
    except Exception as e:
        app.send_message(
            message.chat.id,
            f"__Failed to Bypass : {e}__",
            reply_to_message_id=message.id,
        )


# start command
@app.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    user = message.from_user
    logger.info(f"Start command received from user {user.id} ({user.first_name})")

    # Check if the start command includes a parameter
    if message.command and len(message.command) > 1:
        parameter = message.command[1]
        logger.info(f"Start command parameter: {parameter}")
        
        # Check for get_token parameter
        if parameter == "get_token":
            logger.info(f"Redirecting to get_token command for user {user.id}")
            # Redirect to get_token command
            await get_token_command(client, message)
            return
        
        # Handle token verification
        token = parameter
        logger.info(f"Attempting to verify token: {token[:6]}... for user {user.id}")
        user_data = users_collection.find_one({"user_id": user.id, "token": token})

        if user_data:
            # Check if the token is expired
            token_expiration = user_data.get("token_expiration", datetime.min)
            if token_expiration > datetime.now():
                # Update the user's verification status
                verified_until = datetime.now() + timedelta(days=1)
                users_collection.update_one(
                    {"user_id": user.id},
                    {"$set": {"verified_until": verified_until}},
                    upsert=True
                )
                logger.info(f"User {user.id} successfully verified until {verified_until}")
                await message.reply_text(
                    f"✅ **Verification Successful!**\n\n"
                    f"You can now use the bot for the next 24 hours without any ads or restrictions.\n"
                    f"Your verification will expire on: {verified_until.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                logger.warning(f"User {user.id} tried to use expired token")
                await message.reply_text(
                    "❌ **Token Expired!**\n\n"
                    "Please generate a new token and try verifying again."
                )
        else:
            logger.warning(f"User {user.id} tried to use invalid token: {token[:6]}...")
            await message.reply_text(
                "❌ **Invalid Token!**\n\n"
                "Please try verifying again."
            )
        return
    
    # If no parameter, send the welcome message and store user ID in MongoDB
    users_collection.update_one(
        {"user_id": user.id},
        {"$set": {"username": user.username, "first_name": user.first_name, "last_name": user.last_name}},
        upsert=True
    )
    logger.info(f"Sending welcome message to user {user.id}")
    await app.send_message(
        message.chat.id,
        f"__👋 Hi **{message.from_user.mention}**, I am Link Bypasser Bot. Just send me any supported links and I will get you results.\nCheckout /help to read more.\n\nIf you face any issue with some sites please report error, We solve it as soon as possible.__",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Request New Sites",
                        url="https://t.me/Assistant_24_7_bot",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Supported Sites",
                        callback_data="send_help",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Dev Channel",
                        url="https://t.me/+WaXaosFDkGowYjI1",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Report Error",
                        url="https://t.me/Assistant_24_7_bot",
                    )
                ],
            ]
        ),
        reply_to_message_id=message.id,
    )


# help command
@app.on_message(filters.command(["help"]))
def send_help(
    client: Client,
    message: Message,
):
    app.send_message(
        message.chat.id,
        HELP_TEXT,
        reply_to_message_id=message.id,
        disable_web_page_preview=True,
    )

# stats command
@app.on_message(filters.command(["stats"]))
async def stats(client: Client, message: Message):
    if message.from_user.id in admin_ids:
        try:
            # Get total users
            total_users = users_collection.count_documents({})

            # Get MongoDB database stats
            db_stats = db.command("dbstats")

            # Calculate used storage
            used_storage_mb = db_stats['dataSize'] / (1024 ** 2)  # Convert bytes to MB

            # Calculate total and free storage (if available)
            if 'fsTotalSize' in db_stats:
                total_storage_mb = db_stats['fsTotalSize'] / (1024 ** 2)  # Convert bytes to MB
                free_storage_mb = total_storage_mb - used_storage_mb
            else:
                total_storage_mb = "N/A"
                free_storage_mb = "N/A"

            # Prepare the response message
            message_text = (
                f"📊 **Bot Statistics**\n\n"
                f"👥 **Total Users:** {total_users}\n"
                f"💾 **MongoDB Used Storage:** {used_storage_mb:.2f} MB\n"
                f"🆓 **MongoDB Free Storage:** {free_storage_mb if isinstance(free_storage_mb, str) else f'{free_storage_mb:.2f} MB'}\n"
            )

            await message.reply_text(message_text)
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            await message.reply_text("❌ An error occurred while fetching stats.")
    else:
        await message.reply_text("You have no rights to use my commands.")
        
# token command
@app.on_message(filters.command(["get_token"]))
async def get_token_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})
    
    if user_data and user_data.get("verified_until", datetime.min) > datetime.now():
        # User has a valid token
        verified_until = user_data.get("verified_until")
        time_left = verified_until - datetime.now()
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Get the user's token
        user_token = user_data.get("token", "Not found")
        
        await message.reply_text(
            f"✅ **You have a valid token!**\n\n"
            f"Your token is active and will expire on:\n"
            f"📅 {verified_until.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"⏱️ Time remaining: {time_left.days} days, {hours} hours, {minutes} minutes\n\n"
            f"🔑 Your token: `{user_token}`"
        )
    else:
        # User needs to verify
        bot_username = (await client.get_me()).username
        token_url = await get_token(user_id, bot_username)
        
        btn = [
            [InlineKeyboardButton("Verify Now", url=token_url)],
            [InlineKeyboardButton("How To Open Link & Verify", url="https://t.me/how_to_download_0011")]
        ]
        
        await message.reply_text(
            text="❌ **You don't have an active token!**\n\n"
                 "To use the bot, you need to verify your token.\n\n"
                 "🔑 Why Tokens?\n"
                 "Tokens unlock premium features with a quick ad process. Enjoy 24 hours of uninterrupted access! 🌟\n\n"
                 "👉 Tap below to verify your token.",
            reply_markup=InlineKeyboardMarkup(btn)
        )

# callback query handler
@app.on_callback_query(filters.regex("send_help"))
def callback_help(client: Client, callback_query: CallbackQuery):
    callback_query.message.edit_text(
        HELP_TEXT,
        disable_web_page_preview=True,
    )

# Define the /broadcast command handler
@app.on_message(filters.command(["broadcast"]))
async def broadcast(client: Client, message: Message):
    if message.from_user.id in admin_ids:
        reply_message = message.reply_to_message
        if reply_message:
            # Fetch all user IDs from MongoDB
            all_users = users_collection.find({}, {"user_id": 1})
            total_users = users_collection.count_documents({})
            sent_count = 0
            block_count = 0
            fail_count = 0

            for user_data in all_users:
                user_id = user_data['user_id']
                try:
                    if reply_message.photo:
                        await client.send_photo(chat_id=user_id, photo=reply_message.photo.file_id, caption=reply_message.caption)
                    elif reply_message.video:
                        await client.send_video(chat_id=user_id, video=reply_message.video.file_id, caption=reply_message.caption)
                    else:
                        await client.send_message(chat_id=user_id, text=reply_message.text)
                    sent_count += 1
                except Exception as e:
                    if 'blocked' in str(e):
                        block_count += 1
                    else:
                        fail_count += 1

            await message.reply_text(
                f"Broadcast completed!\n\n"
                f"Total users: {total_users}\n"
                f"Messages sent: {sent_count}\n"
                f"Users blocked the bot: {block_count}\n"
                f"Failed to send messages: {fail_count}"
            )
        else:
            await message.reply_text("Please reply to a message with /broadcast to send it to all users.")
    else:
        await message.reply_text("You have no rights to use my commands.")
        
# links
@app.on_message(filters.text)
async def receive(client: Client, message: Message):
    user = message.from_user
    logger.info(f"Received message from user {user.id}: {message.text[:20]}...")

    # Check if user is admin
    if user.id in admin_ids:
        logger.info(f"User {user.id} is admin, bypassing verification")
        # Admin does not need verification
        pass
    else:
        # User needs verification
        verification_status = await check_verification(user.id)
        if not verification_status:
            logger.info(f"User {user.id} needs verification, sending token link")
            # User needs to verify
            try:
                bot_username = (await client.get_me()).username
                token_url = await get_token(user.id, bot_username)
                
                btn = [
                    [InlineKeyboardButton("Verify", url=token_url)],
                    [InlineKeyboardButton("How To Open Link & Verify", url="https://t.me/how_to_download_0011")]
                ]
                
                await message.reply_text(
                    text="🚨 Token Expired!\n\n"
                         "Timeout: 24 hours\n\n"
                         "Your access token has expired. Verify it to continue using the bot!\n\n"
                         "🔑 Why Tokens?\n\n"
                         "Tokens unlock premium features with a quick ad process. Enjoy 24 hours of uninterrupted access! 🌟\n\n"
                         "👉 Tap below to verify your token.\n\n"
                         "Thank you for your support! ❤️",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
            except Exception as e:
                logger.error(f"Error while sending verification message: {e}")
                await message.reply_text("An error occurred. Please try again later or contact the bot admin.")
                return
    
    # Proceed with the bypass process
    logger.info(f"Processing links for user {user.id}")
    bypass = Thread(target=lambda: loopthread(message), daemon=True)
    bypass.start()

async def check_verification(user_id: int) -> bool:
    user = users_collection.find_one({"user_id": user_id})
    if user and user.get("verified_until", datetime.min) > datetime.now():
        logger.info(f"User {user_id} is verified until {user.get('verified_until')}")
        return True
    if user:
        logger.info(f"User {user_id} verification expired or not found - last expiry: {user.get('verified_until', 'never')}")
    else:
        logger.info(f"User {user_id} not found in database")
    return False

async def get_token(user_id: int, bot_username: str) -> str:
    # Generate a random token
    token = os.urandom(16).hex()
    # Set token expiration time (24 hours from now)
    token_expiration = datetime.now() + timedelta(hours=24)
    # Update user's verification status in database
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "token": token, 
            "token_expiration": token_expiration, 
            "verified_until": datetime.min
        }},  # Reset verified_until to min
        upsert=True
    )
    # Log token generation for debugging
    logger.info(f"Generated token for user {user_id}: {token}")
    
    # Create verification link with the actual token for verification
    verification_link = f"https://telegram.me/{bot_username}?start={token}"
    
    # Shorten verification link using shorten_url_link function
    try:
        shortened_link = shorten_url_link(verification_link)
        logger.info(f"Shortened verification link generated for user {user_id}")
        return shortened_link
    except Exception as e:
        logger.error(f"Failed to shorten URL, using original link: {e}")
        return verification_link

def shorten_url_link(url):
    api_url = 'https://adrinolinks.in/api'
    api_key = '599ee2c148d46fe9061578db049f3cd32f528bf6'
    params = {
        'api': api_key,
        'url': url
    }
    
    logger.info(f"Attempting to shorten URL via Arolinks API")
    
    try:
        # Use custom certificate bundle for SSL verification
        cert_path = os.path.join("certificates", "ca-bundle.crt")
        
        # Check if certificate file exists
        if os.path.exists(cert_path):
            # Set verify to the custom certificate bundle path
            logger.info(f"Using custom certificate bundle at {cert_path}")
            response = requests.get(api_url, params=params, verify=cert_path, timeout=10)
        else:
            logger.warning(f"Certificate file not found at {cert_path}, using default verification")
            response = requests.get(api_url, params=params, timeout=10)
            
        if response.status_code == 200:
            try:
                data = response.json()
                if data and isinstance(data, dict) and data.get('status') == 'success' and 'shortenedUrl' in data:
                    logger.info(f"Arolinks shortened URL successfully")
                    return data['shortenedUrl']
                else:
                    logger.error(f"Invalid response format from Arolinks API: {data}")
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {e}")
        else:
            logger.error(f"Arolinks API returned status code {response.status_code}")
            
    except requests.exceptions.SSLError as ssl_error:
        logger.error(f"SSL Certificate error: {ssl_error}")
    except requests.exceptions.Timeout:
        logger.error("Request to Arolinks API timed out")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error when calling Arolinks API")
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
    
    logger.warning(f"Failed to shorten URL with Arolinks, returning original URL")
    return url


# doc thread
def docthread(message: Message):
    msg: Message = app.send_message(
        message.chat.id, "🔎 __bypassing...__", reply_to_message_id=message.id
    )
    print("sent DLC file")
    file = app.download_media(message)
    dlccont = open(file, "r").read()
    links = bypasser.getlinks(dlccont)
    app.edit_message_text(
        message.chat.id, msg.id, f"__{links}__", disable_web_page_preview=True
    )
    remove(file)


# files
@app.on_message([filters.document, filters.photo, filters.video])
def docfile(
    client: Client,
    message: Message,
):

    try:
        if message.document.file_name.endswith("dlc"):
            bypass = Thread(target=lambda: docthread(message), daemon=True)
            bypass.start()
            return
    except:
        pass

    bypass = Thread(target=lambda: loopthread(message, True), daemon=True)
    bypass.start()


# server loop
print("Bot Starting")
app.run()
