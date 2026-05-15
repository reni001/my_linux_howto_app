# Linux HowTo App
> A data-driven documentation hub for Linux enthusiasts.This Kivy-based application serves as a personal documentation hub. This project features dynamic synchronization between a local Excel database and Google Firebase.

Developed by: **Renate Schwiedernoch** Version: **0.1.0-dev**

## 📸 Screenshots
| Main Menu | Category View | Article View | Menu Section |
| :---: | :---: | :---: |:---: |
| ![Menu](assets/screenshots/start.png) | ![Category](assets/screenshots/detailscreen.png) |![Article](assets/screenshots/articlescreen.png) | ![Menu](assets/screenshots/menu.png) |

## 🚀 Key Features
* **Cloud Sync:** Fetches real-time documentation from Firebase via a custom Excel-to-Cloud pipeline.
* **Intelligent Navigation:** Multi-tier categorization (OS > Category > Subcategory) with expandable sections.
* **Search Engine:** Includes global search across all articles and local filtering within categories.
* **Dynamic Article Builder:** Renders instructions, code snippets with "Copy to Clipboard" functionality, and stylized warnings/notes.
* **Cross-Platform UI:** Responsive design built with Kivy, featuring orientation toggles and adaptive layouts.

## 🛠 Tech Stack
* **Language:** Python
* **Framework:** Kivy (UI/UX)
* **Backend:** Firebase Realtime Database
* **Data Management:** Pandas & Openpyxl (Excel processing)

---

## 📁 Project Structure
* `main.py`: Core application logic and Kivy UI.
* `sync.py`: Automation script for Firebase updates and GitHub synchronization.
* `assets/icons/`: UI elements (`howto.png`, `menu.png`, `arrow_back.png`).
* `assets/screenshots/`: Visual guides for app usage.
* `data/main.xlsx`: The local Excel database for documentation.
* `requirements.txt`: Python dependency manifest.

---

## 🚀 General Setup & Installation

## 🔧 Installation & Setup
1. Clone the repository:
   ```bash
   git clone [https://github.com/yourusername/linux-howto-app.git](https://github.com/yourusername/linux-howto-app.git)

2. Environment Configuration
We utilize a virtual environment to prevent system-wide package conflicts.

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

3. Install Requirements
pip install -r requirements.txt


#########################
🔥 Firebase Configuration
The sync.py script requires administrative access to your Firebase instance:

Generate a serviceAccountKey.json from the Firebase Console (Project Settings > Service Accounts).

Place the file in the project root.

Security Note: This file is ignored by Git to prevent exposing your private database keys.

#########################
🔧 Arch-Based Linux: Special Instructions
Arch Linux (Manjaro, EndeavourOS) requires specific steps due to its "Rolling Release" nature and strict Python management.

1. Python 3.12 Requirement
Arch often moves to new Python versions (e.g., 3.13+) before Kivy/Buildozer wheels are ready.
Solution: Use pyenv to maintain stability.

    sudo pacman -S pyenv
    pyenv install 3.12
    pyenv local 3.12
    
    Verify the version before creating your venv:
    python --version  # Should show 3.12.x
         
    ### Why we had to do this:
    * **Kivy Wheels:** Sometimes Kivy doesn't have "pre-built" wheels for the brand-new Python version that Arch just released. By moving back to 3.12, we ensure all the library "parts" fit together without having to compile them from scratch (which takes forever).

2. System Dependencies
Kivy requires specific X11 and OpenGL headers to render the UI on Arch:
    
    sudo pacman -S --needed base-devel libx11 libxkbcommon-x11 mesa-utils mtdev

3. PEP 668 (Externally Managed Environment)
Arch enforces virtual environments. If you see a "break-system-packages" error, you must use the venv steps listed in the General Setup section.

4. Solving the "Externally Managed Environment" Error
Arch Linux prevents pip install outside of a virtual environment to protect the system. You must use a Virtual Environment (venv):

    # Create the venv
    python -m venv venv

    # Activate it
    source venv/bin/activate

    # Now install the requirements inside the venv
    pip install -r requirements.txt

5. Kivy & Wayland (Optional)
If you are using Wayland instead of X11 and the app won't open, try forcing the window provider by running:

    KIVY_WINDOW=sdl2 python main.py

#########################
## 🖥️ Linux Desktop Integration
To add this app to your system launcher:
1. Create `run_app.sh` and make it executable: `chmod +x run_app.sh`.
2. Create a `.desktop` file in `~/.local/share/applications/`.
3. Ensure the `Exec` and `Icon` paths point to your absolute project directory.

##########################

⚠️ Known Issues & Solutions

Issue: App won't open on Wayland,
Cause: Graphics backend mismatch,
Fix: Run: KIVY_WINDOW=sdl2 python main.py

Issue: Icons aligned to the left,
Cause: Missing layout spacer,
Fix: A Widget spacer was added in ArticleScreen KV to force icons to the right.

Issue: """Write access denied"" (403)",
Cause: Cached Git credentials,
Fix: Clear Git cache or use a Personal Access Token (PAT) for authentication.

Issue: Massive Repo Size (93MB),
Cause: venv folder tracked,
Fix: Use git rm -r --cached . and update .gitignore to purge large environment files.

Issue: Clipboard Fail,
Cause: Missing xclip,
Fix: Install xclip or xsel via pacman for terminal copy-paste support.


#########################
📱 Features
Dynamic UI: Pulls documentation categories directly from Firebase/Excel.
Searchable Content: Browse through Linux tips and commands.
Responsive Layout: Handles screen orientation changes.

Copy to Clipboard: One-tap copying for terminal commands.

#########################
🛠 Built With
Kivy - The Python Framework for NUI.
Firebase - Realtime Database.
Pandas - For Excel data handling.
