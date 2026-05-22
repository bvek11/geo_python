#!/usr/bin/env python3
"""
SharePoint URL Decoder - GUI Version
Interactive dialog-based interface for parsing SharePoint URLs
"""

import urllib.parse
import re
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from typing import Dict


class SharePointURLDecoder:
    def __init__(self, url: str):
        self.original_url = url
        self.parsed = urllib.parse.urlparse(url)
        self.query_params = urllib.parse.parse_qs(self.parsed.query)
        self.result = {
            "original_url": url,
            "domain": "",
            "site_collection": "",
            "file_path": "",
            "parent_folder": "",
            "file_name": "",
            "file_type": "",
            "folder_structure": [],
            "url_type": "",
            "decoded_components": {}
        }
    
    def decode(self) -> Dict:
        """Main decoding function"""
        self._parse_domain()
        self._detect_url_type()
        
        if "AllItems.aspx" in self.original_url:
            self._parse_library_view()
        elif "/r/" in self.parsed.path or "/:x:/" in self.original_url or "/:w:/" in self.original_url:
            self._parse_direct_link()
        else:
            self._parse_generic()
        
        self._build_folder_structure()
        return self.result
    
    def _parse_domain(self):
        """Extract domain and base site"""
        self.result["domain"] = f"{self.parsed.scheme}://{self.parsed.netloc}"
    
    def _detect_url_type(self):
        """Detect the type of SharePoint URL"""
        url = self.original_url.lower()
        
        if "/forms/allitems.aspx" in url:
            self.result["url_type"] = "Document Library View"
        elif "/:x:/" in url:
            self.result["url_type"] = "Excel File Direct Link"
        elif "/:w:/" in url:
            self.result["url_type"] = "Word File Direct Link"
        elif "/:p:/" in url:
            self.result["url_type"] = "PowerPoint File Direct Link"
        elif "/:b:/" in url:
            self.result["url_type"] = "PDF File Direct Link"
        elif "/r/" in url:
            self.result["url_type"] = "Direct Resource Link"
        elif "_layouts" in url:
            self.result["url_type"] = "SharePoint System Page"
        else:
            self.result["url_type"] = "Generic SharePoint Link"
    
    def _parse_library_view(self):
        """Parse AllItems.aspx document library view URLs"""
        path_parts = self.parsed.path.split("/Forms/AllItems.aspx")[0]
        self.result["site_collection"] = path_parts
        
        if 'id' in self.query_params:
            file_path = urllib.parse.unquote(self.query_params['id'][0])
            self.result["file_path"] = file_path
            self.result["file_name"] = file_path.split("/")[-1] if file_path else ""
            
            if "." in self.result["file_name"]:
                self.result["file_type"] = self.result["file_name"].split(".")[-1].upper()
        
        if 'parent' in self.query_params:
            parent_path = urllib.parse.unquote(self.query_params['parent'][0])
            self.result["parent_folder"] = parent_path
        
        for key, value in self.query_params.items():
            decoded_value = urllib.parse.unquote(value[0]) if value else ""
            self.result["decoded_components"][key] = decoded_value
    
    def _parse_direct_link(self):
        """Parse direct file links (/:x:/, /:w:/, /r/, etc.)"""
        if "/sites/" in self.parsed.path:
            site_match = re.search(r'/sites/[^/]+(?:/[^/]+)*?(?=/(?:_layouts|:x:|:w:|:p:|:b:|r/))', self.parsed.path)
            if site_match:
                self.result["site_collection"] = site_match.group(0)
        
        if 'd' in self.query_params:
            file_id = self.query_params['d'][0]
            self.result["decoded_components"]["file_id"] = file_id
        
        path_after_site = self.parsed.path
        if "/r/" in path_after_site:
            path_parts = path_after_site.split("/r/", 1)
            if len(path_parts) > 1:
                file_path = urllib.parse.unquote(path_parts[1])
                self.result["file_path"] = file_path
                self.result["file_name"] = file_path.split("/")[-1].split("?")[0]
                
                if "." in self.result["file_name"]:
                    self.result["file_type"] = self.result["file_name"].split(".")[-1].upper()
        
        for key, value in self.query_params.items():
            if key not in self.result["decoded_components"]:
                decoded_value = urllib.parse.unquote(value[0]) if value else ""
                self.result["decoded_components"][key] = decoded_value
    
    def _parse_generic(self):
        """Parse generic SharePoint URLs"""
        self.result["site_collection"] = self.parsed.path
        
        path_parts = self.parsed.path.split("/")
        if path_parts and "." in path_parts[-1]:
            self.result["file_name"] = path_parts[-1]
            self.result["file_type"] = path_parts[-1].split(".")[-1].upper()
            self.result["file_path"] = self.parsed.path
        
        for key, value in self.query_params.items():
            decoded_value = urllib.parse.unquote(value[0]) if value else ""
            self.result["decoded_components"][key] = decoded_value
    
    def _build_folder_structure(self):
        """Build hierarchical folder structure from file path"""
        path = self.result.get("file_path") or self.result.get("parent_folder") or ""
        
        if path:
            path = path.strip("/")
            parts = path.split("/")
            
            for i, part in enumerate(parts):
                decoded_part = urllib.parse.unquote(part)
                indent = "  " * i
                
                is_file = (i == len(parts) - 1 and "." in decoded_part)
                item_type = "📄 FILE" if is_file else "📁 FOLDER"
                
                self.result["folder_structure"].append({
                    "level": i,
                    "name": decoded_part,
                    "type": "file" if is_file else "folder",
                    "display": f"{indent}{item_type}: {decoded_part}"
                })
    
    def get_formatted_report(self) -> str:
        """Return a formatted text report"""
        report = []
        report.append("=" * 80)
        report.append("SHAREPOINT URL DECODER - ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"🌐 Domain:          {self.result['domain']}")
        report.append(f"📋 URL Type:        {self.result['url_type']}")
        report.append(f"🏢 Site Collection: {self.result['site_collection']}")
        report.append("")
        
        if self.result['file_name']:
            report.append(f"📄 File Name:  {self.result['file_name']}")
            report.append(f"📑 File Type:  {self.result['file_type']}")
            report.append("")
        
        if self.result['file_path']:
            report.append("📍 FULL FILE PATH:")
            report.append(f"   {self.result['file_path']}")
            report.append("")
        
        if self.result['folder_structure']:
            report.append("🗂️  FOLDER STRUCTURE:")
            for item in self.result['folder_structure']:
                report.append(f"   {item['display']}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


class SharePointDecoderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SharePoint URL Decoder")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Set window icon (if possible)
        try:
            self.root.iconbitmap('')
        except:
            pass
        
        self.current_result = None
        self.setup_ui()
        
        # Center window on screen
        self.center_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the user interface"""
        # Header
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            header_frame, 
            text="📎 SharePoint URL Decoder", 
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Decode and analyze SharePoint URLs",
            font=("Arial", 10)
        )
        subtitle_label.pack()
        
        # Input frame
        input_frame = ttk.LabelFrame(self.root, text="Input", padding="10")
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="Paste SharePoint URL:").pack(anchor=tk.W)
        
        # URL Entry with scrollbar
        entry_frame = ttk.Frame(input_frame)
        entry_frame.pack(fill=tk.X, pady=5)
        
        self.url_entry = tk.Text(entry_frame, height=3, wrap=tk.WORD, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(entry_frame, command=self.url_entry.yview)
        self.url_entry.config(yscrollcommand=scrollbar.set)
        
        self.url_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.decode_button = ttk.Button(
            button_frame,
            text="🔍 Decode URL",
            command=self.decode_url,
            style="Accent.TButton"
        )
        self.decode_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(
            button_frame,
            text="🗑️ Clear",
            command=self.clear_all
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.paste_button = ttk.Button(
            button_frame,
            text="📋 Paste from Clipboard",
            command=self.paste_from_clipboard
        )
        self.paste_button.pack(side=tk.LEFT, padx=5)
        
        # Output frame
        output_frame = ttk.LabelFrame(self.root, text="Analysis Results", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Export buttons frame
        export_frame = ttk.Frame(self.root, padding="10")
        export_frame.pack(fill=tk.X)
        
        self.export_json_button = ttk.Button(
            export_frame,
            text="💾 Export to JSON",
            command=self.export_json,
            state=tk.DISABLED
        )
        self.export_json_button.pack(side=tk.LEFT, padx=5)
        
        self.copy_button = ttk.Button(
            export_frame,
            text="📄 Copy to Clipboard",
            command=self.copy_results,
            state=tk.DISABLED
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Paste a SharePoint URL and click 'Decode URL'")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Bind Enter key to decode
        self.url_entry.bind('<Control-Return>', lambda e: self.decode_url())
    
    def paste_from_clipboard(self):
        """Paste URL from clipboard"""
        try:
            clipboard_content = self.root.clipboard_get()
            self.url_entry.delete("1.0", tk.END)
            self.url_entry.insert("1.0", clipboard_content)
            self.status_var.set("✅ Pasted from clipboard")
        except:
            messagebox.showwarning("Clipboard", "No text found in clipboard")
    
    def decode_url(self):
        """Decode the SharePoint URL"""
        url = self.url_entry.get("1.0", tk.END).strip()
        
        # Validate URL
        if not url:
            messagebox.showwarning("Input Required", "Please paste a SharePoint URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Invalid URL", "URL must start with http:// or https://")
            return
        
        try:
            self.status_var.set("🔍 Analyzing URL...")
            self.root.update()
            
            # Decode the URL
            decoder = SharePointURLDecoder(url)
            self.current_result = decoder.decode()
            
            # Display results
            report = decoder.get_formatted_report()
            self.results_text.config(state=tk.NORMAL)
            self.results_text.delete("1.0", tk.END)
            self.results_text.insert("1.0", report)
            self.results_text.config(state=tk.DISABLED)
            
            # Enable export buttons
            self.export_json_button.config(state=tk.NORMAL)
            self.copy_button.config(state=tk.NORMAL)
            
            self.status_var.set("✅ URL decoded successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to decode URL:\n{str(e)}")
            self.status_var.set("❌ Error decoding URL")
    
    def export_json(self):
        """Export results to JSON file"""
        if not self.current_result:
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="sharepoint_decoded.json"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.current_result, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Export Successful", f"Results exported to:\n{filename}")
                self.status_var.set(f"✅ Exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export:\n{str(e)}")
    
    def copy_results(self):
        """Copy results to clipboard"""
        results = self.results_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(results)
        messagebox.showinfo("Copied", "Results copied to clipboard!")
        self.status_var.set("✅ Results copied to clipboard")
    
    def clear_all(self):
        """Clear all fields"""
        self.url_entry.delete("1.0", tk.END)
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state=tk.DISABLED)
        self.current_result = None
        self.export_json_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
        self.status_var.set("Ready. Paste a SharePoint URL and click 'Decode URL'")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = SharePointDecoderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
