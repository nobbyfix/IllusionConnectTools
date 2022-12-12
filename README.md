# IllusionConnectTools
Tools to import APKs, download new updates and decrypt all files for the mobile game Illusion Connect.

## Dependencies
* Python 3.9+ with Cython, requests
* TexturePacker and Python Pillow for `apply_image_alpha.py`
* Clone the [luajit decompiler](https://gitlab.com/znixian/luajit-decompiler) into the `lib/bin` folder (you need to create the "bin" folder inside "lib")
* Python Git to execute `update.py` (i'd recommend to just comment all git code out since you would also need to build git repository)


## Setup
1. Clone this repository
2. Download all required dependencies as seen above
3. Run `py setup.py build_ext --inplace` in the `lib/xxtea` folder (or run the `setup.bat` if you are on windows)
4. Optionally add a user agent and device id to the `config.json` (dont know if needed/the server rejects you if you run the update script)

## Additional Notes
* You need to import from apk if you want everything to work as is.
* If you need help using this, you can message me on Discord (nobbyfix#2338), although i'm not going to help you with basic stuff like editing python code or whatever. I don't have time for that.
