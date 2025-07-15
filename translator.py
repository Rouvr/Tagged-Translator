import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox # Import ttk for Combobox
import typing
import re
import deepl

DEEPL_PROHIBIT_TRANSLATION = False

class RuvysTaggedTranslator:
    
    ColourScheme = {
        "background": "#f0f0f0",
        "foreground": "#333333",
        "font": ("Inter", 12),
        "button_bg": "#0275d8",
        "button_fg": "white",
        "button_active_bg": "#025aa5",
        "footer_bg": "#333333",
        
        # Action buttons colors
        "action_green": "#5cb85c",
        "action_active_green": "#4cae4c",
        "action_yellow": "#d39f04",
        "action_active_yellow": "#ec971f",
        "action_red": "#d9534f",
        "action_active_red": "#c9302c",
        "action_blue": "#0275d8",
        "action_active_blue": "#025aa5",

        # Footer info text colors
        "msg_fail": "#d9534f",  
        "msg_pass": "#5cb85c",  
        "msg_unknown": "#ffc107",  
        "msg_default": "#ffffff",  
        "msg_working": "#0275d8", 
    }

    LEFT_HELPTEXT = "Paste text for translation here.\n\nExample:\n<div class='container'>\n  <p>Hello <b>world</b> from Prague!</p>\n  <span class='highlight'>Please translate this text.</span>\n</div>\n\nAnother paragraph here."
    RIGHT_HELPTEXT = "Here you can check if the <> tags in both texts match fully by pressing the 'Check Tags' button.\n\nYou will also see the translated text with original tags preserved.\n\nIf you want to see only the <> tags, use the 'Filter <> tags' button.\n\nTo see only the plaintext, use the 'Filter plaintext' button.\n<Example tag>"

    def __init__(self, master):
        self.DEBUG_MODE = False
        
        # Initialize the translator. It will attempt to read the API key from 'api.key' file
        try:
            self.translator = DeepLTranslator()
        except ValueError as e:
            self.translator = None # Let user to provide API key later

        self.master = master
        master.title("<> Tag Comparator & Translator")

        self.history = []
        self.history_index = -1

        self.master.bind_all("<Control-z>", lambda event: self.text_undo())
        self.master.bind_all("<Control-y>", lambda event: self.text_redo())
        self.master.bind("<Configure>", self._on_window_resize)

        # --- AI assisted UI ---

        # Configure grid weights for responsive layout
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)

        # --- Left Text Box ---
        self.text_box_top = scrolledtext.ScrolledText(
            master,
            wrap=tk.WORD,
            bg=self.ColourScheme["background"],
            fg=self.ColourScheme["foreground"],
            font=self.ColourScheme["font"],
            relief=tk.FLAT,
            bd=2,
            padx=10,
            pady=10
        )
        self.text_box_top.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.text_box_top.insert(tk.END, self.LEFT_HELPTEXT)

        # --- Right Text Box ---
        self.text_box_bottom = scrolledtext.ScrolledText(
            master,
            wrap=tk.WORD,
            bg=self.ColourScheme["background"],
            fg=self.ColourScheme["foreground"],
            font=self.ColourScheme["font"],
            relief=tk.FLAT,
            bd=2,
            padx=10,
            pady=10
        )
        self.text_box_bottom.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.text_box_bottom.insert(tk.END, self.RIGHT_HELPTEXT)

        self.history.append([self.LEFT_HELPTEXT, self.RIGHT_HELPTEXT]) # Add initial state to history

        # --- Footer Frame ---
        self.footer_frame = tk.Frame(master, bg=self.ColourScheme["footer_bg"], height=50)
        self.footer_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.footer_frame.grid_propagate(False)

        # Configure columns within the footer frame to distribute space
        # Now 7 columns: Check, Convert, Debug, Translate, Language Selector, Language Status, General Status
        self.footer_frame.grid_columnconfigure(0, weight=1) # Check button
        self.footer_frame.grid_columnconfigure(1, weight=1) # Convert button
        self.footer_frame.grid_columnconfigure(2, weight=1) # Debug button
        self.footer_frame.grid_columnconfigure(3, weight=1) # Translate button
        self.footer_frame.grid_columnconfigure(4, weight=1) # Language selector
        self.footer_frame.grid_columnconfigure(5, weight=1) # New Language Status
        self.footer_frame.grid_columnconfigure(6, weight=1) # Original Status indicator

        # --- Footer Buttons ---
        self.button_check = tk.Button(
            self.footer_frame,
            text="Check Tags",
            command=self.check_texts_equality,
            bg=self.ColourScheme["action_green"],
            fg="white",
            font=("Inter", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            activebackground=self.ColourScheme["action_active_green"],
            padx=10, pady=5,
            cursor="hand2"
        )
        self.button_check.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.button_convert = tk.Button(
            self.footer_frame,
            text="Filter <> tags",
            command=self.convert_texts_tags,
            bg=self.ColourScheme["action_yellow"],
            fg="white",
            font=("Inter", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            activebackground=self.ColourScheme["action_active_yellow"],
            padx=10, pady=5,
            cursor="hand2"
        )
        self.button_convert.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.button_convert = tk.Button(
            self.footer_frame,
            text="Filter plaintext",
            command=self.convert_texts_plaintext,
            bg=self.ColourScheme["action_yellow"],
            fg="white",
            font=("Inter", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            activebackground=self.ColourScheme["action_active_yellow"],
            padx=10, pady=5,
            cursor="hand2"
        )
        self.button_convert.grid(row=0, column=2, padx=5, pady=5, sticky="ew")



        # --- Translate Button (now fully functional, no "dummy" label) ---
        self.button_translate = tk.Button( # Renamed from button_translate_dummy
            self.footer_frame,
            text="Translate",
            command=self.translate_content,
            bg=self.ColourScheme["action_blue"],
            fg="white",
            font=("Inter", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            activebackground=self.ColourScheme["action_active_blue"],
            padx=10, pady=5,
            cursor="hand2",
            state = tk.NORMAL # Now prompt user for API key if translator is not available
        )
        self.button_translate.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # --- Debug Button ---
        if self.DEBUG_MODE:
            self.button_debug = tk.Button(
                self.footer_frame,
                text="Debug Tags",
                command=self.debug_texts,
                bg=self.ColourScheme["action_red"],
                fg="white",
                font=("Inter", 10, "bold"),
                relief=tk.RAISED,
                bd=2,
                activebackground=self.ColourScheme["action_active_red"],
                padx=10, pady=5,
                cursor="hand2"
            )
            self.button_debug.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        # --- Language Selector ---
        self.target_lang_var = tk.StringVar(master)
        # Set initial value to English (US) if translator is available, otherwise default
        if self.translator:
            self.target_lang_var.set(self.translator.current_language())
            available_langs_desc = self.translator.available_languages_desc()
        else:
            self.target_lang_var.set("N/A")
            available_langs_desc = ["N/A - Translator not available"]

        # Create a Combobox for language selection
        self.lang_selector = ttk.Combobox(
            self.footer_frame,
            textvariable=self.target_lang_var,
            values=available_langs_desc,
            state="readonly" if self.translator else "disabled", # Disable if no translator
            font=("Inter", 10)
        )
        # Bind the selection event to update the translator's target language
        self.lang_selector.bind("<<ComboboxSelected>>", self.on_language_selected)
        self.lang_selector.grid(row=0, column=4, padx=5, pady=5, sticky="ew")
        self.lang_selector.config(width=25) # Adjust width to show descriptions better

        # --- Language Status Indicator (New) ---
        self.language_status_label = tk.Label(
            self.footer_frame,
            text="Lang: N/A", # Initial text
            bg=self.ColourScheme["footer_bg"], # Same as footer background
            fg=self.ColourScheme["foreground"], # White text
            font=self.ColourScheme["font"],
            anchor="w" # Align text to the left
        )
        self.language_status_label.grid(row=0, column=5, padx=10, pady=5, sticky="ew")

        # --- General Status Indicator (Original) ---
        self.status_label = tk.Label(
            self.footer_frame,
            text="Ready", # Initial status text
            bg=self.ColourScheme["footer_bg"], # Same as footer background
            fg=self.ColourScheme["foreground"], # White text
            font=self.ColourScheme["font"],
            anchor="e" # Align text to the right
        )
        self.status_label.grid(row=0, column=6, padx=10, pady=5, sticky="ew") # Adjusted column for status
        
        self.button_undo = tk.Button(
            self.footer_frame,
            text="↶",  # Undo icon (curved arrow left)
            command=self.text_undo,
            font=("Segoe UI", 12),
            width=2,
            bg=self.ColourScheme["footer_bg"],
            fg="white",
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.button_undo.grid(row=0, column=7, padx=(2, 0), pady=5, sticky="e")

        self.button_redo = tk.Button(
            self.footer_frame,
            text="↷",  # Redo icon (curved arrow right)
            command=self.text_redo,
            font=("Segoe UI", 12),
            width=2,
            bg=self.ColourScheme["footer_bg"],
            fg="white",
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.button_redo.grid(row=0, column=8, padx=(0, 10), pady=5, sticky="e")

        for i in range(6):
            self.footer_frame.grid_columnconfigure(i, weight=0)  # Fixed width buttons
        self.footer_frame.grid_columnconfigure(6, weight=1)  # Expanding status label
        self.footer_frame.grid_columnconfigure(7, weight=0)  # Undo button
        self.footer_frame.grid_columnconfigure(8, weight=0)  # Redo button

        # Adjust undo and redo button widths (already small), but can enforce via .grid()
        self.button_undo.grid(row=0, column=7, padx=(2, 0), pady=5)
        self.button_redo.grid(row=0, column=8, padx=(0, 10), pady=5)

        # Initial update for the language status
        self.update_language_status()

    def _on_window_resize(self, event):
        min_width = 800
        
        if event.widget != self.master:
            return
        
        width = event.width
        if width < min_width:
            for i in range(6):
                self.footer_frame.grid_columnconfigure(i, weight=1)
        elif width >= 400:
            for i in range(6):
                self.footer_frame.grid_columnconfigure(i, weight=0)
        else:
            print("Unexpected width:", width)
            

    def update_status(self, message):
        """Updates the text in the general status indicator and sets its color."""
        self.status_label.config(text=message)
        if "PASS" in message:
            self.status_label.config(fg=self.ColourScheme["msg_pass"])
        elif "FAIL" in message:
            self.status_label.config(fg=self.ColourScheme["msg_fail"])
        elif "UNKNOWN" in message:
            self.status_label.config(fg=self.ColourScheme["msg_unknown"])
        elif "Translating" in message or "Processing" in message:
            self.status_label.config(fg=self.ColourScheme["msg_working"])
        else:
            self.status_label.config(fg=self.ColourScheme["msg_default"]) 

    def update_language_status(self):
        """Updates the text in the language status indicator."""
        if self.translator:
            current_lang = self.translator.current_language()
            self.language_status_label.config(text=f"Lang: {current_lang}")
        else:
            self.language_status_label.config(text="Lang: N/A")

    def check_texts_equality(self):
        """
        Retrieves text from both text boxes, removes plaintext (keeping only tags),
        and compares the results. Updates status to PASS (green) or FAIL (red).
        """
        text_top = self.text_box_top.get("1.0", tk.END)
        text_bottom = self.text_box_bottom.get("1.0", tk.END)

        cleaned_top = remove_plaintext_except_newlines(text_top).replace('\n', '')
        cleaned_bottom = remove_plaintext_except_newlines(text_bottom).replace('\n', '')

        if cleaned_top == cleaned_bottom:
            self.update_status("PASS: Tags match")
        else:
            self.update_status("FAIL: Tags do NOT match")

    def convert_texts_tags(self):
        """
        Retrieves text from both text boxes, converts them by removing plaintext,
        and replaces the content of the text boxes with the converted results.
        Updates status to UNKNOWN (yellow).
        """
        text_top = self.text_box_top.get("1.0", tk.END)
        text_bottom = self.text_box_bottom.get("1.0", tk.END)

        converted_top = remove_plaintext_except_newlines(text_top)
        converted_bottom = remove_plaintext_except_newlines(text_bottom)

        self.text_update("both", [converted_top, converted_bottom])

        self.update_status("UNKNOWN: Converted to tags")
    
    def text_paste_from_history(self, index):
        state = self.history[index] if 0 <= index < len(self.history) else ["History index out of range, you found a bug", "History index out of range, you found a bug"]
        self.text_box_top.delete("1.0", tk.END)
        self.text_box_bottom.delete("1.0", tk.END)
        self.text_box_top.insert(tk.END, state[0])
        self.text_box_bottom.insert(tk.END, state[1])
    
    def text_undo(self):
        
        # At the end, insert current state into history
        if self.history_index == -1:
            current_state = [self.text_box_top.get("1.0", tk.END), self.text_box_bottom.get("1.0", tk.END)]
            self.history.append(current_state) 
            self.history_index = len(self.history) 
        
        if self.history_index > 0:
            self.history_index -= 1
            self.text_paste_from_history(self.history_index)
            self.update_status(f"History: {self.history_index + 1}/{len(self.history)}")
    
    def text_redo(self):
        if self.history_index == -1:
            self.update_status("No history to redo.")
            return
        
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.text_paste_from_history(self.history_index)
            self.update_status(f"History: {self.history_index + 1}/{len(self.history)}")

    def text_update(self, textbox_id, text : str | typing.List[str]):
        if isinstance(text, list) and textbox_id not in ["both"]:
            raise ValueError(f"Unsupported type list[str] for textbox_id '{textbox_id}'. Use a single string instead.")

        current_state = [self.text_box_top.get("1.0", tk.END), self.text_box_bottom.get("1.0", tk.END)]
        
        # delete all history after current index, counting up from 0
        if self.history_index != -1: 
            self.history = self.history[:self.history_index + 1]

        #ignore type errors, caught by the exception above
        
        if textbox_id == "top":
            self.text_box_top.delete("1.0", tk.END)
            self.text_box_top.insert(tk.END, text) # type: ignore
            current_state[0] = text # type: ignore
        elif textbox_id == "bottom":
            self.text_box_bottom.delete("1.0", tk.END)
            self.text_box_bottom.insert(tk.END, text) # type: ignore
            current_state[1] = text # type: ignore
        elif textbox_id == "both":
            self.text_box_top.delete("1.0", tk.END)
            self.text_box_bottom.delete("1.0", tk.END)
            self.text_box_top.insert(tk.END, text[0])
            self.text_box_bottom.insert(tk.END, text[1])
            current_state = [text[0], text[1]]

        self.history.append(current_state)
        self.history_index = len(self.history) - 1
        
    def convert_texts_plaintext(self):
        """
        Retrieves text from both text boxes, converts them by removing HTML tags,
        and replaces the content of the text boxes with the converted results.
        Updates status to UNKNOWN (yellow).
        """
        text_top = self.text_box_top.get("1.0", tk.END)
        text_bottom = self.text_box_bottom.get("1.0", tk.END)

        converted_top = re.sub(r'<[^>]+>', '', text_top).strip()
        converted_bottom = re.sub(r'<[^>]+>', '', text_bottom).strip()

        self.text_update("both", [converted_top, converted_bottom])

        self.update_status("UNKNOWN: Converted to plaintext")

    def debug_texts(self):
        """
        Retrieves text from both text boxes, extracts HTML tags, and replaces
        the content of the text boxes with the extracted tags, each on a new line
        and enclosed in double quotes. Updates status to UNKNOWN (yellow).
        """
        text_top = self.text_box_top.get("1.0", tk.END)
        text_bottom = self.text_box_bottom.get("1.0", tk.END)

        extracted_tags_top = extract_html_tags(text_top)
        extracted_tags_bottom = extract_html_tags(text_bottom)

        formatted_top = "\n".join([f'"{tag}"' for tag in extracted_tags_top])
        formatted_bottom = "\n".join([f'"{tag}"' for tag in extracted_tags_bottom])

        self.text_update("both", [formatted_top, formatted_bottom])

        self.update_status("UNKNOWN: Debugged tags")
        
        

    def translate_content(self):
        if not self.translator:
            self.show_api_key_prompt()
            return

        source_text = self.text_box_top.get("1.0", tk.END).strip()
        if not source_text:
            self.update_status("FAIL: Nothing to translate")
            return

        self.button_translate.config(state=tk.DISABLED)
        self.lang_selector.config(state=tk.DISABLED)
        self.update_status("Processing text for translation...")

        text_parts = split_html_and_plaintext(source_text)
        plaintext_segments = [content for part_type, content in text_parts if part_type == 'plaintext']

        if not plaintext_segments:
            self.update_status("No plaintext found to translate.")
            self.text_update("bottom", source_text)
            self.button_translate.config(state=tk.NORMAL)
            self.lang_selector.config(state="readonly")
            return

        target_lang = self.translator.current_language()
        self.update_status(f"Translating {len(plaintext_segments)} segments to {target_lang}...")

        try:
            translated_plaintexts = []
            if not DEEPL_PROHIBIT_TRANSLATION:
                translated_plaintexts = self.translator.translate_batch(plaintext_segments, target_lang)
            else:
                translated_plaintexts = plaintext_segments
            
            final_translated_text = reassemble_text_with_translations(text_parts, translated_plaintexts)

            self.text_update("bottom", final_translated_text)
            self.update_status("PASS: Translation complete")
        except Exception as e:
            self.update_status(f"FAIL: Translation error - {e}")
        finally:
            self.button_translate.config(state=tk.NORMAL)
            self.lang_selector.config(state="readonly")


    def on_language_selected(self, event):
        """
        Callback for when a language is selected from the Combobox.
        Sets the target language for the DeepL translator and updates the status.
        """
        if self.translator:
            selected_desc = self.target_lang_var.get()
            # Extract the language code from the description (e.g., "EN-US - English (American)") # -- Eh, it works...
            selected_code = selected_desc.split(" - ")[0]
            if self.translator.set_target_language(selected_code):
                self.update_status(f"Language set to: {selected_code}")
                self.update_language_status() # Update the new language status label
            else:
                self.update_status(f"FAIL: Could not set language to {selected_code}")
        else:
            self.update_status("FAIL: Translator not initialized.")
            
    def show_api_key_prompt(self):
        popup = tk.Toplevel(self.master)
        popup.title("Enter DeepL API Key")
        popup.geometry("400x150")
        popup.grab_set()

        label = tk.Label(popup, text="Please provide a valid DeepL API key:")
        label.pack(pady=(10, 5))

        api_entry = tk.Entry(popup, width=40, show='*')
        api_entry.pack(pady=5)

        def select_file():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
            if file_path:
                try:
                    with open(file_path, 'r') as file:
                        content = file.read().strip()
                        api_entry.delete(0, tk.END)
                        api_entry.insert(0, content)
                except Exception as e:
                    messagebox.showerror("File Error", f"Failed to read file: {e}")

        def submit_key():
            key = api_entry.get().strip()
            if key:
                try:
                    self.translator = DeepLTranslator(api_key=key)
                    self.button_translate.config(state=tk.NORMAL)
                    self.lang_selector.config(state="readonly")
                    self.target_lang_var.set(self.translator.current_language())
                    self.lang_selector.config(values=self.translator.available_languages_desc())
                    self.update_language_status()
                    popup.destroy()
                except Exception as e:
                    messagebox.showerror("Translator Initialization Failed", str(e))

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Select File", command=select_file).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Submit", command=submit_key).grid(row=0, column=1, padx=5)



def extract_html_tags(html_snippet: str) -> list[str]:
    """
    Extracts all HTML tags (e.g., <div>, </div>, <p class="article-perex">)
    from a given HTML snippet, including any attributes.
    """
    pattern = r'<[^>]+>'
    tags = re.findall(pattern, html_snippet)
    return tags

def remove_plaintext_except_newlines(html_snippet: str) -> str:
    """
    Removes all plaintext content from an HTML snippet, preserving only
    HTML tags (including attributes) and newline characters.
    """
    pattern = r'(<[^>]+>)|(\n)|([^<>\n]+)'

    def replacer(match):
        if match.group(1):
            return match.group(1)
        elif match.group(2):
            return match.group(2)
        elif match.group(3):
            return ''
        return ''

    return re.sub(pattern, replacer, html_snippet)

def split_html_and_plaintext(text: str) -> typing.List[typing.Tuple[str, str]]:
    """
    Splits text into a list of tuples, identifying HTML tags and plaintext segments.
    Each tuple is (type, content), where type is 'tag' or 'plaintext'.
    """
    parts = []
    # Regex to capture either an HTML tag or any text that is not part of a tag
    # re.DOTALL ensures that '.' matches newlines as well, allowing plaintext to span lines.
    pattern = re.compile(r'(<[^>]+>)|([^<]+)', re.DOTALL)
    

    for match in pattern.finditer(text):
        if match.group(1):  # It's an HTML tag
            parts.append(('tag', match.group(1)))
        elif match.group(2): # It's plaintext
            parts.append(('plaintext', match.group(2)))
    return parts

def reassemble_text_with_translations(
    original_parts: typing.List[typing.Tuple[str, str]], translated_plaintexts: typing.List[str]
) -> str:
    """
    Reassembles the text using original tags and provided translated plaintext segments.
    Assumes translated_plaintexts are in the same order as original plaintext segments.
    """
    reassembled_text = []
    translation_idx = 0
    for part_type, content in original_parts:
        if part_type == 'tag':
            reassembled_text.append(content)
        elif part_type == 'plaintext':
            if translation_idx < len(translated_plaintexts):
                reassembled_text.append(translated_plaintexts[translation_idx])
                translation_idx += 1
            else:
                # Fallback: if somehow translation is missing, use original plaintext
                print(f"Warning: Missing translation for plaintext segment: '{content}'. Using original.")
                reassembled_text.append(content)
    return "".join(reassembled_text)



class DeepLTranslator:
    available_langs_desc = [
        ("AR", " - Arabic"),("BG", " - Bulgarian"),("CS", " - Czech"),("DA", " - Danish"),
        ("DE", " - German"),("EL", " - Greek"),("EN", " - English (unspecified variant for backward compatibility; please select EN-GB or EN-US instead)"),
        ("EN-GB", " - English (British)"),("EN-US", " - English (American)"),("ES", " - Spanish"),
        ("ES-419", " - Spanish (Latin American)"),("ET", " - Estonian"),("FI", " - Finnish"),
        ("FR", " - French"),("HE", " - Hebrew (text translation via next-gen models only)"),
        ("HU", " - Hungarian"),("ID", " - Indonesian"),("IT", " - Italian"),("JA", " - Japanese"),
        ("KO", " - Korean"),("LT", " - Lithuanian"),("LV", " - Latvian"),("NB", " - Norwegian Bokmål"),
        ("NL", " - Dutch"),("PL", " - Polish"),
        ("PT", " - Portuguese (unspecified variant for backward compatibility; please select PT-BR or PT-PT instead)"),
        ("PT-BR", " - Portuguese (Brazilian)"),("PT-PT", " - Portuguese (all Portuguese variants excluding Brazilian Portuguese)"),
        ("RO", " - Romanian"),("RU", " - Russian"),("SK", " - Slovak"),("SL", " - Slovenian"),
        ("SV", " - Swedish"),("TH", " - Thai (text translation via next-gen models only)"),
        ("TR", " - Turkish"),("UK", " - Ukrainian"),
        ("VI", " - Vietnamese (text translation via next-gen models only)"),
        ("ZH", " - Chinese (unspecified variant for backward compatibility; please select ZH-HANS or ZH-HANT instead)"),
        ("ZH-HANS", " - Chinese (simplified)"),("ZH-HANT", " - Chinese (traditional)"),
    ]
    available_langs = {lang[0] for lang in available_langs_desc}

    def __init__(self, api_key: str = ""):
        if api_key:
            self.api_key = api_key
        else:
            try:
                # Attempt to read the API key from a file
                with open("api.key", "r") as file:
                    self.api_key = file.read().strip()
            except FileNotFoundError:
                raise ValueError("API key file 'api.key' not found. Please provide a valid DeepL API key.")

        self.translator = deepl.Translator(self.api_key)
        self.target_lang = "EN-US" # Default target language
        
    

    def current_language(self) -> str:
        """Returns the current target language for translation."""
        return self.target_lang

    def available_languages(self) -> typing.List[str]:
        """Returns a list of available language codes for translation."""
        return [lang[0] for lang in self.available_langs_desc]

    def available_languages_desc(self) -> typing.List[str]:
        """Returns a list of available languages for translation with descriptions."""
        return [lang[0] + lang[1] for lang in self.available_langs_desc]

    def set_target_language(self, lang: str) -> bool:
        """Sets the target language for translation."""
        lang = lang.upper()
        if lang in self.available_langs:
            self.target_lang = lang
            return True
        else:
            print(f"Unsupported language: {lang}. Available languages: {self.available_langs}")
            return False

    def translate(self, text: str, target_lang: str = "") -> str:
        """
        Translates the given text to the specified target language using DeepL.
        """
        if DEEPL_PROHIBIT_TRANSLATION:
            raise Exception("Translation is currently prohibited, safeguard in case I want to limit API usage while testing.")
        
        if target_lang and not self.set_target_language(target_lang):
            raise ValueError(f"Unsupported target language: {target_lang}. Please select from the available languages.")

        try:
            result = self.translator.translate_text(text, target_lang=self.target_lang)
            return result.text # type: ignore
        except deepl.exceptions.DeepLException as e:
            raise Exception(f"DeepL API error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during translation: {e}")

    def translate_batch(self, texts: typing.List[str], lang: str = "") -> typing.List[str]:
        """
        Translates a list of texts to the specified target language using DeepL.
        This function is designed to be called asynchronously (e.g., in a separate thread).
        It leverages DeepL's capability to translate lists of strings directly.
        """
        if DEEPL_PROHIBIT_TRANSLATION:
            raise Exception("Translation is currently prohibited, safeguard in case I want to limit API usage while testing.")
        
        if lang and not self.set_target_language(lang):
            raise ValueError(f"Unsupported target language: {lang}. Please select from the available languages.")

        # Filter out empty strings before sending to DeepL to avoid unnecessary API calls
        # and potential errors if DeepL doesn't handle empty strings well in batches.
        # Keep track of original indices to reinsert empty strings later.
        non_empty_texts_map = []
        original_to_filtered_indices = {}
        for i, text in enumerate(texts):
            if text.strip(): # Only process non-empty, non-whitespace strings
                non_empty_texts_map.append(text)
                original_to_filtered_indices[len(non_empty_texts_map) - 1] = i # Map filtered index to original index
        
        if not non_empty_texts_map:
            return [""] * len(texts) # If all are empty, return empty list of same length

        try:
            # The DeepL Python client library's translate_text method can accept a list of strings
            # and will handle the batching internally.
            results = self.translator.translate_text(non_empty_texts_map, target_lang=self.target_lang)
            
            # The results object will be a list of TextResult objects.
            # We need to extract the 'text' attribute from each.
            translated_filtered_texts = [res.text for res in results] # type: ignore

            # Reconstruct the full list, reinserting empty strings at their original positions
            final_translated_texts = texts
            for filtered_idx, original_idx in original_to_filtered_indices.items():
                if filtered_idx < len(translated_filtered_texts):
                    final_translated_texts[original_idx] = translated_filtered_texts[filtered_idx]
            
            return final_translated_texts

        except deepl.exceptions.DeepLException as e:
            raise Exception(f"DeepL API batch translation error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during batch translation: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("<> Tag Comparator & Translator")

    root.geometry("1000x600")

    app = RuvysTaggedTranslator(root)
    root.mainloop()
