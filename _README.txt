First run steps:

1. Run the included _SETUP.bat
	- This is only necessary if you do not already have FFMPEG installed

2. Run Demixer.exe

You can now run Demixer whenever. However, if you move the demixer folder, you
will need to run _SETUP.bat again to add the new FFMPEG location to the system
PATH.


How to operate:

1. Use the input file selector to choose your input audio file.
   - Note: If you have already selected a file and saved slices, you will either have to
     export the slices or clear them before being able to select a new input

2. While this file loads, you will see an audio loading message.
   - This may take upwards of a minute depending on the file size

3. Once the file is loaded you will see an audio ready message.

4. You can now use the playback controls and the audio slider to move through the audio

5. When you find the location where you want to split the audio, press the set button next
   to the corresponding start/end time

6. Once you have set a start and end time for the slice, press the save button. This will
   generate a preview that you can play/pause/seek on. You can also set whatever name you
   want for the track, excluding file extensions. You can also use the X button to remove
   the saved slice
   - Note: Any playing track must be paused before another will be allowed to play

7. Once you have saved any number of slices, use the export path selector to select where
   you want the track files to be saved to.

8. After selecting where to export to, hit the export button. You will see an export message
   displaying the progress as it exports the saved slices. After it finishes exporting it will
   clear the saved slices.

Known bugs:
- When you want to move slider on a slice preview, long press instead of tap
- When using the file selectors, I recommend you use the arrows (next to folder name)
  to drill down into the file structure due to strange behaviors at times when selecting
  the folder name
- Currently file selectors will only show folder/files on the same disk

Enjoy, and let me known about any issues at astraeusdev@gmail.com