import tkinter as tk
import os
import sys
from functools import partial
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import subprocess

Image.MAX_IMAGE_PIXELS = None

TILE_SIZE = 256

try:
    from PIL import Image
except ImportError:
    print("Installing the Pillow library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyDraw")
        self.brush_size = 5
        self.canvas_frame = tk.Frame(self.root)
        self.setup_ui()
        self.color = "black"
        self.tile_dict = {}
        self.last_x = None
        self.last_y = None
        self.image = Image.new("RGB", (1280, 720), "white")
        self.original_image = None
        self.zoom_factor = 1
        self.undo_stack = []
        self.line_objects = []
        self.edited = False
        self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height))
        self.canvas_frame.config(width=800, height=600)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)
        self.zoom_options = [0.1, 0.5, 1, 2, 3]
        self.zoom_index = 2  # Start at 1x zoom
        self.bind_keys()

    def setup_ui(self):
     menubar = tk.Menu(self.root)
     self.root.config(menu=menubar)

     file_menu = tk.Menu(menubar, tearoff=0)
     menubar.add_cascade(label="File", menu=file_menu)
     file_menu.add_command(label="Open", command=self.open_image)
     file_menu.add_command(label="Save", command=self.save_image)

     view_menu = tk.Menu(menubar, tearoff=0)
     menubar.add_cascade(label="View", menu=view_menu)
     zoom_menu = tk.Menu(view_menu, tearoff=0)
     view_menu.add_cascade(label="Zoom", menu=zoom_menu)
     zoom_menu.add_command(label="0.1x", command=partial(self.set_zoom, 0.1))
     zoom_menu.add_command(label="0.5x", command=partial(self.set_zoom, 0.5))
     zoom_menu.add_command(label="1x", command=partial(self.set_zoom, 1))
     zoom_menu.add_command(label="2x", command=partial(self.set_zoom, 2))
     zoom_menu.add_command(label="3x", command=partial(self.set_zoom, 3))
     draw_menu = tk.Menu(menubar, tearoff=0)
     menubar.add_cascade(label="Draw", menu=draw_menu)
     draw_menu.add_command(label="Clear Canvas", command=self.clear_canvas)
     brush_size_menu = tk.Menu(draw_menu, tearoff=0)
     draw_menu.add_cascade(label="Brush Size", menu=brush_size_menu)
     brush_size_menu.add_command(label="+", command=self.increase_brush_size)
     brush_size_menu.add_command(label="-", command=self.decrease_brush_size)

     self.color_frame = tk.Frame(self.root)
     self.color_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

     colors = ["red", "orange", "yellow", "green", "blue", "purple", "black", "white"]

     for idx, color in enumerate(colors):
        button = CircleButton(self.color_frame, color, radius=10, command=lambda c=color: self.set_color(c))
        button.grid(row=0, column=idx, padx=(2, 2), pady=2)

     self.canvas_container = tk.Frame(self.canvas_frame, width=800, height=600, bg='white')
     self.canvas_container.pack(fill=tk.BOTH, expand=True)

     self.canvas_container.columnconfigure(0, weight=1)  # Add this line
     self.canvas_container.rowconfigure(0, weight=1)  # Add this line

     self.canvas = tk.Canvas(self.canvas_container, bg='white', width=800, height=600)
     self.x_scrollbar = tk.Scrollbar(self.canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
     self.y_scrollbar = tk.Scrollbar(self.canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)

     self.canvas.config(xscrollcommand=self.x_scrollbar.set, yscrollcommand=self.y_scrollbar.set)

     self.canvas.grid(row=0, column=0, sticky='nsew')
     self.x_scrollbar.grid(row=1, column=0, sticky='ew')
     self.y_scrollbar.grid(row=0, column=1, sticky='ns')

    def canvas_to_image(self, x, y):
     return int(self.canvas.canvasx(x) / self.zoom_factor), int(self.canvas.canvasy(y) / self.zoom_factor)

    def image_to_canvas(self, x, y):
     return x * self.zoom_factor - int(self.canvas.canvasx(0)), y * self.zoom_factor - int(self.canvas.canvasy(0))

    def set_color(self, color):
        self.color = color

    def draw(self, event):
     x, y = self.canvas_to_image(event.x, event.y)
     if self.last_x is not None and self.last_y is not None:
        canvas_last_x, canvas_last_y = self.image_to_canvas(self.last_x, self.last_y)
        line_object = self.canvas.create_line(self.canvas.canvasx(canvas_last_x), self.canvas.canvasy(canvas_last_y),
                                              self.canvas.canvasx(event.x), self.canvas.canvasy(event.y), fill=self.color,
                                              width=self.brush_size * self.zoom_factor, capstyle=tk.ROUND, smooth=True)
        self.line_objects.append(line_object)

        tile_coords = self.get_line_tiles(self.last_x, self.last_y, x, y)
        for coord in tile_coords:
            if coord not in self.tile_dict:
                self.tile_dict[coord] = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))
            tile_image = self.tile_dict[coord]
            tile_draw = ImageDraw.Draw(tile_image)

            adjusted_line = (self.last_x - coord[0] * TILE_SIZE, self.last_y - coord[1] * TILE_SIZE,
                             x - coord[0] * TILE_SIZE, y - coord[1] * TILE_SIZE)
            tile_draw.line(adjusted_line, fill=self.color, width=self.brush_size, joint='curve')

     self.last_x = x
     self.last_y = y
     self.edited = True

    def bind_keys(self):
        self.root.bind_all("<Shift-+>", self.increase_zoom)
        self.root.bind_all("<Shift-_>", self.decrease_zoom)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.reset_last_points)
        self.root.bind_all('<Control-z>', self.undo)

    def increase_zoom(self, event):
        if self.zoom_index < len(self.zoom_options) - 1:
            self.zoom_index += 1
            self.set_zoom(self.zoom_options[self.zoom_index])

    def decrease_zoom(self, event):
        if self.zoom_index > 0:
            self.zoom_index -= 1
            self.set_zoom(self.zoom_options[self.zoom_index])

    def undo(self, event=None):
     if self.undo_stack:
        last_action = self.undo_stack.pop()
        line_objects, color, brush_size = last_action
        for line_object in line_objects:
            self.canvas.delete(line_object)
        self.edited = True
     else:
        self.edited = False

    def redraw_canvas(self):
     for x1, y1, x2, y2, color, brush_size in self.undo_stack:
        canvas_x1, canvas_y1 = self.image_to_canvas(x1, y1)
        canvas_x2, canvas_y2 = self.image_to_canvas(x2, y2)
        self.canvas.create_line(self.canvas.canvasx(canvas_x1), self.canvas.canvasy(canvas_y1),
                                self.canvas.canvasx(canvas_x2), self.canvas.canvasy(canvas_y2), fill=color,
                                width=brush_size * self.zoom_factor, capstyle=tk.ROUND, smooth=True)    

    def set_zoom(self, zoom_factor):
     self.zoom_factor = zoom_factor
     self.canvas.delete("all")

     zoomed_width = int(self.image.width * zoom_factor)
     zoomed_height = int(self.image.height * zoom_factor)

     zoomed_image = Image.new("RGB", (zoomed_width, zoomed_height), "white")

     if self.original_image:
        resized_original = self.original_image.resize((int(self.original_image.width * zoom_factor), int(self.original_image.height * zoom_factor)), Image.LANCZOS)
        if resized_original.mode in ('RGBA', 'LA'):
            mask = resized_original.split()[-1]
            zoomed_image.paste(resized_original, (0, 0), mask)
        else:
            zoomed_image.paste(resized_original, (0, 0))

     for coord, tile in self.tile_dict.items():
        x_offset, y_offset = int(coord[0] * TILE_SIZE * self.zoom_factor), int(coord[1] * TILE_SIZE * self.zoom_factor)
        resized_tile = tile.resize((int(tile.width * zoom_factor), int(tile.height * zoom_factor)), Image.LANCZOS)
        zoomed_image.paste(resized_tile, (x_offset, y_offset), resized_tile.split()[-1])

     self.tk_image = ImageTk.PhotoImage(zoomed_image)
     self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
     self.canvas.config(scrollregion=(0, 0, zoomed_width, zoomed_height))

    def reset_last_points(self, event):
     if self.line_objects:
        self.undo_stack.append((self.line_objects, self.color, self.brush_size))
        self.line_objects = []
     self.last_x = None
     self.last_y = None

    def get_line_tiles(self, x1, y1, x2, y2):
        coords = set()

        min_x, max_x = sorted([x1 // TILE_SIZE, x2 // TILE_SIZE])
        min_y, max_y = sorted([y1 // TILE_SIZE, y2 // TILE_SIZE])

        for i in range(min_x, max_x + 1):
            for j in range(min_y, max_y + 1):
                coords.add((i, j))

        return coords

    def clear_canvas(self):
     self.canvas.delete("all")
     self.image = Image.new("RGB", (1280, 720), "white")
     self.canvas.config(width=800, height=600)  # Change the width and height back to 800x600
     self.canvas.config(scrollregion=(0, 0, 1280, 720))
     self.tile_dict = {}
     self.canvas_frame.config(width=800, height=600)  # Add this line to resize the window

    def increase_brush_size(self):
        if self.brush_size < 15:
            self.brush_size += 1

    def decrease_brush_size(self):
        if self.brush_size > 1:
            self.brush_size -= 1

    def save_image(self):
     file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("BMP", "*.bmp"), ("GIF", "*.gif")])
     if file_path:
        if self.edited:
            output_image = self.image.copy()

            for coord, tile in self.tile_dict.items():
                x_offset, y_offset = coord[0] * TILE_SIZE, coord[1] * TILE_SIZE
                output_image.paste(tile, (x_offset, y_offset), tile.split()[-1])

            # Calculate the bounding box
            min_x = min((coord[0] * TILE_SIZE) for coord in self.tile_dict.keys())
            min_y = min((coord[1] * TILE_SIZE) for coord in self.tile_dict.keys())
            max_x = max(((coord[0] + 1) * TILE_SIZE) for coord in self.tile_dict.keys())
            max_y = max(((coord[1] + 1) * TILE_SIZE) for coord in self.tile_dict.keys())

            # Make sure the bounding box includes the original image
            min_x = min(min_x, 0)
            min_y = min(min_y, 0)
            max_x = max(max_x, self.original_image.width)
            max_y = max(max_y, self.original_image.height)

            # Add padding around the bounding box
            padding = 10
            min_x = max(min_x - padding, 0)
            min_y = max(min_y - padding, 0)
            max_x = min(max_x + padding, output_image.width)
            max_y = min(max_y + padding, output_image.height)

            # Crop the image
            output_image = output_image.crop((min_x, min_y, max_x, max_y))

        else:
            output_image = self.original_image

        # Save the image
        output_image.save(file_path)

    def open_image(self):
     file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
     if file_path:
        self.clear_canvas()

        self.original_image = Image.open(file_path).convert("RGB")
        self.image = Image.new("RGB", (max(1280, self.original_image.width), max(720, self.original_image.height)), "white")
        self.image.paste(self.original_image, (0, 0))

        # Check if the image dimensions are greater than 3000 and set the zoom factor to 0.1x if needed
        if self.original_image.width > 3000 or self.original_image.height > 3000:
            self.set_zoom(0.1)
        else:
            self.set_zoom(1)

        self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height))

class CircleButton(tk.Canvas):
    def __init__(self, parent, color, radius=10, command=None, *args, **kwargs):
        tk.Canvas.__init__(self, parent, width=radius * 2 - 4, height=radius * 2 - 4, *args, **kwargs)  # Reduce the canvas size
        self.configure(borderwidth=0, highlightthickness=0)
        self.color = color
        self.radius = radius
        self.command = command

        outline_color = "darkgray" if color == "white" else color  # Add outline for the white button
        self.create_oval(0, 0, radius * 2 - 4, radius * 2 - 4, fill=color, outline=outline_color)  # Adjust the oval size
        self.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        if self.command:
            self.command()

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = DrawingApp(root)
    root.iconbitmap(resource_path('favicon.ico'))
    root.mainloop()

