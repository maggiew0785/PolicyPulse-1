import os
from flask import Flask, render_template

template_dir = os.path.abspath('../frontend/build')
static_dir = os.path.abspath('../frontend/static')

print(f"Template directory: {template_dir}")
print(f"Static directory: {static_dir}")

app = Flask(
    __name__, 
    static_folder=static_dir, 
    template_folder=template_dir)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
