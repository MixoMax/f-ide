# Text-Based Text Editor

import keyboard
from pynput import keyboard as pn_keyboard
import threading
import time
import os
import datetime
import json


global keys_pressed
keys_pressed = []

t_program_start = time.time()
YYYY_MM_DD_HH_MM_SS = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

def log(message: str, do_log: bool = True):
    if not do_log:
        return
    
    fp = f"./logs/log_{YYYY_MM_DD_HH_MM_SS}.txt"
    if not os.path.exists(fp):
        with open(fp, "w", encoding="utf-8") as file:
            file.write(f"Log file created at {YYYY_MM_DD_HH_MM_SS}\n")
    
    with open(fp, "a", encoding="utf-8") as file:
        file.write(f"{time.time() - t_program_start:.2f}: {message}\n")

def on_press(key):
    global keys_pressed
    key = str(key).replace("'", "").replace("\\", "key.").lower()
    if key not in keys_pressed:
        keys_pressed.append(key)
        log(f"Key pressed: {key}")


def on_release(key):
    global keys_pressed
    key = str(key).replace("'", "").replace("\\", "key.").lower()
    if key in keys_pressed:
        keys_pressed.remove(key)
    log(f"Key released: {key}")
    

class TextEditor:
    config: dict = {}

    curser_x: int = 0
    curser_y: int = 0
    cursor_char: str = "\033[91m|\033[0m"

    max_lines: int = 5
    max_chars: int = 80

    line_upper: int = 0
    line_lower: int = -1

    row_left: int = 0
    row_right: int = -1

    selection_start: tuple = (-1, -1)
    selection_end: tuple = (-1, -1)
    selection_active: bool = False
    selection_color: str = "\033[92m"
    copy_buffer: str = ""

    word_splits: list = [" ", "\n", "\t", "-", "_", ".", ",", ";", ":", "!", "?", "(", ")", "[", "]"]

    clear_cmd: str = "cls" if os.name == "nt" else "clear"

    file_path: str = ""
    file_content: list = []
    file_name: str = ""

    def __init__(self, config: dict):
        self.config = config

        self.cursor_char = self.config.get("cursor_char", "\033[91m|\033[0m")
        self.max_lines = self.config.get("max_lines", 5)
        self.max_chars = self.config.get("max_chars", 80)
        self.clear_cmd = "cls" if os.name == "nt" else "clear"
        self.selection_color = self.config.get("selection_color", "\033[92m")

        self.file_path = input("Enter file path: ")
        self.file_name = self.file_path.split("/")[-1]
        self.load_file()
        self.start_editor()
    
    def load_new_file(self):
        self.file_path = input("Enter file path: ")
        self.file_name = self.file_path.split("/")[-1]
        self.load_file()
    
    def load_file(self):
        log(f"Loading file: {self.file_name}")
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                self.file_content = file.readlines()
        else:
            self.file_content = [""]
        
        if len(self.file_content) > self.max_lines:
            self.line_lower = self.max_lines
        else:
            self.line_lower = len(self.file_content)
    
    def save_file(self):
        log(f"Saving file: {self.file_name}")
        with open(self.file_path, "w") as file:
            for line in self.file_content:
                line = line.replace("\n", "")
                file.write(line + "\n")
    
    def dump(self):
        fp = f"./logs/dump_{YYYY_MM_DD_HH_MM_SS}.json"
        log(f"Dumping data to {fp}")
        with open(fp, "w", encoding="utf-8") as file:
            json.dump(self.__dict__, file, indent=4)
    
    def move_curser(self, x: int, y: int):
        shift = "key.shift" in keys_pressed
        # if shift is pressed, we need to start a selection
        if shift and not self.selection_active:
            # start selection before moving curser
            self.selection_start = (self.curser_x, self.curser_y)
            self.selection_active = True
        elif not shift and self.selection_active:
            # reset selection if shift is not pressed
            self.selection_active = False
            self.selection_start = (-1, -1)
            self.selection_end = (-1, -1)

        self.curser_x += x
        if self.curser_x < self.row_left:
            if self.curser_x < 0:
                self.curser_x = 0
            self.row_left = self.curser_x
            self.row_right = self.curser_x + self.max_chars
        elif self.curser_x >= self.max_chars:
            self.curser_x = self.max_chars - 1
            self.row_left = self.curser_x - self.max_chars
            if self.row_left < 0:
                self.row_left = 0
            self.row_right = self.curser_x
        
        self.curser_y += y
        
        if self.curser_y < 0:
            self.curser_y = 0
        elif self.curser_y >= len(self.file_content):
            self.curser_y = len(self.file_content) - 1
        
        if self.curser_y < self.line_upper:
            self.line_upper = self.curser_y
            self.line_lower = self.line_upper + self.max_lines
        elif self.curser_y >= self.line_lower:
            self.line_lower = self.curser_y + 1
            self.line_upper = self.line_lower - self.max_lines
        
        if self.curser_x >= len(self.file_content[self.curser_y]):
            self.curser_x = len(self.file_content[self.curser_y])
        
        if self.selection_active:
            self.selection_end = (self.curser_x, self.curser_y)

    def handle_keypress(self, key: str):
        key = key.replace("key.", "").lower()
        ctrl = "key.ctrl_l" in keys_pressed or "key.ctrl_r" in keys_pressed
        shift = "key.shift" in keys_pressed

        if not ctrl:
            match key:
                case "up": self.move_curser(0, -1)
                case "down": self.move_curser(0, 1)
                case "left": self.move_curser(-1, 0)
                case "right": self.move_curser(1, 0)
                case "end": self.move_curser(len(self.file_content[self.curser_y]) - self.curser_x, 0)
                case "home": self.move_curser(-self.curser_x, 0)
                case "enter":
                    if self.curser_x == len(self.file_content[self.curser_y]):
                        # create new line if curser is at the end of the line
                        self.file_content.insert(self.curser_y + 1, " ")
                        if self.curser_y >= self.line_lower:
                            self.line_lower += 1
                        self.move_curser(-self.curser_x, 1)
                    else:
                        # split line at curser position
                        line = self.file_content[self.curser_y]
                        self.file_content[self.curser_y] = line[:self.curser_x]
                        self.file_content.insert(self.curser_y + 1, line[self.curser_x:])
                        if self.curser_y >= self.line_lower:
                            self.line_lower += 1
                        self.move_curser(0, 1)
                case "backspace":
                    if self.selection_active:
                        self.delete_selection()
                        return
                    if self.curser_x != 0:
                        # remove character before curser
                        line = self.file_content[self.curser_y]
                        self.file_content[self.curser_y] = line[:self.curser_x - 1] + line[self.curser_x:]
                        self.move_curser(-1, 0)

                    elif self.curser_y != 0:
                        # remove current line and append to previous line
                        line = self.file_content[self.curser_y]
                        self.file_content.pop(self.curser_y)
                        self.curser_y -= 1
                        self.curser_x = len(self.file_content[self.curser_y])
                        self.file_content[self.curser_y] += line
                case "delete":
                    if self.selection_active:
                        self.delete_selection()
                        return
                    # pretty much the same as backspace but reverse
                    if self.curser_x != len(self.file_content[self.curser_y]):
                        line = self.file_content[self.curser_y]
                        self.file_content[self.curser_y] = line[:self.curser_x] + line[self.curser_x + 1:]
                    elif self.curser_y != len(self.file_content) - 1:
                        line = self.file_content[self.curser_y]
                        self.file_content[self.curser_y] += self.file_content.pop(self.curser_y + 1)
                case _ : self.handle_char_input(key)
        else:
            match key:
                case "x19": # x19 = y
                    log("Ctrl + Y")
                    self.dump()
                case "x13": # x13 = s
                    log("Ctrl + S")
                    self.save_file()
                case "n":
                    self.load_new_file()
                case "left":
                    # move curser to the left of the word
                    line = self.file_content[self.curser_y]
                    word = ""
                    for i in range(self.curser_x - 1, -1, -1):
                        if line[i] in self.word_splits and i != self.curser_x - 1:
                            break
                        word += line[i]
                    self.move_curser(-len(word), 0)
                case "right":
                    # move curser to the right of the word
                    line = self.file_content[self.curser_y]
                    word = ""
                    for i in range(self.curser_x, len(line)):
                        if line[i] in self.word_splits and i != self.curser_x:
                            break
                        word += line[i]
                    self.move_curser(len(word), 0)
                
                #TODO: FIX
                # |
                # V
                case "c":
                    log("Copy")
                    if self.selection_active:
                        self.copy_buffer = ""
                        for y in range(self.selection_start[1], self.selection_end[1] + 1):
                            line = self.file_content[y]
                            if y == self.selection_start[1]:
                                self.copy_buffer += line[self.selection_start[0]:]
                            elif y == self.selection_end[1]:
                                self.copy_buffer += line[:self.selection_end[0]]
                            else:
                                self.copy_buffer += line
                        self.selection_active = False
                case "v":
                    log(f"Pasting")
                    if self.copy_buffer:
                        self.handle_char_input(self.copy_buffer)
                case "x":
                    log(f"Cutting")
                    if self.selection_active:
                        self.copy_buffer = ""
                        for y in range(self.selection_start[1], self.selection_end[1] + 1):
                            line = self.file_content[y]
                            if y == self.selection_start[1]:
                                self.copy_buffer += line[self.selection_start[0]:]
                            elif y == self.selection_end[1]:
                                self.copy_buffer += line[:self.selection_end[0]]
                            else:
                                self.copy_buffer += line
                        self.delete_selection()
                case _ : pass

                    


            


    def handle_char_input(self, char: str):
        dont_print_keys = ["shift", "ctrl", "alt"]
        if char in dont_print_keys:
            return
        shift = "key.shift" in keys_pressed

        replacements = (
            ("space", " "),
            ("tab", "\t")
        )
        for old, new in replacements:
            char = char.replace(old, new)

        line = self.file_content[self.curser_y]
        
        # char might be 1 char, or multiple lines, so we need to split it
        char_lines = char.split("\n")
        if len(char) == 1:
            if shift:
                char = char.upper()
            else:
                char = char.lower()
            
            # single char input
            self.file_content[self.curser_y] = "".join([line[:self.curser_x], char, line[self.curser_x:]])
            self.move_curser(1, 0)
        elif len(char_lines) == 1:
            # multiple char input but in the same line
            self.file_content[self.curser_y] = "".join([line[:self.curser_x], char, line[self.curser_x:]])
            self.move_curser(len(char), 0)
        else:
            # multiple char input in multiple lines
            self.file_content[self.curser_y] = "".join([line[:self.curser_x], char_lines[0]])
            self.move_curser(len(char_lines[0]), 0)
            for i in range(1, len(char_lines) - 1):
                self.file_content.insert(self.curser_y + i, char_lines[i])
                self.move_curser(0, 1)
            self.file_content.insert(self.curser_y + len(char_lines) - 1, char_lines[-1])
            self.move_curser(len(char_lines[-1]), 0)

    def delete_selection(self):
        # delete selected text
        start = self.selection_start
        end = self.selection_end

        if start[1] == end[1]:
            # same line
            line = self.file_content[start[1]]
            line = line[:start[0]] + line[end[0]:]
            self.file_content[start[1]] = line
        else:
            # multiple lines
            line = self.file_content[start[1]]
            line = line[:start[0]] + self.file_content[end[1]][end[0]:]
            self.file_content[start[1]] = line

            for y in range(start[1] + 1, end[1] + 1):
                self.file_content.pop(start[1] + 1)
                        

    def print_editor(self):
        os.system(self.clear_cmd)
        
        for y_line in range(self.line_upper, self.line_lower):
            try:
                content = self.file_content[y_line]
            except IndexError:
                content = ""

            if y_line == self.curser_y:
                content = "".join([content[:self.curser_x], self.cursor_char, content[self.curser_x:]])
            if self.selection_active and self.selection_start[1] <= y_line <= self.selection_end[1]:
                if y_line == self.selection_start[1]:
                    content = "".join([content[:self.selection_start[0]], self.selection_color, content[self.selection_start[0]:]])
                elif y_line == self.selection_end[1]:
                    content = "".join([content[:self.selection_end[0]], self.selection_color, content[self.selection_end[0]:]])
                else:
                    content = self.selection_color + content
            
            #content: abcdefghijklmnopqrstuvwxyz
            #  self.row_left:|-----| self.row_right
            print(content[self.row_left:self.row_right])

    

    def start_editor(self):
        global keys_pressed
        t_last_print = time.time()
        timeout_print = 0.05
        timeout_key = 0.1

        listener = pn_keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        
        while True:
            
            for key in keys_pressed:
                self.handle_keypress(key)
                time.sleep(timeout_key)
            

            
            if time.time() - t_last_print > timeout_print:
                try:
                    self.print_editor()
                    t_last_print = time.time()
                    print(keys_pressed)
                except Exception as e:
                    log(f"Error: {e}")
                    self.dump()
            



if __name__ == "__main__":
    config = {
        "cursor_char": "\033[91m|\033[0m",
        "selection_color": "\033[92m",
        "max_lines": 5,
        "max_chars": 80,
        
        "do_log": True,
        "log_path": "./logs",
        "log_name": f"log_{YYYY_MM_DD_HH_MM_SS}.txt"

    }
    editor = TextEditor(config)