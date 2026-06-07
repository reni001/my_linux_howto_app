# 🧠 Linux HowTo App 

## 📖 Overview 

The Linux HowTo App is a Python + Kivy desktop application for browsing, managing, and synchronising Linux documentation. 

It acts as a personal documentation hub + lightweight content management system (CMS) with: 

✅ Online + offline support 
✅ Structured categories & subcategories 
✅ Editable topics with steps and code snippets 
✅ Synchronisation via Firebase + Git 

## 📸 Screenshots
| Main Menu | Category View | Article View | Menu Section |
| :---: | :---: | :---: |:---: |
| ![Menu](assets/screenshots/start.png) | ![Category](assets/screenshots/detailscreen.png) |![Article](assets/screenshots/articlescreen.png) | ![Menu](assets/screenshots/menu.png) |

---

## 🚀 Key Features 

### 📂 Content System 

- Categories & Subcategories 
- Topics with structured steps 
- Code snippets, screenshots, URLs 
- Automatic taxonomy generation from content 

### 🔄 Synchronisation 

- Firebase → content updates 
- Git → icons & screenshots 
- Local cache → offline usage 

✅ Works offline after first sync 
✅ Sync across multiple devices 
✅ No backend setup required for standard users 
 

### 🧑‍💻 Editing & Content Management 

- Create, edit, and delete topics 
- Step-by-step editor with ordering 
- Auto-generated Topic IDs 
- Icon preview and management 
- Promote / demote content (local ↔ official) 
 

### 🧩 Dynamic Taxonomy 

- Categories and subcategories stored as JSON 
- Automatically generated from topic data 
- Editable via UI dialogs 
- Icons linked to categories (Cat_Icon) 

 ### 🎨 UI & UX 

- Responsive layout (desktop + laptop) 
- Unified icon system 
- Clean top/bottom navigation bars 
- Admin-aware UI (features enabled/disabled dynamically) 
 
---
## 🔐 Admin vs User Mode 

The app operates in two modes: 
 
### 👤 User Mode (Default) 

✅ Can: 

- Browse content 
- Search topics 
- Work offline 
- View documentation
- Manage categories/subcategories (only offline content)

❌ Cannot: 

- Edit topics 
- Delete entries 
- Sync or push changes 


### 🛠 Admin Mode 

✅ Can: 

- Create / edit / delete topics 
- Manage categories & subcategories 
- Promote local topics → official (Firebase) 
- Demote official topics → local 
- Run sync (Firebase + Git) 
 

### 🔄 Switching Mode 

Toggle in the Application Menu 

- UI updates dynamically: 
- Buttons enabled/disabled 
- Icons change visibility 
 
---

## ⚙️ Requirements 

### ✅ Supported Systems 

Arch Linux (tested) 
Ubuntu / Debian (tested) 

 
### ⚠️ Python Version 

✅ Python 3.12 
✅ minimum Python 3.9

❌ Python 3.14 (Kivy incompatibility) 
 
---

## 📦 Installation 

### ✅ Option 1 — Quick Install (Recommended) 

```
1     git clone https://github.com/reni001/my_linux_howto_app.git 
2     cd my_linux_howto_app 
3      
4     ./install.sh 
5     ./run.sh 
```
 
### ✅ Option 2 — Manual Install 

#### 1️⃣ Install dependencies 

Arch Linux 
```
1     sudo pacman -Syu 
2     sudo pacman -S python python-pip git 
```

If Python 3.14: 

```
1     sudo pacman -S pyenv 
2     pyenv install 3.12 
3     pyenv local 3.12 
```
 

Ubuntu / Debian 

```
1     sudo apt update 
2     sudo apt install python3.12 python3.12-venv python3-pip git 
```

 
#### 2️⃣ System libraries (Kivy) 
```
1     sudo pacman -S --needed base-devel libx11 libxkbcommon-x11 mesa-utils mtdev 
```

 
#### 3️⃣ Clone repository 

```
1     git clone https://github.com/reni001/my_linux_howto_app.git 
2     cd my_linux_howto_app 
```
 

#### 4️⃣ Create virtual environment 

```
1     python3.12 -m venv venv 
2     source venv/bin/activate 
```
 

#### 5️⃣ Install Python dependencies 
```
1     pip install --upgrade pip setuptools wheel 
2     pip install kivy pandas requests firebase-admin openpyxl 
```

 

#### 6️⃣ Run the app 
```
1     python -m src.main 
```

 
#### 📁 Runtime Data Location 
```
1     ~/.local/share/linux-howto/ 
```
 
---

## Structure 

```
1     data/ 
2     ├── cache.json 
3     ├── firebase.json 
4     ├── categories.json 
5     ├── subcategories.json 
6      
7     assets/ 
8     ├── icons/ 
9     ├── screenshots/ 
```
 

### 🧠 Data Flow 

| Source | Purpose |
| :---: | :---: |
| Firebase | official content  |
| Local cache |offline storage | 
| categories.json | category registry |
| subcategories.json | subcategory registry 
| assets/ | images and icons|


### 🔄 Synchronisation Flow 

At startup: 

1. Fetch data from Firebase 
2. Merge with local cache 
3. Build internal data structures 
4. Generate categories & subcategories 
5. Load UI 

---
 
## 📂 Project Structure 

```
1     src/ 
2     ├── main.py                  # app entrypoint 
3     ├── services/               # business logic layer 
4     │   ├── category_service.py 
5     │   ├── subcategory_service.py 
6     │   ├── data_service.py 
7     │   ├── sync.py 
8     │ 
9     ├── ui/ 
10    │   ├── dialogs/ 
11    │   ├── theme.py 
12    │ 
13    ├── screens/ 
14    │   ├── menu_screen.py 
15    │   ├── detail_screen.py 
16    │   ├── article_screen.py 
17    │   ├── add_topic_screen.py 
18  
19    assets/ 
20    data/ 
21    config/ 
```

--- 

## 🔧 Architecture Overview 
```
1     UI (Kivy) 
2        ↓ 
3     App Controller (main.py) 
4        ↓ 
5     Services Layer 
6        ↓ 
7     Data Layer (Firebase / JSON / Cache) 
```
 
---

## 📡 Sync Model 

| Component | Source |
| :---: | :---: |
| Topics | Firebase |
| Categories | generated from topics|
| Subcategories | generated from topics| 
| Icons | Git |
| Cache | local system | 

---

## ⚠️ Troubleshooting 

### App doesn’t start 
```
1     python -m src.main 
```
 
### Firebase issues 

Check: 
```
1     ~/.local/share/linux-howto/data/firebase.json 
```
 
### Missing icons 
```
1     git pull 
```
 
### Kivy issues (Wayland) 
```
1     KIVY_WINDOW=sdl2 python src/main.py 
```
 
### Clipboard issues 
```
1     sudo pacman -S xclip 
```
--- 

## 🧪 Developer Notes 

You maintain: 

- Firebase data 
- Categories & subcategories 
- Icons & screenshots 
- UI components 

 
---

## 💡 Extensibility 

You can: 

- Replace Firebase backend 
- Extend topic schema 
- Modify UI (Kivy KV files) 
- Add new sync logic 
 
---

## ✅ Summary 

The app is now a: 

✅ Linux documentation browser 
✅ Offline-capable knowledge base 
✅ Lightweight content management system 
✅ Multi-device synchronised environment 
 
---

## 🚀 Current Version 

v1.9.0 — Category System Integration 
