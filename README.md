# UIA-Lens

UIA-Lens is a web application for interactive image layer editing and visualization built with Flask.  
It allows users to load, manipulate and save image layers in a streamlined interface.

---

## 🚀 Features
- Web-based interface for layer-based image editing  
- Modular backend built using Flask in the `app/` directory  
- Uses OpenCV and NumPy for image processing tasks  
- Static frontend assets (CSS, JS) under `app/static/` and HTML templates under `app/templates/`  
- Supports loading layer stacks, generating PNGs for layers, and saving edited images  

---

## 🧰 Requirements
Make sure you have:
- Python 3.8 or higher  
- pip (Python package installer)  
- (Recommended) a virtual environment tool such as `venv`  

---

## ⚙️ Installation
Clone the repository:
bash
git clone https://github.com/aleksanew/UIA-Lens.git
cd UIA-Lens

Running the application
For windows:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask run

For IOS:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run

Then open browser and go to:
http://127.0.0.1:5000

## App Navigation
To use the different tools, click the buttons on the left hand side.
Layer controls are on the right hand side.
Earlier projects are easily accessible on the right hand side.
To cycle through shapes, click the button multiple times.
To write text, click the text button and then click on the canvas.
  Text and Shape settings are on the right hand side.
  Shape outline width is the same as the draw/stroke width


