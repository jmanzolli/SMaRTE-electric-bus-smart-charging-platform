from pathlib import Path
import tkinter as tk
from tkinter import Tk, Canvas, Entry, Button, PhotoImage, filedialog, Text
from optimization import *
import threading

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / \
    Path(r"/Users/natomanzolli/Documents/GitHub/Electric Bus Smart Charging/GUI/assets/frame0")
def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Global variables to store results and models
results = None
model_global = None
path_global = None

### Functions ###
def clean():
    global results, model_global, path_global
    results = None
    model_global = None
    path_global = None
    entry_2.delete(1.0, tk.END)
    message = 'Reseted.\n'
    update_text_widget(message)

def browse_file():
    global results, model_global, path_global
    path = filedialog.askopenfilename()
    if path:
        entry_1.delete(0, tk.END)  # Clear the entry
        entry_1.insert(tk.END, path)
    path_global = path

def update_text_widget(message):
    entry_2.config(state=tk.NORMAL)
    entry_2.insert(tk.END, message)
    entry_2.see(tk.END)  # Scroll to the end
    entry_2.config(state=tk.DISABLED)  # Disable editing

def save():
    global results, model_global
    if path_global is not None:
        save_results(model_global)
        message = 'Results saved in output_data.xlsx.\n'
        update_text_widget(message)
    else:
        entry_2.config(state=tk.NORMAL)
        entry_2.delete(1.0, tk.END)
        entry_2.insert(tk.END, 'Solve model first!\n')

def calculation():
    global path_global
    entry_2.delete(1.0, tk.END)  # Clear the entry
    if path_global is not None:
        data = read_file(path_global)
        entry_2.insert(tk.END, 'Calculating... Please wait.\n')
        entry_2.config(state=tk.NORMAL)
        entry_2.update_idletasks()  # Force GUI update to display the message

        def solve_and_update():
            global results, model_global
            model = solveModel(data)
            model_global = model
            results = (model)
            entry_2.delete(1.0, tk.END)
            message = f"Calculation complete.\nOperational Costs: {model.obj()}\n"
            update_text_widget(message)
            message = 'Click "Plot" to visualize results.\n'
            update_text_widget(message)
            button_3.config(state=tk.NORMAL)

        # Start the Solve function in a separate thread
        calculation_thread = threading.Thread(target=solve_and_update)
        calculation_thread.start()
    else:
        entry_2.config(state=tk.NORMAL)
        entry_2.delete(1.0, tk.END)
        entry_2.insert(tk.END, 'Browse file first!\n')

def show_graphics():
    global results,model_global
    if results is not None:
        plot(model_global)
    else:
        entry_2.config(state=tk.NORMAL)
        entry_2.delete(1.0, tk.END)
        entry_2.insert(tk.END, 'The results have not yet been calculated.\n')


### GUI ###
window = Tk()
window.geometry("911x816")
window.configure(bg = "#FFFFFF")
window.title('DRIVE-TECH - Moving Sustainability Further')

canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 816,
    width = 911,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
canvas.create_rectangle(
    0.0,
    191.0,
    911.0,
    816.0,
    fill="#3C3D41",
    outline="")

entry_image_1 = PhotoImage(
    file=relative_to_assets("entry_1.png"))
entry_bg_1 = canvas.create_image(
    396.5,
    230.0,
    image=entry_image_1
)
entry_1 = Entry(
    bd=0,
    bg="#D9D9D9",
    fg="#000716",
    highlightthickness=0
)
entry_1.place(
    x=59.0,
    y=211.0,
    width=675.0,
    height=36.0
)

entry_image_2 = PhotoImage(
    file=relative_to_assets("entry_2.png"))
entry_bg_2 = canvas.create_image(
    453.5,
    586.5,
    image=entry_image_2
)
entry_2 = Text(
    bd=0,
    bg="#D9D9D9",
    fg="#000716",
    highlightthickness=0,
    font=('Arial',22)
)
entry_2.place(
    x=56.0,
    y=392.0,
    width=795.0,
    height=391.0
)

button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=clean,
    relief="flat"
)
button_1.place(
    x=406.0,
    y=270.0,
    width=99.0,
    height=40.0
)

button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=browse_file,
    relief="flat"
)
button_2.place(
    x=770.0,
    y=209.0,
    width=99.0,
    height=40.0
)

button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=show_graphics,
    relief="flat"
)
button_3.place(
    x=162.0,
    y=270.0,
    width=99.0,
    height=40.0
)

button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png"))
button_4 = Button(
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=save,
    relief="flat"
)
button_4.place(
    x=284.0,
    y=270.0,
    width=99.0,
    height=40.0
)

button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png"))
button_5 = Button(
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=calculation,
    relief="flat"
)
button_5.place(
    x=40.0,
    y=270.0,
    width=99.0,
    height=40.0
)

image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    455.0,
    96.0,
    image=image_image_1
)

image_image_2 = PhotoImage(
    file=relative_to_assets("image_2.png"))
image_2 = canvas.create_image(
    825.0,
    96.0,
    image=image_image_2
)

canvas.create_text(
    284.0,
    26.0,
    anchor="nw",
    text="DRIVE-TECH",
    fill="#FFFFFF",
    font=("Space Grotesk", 100 * -1)
)

canvas.create_text(
    40.0,
    348.0,
    anchor="nw",
    text="Terminal",
    fill="#D9D9D9",
    font=("Space Grotesk", 20 * -1)
)

canvas.create_rectangle(
    31.4981689453125,
    327.0,
    869.0018310546875,
    332.5029296875,
    fill="#D6D6D6",
    outline="")

image_image_3 = PhotoImage(
    file=relative_to_assets("image_3.png"))
image_3 = canvas.create_image(
    138.0,
    102.0,
    image=image_image_3
)
window.resizable(False, False)
window.mainloop()
