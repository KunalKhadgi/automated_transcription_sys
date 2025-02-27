
Once any of "mp3", "wav", "mp4", "mkv", "mov", "flv", "aac", "m4a" file type Is
 introduced in media folder,
watchdog catches the new file and the code generates a new txt file
using openai's wisper model with subtitles for it.

Additionally on downloading a certain file type, code checks the download for the 
duration of 15 min every 5 sec and proceeds with the subtitles ensuring real-time
monitoring for newly added media files.