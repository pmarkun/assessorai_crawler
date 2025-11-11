#!/usr/bin/env python3
"""
AssessorAI Crawler TUI - Terminal User Interface for managing scrapers.
"""

import os
import json
import subprocess
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.widgets import Header, Footer, ListView, ListItem, Input, Button, TextArea, Label, Checkbox, Select, Static, Log
from textual.widget import Widget
from textual import events
from textual.binding import Binding

from assessorai_crawler.settings import OUTPUT_DIR, TEST_OUTPUT_DIR


class SpiderSelector(Widget):
    """Widget for selecting a spider from the list."""

    def __init__(self):
        super().__init__()
        self.spiders = self.load_spiders()

    def load_spiders(self) -> List[Dict]:
        """Load available spiders from the spiders directory."""
        spiders_dir = Path("assessorai_crawler/spiders")
        spiders = []

        for file in spiders_dir.glob("*.py"):
            if file.name.startswith("base_") or file.name == "__init__.py":
                continue

            spider_name = file.stem
            # Read the spider file to get house info
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract house from the class
                    house_line = None
                    for line in content.split('\n'):
                        if 'house =' in line:
                            house_line = line.strip()
                            break
                    house = house_line.split('=')[1].strip().strip('"\'') if house_line else "Unknown"
            except:
                house = "Unknown"

            spiders.append({
                "name": spider_name,
                "house": house,
                "args": self.get_spider_args(spider_name)
            })

        return sorted(spiders, key=lambda x: x["name"])

    def get_spider_args(self, spider_name: str) -> List[str]:
        """Determine arguments for a spider based on its base class."""
        file_path = Path("assessorai_crawler/spiders") / f"{spider_name}.py"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check base class
            if "BaseCamarasempapelSpider" in content:
                return ["ano"]
            elif "BaseSaplSpider" in content:
                return ["ano"]
            elif "BaseSiscamSpider" in content:
                return ["ano"]
            else:
                return ["ano"]  # fallback
        except:
            return ["ano"]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Select a Spider:")
            yield ListView(id="spider_list")

    def on_mount(self):
        """Populate the list after mounting."""
        list_view = self.query_one("#spider_list", ListView)
        for spider in self.spiders:
            list_view.append(ListItem(Label(f"{spider['name']} - {spider['house']}")))


# Removed ArgsForm, ExecutionPanel, ResultsPanel - integrated into main layout


class AssessorAICrawlerTUI(App):
    """Main TUI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
    }

    Footer {
        background: $primary;
        color: $text;
    }

    #selection_menu {
        height: auto;
        padding: 1;
        border-bottom: solid $primary;
    }

    #main_layout {
        display: none;
        height: 100%;
    }

    #top_half {
        height: 20%;
        padding: 0 1;
        border-bottom: solid $primary;
    }

    #bottom_half {
        height: 80%;
    }

    #logs_column {
        width: 50%;
        padding: 1;
        border-right: solid $primary;
    }

    #results_column {
        width: 50%;
        padding: 1;
    }

    #results_list {
        height: 80%;
    }

    #details_view {
        display: none;
        height: 100%;
    }

    .section-title {
        text-style: bold;
        margin: 1 0;
    }

    #run_button {
        background: $success;
        color: $text;
        border: solid $success;
    }

    Button {
        margin: 0 1 0 0;
        height: 3;
    }

    #back_button {
        background: transparent;
        border: none;
        color: $primary;
        padding: 0 1;
        margin: 0 0 1 0;
        height: 3;
        text-style: bold;
    }

    Input {
        margin: 0 1 0 0;
        width: 15;
        height: 3;
    }

    #config_row {
        align-vertical: middle;
    }

    Checkbox {
        margin: 0 1 0 0;
        height: 3;
    }

    #content_scroll {
        height: 70vh;
    }

    #scrapy-log {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("f1", "select_scraper", "Select Scraper"),
        Binding("f2", "help", "Help"),
        Binding("f3", "refresh_results", "Refresh Results"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.current_spider = None
        self.current_args = {}
        self.execution_task = None
        self.spider_selected = False
        self.scraping_running = False
        self.last_click_time = 0
        self.last_click_item = None
        self.showing_years = True
        self.current_year = None

    def compose(self) -> ComposeResult:
        yield Header()
        # Spider selection menu
        with Vertical(id="selection_menu"):
            yield Label("Select Scraper:")
            spider_options = [(f"{spider['house']} ({spider['name']})", spider["name"]) for spider in SpiderSelector().load_spiders()]
            yield Select(options=spider_options, id="spider_select", prompt="Choose a scraper...")

        # Main layout (hidden initially)
        with Vertical(id="main_layout"):
            # Top half: Config and Run
            with Vertical(id="top_half"):
                yield Static("", id="scraper_name")
                with Horizontal(id="config_row"):
                    # Args inputs will be added dynamically here
                    yield Button("Run Scrape", id="run_button", disabled=True)

            # Bottom half: Logs left, Results right
            with Horizontal(id="bottom_half"):
                # Left: Logs
                with Vertical(id="logs_column"):
                    yield Static("Execution Logs:", classes="section-title")
                    yield Log(id="scrapy-log", auto_scroll=True, highlight=False)

                # Right: Results
                with Vertical(id="results_column"):
                    yield Static("Results:", classes="section-title")
                    yield ListView(id="results_list")
                    # Details view (hidden initially)
                    with Vertical(id="details_view"):
                        yield Button("Back", id="back_button")
                        with VerticalScroll(id="content_scroll"):
                            yield TextArea("", id="md_area", read_only=True)

        yield Footer()

    def on_select_changed(self, event: Select.Changed):
        """Handle spider selection from dropdown."""
        if event.select.id == "spider_select" and event.value:
            spider_name = event.value
            spiders = SpiderSelector().load_spiders()
            for spider in spiders:
                if spider["name"] == spider_name:
                    self.current_spider = spider
                    self.spider_selected = True
                    self.show_main_layout()
                    break

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle item selection in results."""
        if event.list_view.id == "results_list" and event.item:
            selected_index = event.list_view.index
            current_time = time.time()
            if current_time - self.last_click_time < 0.3 and self.last_click_item == selected_index:
                # Double-click detected
                if self.showing_years:
                    years_sorted = sorted(self.years.keys())
                    if 0 <= selected_index < len(years_sorted):
                        year = years_sorted[selected_index]
                        self.show_year_items(year)
                else:
                    if selected_index == 0:
                        self.show_years()
                    else:
                        items = self.years.get(self.current_year, [])
                        if 0 <= selected_index - 1 < len(items):
                            item = items[selected_index - 1]
                            self.show_item_details(item)
            self.last_click_time = current_time
            self.last_click_item = selected_index

    def on_key(self, event: events.Key):
        """Handle key presses."""
        if event.key == "enter":
            if not self.spider_selected:
                # If not selected yet, focus on select
                try:
                    select = self.query_one("#spider_select", Select)
                    select.focus()
                except:
                    pass
            else:
                # If spider selected, check if results list is focused
                try:
                    results_list = self.query_one("#results_list", ListView)
                    if results_list.has_focus and results_list.index is not None:
                        selected_index = results_list.index
                        if self.showing_years:
                            years_sorted = sorted(self.years.keys())
                            if 0 <= selected_index < len(years_sorted):
                                year = years_sorted[selected_index]
                                self.show_year_items(year)
                        else:
                            if selected_index == 0:
                                self.show_years()
                            else:
                                items = self.years.get(self.current_year, [])
                                if 0 <= selected_index - 1 < len(items):
                                    item = items[selected_index - 1]
                                    self.show_item_details(item)
                except:
                    pass

# Args form integrated into config_section

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "run_button":
            if self.scraping_running:
                self.cancel_execution()
            else:
                self.run_spider()
        elif event.button.id == "back_button":
            self.show_results_list()

    def run_spider(self):
        """Execute the spider."""
        if not self.current_spider:
            return

        self.scraping_running = True
        run_button = self.query_one("#run_button", Button)
        run_button.label = "Stop"
        self.execution_task = asyncio.create_task(self.execute_spider())

    async def execute_spider(self):
        """Execute the spider asynchronously."""
        scrapy_log = self.query_one("#scrapy-log", Log)
        run_button = self.query_one("#run_button", Button)

        # Get args from inputs
        self.current_args = {}
        for arg in self.current_spider.get("args", []):
            input_widget = self.query_one(f"#input_{arg}", Input)
            if input_widget.value.strip():
                self.current_args[arg] = input_widget.value.strip()

        # Check test mode
        test_mode = self.query_one("#test_mode", Checkbox).value
        if test_mode:
            self.current_args["max_pages"] = "1"
            self.current_args["test_mode"] = "True"

        # Check reset mode
        reset_mode = self.query_one("#reset_mode", Checkbox).value
        if reset_mode:
            self.current_args["reset"] = "True"

        # Build command
        cmd = ["scrapy", "crawl", self.current_spider["name"]]
        for arg, value in self.current_args.items():
            cmd.extend(["-a", f"{arg}={value}"])

        scrapy_log.write_line(f"Running: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=os.getcwd()
            )

            self.execution_task = process

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                scrapy_log.write_line(line.decode().strip())

            await process.wait()

            if process.returncode == 0:
                scrapy_log.write_line("Execution completed successfully!")
                # Reload results
                await asyncio.sleep(1)
                self.load_results()
            else:
                scrapy_log.write_line(f"Execution failed with code {process.returncode}")

        except Exception as e:
            scrapy_log.write_line(f"Error: {str(e)}")
        finally:
            run_button.label = "Run Scrape"
            self.scraping_running = False
            self.execution_task = None

    def cancel_execution(self):
        """Cancel the current execution."""
        if self.execution_task:
            try:
                self.execution_task.terminate()
                # Wait a bit for graceful shutdown
                import asyncio
                asyncio.create_task(self.wait_for_process())
            except:
                pass
            self.execution_task = None
        run_button = self.query_one("#run_button", Button)
        run_button.label = "Run Scrape"
        self.scraping_running = False

    async def wait_for_process(self):
        """Wait for process to terminate gracefully."""
        if self.execution_task:
            try:
                await asyncio.wait_for(self.execution_task.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.execution_task.kill()  # Force kill if not terminating

    def load_results(self):
        """Load scraped items."""
        json_path = Path("storage/output") / f"{self.current_spider['name']}_proposicoes.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.items = json.load(f)

                self.group_by_year()
                self.show_years()

            except Exception as e:
                results_column = self.query_one("#results_column")
                results_column.mount(Static(f"Error loading results: {str(e)}", classes="error-text"))
        else:
            results_column = self.query_one("#results_column")
            results_column.mount(Static("No results file found.", classes="info-text"))




    def show_item_details(self, item: Dict):
        """Show details and MD content for selected item."""
        # Hide list, show details
        results_list = self.query_one("#results_list", ListView)
        results_list.display = False
        details_view = self.query_one("#details_view")
        details_view.display = True

        md_area = self.query_one("#md_area", TextArea)

        # Show item details
        details = f"Title: {item.get('title', 'N/A')}\n"
        details += f"Number: {item.get('number', 'N/A')}\n"
        details += f"Year: {item.get('year', 'N/A')}\n"
        details += f"Type: {item.get('type', 'N/A')}\n"
        details += f"Author: {', '.join(item.get('author', []))}\n"
        details += f"Subject: {item.get('subject', 'N/A')}\n\n"

        # Show content
        full_text = item.get('full_text')
        if full_text:
            content = details + "--- Content ---\n\n" + full_text
        else:
            md_files = item.get('md_files')
            if md_files:
                test_mode = self.query_one("#test_mode", Checkbox).value
                output_dir = TEST_OUTPUT_DIR if test_mode else OUTPUT_DIR
                md_path = Path.cwd() / output_dir / md_files
                if md_path.exists():
                    try:
                        with open(md_path, 'r', encoding='utf-8') as f:
                            md_content = f.read()
                        content = details + "--- Content ---\n\n" + md_content
                    except Exception as e:
                        content = details + f"Error loading content: {str(e)}\n"
                else:
                    content = details + "Content file not found.\n"
            else:
                content = details + "No content available.\n"

        md_area.text = content
        self.refresh()

    def group_by_year(self):
        """Group items by year."""
        self.years = {}
        for item in self.items:
            year = item.get("year", "Unknown")
            if year not in self.years:
                self.years[year] = []
            self.years[year].append(item)

    def show_years(self):
        """Show grouped years with counts."""
        self.showing_years = True
        results_list = self.query_one("#results_list", ListView)
        results_list.clear()
        for year in sorted(self.years.keys()):
            count = len(self.years[year])
            results_list.append(ListItem(Label(f"{year} ({count} projetos)")))

    def show_year_items(self, year):
        """Show items for selected year."""
        self.showing_years = False
        self.current_year = year
        results_list = self.query_one("#results_list", ListView)
        results_list.clear()
        results_list.append(ListItem(Label("..")))
        for item in self.years[year]:
            title = item.get("title", "Unknown")
            number = item.get("number", "Unknown")
            label = f"{title} - {number}"
            # Check if markdown file exists
            md_files = item.get("md_files")
            if md_files:
                full_path = Path("storage/output") / md_files
                if full_path.exists():
                    label += " (+)"
            results_list.append(ListItem(Label(label)))

    def show_main_layout(self):
        """Show the main two-column layout after spider selection."""
        # Hide selection menu
        selection_menu = self.query_one("#selection_menu")
        selection_menu.display = False

        # Show main layout
        main_layout = self.query_one("#main_layout")
        main_layout.display = True

        # Set scraper name
        scraper_name = self.query_one("#scraper_name", Static)
        scraper_name.update(f"Scraper: {self.current_spider['house']} ({self.current_spider['name']})")

        # Add args inputs
        config_row = self.query_one("#config_row")
        # Remove existing inputs/checkboxes, keep only button
        for child in list(config_row.children):
            if child.id != "run_button":
                child.remove()
        for arg in self.current_spider.get("args", []):
            if arg != "max_pages":  # Skip max_pages input
                config_row.mount(Input(placeholder=arg.upper(), id=f"input_{arg}"))

        config_row.mount(Checkbox("Test", id="test_mode"))
        config_row.mount(Checkbox("Reset", id="reset_mode"))

        # Enable run button
        run_button = self.query_one("#run_button", Button)
        run_button.disabled = False

        # Clear previous results
        results_list = self.query_one("#results_list")
        results_list.clear()

        # Check if results exist
        json_path = Path("storage/output") / f"{self.current_spider['name']}_proposicoes.json"
        if json_path.exists():
            self.load_results()
        else:
            # Show message in results
            results_column = self.query_one("#results_column")
            results_column.mount(Static("No results yet. Run scrape to generate data.", classes="info-text"))

    def show_selection_menu(self):
        """Show the scraper selection menu."""
        # Interrupt current scraper if running
        if self.scraping_running:
            self.cancel_execution()

        # Clear config_row to prevent duplicate IDs
        config_row = self.query_one("#config_row")
        for child in list(config_row.children):
            if child.id != "run_button":
                child.remove()

        # Hide main layout
        main_layout = self.query_one("#main_layout")
        main_layout.display = False

        # Show selection menu
        selection_menu = self.query_one("#selection_menu")
        selection_menu.display = True

        # Reset state
        self.spider_selected = False
        self.current_spider = None
        self.items = []
        self.years = {}
        self.showing_years = True

        # Focus select
        try:
            select = self.query_one("#spider_select", Select)
            select.focus()
        except:
            pass

    def show_results_list(self):
        """Show the results list."""
        results_list = self.query_one("#results_list", ListView)
        results_list.display = True
        details_view = self.query_one("#details_view")
        details_view.display = False
        if not self.showing_years:
            self.show_years()

    def action_select_scraper(self):
        """Switch to scraper selection menu."""
        self.show_selection_menu()

    def action_help(self):
        """Show help."""
        help_text = """
        Navigation:
        Arrow keys: Navigate lists/dropdown
        Enter: Select spider or show item details
        F1: Focus scraper selection
        F2: Help
        Ctrl+Q: Quit
        """
        self.notify(help_text, title="Help")

    def action_refresh_results(self):
        """Refresh the results."""
        if self.current_spider:
            self.load_results()

    def action_quit(self):
        """Quit the application."""
        self.exit()


if __name__ == "__main__":
    app = AssessorAICrawlerTUI()
    app.run()
