import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
from pymongo import MongoClient
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, ImageClip
from datetime import datetime

# MongoDB setup
client = MongoClient("mongodb+srv://Cenzo:Cenzo123@cenzo.azbk1.mongodb.net/")
db = client['rename_bot']
file_collection = db['files']

# Stages for conversation
ASK_WATERMARK, ASK_TEXT, ASK_IMAGE = range(3)

# Start renaming command
async def start_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Rename with Watermark", callback_data="rename_with_watermark")],
        [InlineKeyboardButton("Rename without Watermark", callback_data="rename_without_watermark")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose renaming option:", reply_markup=reply_markup)

# Watermark option handler
async def watermark_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Text Watermark", callback_data="watermark_text")],
        [InlineKeyboardButton("Image Watermark", callback_data="watermark_image")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Choose watermark type:", reply_markup=reply_markup)

# Function to add a text watermark
def add_text_watermark(video_path, text):
    video = VideoFileClip(video_path)
    watermark = TextClip(text, fontsize=24, color='white', bg_color='black')
    watermark = watermark.set_position(("right", "bottom")).set_duration(video.duration)
    final = CompositeVideoClip([video, watermark])
    output_path = "output_with_text_watermark.mp4"
    final.write_videofile(output_path, codec="libx264")
    return output_path

# Function to add an image watermark
def add_image_watermark(video_path, image_path):
    video = VideoFileClip(video_path)
    watermark = ImageClip(image_path).set_duration(video.duration).set_position(("right", "bottom")).resize(height=50)
    final = CompositeVideoClip([video, watermark])
    output_path = "output_with_image_watermark.mp4"
    final.write_videofile(output_path, codec="libx264")
    return output_path

# Handle text watermark input
async def receive_text_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watermark_text = update.message.text
    video_path = context.user_data.get("video_path")  # Load video path from user data
    output_path = add_text_watermark(video_path, watermark_text)
    
    # Log to MongoDB
    log_action(update, "text watermark", video_path, output_path)

    await update.message.reply_video(video=open(output_path, 'rb'))
    await update.message.reply_text(f"Renamed file: ```{os.path.basename(output_path)}```", parse_mode="MarkdownV2")
    os.remove(output_path)

# Handle image watermark input
async def receive_image_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    image_path = "watermark_image.jpg"
    await photo.get_file().download(image_path)
    video_path = context.user_data.get("video_path")
    output_path = add_image_watermark(video_path, image_path)
    
    # Log to MongoDB
    log_action(update, "image watermark", video_path, output_path)

    await update.message.reply_video(video=open(output_path, 'rb'))
    await update.message.reply_text(f"Renamed file: ```{os.path.basename(output_path)}```", parse_mode="MarkdownV2")
    os.remove(output_path)
    os.remove(image_path)

# Log action to MongoDB
def log_action(update, operation, original_path, new_path):
    log_entry = {
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "operation": operation,
        "original_name": os.path.basename(original_path),
        "new_name": os.path.basename(new_path),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    file_collection.insert_one(log_entry)

# Callback to rename without watermark
async def rename_without_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Process renaming logic
    video_path = context.user_data.get("video_path")
    new_name = "renamed_file.mp4"  # Replace with actual logic if needed
    os.rename(video_path, new_name)
    
    # Log to MongoDB
    log_action(update, "rename without watermark", video_path, new_name)

    # Send the renamed file with the name in monospaced text
    await update.message.reply_video(video=open(new_name, 'rb'))
    await update.message.reply_text(f"Renamed file: ```{new_name}```", parse_mode="MarkdownV2")
    os.remove(new_name)

# Main handler setup
def main():
    application = Application.builder().token("7463193602:AAHzVUiVeiO9-YHBDiFMqCXfAtBul52-WP4").build()

    # Add handlers
    application.add_handler(CommandHandler("rename", start_rename))
    application.add_handler(CallbackQueryHandler(watermark_option, pattern="rename_with_watermark"))
    application.add_handler(CallbackQueryHandler(rename_without_watermark, pattern="rename_without_watermark"))
    application.add_handler(CallbackQueryHandler(receive_text_watermark, pattern="watermark_text"))
    application.add_handler(CallbackQueryHandler(receive_image_watermark, pattern="watermark_image"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_watermark))
    application.add_handler(MessageHandler(filters.PHOTO, receive_image_watermark))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
