## file_sorter.py
import os
import re
import json
import shutil
import requests
from pathlib import Path
from PIL import Image

class FileSorter:
    def __init__(self):
        self.ollama_endpoint = "http://localhost:11434/api/generate"
        self.rules = self.load_rules()
        self.categories = self.extract_categories_from_rules()
        self.variable_pattern = re.compile(r"{(\w+)}")
        self.temp_image_path = os.path.join(os.path.expanduser("~"), "temp_analysis.jpg")

    def load_rules(self):
        """Load sorting rules from file"""
        try:
            with open("sorting_rules.txt", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading rules: {e}")
            return []

    def extract_categories_from_rules(self):
        """Extract unique categories from rule conditions"""
        categories = set()
        for rule in self.rules:
            matches = re.findall(r"category == ['\"]([\w-]+)['\"]", rule['condition'])
            categories.update(matches)
        return list(categories)

    def classify_application(self, process_name, window_title):
        """Classify application using AI"""
        prompt = (
            f"Classify this application ({process_name}) with window title '{window_title}' "
            f"into one of these categories: {self.categories}. Respond with only the category name. If no category fits, reply with 'Other'."
        )
        try:
            response = requests.post(
                self.ollama_endpoint,
                json={"model": "mistral", "prompt": prompt, "stream": False},
                timeout=20
            )
            return response.json().get("response", "other").strip().lower()
        except Exception as e:
            print(f"Classification failed: {e}")
            return "other"

    def analyze_image_content(self, image_path):
        """Analyze image content using AI vision"""
        try:
            # Convert to compatible format
            with Image.open(image_path) as img:
                img.convert("RGB").save(self.temp_image_path)
            
            response = requests.post(
                self.ollama_endpoint,
                json={
                    "model": "pixtral",
                    "prompt": f"Categorize this image into one of: {self.categories}. Respond with only the category name.",
                    "images": [self.temp_image_path]
                },
                timeout=15
            )
            return response.json().get("response", "other").strip().lower()
        except Exception as e:
            print(f"Image analysis failed: {e}")
            return "other"
        finally:
            if os.path.exists(self.temp_image_path):
                os.remove(self.temp_image_path)

    def apply_rules(self, filepath, window_info):
        """Main rule processing method"""
        variables = self.extract_variables(filepath, window_info)
        variables['category'] = self.determine_category(filepath, variables)
        
        for rule in sorted(self.rules, key=lambda x: x.get('priority', 1), reverse=True):
            if self.evaluate_rule(rule['condition'], variables):
                self.execute_action(rule['action'], filepath, variables)
                return True
        return False

    def extract_variables(self, filepath, window_info):
        """Dynamically extract variables from multiple sources"""
        base_vars = {
            'filename': os.path.basename(filepath),
            'filetype': os.path.splitext(filepath)[1][1:].lower(),
            'source_app': window_info.get('process_name', 'unknown'),
            'window_title': window_info.get('window_title', ''),
            'source_category': self.classify_application(
                window_info.get('process_name', 'unknown'),
                window_info.get('window_title', '')
            )
        }
        
        # Detect required variables from all rule templates
        required_vars = set()
        for rule in self.rules:
            if 'target_path' in rule.get('action', {}):
                required_vars.update(self.variable_pattern.findall(rule['action']['target_path']))
        
        # AI-powered variable extraction
        enhanced_vars = self.ai_extract_variables(filepath, window_info, required_vars)
        
        return {**base_vars, **enhanced_vars}

    def ai_extract_variables(self, filepath, window_info, required_vars):
        """Use AI to fill missing template variables"""
        extracted = {}
        
        # Analyze window title for missing variables
        if 'game_name' in required_vars:
            extracted['game_name'] = self.analyze_window_title(window_info.get('window_title', '')).lower()
        
        # Analyze image content for missing variables
        if 'content_type' in required_vars:
            extracted['content_type'] = self.analyze_image_content(filepath)
        
        return extracted

    def analyze_window_title(self, title):
        """Extract structured data from window titles"""
        prompt = f"Extract game name from this window title: '{title}'. Respond only with the name."
        try:
            response = requests.post(
                self.ollama_endpoint,
                json={"model": "mistral", "prompt": prompt, "stream": False},
                timeout=10
            )
            return response.json().get("response", "").strip().lower()
        except Exception as e:
            print(f"Title analysis failed: {e}")
            return ""

    def determine_category(self, filepath, variables):
        """Determine final classification category"""
        if variables['source_category'] == 'browser':
            return self.analyze_image_content(filepath)
        return variables['source_category']

    def evaluate_rule(self, condition, variables):
        """Safely evaluate rule conditions"""
        try:
            # Create safe evaluation environment
            safe_env = {
                **variables,
                "__builtins__": None,
                "True": True,
                "False": False,
                "None": None
            }
            return eval(condition, safe_env)
        except Exception as e:
            print(f"Rule evaluation failed: {str(e)}")
            return False

   # In execute_action method
    def execute_action(self, action, filepath, variables):
        """Execute file operation with directory handling"""
        template = action.get('target_path', '')
        
        # Force include filename if missing
        if not any(p in template for p in ['{filename}', '{file_name}']):
            template = os.path.join(template, '{filename}')
        
        # Resolve target path
        target_path = self.resolve_template(template, variables)
        
        if action['type'] == 'move':
            self.move_file(filepath, target_path)
        elif action['type'] == 'copy':
            self.copy_file(filepath, target_path)
        else:
            print(f"Unsupported action type: {action['type']}")


    def resolve_template(self, template, variables):
        """Resolve templates with AI-assisted missing variables"""
        required_vars = set(self.variable_pattern.findall(template))
        
        # Generate missing variables through AI
        for var in required_vars - variables.keys():
            variables[var] = self.ai_generate_variable(var, variables)
        
        # Validate after AI generation
        missing = required_vars - variables.keys()
        if missing:
            raise ValueError(f"Missing variables after AI analysis: {missing}")
        
        return self.variable_pattern.sub(
            lambda m: str(variables[m.group(1)]),
            template
        )

    def ai_generate_variable(self, var_name, context):
        """Generate missing variables using AI"""
        prompt = f"""Based on this file context:
        - Filename: {context.get('filename', '')}
        - Source app: {context.get('source_app', '')}
        - Window title: {context.get('window_title', '')}
        Generate appropriate value for {var_name}. Respond only with the value."""
        
        try:
            response = requests.post(
                self.ollama_endpoint,
                json={"model": "mistral", "prompt": prompt, "stream": False},
                timeout=15
            )
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"AI variable generation failed: {e}")
            return ""


    def move_file(self, src, dest):
        """Move file with conflict resolution"""
        return self._file_operation(src, dest, shutil.move)

    def copy_file(self, src, dest):
        """Copy file with conflict resolution"""
        return self._file_operation(src, dest, shutil.copy)

    def _file_operation(self, src, dest, operation):
        """Handle directory creation and conflict resolution"""
        # Ensure destination is always a file path
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src))

        dest_dir = os.path.dirname(dest)
        filename = os.path.basename(dest)
        
        # Ensure parent directory exists
        os.makedirs(dest_dir, exist_ok=True)
        
        # Conflict resolution
        base, ext = os.path.splitext(filename)
        counter = 1
        new_dest = dest
        
        while os.path.exists(new_dest):
            new_filename = f"{base}_{counter}{ext}"
            new_dest = os.path.join(dest_dir, new_filename)
            counter += 1
        
        # Perform operation
        operation(src, new_dest)
        print(f"Processed {os.path.basename(src)} -> {new_dest}")
        return new_dest



def classify_and_move(filepath, window_info):
    sorter = FileSorter()
    return sorter.apply_rules(filepath, window_info)
