"""
Internet Archive Download Script with User Input
Allows user to enter custom search query and choose to check filesize or download
"""

import os
import sys
import json
import csv
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

try:
    from rich.console import Console
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class IADownloader:
    def __init__(self):
        self.error_log = []
        
    def format_file_size(self, bytes_size: int) -> str:
        """Format file size in human readable format"""
        if bytes_size <= 0:
            return "0 Bytes"
        
        units = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
        power = min(len(units) - 1, int(bytes_size.bit_length() - 1) // 10)
        size = bytes_size / (1024 ** power)
        return f"{size:.2f} {units[power]}"
    
    def print_colored(self, text: str, color: str = "white"):
        """Print colored text using rich if available, otherwise plain text"""
        if RICH_AVAILABLE:
            console.print(text, style=color)
        else:
            print(text)
    
    def get_search_query(self) -> str:
        """Get search query from user with examples"""
        if RICH_AVAILABLE:
            console.print("=== Internet Archive Download Script ===", style="cyan bold")
            console.print()
            console.print("Examples of search queries:", style="yellow")
            console.print('  title:("Statutes of the Province of Ontario") AND collection:(ontario_council_university_libraries)')
            console.print('  creator:"Ontario" AND mediatype:texts')
            console.print('  collection:americana AND date:[1800 TO 1900]')
            console.print()
        else:
            print("=== Internet Archive Download Script ===")
            print()
            print("Examples of search queries:")
            print('  title:("Statutes of the Province of Ontario") AND collection:(ontario_council_university_libraries)')
            print('  creator:"Ontario" AND mediatype:texts')
            print('  collection:americana AND date:[1800 TO 1900]')
            print()
        
        while True:
            if RICH_AVAILABLE:
                query = Prompt.ask("Enter your Internet Archive search query")
            else:
                query = input("Enter your Internet Archive search query: ")
            
            if query.strip():
                return query.strip()
            
            self.print_colored("Please enter a valid search query.", "red")
    
    def get_user_action(self) -> int:
        """Get user's choice of action"""
        if RICH_AVAILABLE:
            console.print()
            console.print("Choose an action:", style="yellow")
            console.print("1. Check total PDF file size only")
            console.print("2. Download PDFs and create metadata CSV")
            console.print()
            
            while True:
                choice = Prompt.ask("Enter your choice", choices=["1", "2"])
                return int(choice)
        else:
            print()
            print("Choose an action:")
            print("1. Check total PDF file size only")
            print("2. Download PDFs and create metadata CSV")
            print()
            
            while True:
                choice = input("Enter your choice (1 or 2): ").strip()
                if choice in ["1", "2"]:
                    return int(choice)
                print("Please enter 1 or 2.")
    
    def get_download_directory(self) -> str:
        """Get download directory from user"""
        if RICH_AVAILABLE:
            console.print()
            console.print("Download Directory Options:", style="yellow")
            console.print("  - Press Enter to download to current directory")
            console.print("  - Or enter a folder name to create/use a subdirectory")
            console.print()
            
            dir_name = Prompt.ask("Enter download directory name (or press Enter for current directory)", default="")
        else:
            print()
            print("Download Directory Options:")
            print("  - Press Enter to download to current directory")
            print("  - Or enter a folder name to create/use a subdirectory")
            print()
            
            dir_name = input("Enter download directory name (or press Enter for current directory): ")
        
        if not dir_name.strip():
            return os.getcwd()
        
        # Clean the directory name for invalid characters
        clean_dir_name = re.sub(r'[<>:"/\\|?*]', '_', dir_name.strip())
        clean_dir_name = re.sub(r'\s+', '_', clean_dir_name)
        clean_dir_name = clean_dir_name.strip('_')
        
        full_path = os.path.join(os.getcwd(), clean_dir_name)
        
        try:
            os.makedirs(full_path, exist_ok=True)
            self.print_colored(f"Created directory: {full_path}", "green")
        except Exception as e:
            self.print_colored(f"Error creating directory '{full_path}': {e}", "red")
            self.print_colored("Using current directory instead.", "yellow")
            return os.getcwd()
        
        return full_path
    
    def check_ia_command(self) -> bool:
        """Check if Internet Archive CLI is available"""
        try:
            subprocess.run(["ia", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def search_items(self, query: str) -> List[str]:
        """Search Internet Archive and return list of item IDs"""
        try:
            # Pass query as single quoted argument to preserve complex search syntax
            result = subprocess.run(
                ["ia", "search", query, "--itemlist"],
                capture_output=True,
                text=True,
                check=True,
                shell=False
            )
            items = [item.strip() for item in result.stdout.strip().split('\n') if item.strip()]
            return items
        except subprocess.CalledProcessError as e:
            self.print_colored(f"Error searching Internet Archive: {e}", "red")
            self.print_colored(f"Command output: {e.stderr if e.stderr else 'No error output'}", "red")
            return []
    
    def get_item_metadata(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific item"""
        try:
            result = subprocess.run(
                ["ia", "metadata", item_id],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None
    
    def get_total_file_size(self, search_query: str, item_list: List[str]):
        """Calculate total file size of PDFs for all items"""
        self.print_colored("\nCalculating total PDF file sizes...", "green")
        
        total_size = 0
        item_sizes = []
        
        if RICH_AVAILABLE:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("Checking", total=len(item_list))
                
                for item_id in item_list:
                    try:
                        metadata = self.get_item_metadata(item_id)
                        if metadata:
                            pdf_files = [f for f in metadata.get('files', []) if f.get('name', '').endswith('.pdf')]
                            item_size = sum(int(f.get('size', 0)) for f in pdf_files)
                            total_size += item_size
                            
                            item_sizes.append({
                                'Item ID': item_id,
                                'Title': metadata.get('metadata', {}).get('title', ''),
                                'PDF Count': len(pdf_files),
                                'Size (Bytes)': item_size,
                                'Size (Formatted)': self.format_file_size(item_size)
                            })
                    except Exception as e:
                        self.error_log.append(f"Failed to get metadata for item: {item_id}. Error: {e}")
                    
                    progress.advance(task)
        else:
            for i, item_id in enumerate(item_list, 1):
                print(f"\rChecking [{i}/{len(item_list)}] {i/len(item_list)*100:.0f}%", end="", flush=True)
                
                try:
                    metadata = self.get_item_metadata(item_id)
                    if metadata:
                        pdf_files = [f for f in metadata.get('files', []) if f.get('name', '').endswith('.pdf')]
                        item_size = sum(int(f.get('size', 0)) for f in pdf_files)
                        total_size += item_size
                        
                        item_sizes.append({
                            'Item ID': item_id,
                            'Title': metadata.get('metadata', {}).get('title', ''),
                            'PDF Count': len(pdf_files),
                            'Size (Bytes)': item_size,
                            'Size (Formatted)': self.format_file_size(item_size)
                        })
                except Exception as e:
                    self.error_log.append(f"Failed to get metadata for item: {item_id}. Error: {e}")
            print("\nSize calculation complete!")
        
        if self.error_log:
            self.print_colored(f"\nEncountered {len(self.error_log)} errors:", "red")
            for error in self.error_log[-5:]:  # Show last 5 errors
                self.print_colored(f" - {error}", "red")
            if len(self.error_log) > 5:
                self.print_colored(f" ... and {len(self.error_log) - 5} more", "red")
        
        # Display summary
        self.print_colored("\n=== File Size Summary ===", "green")
        print(f"Search Query: {search_query}")
        print(f"Total Items Scanned: {len(item_list)}")
        print(f"Total PDF Files: {sum(item['PDF Count'] for item in item_sizes)}")
        print(f"Total Size: {self.format_file_size(total_size)}")
        print()
        
        # Export report option
        if RICH_AVAILABLE:
            export_report = Confirm.ask("Export detailed size report to CSV?")
        else:
            export_report = input("Export detailed size report to CSV? (y/n): ").lower().startswith('y')
        
        if export_report:
            csv_path = os.path.join(os.getcwd(), "filesize_report.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                if item_sizes:
                    writer = csv.DictWriter(csvfile, fieldnames=item_sizes[0].keys())
                    writer.writeheader()
                    writer.writerows(item_sizes)
            self.print_colored(f"Size report exported to: {csv_path}", "green")
    
    def download_files_and_create_metadata(self, search_query: str, item_list: List[str], download_dir: str):
        """Download PDFs and create metadata CSV"""
        download_location = "Current directory" if download_dir == os.getcwd() else f"Directory: {download_dir}"
        
        self.print_colored("\nDownload Settings:", "green")
        print(f"  Search Query: {search_query}")
        print(f"  Items found: {len(item_list)}")
        print(f"  Download location: {download_location}")
        print()
        
        if RICH_AVAILABLE:
            if not Confirm.ask("Proceed with download?"):
                self.print_colored("Download cancelled.", "yellow")
                return
        else:
            confirm = input("Proceed with download? (y/n): ").lower()
            if not confirm.startswith('y'):
                self.print_colored("Download cancelled.", "yellow")
                return
        
        all_metadata = []
        
        self.print_colored("\nStarting download and metadata collection...", "green")
        
        if RICH_AVAILABLE:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("Downloading", total=len(item_list))
                
                for item_id in item_list:
                    self._process_item_download(item_id, download_dir, all_metadata)
                    progress.advance(task)
        else:
            for i, item_id in enumerate(item_list, 1):
                print(f"\rDownloading [{i}/{len(item_list)}] {i/len(item_list)*100:.0f}%", end="", flush=True)
                self._process_item_download(item_id, download_dir, all_metadata)
            print("\nDownload and metadata collection complete!")
        
        if self.error_log:
            self.print_colored(f"\nEncountered {len(self.error_log)} errors during download:", "red")
            for error in self.error_log[-5:]:  # Show last 5 errors
                self.print_colored(f" - {error}", "red")
            if len(self.error_log) > 5:
                self.print_colored(f" ... and {len(self.error_log) - 5} more", "red")
        
        if all_metadata:
            csv_path = os.path.join(download_dir, "internet_archive_metadata.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                if all_metadata:
                    writer = csv.DictWriter(csvfile, fieldnames=all_metadata[0].keys())
                    writer.writeheader()
                    writer.writerows(all_metadata)
            
            self.print_colored("\n=== Download Summary ===", "green")
            print(f"Successfully processed {len(all_metadata)} files from {len(item_list)} items.")
            print(f"PDFs saved to: {download_dir}")
            print(f"Metadata file created: {csv_path}")
        else:
            self.print_colored("No items were successfully processed or downloaded.", "red")
    
    def _process_item_download(self, item_id: str, download_dir: str, all_metadata: List[Dict]):
        """Process download for a single item"""
        try:
            # Get metadata first
            metadata = self.get_item_metadata(item_id)
            if not metadata:
                self.error_log.append(f"Failed to get metadata for item: {item_id}")
                return
            
            # Download PDFs to temporary subfolder
            subprocess.run(
                ["ia", "download", item_id, "--glob=*.pdf"],
                cwd=os.getcwd(),
                capture_output=True,
                check=True
            )
            
            # Check if temp directory was created
            item_subdir = os.path.join(os.getcwd(), item_id)
            if os.path.exists(item_subdir):
                # Find downloaded PDFs
                pdf_files = [f for f in os.listdir(item_subdir) if f.endswith('.pdf')]
                
                if pdf_files:
                    # Create metadata entries for each PDF
                    for pdf_file in pdf_files:
                        metadata_entry = {
                            'ItemID': item_id,
                            'FileName': pdf_file,
                            'title': metadata.get('metadata', {}).get('title', ''),
                            'creator': metadata.get('metadata', {}).get('creator', ''),
                            'publisher': metadata.get('metadata', {}).get('publisher', ''),
                            'date': metadata.get('metadata', {}).get('date', ''),
                            'subject': metadata.get('metadata', {}).get('subject', ''),
                            'language': metadata.get('metadata', {}).get('language', ''),
                            'description': metadata.get('metadata', {}).get('description', ''),
                            'call_number': metadata.get('metadata', {}).get('call number', '')
                        }
                        all_metadata.append(metadata_entry)
                    
                    # Move PDFs to final destination
                    for pdf_file in pdf_files:
                        src = os.path.join(item_subdir, pdf_file)
                        dst = os.path.join(download_dir, pdf_file)
                        shutil.move(src, dst)
                
                # Cleanup temp directory
                shutil.rmtree(item_subdir, ignore_errors=True)
                
        except Exception as e:
            self.error_log.append(f"Failed to process item: {item_id}. Error: {e}")
    
    def run(self):
        """Main execution function"""
        try:
            # Check if IA CLI is available
            if not self.check_ia_command():
                self.print_colored("Error: The Internet Archive CLI tool ('ia') is not installed or not in your PATH.", "red")
                self.print_colored("Please install it by running: pip install internetarchive", "yellow")
                sys.exit(1)
            
            # Get search query
            search_query = self.get_search_query()
            
            # Search for items
            self.print_colored("\nSearching Internet Archive...", "yellow")
            item_list = self.search_items(search_query)
            
            if not item_list:
                self.print_colored(f"No items found for the search query: {search_query}", "red")
                self.print_colored("Please check your search syntax and try again.", "red")
                sys.exit(1)
            
            self.print_colored(f"Found {len(item_list)} items matching your search.", "green")
            
            # Get user action
            user_choice = self.get_user_action()
            
            if user_choice == 1:
                self.get_total_file_size(search_query, item_list)
            elif user_choice == 2:
                download_dir = self.get_download_directory()
                self.download_files_and_create_metadata(search_query, item_list, download_dir)
                
        except KeyboardInterrupt:
            self.print_colored("\nOperation cancelled by user.", "yellow")
            sys.exit(0)
        except Exception as e:
            self.print_colored(f"\nAn unexpected error occurred: {e}", "red")
            sys.exit(1)
        
        self.print_colored("\nScript finished.", "cyan")


if __name__ == "__main__":
    downloader = IADownloader()
    downloader.run()